from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.schemas.location import LocationResolveResponse


TGOS_URL = "https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass(slots=True)
class LocationResolver:
    google_maps_api_key: str | None = None
    tgos_app_id: str | None = None
    tgos_api_key: str | None = None
    timeout_seconds: float = 5.0

    @property
    def tgos_available(self) -> bool:
        return bool(self.tgos_app_id and self.tgos_api_key)

    @property
    def google_available(self) -> bool:
        return bool(self.google_maps_api_key)

    def resolve(self, address: str) -> LocationResolveResponse:
        query = address.strip()
        if not query:
            return self._unresolved("請提供完整地址文字後再進行定位。")

        if not self.tgos_available and not self.google_available:
            return self._unavailable("目前尚未設定 TGOS 或 Google 定位憑證，暫時無法解析地址。")

        tgos_result = self._resolve_tgos(query)
        if tgos_result.status == "resolved":
            return self._to_response(tgos_result, confidence="high")

        google_result = self._resolve_google(query)
        if google_result.status == "resolved":
            return self._to_response(google_result, confidence="medium")

        if tgos_result.status == "no_result" and google_result.status == "no_result":
            return self._unresolved("TGOS 與 Google 都未回傳可信定位結果，請檢查地址是否完整或稍後再試。")

        return self._unavailable("目前定位服務暫時不可用，請稍後再試。")

    def _resolve_tgos(self, address: str) -> ProviderOutcome:
        if not self.tgos_available:
            return ProviderOutcome(status="unavailable", source="tgos")

        params = {
            "oAPPId": self.tgos_app_id,
            "oAPIKey": self.tgos_api_key,
            "oAddress": address,
            "oSRS": "EPSG:4326",
            "oFuzzyType": "0",
            "oResultDataType": "JSON",
            "oFuzzyBuffer": "0",
            "oIsOnlyFullMatch": "false",
            "oReturnMaxCount": "1",
        }
        try:
            response = httpx.get(TGOS_URL, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            item = self._first_item(payload.get("AddressList") or payload.get("addressList"))
            if item is None:
                return ProviderOutcome(status="no_result", source="tgos")

            longitude = self._coerce_float(
                item.get("X") or item.get("x") or item.get("longitude") or item.get("Lng") or item.get("lng")
            )
            latitude = self._coerce_float(
                item.get("Y") or item.get("y") or item.get("latitude") or item.get("Lat") or item.get("lat")
            )
            if latitude is None or longitude is None:
                return ProviderOutcome(status="unavailable", source="tgos")

            formatted_address = str(
                item.get("FULL_ADDR")
                or item.get("fullAddress")
                or item.get("Address")
                or item.get("address")
                or address
            )
            return ProviderOutcome(
                status="resolved",
                source="tgos",
                formatted_address=formatted_address,
                latitude=latitude,
                longitude=longitude,
            )
        except (httpx.TimeoutException, httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return ProviderOutcome(status="unavailable", source="tgos")

    def _resolve_google(self, address: str) -> ProviderOutcome:
        if not self.google_available:
            return ProviderOutcome(status="unavailable", source="google")

        params = {
            "address": address,
            "language": "zh-TW",
            "region": "tw",
            "key": self.google_maps_api_key,
        }
        try:
            response = httpx.get(GOOGLE_GEOCODE_URL, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            status = str(payload.get("status", ""))
            if status == "ZERO_RESULTS":
                return ProviderOutcome(status="no_result", source="google")
            if status != "OK":
                return ProviderOutcome(status="unavailable", source="google")
            results = payload.get("results")
            if not isinstance(results, list) or not results:
                return ProviderOutcome(status="unavailable", source="google")
            result = results[0]
            if not isinstance(result, dict):
                return ProviderOutcome(status="unavailable", source="google")
            geometry = result.get("geometry")
            if not isinstance(geometry, dict):
                return ProviderOutcome(status="unavailable", source="google")
            location = geometry.get("location")
            if not isinstance(location, dict):
                return ProviderOutcome(status="unavailable", source="google")
            latitude = self._coerce_float(location.get("lat"))
            longitude = self._coerce_float(location.get("lng"))
            if latitude is None or longitude is None:
                return ProviderOutcome(status="unavailable", source="google")

            formatted_address = result.get("formatted_address") or address
            return ProviderOutcome(
                status="resolved",
                source="google",
                formatted_address=str(formatted_address),
                latitude=latitude,
                longitude=longitude,
            )
        except (httpx.TimeoutException, httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return ProviderOutcome(status="unavailable", source="google")

    @staticmethod
    def _first_item(value: Any) -> dict[str, Any] | None:
        if isinstance(value, list) and value:
            first = value[0]
            return first if isinstance(first, dict) else None
        if isinstance(value, dict):
            return value
        return None

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _unresolved(message: str) -> LocationResolveResponse:
        return LocationResolveResponse(
            status="unresolved",
            source="none",
            formatted_address=None,
            latitude=None,
            longitude=None,
            confidence="unknown",
            message=message,
        )

    @staticmethod
    def _unavailable(message: str) -> LocationResolveResponse:
        return LocationResolveResponse(
            status="unavailable",
            source="none",
            formatted_address=None,
            latitude=None,
            longitude=None,
            confidence="unknown",
            message=message,
        )

    @staticmethod
    def _to_response(outcome: ProviderOutcome, confidence: Literal["high", "medium", "unknown"]) -> LocationResolveResponse:
        return LocationResolveResponse(
            status="resolved",
            source=outcome.source,
            formatted_address=outcome.formatted_address,
            latitude=outcome.latitude,
            longitude=outcome.longitude,
            confidence=confidence,
            message=(
                "已由 TGOS 取得可信座標，可用於後續分析。"
                if outcome.source == "tgos"
                else "已由 Google Geocoding 取得可信座標，可用於後續分析。"
            ),
        )


@dataclass(slots=True)
class ProviderOutcome:
    status: Literal["resolved", "no_result", "unavailable"]
    source: Literal["tgos", "google"]
    formatted_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def build_location_resolver() -> LocationResolver:
    return LocationResolver(
        google_maps_api_key=settings.google_maps_api_key,
        tgos_app_id=settings.tgos_app_id,
        tgos_api_key=settings.tgos_api_key,
    )