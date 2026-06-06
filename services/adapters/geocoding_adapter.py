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

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not self.api_key or not query.strip():
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
            return {
                "id": f"google-{result.get('place_id', 'location')}",
                "city": "",
                "district": "",
                "road": result.get("formatted_address", query),
                "center": {"lat": float(location["lat"]), "lng": float(location["lng"])},
                "zoom": 15,
                "area_summary": f"{result.get('formatted_address', query)} 周遭生活機能查詢。",
                "poi_summary": "周遭設施將由 Google Places 或 mock fallback 提供。",
                "poi_layers": [],
            }
        except (httpx.HTTPError, IndexError, KeyError, TypeError, ValueError):
            return None
