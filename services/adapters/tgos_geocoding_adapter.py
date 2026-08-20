"""Optional backend-only TGOS geocoding adapter."""

from __future__ import annotations

import os
import math
import threading
from typing import Any

import httpx


TGOS_URL = "https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr"


class TgosGeocodingAdapter:
    """Resolve Taiwan addresses through TGOS when backend credentials exist."""

    def __init__(
        self,
        app_id: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.app_id = (app_id if app_id is not None else os.getenv("TGOS_APP_ID", "")).strip()
        self.api_key = (api_key if api_key is not None else os.getenv("TGOS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.last_error = ""
        self._client = client
        self._owns_client = client is None
        self._client_lock = threading.Lock()

    @property
    def available(self) -> bool:
        """Return whether both backend-only TGOS credentials are configured."""

        return bool(self.app_id and self.api_key)

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Return one normalized TGOS address result or None."""

        del regions
        normalized_query = query.strip()
        if not self.available:
            self.last_error = "TGOS credentials are not configured"
            return None
        if not normalized_query:
            self.last_error = "TGOS query is empty"
            return None
        params = {
            "oAPPId": self.app_id,
            "oAPIKey": self.api_key,
            "oAddress": normalized_query,
            "oSRS": "EPSG:4326",
            "oFuzzyType": "0",
            "oResultDataType": "JSON",
            "oFuzzyBuffer": "0",
            "oIsOnlyFullMatch": "false",
            "oReturnMaxCount": "1",
        }
        try:
            response = self._get_client().get(TGOS_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            item = (payload.get("AddressList") or payload.get("addressList") or [])[0]
            x = item.get("X") or item.get("x") or item.get("longitude")
            y = item.get("Y") or item.get("y") or item.get("latitude")
            latitude = float(y)
            longitude = float(x)
            if not _is_plausible_taiwan_coordinate(latitude, longitude):
                raise ValueError("invalid coordinate")
            address = str(item.get("FULL_ADDR") or item.get("fullAddress") or item.get("Address") or "").strip()
            if not address:
                raise ValueError("empty address")
            self.last_error = ""
            return {
                "id": f"tgos-{address}",
                "city": item.get("COUNTY", ""),
                "district": item.get("TOWN", ""),
                "road": item.get("ROAD", address),
                "formatted_address": address,
                "place_id": "",
                "center": {"lat": latitude, "lng": longitude},
                "zoom": 15,
                "area_summary": f"{address} 的區域定位結果。",
                "poi_summary": "定位由 TGOS 提供，周遭設施另由 Google Places 或展示資料補充。",
                "poi_layers": [],
            }
        except httpx.TimeoutException:
            self.last_error = "TGOS 暫時無法回應"
        except (httpx.HTTPError, AttributeError, IndexError, KeyError, TypeError, ValueError):
            self.last_error = "TGOS 暫時無法取得定位結果"
        return None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    timeout = httpx.Timeout(
                        self.timeout_seconds,
                        connect=min(1.5, self.timeout_seconds),
                        pool=min(1.0, self.timeout_seconds),
                    )
                    self._client = httpx.Client(timeout=timeout)
        return self._client

    def close(self) -> None:
        """Close an internally owned reusable client."""

        if not self._owns_client:
            return
        with self._client_lock:
            client, self._client = self._client, None
        if client is not None:
            client.close()

    def __enter__(self) -> "TgosGeocodingAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _is_plausible_taiwan_coordinate(latitude: float, longitude: float) -> bool:
    return math.isfinite(latitude) and math.isfinite(longitude) and 21 <= latitude <= 26 and 119 <= longitude <= 123
