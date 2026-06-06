"""Optional backend-only TGOS geocoding adapter."""

from __future__ import annotations

import os
from typing import Any

import httpx


TGOS_URL = "https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr"


class TgosGeocodingAdapter:
    """Resolve Taiwan addresses through TGOS when backend credentials exist."""

    def __init__(self, app_id: str | None = None, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self.app_id = (app_id if app_id is not None else os.getenv("TGOS_APP_ID", "")).strip()
        self.api_key = (api_key if api_key is not None else os.getenv("TGOS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.last_error = ""

    @property
    def available(self) -> bool:
        """Return whether both backend-only TGOS credentials are configured."""

        return bool(self.app_id and self.api_key)

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Return one normalized TGOS address result or None."""

        del regions
        if not self.available or not query.strip():
            return None
        params = {
            "oAPPId": self.app_id,
            "oAPIKey": self.api_key,
            "oAddress": query,
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
            item = (payload.get("AddressList") or payload.get("addressList") or [])[0]
            x = item.get("X") or item.get("x") or item.get("longitude")
            y = item.get("Y") or item.get("y") or item.get("latitude")
            address = item.get("FULL_ADDR") or item.get("fullAddress") or item.get("Address") or query
            self.last_error = ""
            return {
                "id": f"tgos-{address}",
                "city": item.get("COUNTY", ""),
                "district": item.get("TOWN", ""),
                "road": item.get("ROAD", address),
                "formatted_address": address,
                "place_id": "",
                "center": {"lat": float(y), "lng": float(x)},
                "zoom": 15,
                "area_summary": f"{address} 的區域定位結果。",
                "poi_summary": "定位由 TGOS 提供，周遭設施另由 Google Places 或展示資料補充。",
                "poi_layers": [],
            }
        except httpx.TimeoutException:
            self.last_error = "TGOS 暫時無法回應"
        except (httpx.HTTPError, IndexError, KeyError, TypeError, ValueError):
            self.last_error = "TGOS 暫時無法取得定位結果"
        return None
