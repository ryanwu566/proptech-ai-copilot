"""TEST-only NLSC TILE_001 reference-imagery observation seam.

The adapter has one operation and one transport destination.  It accepts only
bounded EPSG:3857 tile coordinates, calls an exact-match allowlisted backend
gateway, and validates a bounded PNG response.  It is never available in a
production-like runtime and never calls an NLSC origin directly.
"""

from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping
from urllib.parse import urlsplit

import httpx

from services.production_config import (
    NLSC_GATEWAY_BASE_URL_ENV,
    NLSC_GATEWAY_CLIENT_TOKEN_ENV,
    load_runtime_configuration,
)


TILE_001_SERVICE_CODE = "TILE_001"
TILE_001_LAYER = "DMAPS"
TILE_001_CRS = "EPSG:3857"
TILE_001_CONTENT_TYPE = "image/png"
TILE_001_MAX_LEVEL = 19
TILE_001_TEST_GATEWAY_ORIGINS_ENV = "NLSC_TILE001_TEST_GATEWAY_ORIGINS"

_TILE_PATH = "/nlsc/tiles/TILE_001"
_TIMEOUT_SECONDS = 4.0
_MAX_RESPONSE_BYTES = 524_288
_RESPONSE_CHUNK_BYTES = 8_192
_MAX_DECOMPRESSED_BYTES = 1_048_576
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_ATTRIBUTION = "內政部國土測繪中心－國土測繪圖資服務雲"
_NOTICE = (
    "Reference imagery only. Blank or nonblank imagery does not establish "
    "parcel existence, parcel absence, a legal boundary, or current cadastral truth."
)
_NLSC_DOMAIN = "nlsc.gov.tw"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class NlscTileObservation:
    """Documented TILE_001 metadata; image bytes live outside this object."""

    source: str
    service_code: str
    retrieved_at: str
    crs: str
    layer: str
    z: int
    x: int
    y: int
    content_type: str
    attribution: str
    notice: str
    coverage: str


@dataclass(frozen=True)
class NlscTilePolicy:
    """Resource and semantic policy carried beside every adapter result."""

    cache_control: str = "no-store"
    store: bool = False
    semantic_scope: str = "reference_imagery_only"


@dataclass(frozen=True)
class NlscTileResult:
    """Bounded binary result plus its normalized observation and policy."""

    status: str
    observation: NlscTileObservation | None
    content: bytes | None = field(repr=False)
    policy: NlscTilePolicy
    error_code: str | None


_NO_STORE_POLICY = NlscTilePolicy()


def _unavailable(error_code: str) -> NlscTileResult:
    return NlscTileResult(
        status="unavailable",
        observation=None,
        content=None,
        policy=_NO_STORE_POLICY,
        error_code=error_code,
    )


def _official_nlsc_origin(value: str) -> bool:
    host = (urlsplit(value).hostname or "").lower().rstrip(".")
    return host == _NLSC_DOMAIN or host.endswith(f".{_NLSC_DOMAIN}")


def _strict_https_origin(value: str) -> bool:
    if not value or value != value.strip() or "*" in value or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https"
        and parsed.netloc
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
        and port != 0
    )


def _approved_origins(raw_value: str) -> frozenset[str]:
    if not raw_value:
        return frozenset()
    origins = tuple(item.strip() for item in raw_value.split(","))
    if (
        not origins
        or any(not item for item in origins)
        or any(not _strict_https_origin(item) for item in origins)
        or any(_official_nlsc_origin(item) for item in origins)
    ):
        return frozenset()
    return frozenset(origins)


def _valid_tile_coordinate(z: object, x: object, y: object) -> bool:
    if any(type(value) is not int for value in (z, x, y)):
        return False
    if not 0 <= z <= TILE_001_MAX_LEVEL:
        return False
    limit = 1 << z
    return 0 <= x < limit and 0 <= y < limit


def _png_scanline_size(
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
) -> int | None:
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    allowed_depths = {
        0: {1, 2, 4, 8, 16},
        2: {8, 16},
        3: {1, 2, 4, 8},
        4: {8, 16},
        6: {8, 16},
    }
    if channels is None or bit_depth not in allowed_depths[color_type]:
        return None
    row_bytes = (width * channels * bit_depth + 7) // 8
    size = height * (row_bytes + 1)
    return size if size <= _MAX_DECOMPRESSED_BYTES else None


def _paeth_predictor(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def _valid_indexed_scanlines(
    decoded: bytes,
    *,
    width: int,
    height: int,
    bit_depth: int,
    palette_entries: int,
) -> bool:
    """Unfilter bounded indexed rows and reject samples outside PLTE."""

    row_bytes = (width * bit_depth + 7) // 8
    previous = bytes(row_bytes)
    offset = 0
    sample_mask = (1 << bit_depth) - 1
    for _ in range(height):
        filter_type = decoded[offset]
        filtered = decoded[offset + 1 : offset + row_bytes + 1]
        reconstructed = bytearray(row_bytes)
        for index, value in enumerate(filtered):
            left = reconstructed[index - 1] if index else 0
            above = previous[index]
            upper_left = previous[index - 1] if index else 0
            predictor = 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = _paeth_predictor(left, above, upper_left)
            reconstructed[index] = (value + predictor) & 0xFF

        remaining = width
        for value in reconstructed:
            for shift in range(8 - bit_depth, -1, -bit_depth):
                if remaining == 0:
                    break
                if ((value >> shift) & sample_mask) >= palette_entries:
                    return False
                remaining -= 1
        previous = bytes(reconstructed)
        offset += row_bytes + 1
    return True


def _valid_png(payload: bytes) -> bool:
    """Validate PNG signature, chunk framing/CRC, IHDR, IDAT, and zlib data."""

    if not payload.startswith(_PNG_SIGNATURE):
        return False
    offset = len(_PNG_SIGNATURE)
    ihdr: tuple[int, int, int, int] | None = None
    idat_parts: list[bytes] = []
    seen_plte = False
    palette_entries: int | None = None
    seen_idat = False
    seen_iend = False

    while offset < len(payload):
        if len(payload) - offset < 12:
            return False
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        chunk_end = data_end + 4
        if (
            length > _MAX_RESPONSE_BYTES
            or chunk_end > len(payload)
            or len(chunk_type) != 4
            or any(not (65 <= byte <= 90 or 97 <= byte <= 122) for byte in chunk_type)
            or chunk_type[2] & 0x20
        ):
            return False
        chunk_data = payload[data_start:data_end]
        expected_crc = struct.unpack(">I", payload[data_end:chunk_end])[0]
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
            return False
        offset = chunk_end

        if ihdr is None and chunk_type != b"IHDR":
            return False
        if chunk_type == b"IHDR":
            if ihdr is not None or length != 13:
                return False
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if (
                width == 0
                or height == 0
                or width > 4096
                or height > 4096
                or compression != 0
                or filtering != 0
                or interlace != 0
                or _png_scanline_size(
                    width=width,
                    height=height,
                    bit_depth=bit_depth,
                    color_type=color_type,
                )
                is None
            ):
                return False
            ihdr = (width, height, bit_depth, color_type)
        elif chunk_type == b"PLTE":
            assert ihdr is not None
            bit_depth, color_type = ihdr[2], ihdr[3]
            selected_palette_entries = length // 3
            if (
                seen_plte
                or seen_idat
                or length == 0
                or length % 3
                or length > 768
                or color_type in {0, 4}
                or (color_type == 3 and selected_palette_entries > 1 << bit_depth)
            ):
                return False
            seen_plte = True
            palette_entries = selected_palette_entries
        elif chunk_type == b"IDAT":
            if length == 0:
                return False
            seen_idat = True
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0 or not seen_idat or offset != len(payload):
                return False
            seen_iend = True
            break
        else:
            # This bounded seam supports the core image chunks only. Reject
            # ancillary chunks rather than partially validating their varied
            # length, multiplicity, and ordering rules.
            return False

    if not seen_iend or ihdr is None:
        return False
    width, height, bit_depth, color_type = ihdr
    if color_type == 3 and not seen_plte:
        return False
    expected_size = _png_scanline_size(
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
    )
    if expected_size is None:
        return False
    try:
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(b"".join(idat_parts), expected_size + 1)
        remaining = expected_size + 1 - len(decoded)
        if remaining > 0:
            decoded += decoder.flush(remaining)
    except zlib.error:
        return False
    if not (
        decoder.eof
        and not decoder.unused_data
        and not decoder.unconsumed_tail
        and len(decoded) == expected_size
    ):
        return False
    row_size = expected_size // height
    if not all(decoded[offset] <= 4 for offset in range(0, expected_size, row_size)):
        return False
    if color_type == 3:
        assert palette_entries is not None
        return _valid_indexed_scanlines(
            decoded,
            width=width,
            height=height,
            bit_depth=bit_depth,
            palette_entries=palette_entries,
        )
    return True


class NlscTileGatewayAdapter:
    """Fetch exactly one TILE_001 DMAPS PNG from an approved TEST gateway."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        environ: Mapping[str, str] | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        values = dict(environ if environ is not None else os.environ)
        self._base_url = values.get(NLSC_GATEWAY_BASE_URL_ENV, "")
        self._client_token = values.get(NLSC_GATEWAY_CLIENT_TOKEN_ENV, "")
        runtime = load_runtime_configuration(values)
        self.configuration_status = runtime.nlsc_gateway_status
        if runtime.production_like:
            self.configuration_status = "production_disabled"
        elif self.configuration_status == "configured" and _official_nlsc_origin(
            self._base_url
        ):
            self.configuration_status = "direct_origin_rejected"
        elif self.configuration_status == "configured":
            allowlist = _approved_origins(
                values.get(TILE_001_TEST_GATEWAY_ORIGINS_ENV, "")
            )
            if self._base_url not in allowlist:
                self.configuration_status = "unapproved_origin"
        self._client = client
        self._owns_client = client is None
        self._clock = clock

    @property
    def available(self) -> bool:
        return self.configuration_status == "configured"

    def _configuration_error(self) -> str:
        return (
            "production_disabled"
            if self.configuration_status == "production_disabled"
            else "not_configured"
        )

    def fetch_tile(self, *, z: object, x: object, y: object) -> NlscTileResult:
        """Return one validated reference-image tile or a closed failure."""

        if not self.available:
            return _unavailable(self._configuration_error())
        if not _valid_tile_coordinate(z, x, y):
            return _unavailable("invalid_input")
        assert isinstance(z, int) and isinstance(x, int) and isinstance(y, int)
        url = f"{self._base_url.rstrip('/')}{_TILE_PATH}/{z}/{y}/{x}"
        try:
            with self._get_client().stream(
                "GET",
                url,
                headers={
                    "Authorization": f"Bearer {self._client_token}",
                    "Accept": TILE_001_CONTENT_TYPE,
                    "Accept-Encoding": "identity",
                    "Cache-Control": "no-store",
                },
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as response:
                if response.is_redirect:
                    return _unavailable("redirect_rejected")
                if not 200 <= response.status_code < 300:
                    return _unavailable("upstream_rejected")
                media_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if media_type != TILE_001_CONTENT_TYPE:
                    return _unavailable("invalid_response")
                content_encoding = response.headers.get("Content-Encoding", "").strip().lower()
                if content_encoding not in {"", "identity"}:
                    return _unavailable("invalid_response")
                declared_length = response.headers.get("Content-Length")
                expected_length: int | None = None
                if declared_length is not None:
                    try:
                        expected_length = int(declared_length)
                    except ValueError:
                        return _unavailable("invalid_response")
                    if expected_length < 0:
                        return _unavailable("invalid_response")
                    if expected_length > _MAX_RESPONSE_BYTES:
                        return _unavailable("response_too_large")
                payload = bytearray()
                for chunk in response.iter_bytes(chunk_size=_RESPONSE_CHUNK_BYTES):
                    if len(chunk) > _MAX_RESPONSE_BYTES - len(payload):
                        return _unavailable("response_too_large")
                    payload.extend(chunk)
                if expected_length is not None and len(payload) != expected_length:
                    return _unavailable("invalid_response")

            content = bytes(payload)
            credential = self._client_token.encode("ascii")
            if credential in content:
                return _unavailable("invalid_response")
            if not _valid_png(content):
                return _unavailable("invalid_response")
            observed_at = self._clock()
            if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
                return _unavailable("invalid_response")
            observation = NlscTileObservation(
                source="NLSC",
                service_code=TILE_001_SERVICE_CODE,
                retrieved_at=observed_at.astimezone(timezone.utc).isoformat(),
                crs=TILE_001_CRS,
                layer=TILE_001_LAYER,
                z=z,
                x=x,
                y=y,
                content_type=TILE_001_CONTENT_TYPE,
                attribution=_ATTRIBUTION,
                notice=_NOTICE,
                coverage="unknown",
            )
            return NlscTileResult(
                status="available",
                observation=observation,
                content=content,
                policy=_NO_STORE_POLICY,
                error_code=None,
            )
        except httpx.TimeoutException:
            return _unavailable("timeout")
        except httpx.HTTPError:
            return _unavailable("transport_error")
        except Exception:
            # Transport details, headers, and response bodies can contain the
            # backend credential.  Never surface or log exception text.
            return _unavailable("invalid_response")

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client()
        return self._client

    def close(self) -> None:
        if not self._owns_client:
            return
        client, self._client = self._client, None
        if client is not None:
            client.close()

    def __enter__(self) -> "NlscTileGatewayAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
