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
            results = response.json().get("results", [])
            if not results:
                self.last_error = "Google Geocoding 未回傳結果"
                return None
            self.last_error = ""
            # Evaluate top candidates (up to 3) and prefer street-address level results
            best = None
            for candidate in results[:3]:
                parsed = self._parse_candidate(candidate, query)
                if parsed is None:
                    continue
                # Prefer street_address or route over landmark/establishment
                candidate_types = set(candidate.get("types", []))
                is_street_level = bool(candidate_types & {"street_address", "route", "premise", "subpremise"})
                if best is None:
                    best = parsed
                elif is_street_level and not best.get("_is_street_level"):
                    best = parsed  # Prefer street-level over landmark
            return best
        except httpx.TimeoutException:
            self.last_error = "Google Geocoding 回應逾時"
            return None
        except httpx.HTTPStatusError:
            self.last_error = "Google Geocoding 目前無法使用"
            return None
        except (httpx.HTTPError, IndexError, KeyError, TypeError, ValueError):
            self.last_error = "Google Geocoding 未回傳可用定位"
            return None

    def _parse_candidate(self, result: dict[str, Any], query: str) -> dict[str, Any] | None:
        """Parse a single Google Geocoding result into structured fields."""
        try:
            location = result["geometry"]["location"]
        except (KeyError, TypeError):
            return None
        city = ""
        district = ""
        level_2 = ""
        level_3 = ""
        route = ""
        street_number = ""
        for component in result.get("address_components", []):
            types = component.get("types", [])
            if "administrative_area_level_1" in types:
                city = component.get("long_name", "")
            elif "administrative_area_level_2" in types:
                level_2 = component.get("long_name", "")
            elif "administrative_area_level_3" in types:
                level_3 = component.get("long_name", "")
            if "route" in types:
                route = component.get("long_name", "")
            if "street_number" in types:
                street_number = component.get("long_name", "")
        # Taiwan: level_2 is district; level_3 is fallback
        # Filter out 里-level results that are NOT real districts
        raw_district = level_2 or level_3
        if raw_district and raw_district.endswith("里") and not raw_district.endswith(("區", "鄉", "鎮", "市")):
            raw_district = ""  # 里 is NOT a district
        district = raw_district
        # Build canonical road from structured route (not formatted_address)
        canonical_road = route if route else ""
        candidate_types = set(result.get("types", []))
        is_street_level = bool(candidate_types & {"street_address", "route", "premise", "subpremise"})
        return {
            "id": f"google-{result.get('place_id', 'location')}",
            "city": city,
            "district": district,
            "road": canonical_road or result.get("formatted_address", query),
            "formatted_address": result.get("formatted_address", query),
            "place_id": result.get("place_id", ""),
            "center": {"lat": float(location["lat"]), "lng": float(location["lng"])},
            "zoom": 15,
            "area_summary": f"{result.get('formatted_address', query)} 周遭生活機能查詢。",
            "poi_summary": "周遭設施將由 Google Places 或 mock fallback 提供。",
            "poi_layers": [],
            "geocoding_metadata": {
                "provider_types": list(result.get("types", [])),
                "location_type": result.get("geometry", {}).get("location_type", ""),
                "partial_match": bool(result.get("partial_match")),
                "route": route,
                "street_number": street_number,
            },
            "_is_street_level": is_street_level,
        }

