"""Server-only, bounded Google Earth Engine satellite adapter."""

from __future__ import annotations

from datetime import date
import math
import threading
from typing import Any, Callable
from urllib.parse import parse_qsl, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from services.satellite_reference import (
    AOI_RADIUS_M,
    CLOUD_FILTER_PERCENT,
    DATASET_ID,
    EXTERNAL_TIMEOUT_SECONDS,
    MAX_PROVIDER_IMAGE_BYTES,
    WINDOW_DAYS,
    EarthEngineCredentialUnavailable,
    EarthEngineImageGenerationError,
    EarthEngineInitializationUnavailable,
    EarthEngineProviderError,
    SatelliteAdapterResult,
    SatelliteQuery,
)


_RGB_BANDS = ("B4", "B3", "B2")
_EXCLUDED_SCL_CLASSES = (3, 8, 9, 10, 11)
_DIMENSIONS = (512, 512)
_FORMAT = "jpg"
_THUMBNAIL_HOST = "earthengine.googleapis.com"
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "authorization",
    "credential",
    "key",
    "private_key",
    "refresh_token",
    "signature",
    "x-goog-credential",
    "x-goog-signature",
}


class EarthEngineSatelliteAdapter:
    """Execute one fixed Sentinel-2 thumbnail query using ADC."""

    def __init__(
        self,
        *,
        project: str,
        ee_module: Any | None = None,
        auth_default: Callable[[], tuple[Any, str | None]] | None = None,
        auth_request_factory: Callable[[], Any] | None = None,
        download_image: Callable[[str, int, float], bytes] | None = None,
    ) -> None:
        self._project = project.strip()
        self._ee_module = ee_module
        self._auth_default = auth_default
        self._auth_request_factory = auth_request_factory
        self._download_image = download_image or _download_thumbnail
        self._initialize_lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Earth Engine once for this adapter without module-import side effects."""

        if self._initialized:
            return
        with self._initialize_lock:
            if self._initialized:
                return
            if not self._project:
                raise EarthEngineCredentialUnavailable("Earth Engine project is unavailable")

            try:
                ee = self._ee_module
                if ee is None:
                    import ee as imported_ee

                    ee = imported_ee
                auth_default = self._auth_default
                if auth_default is None:
                    import google.auth

                    auth_default = google.auth.default
                credentials, _ = auth_default()
                if hasattr(credentials, "valid") and not credentials.valid:
                    request_factory = self._auth_request_factory
                    if request_factory is None:
                        from google.auth.transport.requests import Request

                        request_factory = Request
                    credentials.refresh(request_factory())
            except Exception as exc:
                raise EarthEngineCredentialUnavailable(
                    "Application Default Credentials are unavailable"
                ) from exc

            try:
                ee.data.setMaxRetries(0)
                ee.Initialize(credentials=credentials, project=self._project)
            except Exception as exc:
                raise EarthEngineInitializationUnavailable(
                    "Earth Engine initialization is unavailable"
                ) from exc

            self._ee_module = ee
            self._initialized = True

    def fetch(self, query: SatelliteQuery) -> SatelliteAdapterResult:
        _validate_query(query)
        self.initialize()
        return self.fetch_initialized(query)

    def fetch_initialized(self, query: SatelliteQuery) -> SatelliteAdapterResult:
        """Execute the fixed thumbnail pipeline after successful initialization."""

        _validate_query(query)
        if not self._initialized or self._ee_module is None:
            raise EarthEngineInitializationUnavailable("Earth Engine initialization is unavailable")
        ee = self._ee_module

        try:
            region = ee.Geometry.Point([query.longitude, query.latitude]).buffer(query.aoi_radius_m)
            collection = (
                ee.ImageCollection(query.dataset)
                .filterBounds(region)
                .filterDate(query.window_start, query.window_end)
                .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", query.cloud_filter_percent))
                .map(_scl_mask)
            )
        except Exception as exc:
            raise EarthEngineProviderError("Earth Engine query failed") from exc

        try:
            image = collection.median().select(list(query.rgb_bands)).visualize(min=0, max=3000)
            provider_url = image.getThumbURL(
                {
                    "region": region,
                    "dimensions": f"{query.dimensions[0]}x{query.dimensions[1]}",
                    "format": query.image_format,
                }
            )
            if not isinstance(provider_url, str) or not _safe_thumbnail_url(provider_url):
                raise EarthEngineImageGenerationError("Earth Engine thumbnail reference was rejected")
            image_bytes = self._download_image(
                provider_url,
                MAX_PROVIDER_IMAGE_BYTES,
                EXTERNAL_TIMEOUT_SECONDS,
            )
            if (
                not image_bytes
                or len(image_bytes) > MAX_PROVIDER_IMAGE_BYTES
                or not image_bytes.startswith(b"\xff\xd8")
                or not image_bytes.endswith(b"\xff\xd9")
            ):
                raise EarthEngineImageGenerationError("Earth Engine thumbnail payload was rejected")
            dimensions = _jpeg_dimensions(image_bytes)
            if (
                dimensions is None
                or dimensions[0] <= 0
                or dimensions[1] <= 0
                or dimensions[0] > _DIMENSIONS[0]
                or dimensions[1] > _DIMENSIONS[1]
            ):
                raise EarthEngineImageGenerationError("Earth Engine thumbnail dimensions were rejected")
        except EarthEngineImageGenerationError:
            raise
        except Exception as exc:
            raise EarthEngineImageGenerationError("Earth Engine thumbnail generation failed") from exc

        return SatelliteAdapterResult(image_bytes=image_bytes)


def _scl_mask(image: Any) -> Any:
    scl = image.select("SCL")
    mask = scl.neq(_EXCLUDED_SCL_CLASSES[0])
    for scl_class in _EXCLUDED_SCL_CLASSES[1:]:
        mask = mask.And(scl.neq(scl_class))
    return image.updateMask(mask)


def _validate_query(query: SatelliteQuery) -> None:
    try:
        window_days = (date.fromisoformat(query.window_end) - date.fromisoformat(query.window_start)).days
    except (TypeError, ValueError) as exc:
        raise EarthEngineProviderError("Satellite query is outside the fixed contract") from exc
    valid = (
        math.isfinite(query.latitude)
        and -90 <= query.latitude <= 90
        and math.isfinite(query.longitude)
        and -180 <= query.longitude <= 180
        and query.dataset == DATASET_ID
        and window_days == WINDOW_DAYS
        and query.aoi_radius_m == AOI_RADIUS_M
        and query.cloud_filter_percent == CLOUD_FILTER_PERCENT
        and query.rgb_bands == _RGB_BANDS
        and query.excluded_scl_classes == _EXCLUDED_SCL_CLASSES
        and query.dimensions == _DIMENSIONS
        and query.image_format == _FORMAT
    )
    if not valid:
        raise EarthEngineProviderError("Satellite query is outside the fixed contract")


def _safe_thumbnail_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != _THUMBNAIL_HOST or parsed.username or parsed.password:
        return False
    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    return not query_keys.intersection(_SENSITIVE_QUERY_KEYS)


def _jpeg_dimensions(payload: bytes) -> tuple[int, int] | None:
    """Read width and height from a JPEG SOF marker without decoding pixels."""

    if len(payload) < 4 or not payload.startswith(b"\xff\xd8"):
        return None
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    offset = 2
    while offset < len(payload):
        if payload[offset] != 0xFF:
            return None
        while offset < len(payload) and payload[offset] == 0xFF:
            offset += 1
        if offset >= len(payload):
            return None
        marker = payload[offset]
        offset += 1
        if marker in {0x01, *range(0xD0, 0xDA)}:
            if marker == 0xD9:
                break
            continue
        if offset + 2 > len(payload):
            return None
        segment_length = int.from_bytes(payload[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(payload):
            return None
        if marker in sof_markers:
            if segment_length < 7:
                return None
            height = int.from_bytes(payload[offset + 3 : offset + 5], "big")
            width = int.from_bytes(payload[offset + 5 : offset + 7], "big")
            return width, height
        if marker == 0xDA:
            break
        offset += segment_length
    return None


def _download_thumbnail(url: str, max_bytes: int, timeout_seconds: float) -> bytes:
    class _RejectRedirects(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        request = Request(url, method="GET")
        with build_opener(_RejectRedirects()).open(request, timeout=timeout_seconds) as response:
            if response.headers.get_content_type().lower() != "image/jpeg":
                raise EarthEngineImageGenerationError("Earth Engine thumbnail media type was rejected")
            declared_size = response.headers.get("content-length")
            if declared_size and int(declared_size) > max_bytes:
                raise EarthEngineImageGenerationError("Earth Engine thumbnail exceeded the byte limit")
            collected = response.read(max_bytes + 1)
            if len(collected) > max_bytes:
                raise EarthEngineImageGenerationError("Earth Engine thumbnail exceeded the byte limit")
    except EarthEngineImageGenerationError:
        raise
    except Exception as exc:
        raise EarthEngineImageGenerationError("Earth Engine thumbnail download failed") from exc
    return collected
