"""Geocoding adapter contract with an offline mock implementation."""

from __future__ import annotations

import os
from typing import Any, Protocol

import httpx


class GeocodingAdapter(Protocol):
    """Resolve a text query into one normalized mock or external location."""

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Return the best matching region or None."""


class MockGeocodingAdapter:
    """Resolve addresses against bundled aliases without external APIs."""

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        normalized = "".join(query.lower().split())
        if not normalized:
            return None
        for region in regions:
            candidates = [region["city"], region["district"], region["road"], *region.get("aliases", [])]
            if any("".join(str(item).lower().split()) in normalized or normalized in "".join(str(item).lower().split()) for item in candidates):
                return region
        return None


class GoogleGeocodingAdapter:
    """Optionally resolve an address with a backend-only Google API key."""

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.last_error = ""

    @property
    def available(self) -> bool:
        """Return whether a backend-only Google API key is configured."""

        return bool(self.api_key)

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not self.available or not query.strip():
            return None
        try:
            response = httpx.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": query, "language": "zh-TW", "region": "tw", "key": self.api_key},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            result = response.json().get("results", [])[0]
            location = result["geometry"]["location"]
            self.last_error = ""
            # Parse city and district from address_components.
            # Taiwan (region=tw) uses administrative_area_level_1 for city (e.g. 臺北市)
            # and administrative_area_level_2 for district (e.g. 大安區).
            # This product targets Taiwan; prefer level_2 for district.
            # Fall back to level_3 only when level_2 is absent.
            city = ""
            district = ""
            level_2 = ""
            level_3 = ""
            for component in result.get("address_components", []):
                types = component.get("types", [])
                if "administrative_area_level_1" in types:
                    city = component.get("long_name", "")
                elif "administrative_area_level_2" in types:
                    level_2 = component.get("long_name", "")
                elif "administrative_area_level_3" in types:
                    level_3 = component.get("long_name", "")
            # Taiwan: level_2 is district; level_3 is fallback for other regions
            district = level_2 or level_3
            return {
                "id": f"google-{result.get('place_id', 'location')}",
                "city": city,
                "district": district,
                "road": result.get("formatted_address", query),
                "formatted_address": result.get("formatted_address", query),
                "place_id": result.get("place_id", ""),
                "center": {"lat": float(location["lat"]), "lng": float(location["lng"])},
                "zoom": 15,
                "area_summary": f"{result.get('formatted_address', query)} 周遭生活機能查詢。",
                "poi_summary": "周遭設施將由 Google Places 或 mock fallback 提供。",
                "poi_layers": [],
            }
        except httpx.TimeoutException:
            self.last_error = "Google Geocoding 回應逾時"
            return None
        except httpx.HTTPStatusError:
            self.last_error = "Google Geocoding 目前無法使用"
            return None
        except (httpx.HTTPError, IndexError, KeyError, TypeError, ValueError):
            self.last_error = "Google Geocoding 未回傳可用定位"
            return None
