"""Two bounded NLSC CAD operations through the configured Taiwan gateway.

This module is intentionally not a generic proxy.  It can issue only the
CAD_009 ``AddressQueryLand`` and CAD_001 ``CadasMapPosition`` operations, and
it accepts only their documented fields.  The configured gateway, rather than
this backend or a browser, is responsible for reaching NLSC.
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import httpx
from defusedxml import ElementTree as DefusedElementTree

from services.production_config import (
    NLSC_GATEWAY_BASE_URL_ENV,
    NLSC_GATEWAY_CLIENT_TOKEN_ENV,
    load_runtime_configuration,
)


CAD_009_SERVICE_CODE = "CAD_009"
CAD_001_SERVICE_CODE = "CAD_001"

_CAD_009_PATH = "/nlsc/cad/CAD_009"
_CAD_001_PATH = "/nlsc/cad/CAD_001"
_TIMEOUT_SECONDS = 4.0
_MAX_RESPONSE_BYTES = 131_072
_RESPONSE_CHUNK_BYTES = 8_192
_MAX_CAD_009_RESULTS = 8
_NLSC_UPSTREAM_DOMAIN = "nlsc.gov.tw"
_CODE = re.compile(r"[A-Za-z0-9]{1,32}\Z")
_LAND_NUMBER = re.compile(r"[0-9]{8}\Z")
_XML_CONTENT_TYPES = frozenset({"application/xml", "text/xml"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _result(
    service_code: str,
    *,
    status: str,
    retrieved_at: str | None = None,
    observations: list[dict[str, object]] | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "source": "NLSC",
        "service_code": service_code,
        "retrieved_at": retrieved_at,
        "coverage": "unknown" if status == "available" else "unavailable",
        "source_record_id": None,
        "raw_confidence": None,
        "observations": observations or [],
        "error_code": error_code,
    }


def _unavailable(service_code: str, error_code: str) -> dict[str, Any]:
    return _result(service_code, status="unavailable", error_code=error_code)


def _valid_query(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    selected = " ".join(value.split())
    if (
        not selected
        or len(selected) > 512
        or any(ord(character) < 32 for character in value)
    ):
        return None
    return selected


def _valid_code(value: object) -> str | None:
    return value if isinstance(value, str) and _CODE.fullmatch(value) else None


def _is_official_nlsc_origin(value: str) -> bool:
    host = (urlsplit(value).hostname or "").lower()
    return host == _NLSC_UPSTREAM_DOMAIN or host.endswith(f".{_NLSC_UPSTREAM_DOMAIN}")


def _leaf_text(node: object, *, maximum: int) -> str:
    if (
        not hasattr(node, "text")
        or getattr(node, "attrib", None)
        or len(node) != 0  # type: ignore[arg-type]
    ):
        raise ValueError("invalid XML leaf")
    value = getattr(node, "text", None)
    if not isinstance(value, str):
        raise ValueError("missing XML text")
    selected = " ".join(value.split())
    if not selected or len(selected) > maximum or "\x00" in selected:
        raise ValueError("invalid XML text")
    return selected


def _children_by_tag(node: object, expected: frozenset[str]) -> dict[str, object]:
    children = list(node)  # type: ignore[arg-type]
    if len(children) != len(expected) or {child.tag for child in children} != expected:
        raise ValueError("unexpected XML schema")
    if any(child.tag in {prior.tag for prior in children[:index]} for index, child in enumerate(children)):
        raise ValueError("duplicate XML field")
    return {child.tag: child for child in children}


def _parse_location(value: str) -> str:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2 or not all(parts):
        raise ValueError("invalid location")
    try:
        longitude, latitude = (float(part) for part in parts)
    except ValueError:
        raise ValueError("invalid location") from None
    if (
        not math.isfinite(longitude)
        or not math.isfinite(latitude)
        or not -180 <= longitude <= 180
        or not -90 <= latitude <= 90
    ):
        raise ValueError("invalid location")
    # Preserve the two documented XML values without assigning an undocumented
    # CRS or deriving any additional coordinate semantics.
    return f"{parts[0]},{parts[1]}"


def _parse_cad_009(payload: bytes, *, max_results: int) -> list[dict[str, object]]:
    root = DefusedElementTree.fromstring(payload)
    if root.tag != "addressItems" or root.attrib:
        raise ValueError("unexpected XML root")
    items = list(root)
    if not 1 <= len(items) <= max_results or any(item.tag != "addressItem" for item in items):
        raise ValueError("unexpected result cardinality")

    expected = frozenset({"content", "location", "office", "sect", "landno"})
    observations: list[dict[str, object]] = []
    for item in items:
        if item.attrib:
            raise ValueError("unexpected XML attributes")
        fields = _children_by_tag(item, expected)
        office = _leaf_text(fields["office"], maximum=32)
        section = _leaf_text(fields["sect"], maximum=32)
        land_number = _leaf_text(fields["landno"], maximum=8)
        if not _CODE.fullmatch(office) or not _CODE.fullmatch(section) or not _LAND_NUMBER.fullmatch(land_number):
            raise ValueError("invalid cadastral code")
        observations.append(
            {
                "content": _leaf_text(fields["content"], maximum=512),
                "location": _parse_location(_leaf_text(fields["location"], maximum=96)),
                "office_code": office,
                "section_code": section,
                "land_number": land_number,
            }
        )
    return observations


def _finite_number(node: object) -> float:
    value = _leaf_text(node, maximum=64)
    try:
        selected = float(value)
    except ValueError:
        raise ValueError("invalid coordinate") from None
    if not math.isfinite(selected):
        raise ValueError("invalid coordinate")
    return 0.0 if selected == 0 else selected


def _parse_cad_001(payload: bytes, *, crs: str) -> list[dict[str, object]]:
    root = DefusedElementTree.fromstring(payload)
    if root.tag != "cadsPositionItem" or root.attrib:
        raise ValueError("unexpected XML root")
    fields = _children_by_tag(
        root,
        frozenset({"repX", "repY", "ldX", "ldY", "rtX", "rtY"}),
    )
    rep_x = _finite_number(fields["repX"])
    rep_y = _finite_number(fields["repY"])
    lower_x = _finite_number(fields["ldX"])
    lower_y = _finite_number(fields["ldY"])
    upper_x = _finite_number(fields["rtX"])
    upper_y = _finite_number(fields["rtY"])
    if not (lower_x <= rep_x <= upper_x and lower_y <= rep_y <= upper_y):
        raise ValueError("representative point outside bounds")
    if crs == "4326" and not (
        -180 <= lower_x <= upper_x <= 180
        and -90 <= lower_y <= upper_y <= 90
    ):
        raise ValueError("invalid EPSG:4326 coordinates")
    crs_name = f"EPSG:{crs}"
    return [
        {
            "representative_point": {"x": rep_x, "y": rep_y, "crs": crs_name},
            "bounds": {
                "lower_left": {"x": lower_x, "y": lower_y},
                "upper_right": {"x": upper_x, "y": upper_y},
                "crs": crs_name,
            },
        }
    ]


class NlscCadGatewayAdapter:
    """Backend-only client for exactly CAD_009 and CAD_001."""

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
        if self.configuration_status == "configured" and _is_official_nlsc_origin(self._base_url):
            self.configuration_status = "malformed"
        elif self.configuration_status == "configured" and runtime.production_like:
            # This slice is deliberately non-production.  Until the exact
            # controlled Taiwan gateway origin is approved and allowlisted,
            # Render/other production-like runtimes must have zero CAD egress.
            self.configuration_status = "production_disabled"
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

    def cad_009_address_query_land(
        self,
        query: str,
        max_results: int = 1,
    ) -> dict[str, Any]:
        """Run only NLSC CAD_009 through the configured Taiwan gateway."""

        if not self.available:
            return _unavailable(CAD_009_SERVICE_CODE, self._configuration_error())
        selected_query = _valid_query(query)
        if (
            selected_query is None
            or not isinstance(max_results, int)
            or isinstance(max_results, bool)
            or not 1 <= max_results <= _MAX_CAD_009_RESULTS
        ):
            return _unavailable(CAD_009_SERVICE_CODE, "invalid_input")
        return self._post_xml(
            service_code=CAD_009_SERVICE_CODE,
            path=_CAD_009_PATH,
            body={"query": selected_query, "max_results": max_results},
            parser=lambda payload: _parse_cad_009(payload, max_results=max_results),
        )

    def cad_001_cadas_map_position(
        self,
        county_code: str,
        section_code: str,
        land_number: str,
        crs: str = "4326",
    ) -> dict[str, Any]:
        """Run only NLSC CAD_001 through the configured Taiwan gateway."""

        if not self.available:
            return _unavailable(CAD_001_SERVICE_CODE, self._configuration_error())
        county = _valid_code(county_code)
        section = _valid_code(section_code)
        if (
            county is None
            or section is None
            or not isinstance(land_number, str)
            or not _LAND_NUMBER.fullmatch(land_number)
            or crs not in {"4326", "3826"}
        ):
            return _unavailable(CAD_001_SERVICE_CODE, "invalid_input")
        return self._post_xml(
            service_code=CAD_001_SERVICE_CODE,
            path=_CAD_001_PATH,
            body={
                "county_code": county,
                "section_code": section,
                "land_number": land_number,
                "crs": crs,
            },
            parser=lambda payload: _parse_cad_001(payload, crs=crs),
        )

    def _post_xml(
        self,
        *,
        service_code: str,
        path: str,
        body: Mapping[str, object],
        parser: Callable[[bytes], list[dict[str, object]]],
    ) -> dict[str, Any]:
        try:
            with self._get_client().stream(
                "POST",
                self._base_url.rstrip("/") + path,
                json=dict(body),
                headers={
                    "Authorization": f"Bearer {self._client_token}",
                    "Accept": "application/xml",
                    "Accept-Encoding": "identity",
                },
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as response:
                if response.is_redirect:
                    return _unavailable(service_code, "redirect_rejected")
                if not 200 <= response.status_code < 300:
                    return _unavailable(service_code, "upstream_rejected")
                media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if media_type not in _XML_CONTENT_TYPES:
                    return _unavailable(service_code, "invalid_response")
                content_encoding = response.headers.get("Content-Encoding", "").strip().lower()
                if content_encoding not in {"", "identity"}:
                    return _unavailable(service_code, "invalid_response")
                declared_length = response.headers.get("Content-Length")
                if declared_length is not None:
                    try:
                        length = int(declared_length)
                        if length < 0:
                            return _unavailable(service_code, "invalid_response")
                        if length > _MAX_RESPONSE_BYTES:
                            return _unavailable(service_code, "response_too_large")
                    except ValueError:
                        return _unavailable(service_code, "invalid_response")
                payload = bytearray()
                for chunk in response.iter_bytes(chunk_size=_RESPONSE_CHUNK_BYTES):
                    if len(chunk) > _MAX_RESPONSE_BYTES - len(payload):
                        return _unavailable(service_code, "response_too_large")
                    payload.extend(chunk)

            observations = parser(bytes(payload))
            observed_at = self._clock()
            if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
                return _unavailable(service_code, "invalid_response")
            retrieved_at = observed_at.astimezone(timezone.utc).isoformat()
            return _result(
                service_code,
                status="available",
                retrieved_at=retrieved_at,
                observations=observations,
            )
        except httpx.TimeoutException:
            return _unavailable(service_code, "timeout")
        except httpx.HTTPError:
            return _unavailable(service_code, "transport_error")
        except Exception:
            # XML/parser errors and unexpected transport details may contain raw
            # payloads or headers.  Never retain or log those details.
            return _unavailable(service_code, "invalid_response")

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

    def __enter__(self) -> "NlscCadGatewayAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
