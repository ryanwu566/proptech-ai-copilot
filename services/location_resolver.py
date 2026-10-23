"""Trusted address resolution with conservative provider fallback."""

from __future__ import annotations

import contextvars
import json
import logging
import math
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

from services.provider_cost_metrics import PROVIDER_COST_METRICS
from services.provider_request_cache import BoundedRequestCache
from services.anti_abuse import AbuseRejected, provider_operation
from services.trusted_address_structure import addresses_agree, address_parts, normalize_address


LocationResolveStatus = Literal["resolved", "unresolved", "unavailable"]
LocationResolveSource = Literal["tgos", "google", "none"]
LocationResolveConfidence = Literal["high", "unknown"]

SAFE_RESPONSE_KEYS = {
    "status",
    "source",
    "formatted_address",
    "latitude",
    "longitude",
    "confidence",
    "message",
    "county",
    "district",
}

TGOS_URL = "https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr"
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# The browser abandons a lookup at 10 s; keep ~2 s for Vercel -> Cloud Run
# transport, admission and serialization so the server answers first.
RESOLVE_BUDGET_SECONDS = 8.0
# A strict TGOS fallback runs only when a meaningful attempt still fits.
TGOS_MIN_REMAINING_SECONDS = 2.0
# Below this, a provider call is not started (no physical call, no spend).
PROVIDER_MIN_REMAINING_SECONDS = 0.5
CONNECT_TIMEOUT_CAP_SECONDS = 1.5
_DEADLINE: contextvars.ContextVar[float | None] = contextvars.ContextVar("location_resolve_deadline", default=None)
_PROCESS_STARTED = time.monotonic()
_FIRST_RESOLVE_LOCK = threading.Lock()
_FIRST_RESOLVE_SEEN = False

# Bounded categories only: never addresses, coordinates, credentials or payloads.
# Own stdout handler: uvicorn does not configure INFO for application loggers.
_EVENT_LOGGER = logging.getLogger("proptech.location_resolve")
if not _EVENT_LOGGER.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _EVENT_LOGGER.addHandler(_handler)
    _EVENT_LOGGER.setLevel(logging.INFO)
    _EVENT_LOGGER.propagate = False


@dataclass(frozen=True)
class LocationResolveResult:
    status: LocationResolveStatus
    source: LocationResolveSource = "none"
    formatted_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: LocationResolveConfidence = "unknown"
    message: str = "定位服務暫時無法完成查詢，請稍後再試。"
    county: str | None = None
    district: str | None = None
    # Internal proof only; never included in the API or accepted-resolution cache.
    acceptance_validated: bool = False
    # Internal bounded outcome category for observability; never in the API.
    reason: str = ""

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "formatted_address": self.formatted_address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "confidence": self.confidence,
            "message": self.message,
            "county": self.county,
            "district": self.district,
        }


class AddressProvider(Protocol):
    @property
    def configured(self) -> bool:
        """Return whether this provider has backend-only credentials."""

    def resolve(self, address: str) -> LocationResolveResult:
        """Resolve an address without exposing provider raw payloads."""


def _is_valid_coordinate(latitude: Any, longitude: Any) -> bool:
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        return False
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    return math.isfinite(lat) and math.isfinite(lon) and 21.7 <= lat <= 26.5 and 118 <= lon <= 122.2


COUNTY_SUFFIXES = ("市", "縣")
DISTRICT_SUFFIXES = ("區", "鄉", "鎮", "市")


def _administrative_name(value: Any, suffixes: tuple[str, ...]) -> str | None:
    """Keep only a bounded county/district name already present in the geocoder response."""
    if not isinstance(value, str):
        return None
    name = value.strip().replace("台", "臺")
    if not name or len(name) > 20 or not name.endswith(suffixes):
        return None
    return name


def _google_administrative_area(result: dict[str, Any]) -> tuple[str | None, str | None]:
    """Taiwan: level 1 is the county/city; level 2 (else level 3) is the district. Villages (里) are not districts."""
    county = level_2 = level_3 = None
    components = result.get("address_components")
    for component in components if isinstance(components, list) else []:
        if not isinstance(component, dict) or not isinstance(component.get("types"), list):
            continue
        types = component["types"]
        if "administrative_area_level_1" in types:
            county = component.get("long_name")
        elif "administrative_area_level_2" in types:
            level_2 = component.get("long_name")
        elif "administrative_area_level_3" in types:
            level_3 = component.get("long_name")
    return _administrative_name(county, COUNTY_SUFFIXES), _administrative_name(level_2, DISTRICT_SUFFIXES) or _administrative_name(level_3, DISTRICT_SUFFIXES)


def _resolved(source: LocationResolveSource, formatted_address: str | None, latitude: Any, longitude: Any, county: Any = None, district: Any = None, *, address: str, precision_accepted: bool) -> LocationResolveResult:
    if source not in {"google", "tgos"} or not precision_accepted:
        return _unresolved("precision_rejected")
    if not _is_valid_coordinate(latitude, longitude):
        return _unresolved("invalid_coordinate")
    if not addresses_agree(address, formatted_address, county=county, district=district):
        return _unresolved("structural_mismatch")
    lat = float(latitude)
    lon = float(longitude)
    provider_label = "TGOS" if source == "tgos" else "Google"
    return LocationResolveResult(
        status="resolved",
        source=source,
        formatted_address=formatted_address or None,
        latitude=lat,
        longitude=lon,
        confidence="high",
        message=f"已取得可信位置（{provider_label}）。",
        county=_administrative_name(county, COUNTY_SUFFIXES),
        district=_administrative_name(district, DISTRICT_SUFFIXES),
        acceptance_validated=True,
        reason="accepted",
    )


def _unresolved(reason: str = "no_match") -> LocationResolveResult:
    return LocationResolveResult(
        status="unresolved",
        source="none",
        message="找不到可信位置，請確認縣市、區域與門牌是否完整。",
        reason=reason,
    )


def _unavailable(reason: str = "provider_error") -> LocationResolveResult:
    return LocationResolveResult(
        status="unavailable",
        source="none",
        message="定位服務暫時無法完成查詢，請稍後再試。",
        reason=reason,
    )


def _provider_timeout(cap_seconds: float) -> httpx.Timeout | None:
    """Fit one provider call inside its own cap and the remaining resolve budget.

    Connect plus read stay within the allowance; None means do not start a call.
    """
    deadline = _DEADLINE.get()
    remaining = cap_seconds if deadline is None else min(cap_seconds, deadline - time.monotonic())
    if remaining < PROVIDER_MIN_REMAINING_SECONDS:
        return None
    connect = min(CONNECT_TIMEOUT_CAP_SECONDS, remaining / 3)
    return httpx.Timeout(remaining - connect, connect=connect)


class TgosAddressProvider:
    """Backend-only TGOS resolver used by the trusted location endpoint."""

    def __init__(self, app_id: str | None = None, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self.app_id = (app_id if app_id is not None else os.getenv("TGOS_APP_ID", "")).strip()
        self.api_key = (api_key if api_key is not None else os.getenv("TGOS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.api_key)

    def resolve(self, address: str) -> LocationResolveResult:
        if not self.configured:
            return _unavailable("not_configured")
        return self._resolve_provider(address)

    @provider_operation("tgos")
    def _resolve_provider(self, address: str) -> LocationResolveResult:
        timeout = _provider_timeout(self.timeout_seconds)
        if timeout is None:
            return _unavailable("deadline_exhausted")
        try:
            PROVIDER_COST_METRICS.record("tgos", "physical_calls")
            response = httpx.get(
                TGOS_URL,
                params={
                    "oAPPId": self.app_id,
                    "oAPIKey": self.api_key,
                    "oAddress": address,
                    "oSRS": "EPSG:4326",
                    "oFuzzyType": "0",
                    "oResultDataType": "JSON",
                    "oFuzzyBuffer": "0",
                    "oIsOnlyFullMatch": "true",
                    "oReturnMaxCount": "1",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException:
            return _unavailable("timeout")
        except (httpx.HTTPError, ValueError):
            return _unavailable("http_error")

        try:
            items = payload.get("AddressList") or payload.get("addressList") or []
        except AttributeError:
            return _unavailable("malformed_response")
        if not isinstance(items, list):
            return _unavailable("malformed_response")
        if not items:
            return _unresolved("zero_results")
        item = items[0]
        if not isinstance(item, dict):
            return _unavailable("malformed_response")

        longitude = item.get("X") or item.get("x") or item.get("longitude")
        latitude = item.get("Y") or item.get("y") or item.get("latitude")
        if not _is_valid_coordinate(latitude, longitude):
            return _unavailable("invalid_coordinate")
        formatted_address = item.get("FULL_ADDR") or item.get("fullAddress") or item.get("Address")
        # The strict request is mandatory. If the response supplies match metadata,
        # it must agree; never accept a fuzzy response even with plausible text.
        info = payload.get("Info", [])
        if not isinstance(info, list) or any(not isinstance(row, dict) or row.get("OutMatchType", "完全比對") != "完全比對" for row in info):
            return _unresolved("fuzzy_rejected")
        actual = address_parts(formatted_address)
        for field, key, suffix in (("ROAD", "road", ""), ("SECTION", "section", "段"), ("LANE", "lane", "巷"), ("ALLEY", "alley", "弄"), ("NUMBER", "number", "號")):
            value = item.get(field)
            if value:
                parsed = address_parts(value)
                if not parsed and suffix and isinstance(value, str):
                    parsed = address_parts(value + suffix)
                if not actual or not parsed or key not in parsed or any(actual.get(part) != component for part, component in parsed.items()):
                    return _unresolved("structural_mismatch")
        return _resolved("tgos", formatted_address, latitude, longitude, item.get("COUNTY"), item.get("TOWN"), address=address, precision_accepted=True)


class GoogleAddressProvider:
    """Primary geocoder; retain raw precision metadata until the acceptance gate."""

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.cache_namespace = object()
        self._requests = BoundedRequestCache("geocoding", ttl_seconds=0, max_entries=256)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def resolve(self, address: str) -> LocationResolveResult:
        if not self.configured:
            return _unavailable("not_configured")
        normalized = " ".join(address.split())
        key = (ADDRESS_RESOLVER_VERSION, GOOGLE_GEOCODING_URL, normalized, "zh-TW", "tw", self.timeout_seconds)

        def resolve():
            result = self._resolve_provider(normalized)
            PROVIDER_COST_METRICS.record("geocoding", "provider_success" if result.status in {"resolved", "unresolved"} else "provider_failure")
            return result

        return self._requests.run(key, resolve)

    @provider_operation("geocoding")
    def _resolve_provider(self, address: str) -> LocationResolveResult:
        timeout = _provider_timeout(self.timeout_seconds)
        if timeout is None:
            return _unavailable("deadline_exhausted")
        try:
            PROVIDER_COST_METRICS.record("geocoding", "physical_calls")
            response = httpx.get(
                GOOGLE_GEOCODING_URL,
                params={"address": address, "language": "zh-TW", "region": "tw", "key": self.api_key},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException:
            PROVIDER_COST_METRICS.record("geocoding", "provider_timeout")
            return _unavailable("timeout")
        except (httpx.HTTPError, ValueError):
            return _unavailable("http_error")

        if not isinstance(payload, dict):
            return _unavailable("malformed_response")
        status = payload.get("status")
        if status == "ZERO_RESULTS":
            return _unresolved("zero_results")
        if status != "OK":
            return _unavailable("provider_status")
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return _unavailable("malformed_response")
        first = results[0]
        if not isinstance(first, dict):
            return _unavailable("malformed_response")
        location = ((first.get("geometry") or {}).get("location") if isinstance(first.get("geometry"), dict) else None)
        if not isinstance(location, dict):
            return _unavailable("malformed_response")
        latitude = location.get("lat")
        longitude = location.get("lng")
        if not _is_valid_coordinate(latitude, longitude):
            return _unavailable("invalid_coordinate")
        formatted_address = first.get("formatted_address")
        county, district = _google_administrative_area(first)
        precision_accepted = first["geometry"].get("location_type") == "ROOFTOP" and first.get("partial_match", False) is False
        # Also validate structured route/number/admin fields from this same response.
        actual = address_parts(formatted_address)
        components = first.get("address_components", [])
        if not isinstance(components, list):
            return _unresolved("malformed_response")
        for component in components:
            if not isinstance(component, dict) or not isinstance(component.get("types"), list):
                return _unresolved("malformed_response")
            types = component["types"]
            name = component.get("long_name")
            if "route" in types:
                route = address_parts(name)
                if not route or not actual or any(actual.get(key) != value for key, value in route.items()):
                    return _unresolved("structural_mismatch")
            if "street_number" in types:
                number = address_parts(normalize_address(name) + "號")
                if not number or not actual or number.get("number") != actual.get("number"):
                    return _unresolved("structural_mismatch")
            if any(t in types for t in ("administrative_area_level_1", "administrative_area_level_2", "administrative_area_level_3")):
                admin = _administrative_name(name, COUNTY_SUFFIXES if "administrative_area_level_1" in types else DISTRICT_SUFFIXES)
                key = "county" if "administrative_area_level_1" in types else "district"
                if admin and (not actual or actual.get(key) != admin):
                    return _unresolved("structural_mismatch")
        return _resolved("google", formatted_address, latitude, longitude, county, district, address=address, precision_accepted=precision_accepted)


_DEFAULT_GOOGLE_PROVIDER: GoogleAddressProvider | None = None
_DEFAULT_GOOGLE_PROVIDER_LOCK = threading.Lock()
_DEFAULT_TGOS_PROVIDER: TgosAddressProvider | None = None
_DEFAULT_TGOS_PROVIDER_LOCK = threading.Lock()
ADDRESS_RESOLVER_VERSION = "trusted-address-google-primary-strict-v2"
# Retain only safe derived accepted coordinates for a short query context.
_RESOLVED_ADDRESS_CACHE = BoundedRequestCache("address_resolution", ttl_seconds=60, max_entries=64)


def _get_google_provider() -> GoogleAddressProvider:
    global _DEFAULT_GOOGLE_PROVIDER
    configured_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    with _DEFAULT_GOOGLE_PROVIDER_LOCK:
        if _DEFAULT_GOOGLE_PROVIDER is None or _DEFAULT_GOOGLE_PROVIDER.api_key != configured_key:
            _DEFAULT_GOOGLE_PROVIDER = GoogleAddressProvider()
        return _DEFAULT_GOOGLE_PROVIDER


def _get_tgos_provider() -> TgosAddressProvider:
    global _DEFAULT_TGOS_PROVIDER
    app_id = os.getenv("TGOS_APP_ID", "").strip()
    api_key = os.getenv("TGOS_API_KEY", "").strip()
    with _DEFAULT_TGOS_PROVIDER_LOCK:
        if _DEFAULT_TGOS_PROVIDER is None or (_DEFAULT_TGOS_PROVIDER.app_id, _DEFAULT_TGOS_PROVIDER.api_key) != (app_id, api_key):
            _DEFAULT_TGOS_PROVIDER = TgosAddressProvider()
            _DEFAULT_TGOS_PROVIDER.cache_namespace = object()
        return _DEFAULT_TGOS_PROVIDER


def _accepted_resolution(result: dict[str, Any]) -> bool:
    return (
        result.get("status") == "resolved" and result.get("confidence") == "high"
        and result.get("source") in {"tgos", "google"}
        and _is_valid_coordinate(result.get("latitude"), result.get("longitude"))
        and set(result) == SAFE_RESPONSE_KEYS
    )


def _process_phase() -> tuple[bool, str]:
    """First resolve in this process and a coarse process age: cold-start evidence."""
    global _FIRST_RESOLVE_SEEN
    with _FIRST_RESOLVE_LOCK:
        first, _FIRST_RESOLVE_SEEN = not _FIRST_RESOLVE_SEEN, True
    age = time.monotonic() - _PROCESS_STARTED
    return first, "lt_30s" if age < 30 else "lt_5m" if age < 300 else "warm"


def _emit_resolve_event(fields: dict[str, Any]) -> None:
    degraded = fields.get("outcome") not in {"google_resolved", "tgos_resolved", "unresolved", "reused"}
    record = {"severity": "WARNING" if degraded else "INFO", "message": "location_resolve", **fields}
    _EVENT_LOGGER.log(logging.WARNING if degraded else logging.INFO, json.dumps(record, ensure_ascii=True, separators=(",", ":")))


def resolve_address(
    address: str,
    *,
    tgos_provider: AddressProvider | None = None,
    google_provider: AddressProvider | None = None,
) -> dict[str, Any]:
    """One Google attempt, then at most one strict TGOS fallback. Candidate only.

    The whole chain shares one server deadline below the browser bound.
    """

    normalized_address = " ".join(address.split())
    if not normalized_address:
        return _unavailable().to_safe_dict()

    started = time.monotonic()
    first_in_process, process_age = _process_phase()
    trace: dict[str, Any] = {}
    outcome = "reused"
    token = _DEADLINE.set(started + RESOLVE_BUDGET_SECONDS)
    try:
        tgos = tgos_provider if tgos_provider is not None else _get_tgos_provider()
        google = google_provider if google_provider is not None else _get_google_provider()
        providers = [google, tgos]
        if tgos_provider is None and google_provider is None:
            key = (
                ADDRESS_RESOLVER_VERSION, normalized_address,
                tgos.cache_namespace, google.cache_namespace,
                TGOS_URL, GOOGLE_GEOCODING_URL, "EPSG:4326", "zh-TW", "tw",
                "tgos-full-match-true-v30", tgos.timeout_seconds, google.timeout_seconds,
            )
            result = _RESOLVED_ADDRESS_CACHE.run(
                key, lambda: _resolve_with_providers(normalized_address, providers, trace),
                cacheable=lambda result: _accepted_resolution(result) and addresses_agree(normalized_address, result.get("formatted_address"), county=result.get("county"), district=result.get("district")),
            )
        else:
            result = _resolve_with_providers(normalized_address, providers, trace)
        # An empty trace means this caller reused a cached or in-flight result.
        if trace:
            outcome = f"{result['source']}_resolved" if result["status"] == "resolved" else result["status"]
        return result
    except AbuseRejected as error:
        outcome = "admission_rejected"
        trace["admission"] = str(error.detail.get("reason_code", "unknown")) if isinstance(error.detail, dict) else "unknown"
        raise
    except Exception:
        outcome = "server_error"
        raise
    finally:
        _DEADLINE.reset(token)
        _emit_resolve_event({
            "outcome": outcome,
            "google": trace.get("google", "not_attempted"),
            "tgos": trace.get("tgos", "not_attempted"),
            "fallback": "tgos_ms" in trace,
            "admission": trace.get("admission", "admitted"),
            "google_ms": trace.get("google_ms"),
            "tgos_ms": trace.get("tgos_ms"),
            "total_ms": int((time.monotonic() - started) * 1000),
            "budget_ms": int(RESOLVE_BUDGET_SECONDS * 1000),
            "first_in_process": first_in_process,
            "process_age": process_age,
        })


def _resolve_with_providers(normalized_address: str, providers: list[AddressProvider], trace: dict[str, Any] | None = None) -> dict[str, Any]:
    trace = trace if trace is not None else {}
    saw_unresolved = False
    saw_configured = False
    budget_skipped = False
    deadline = _DEADLINE.get()
    for name, provider in zip(("google", "tgos"), providers):
        if not provider.configured:
            trace[name] = "not_configured"
            continue
        saw_configured = True
        if name == "tgos" and deadline is not None and deadline - time.monotonic() < TGOS_MIN_REMAINING_SECONDS:
            trace[name] = "skipped_budget"
            budget_skipped = True
            continue
        provider_started = time.monotonic()
        trace[name] = "started"
        result = provider.resolve(normalized_address)
        trace[f"{name}_ms"] = int((time.monotonic() - provider_started) * 1000)
        trace[name] = result.reason or result.status
        if result.status == "resolved":
            if result.acceptance_validated and _accepted_resolution(result.to_safe_dict()) and addresses_agree(normalized_address, result.formatted_address, county=result.county, district=result.district):
                return result.to_safe_dict()
            trace[name] = "structural_mismatch"
            saw_unresolved = True
        if result.status == "unresolved":
            saw_unresolved = True

    # An incomplete strict chain is retryable, never a confident "not found".
    if budget_skipped:
        return _unavailable("deadline_exhausted").to_safe_dict()
    if saw_unresolved:
        return _unresolved().to_safe_dict()
    if not saw_configured:
        return _unavailable().to_safe_dict()
    return _unavailable().to_safe_dict()
