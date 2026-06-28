"""Trusted address resolution with conservative provider fallback."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx


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
}

TGOS_URL = "https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr"
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass(frozen=True)
class LocationResolveResult:
    status: LocationResolveStatus
    source: LocationResolveSource = "none"
    formatted_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: LocationResolveConfidence = "unknown"
    message: str = "定位服務暫時無法完成查詢，請稍後再試。"

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "formatted_address": self.formatted_address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "confidence": self.confidence,
            "message": self.message,
        }


class AddressProvider(Protocol):
    @property
    def configured(self) -> bool:
        """Return whether this provider has backend-only credentials."""

    def resolve(self, address: str) -> LocationResolveResult:
        """Resolve an address without exposing provider raw payloads."""


def _is_valid_coordinate(latitude: Any, longitude: Any) -> bool:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def _resolved(source: LocationResolveSource, formatted_address: str | None, latitude: Any, longitude: Any) -> LocationResolveResult:
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
    )


def _unresolved() -> LocationResolveResult:
    return LocationResolveResult(
        status="unresolved",
        source="none",
        message="找不到可信位置，請確認縣市、區域與門牌是否完整。",
    )


def _unavailable() -> LocationResolveResult:
    return LocationResolveResult(
        status="unavailable",
        source="none",
        message="定位服務暫時無法完成查詢，請稍後再試。",
    )


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
            return _unavailable()
        try:
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
                    "oIsOnlyFullMatch": "false",
                    "oReturnMaxCount": "1",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError):
            return _unavailable()

        try:
            items = payload.get("AddressList") or payload.get("addressList") or []
        except AttributeError:
            return _unavailable()
        if not items:
            return _unresolved()
        item = items[0]
        if not isinstance(item, dict):
            return _unavailable()

        longitude = item.get("X") or item.get("x") or item.get("longitude")
        latitude = item.get("Y") or item.get("y") or item.get("latitude")
        if not _is_valid_coordinate(latitude, longitude):
            return _unavailable()
        formatted_address = item.get("FULL_ADDR") or item.get("fullAddress") or item.get("Address")
        return _resolved("tgos", str(formatted_address) if formatted_address else None, latitude, longitude)


class GoogleAddressProvider:
    """Backend-only Google Geocoding resolver used as TGOS fallback."""

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def resolve(self, address: str) -> LocationResolveResult:
        if not self.configured:
            return _unavailable()
        try:
            response = httpx.get(
                GOOGLE_GEOCODING_URL,
                params={"address": address, "language": "zh-TW", "region": "tw", "key": self.api_key},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError):
            return _unavailable()

        if not isinstance(payload, dict):
            return _unavailable()
        status = payload.get("status")
        if status == "ZERO_RESULTS":
            return _unresolved()
        if status != "OK":
            return _unavailable()
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return _unavailable()
        first = results[0]
        if not isinstance(first, dict):
            return _unavailable()
        location = ((first.get("geometry") or {}).get("location") if isinstance(first.get("geometry"), dict) else None)
        if not isinstance(location, dict):
            return _unavailable()
        latitude = location.get("lat")
        longitude = location.get("lng")
        if not _is_valid_coordinate(latitude, longitude):
            return _unavailable()
        formatted_address = first.get("formatted_address")
        return _resolved("google", str(formatted_address) if formatted_address else None, latitude, longitude)


def resolve_address(
    address: str,
    *,
    tgos_provider: AddressProvider | None = None,
    google_provider: AddressProvider | None = None,
) -> dict[str, Any]:
    """Resolve an address using TGOS first, then Google, returning only safe fields."""

    normalized_address = address.strip()
    if not normalized_address:
        return _unavailable().to_safe_dict()

    providers: list[AddressProvider] = [
        tgos_provider if tgos_provider is not None else TgosAddressProvider(),
        google_provider if google_provider is not None else GoogleAddressProvider(),
    ]
    saw_unresolved = False
    saw_configured = False
    for provider in providers:
        if not provider.configured:
            continue
        saw_configured = True
        result = provider.resolve(normalized_address)
        if result.status == "resolved":
            return result.to_safe_dict()
        if result.status == "unresolved":
            saw_unresolved = True

    if saw_unresolved:
        return _unresolved().to_safe_dict()
    if not saw_configured:
        return _unavailable().to_safe_dict()
    return _unavailable().to_safe_dict()
