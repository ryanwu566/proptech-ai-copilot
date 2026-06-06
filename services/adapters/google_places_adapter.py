"""Google Places (New) nearby-search adapter with a normalized response."""

from __future__ import annotations

import math
import os
import time
from typing import Any

import httpx


PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.location",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "places.types",
    ]
)
CATEGORY_TYPES = {
    "transport": ["transit_station", "bus_station", "subway_station", "train_station"],
    "school": ["school", "university"],
    "park": ["park"],
    "medical": ["hospital", "doctor", "pharmacy"],
    "shopping": ["shopping_mall", "supermarket", "convenience_store"],
    "food": ["restaurant", "cafe"],
}


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Return the haversine distance between two WGS84 points."""

    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    value = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value)))


class GooglePlacesAdapter:
    """Fetch and normalize nearby places without exposing the API key."""

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self._cache: dict[tuple[Any, ...], tuple[float, list[dict[str, Any]]]] = {}
        self.cache_ttl_seconds = 600

    @property
    def available(self) -> bool:
        """Return whether a Google API key is configured."""

        return bool(self.api_key)

    def nearby(
        self,
        lat: float,
        lng: float,
        radius_m: int,
        category: str,
        language_code: str = "zh-TW",
    ) -> list[dict[str, Any]]:
        """Return normalized Google Places for one supported category."""

        if not self.available:
            return []
        cache_key = (round(lat, 5), round(lng, 5), radius_m, category, language_code)
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        payload = {
            "includedTypes": CATEGORY_TYPES[category],
            "maxResultCount": 10,
            "languageCode": language_code,
            "rankPreference": "DISTANCE",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(PLACES_URL, json=payload, headers=headers)
            response.raise_for_status()
        places = [self._normalize(row, lat, lng, category) for row in response.json().get("places", [])]
        self._cache[cache_key] = (time.monotonic(), places)
        return places

    @staticmethod
    def _normalize(row: dict[str, Any], center_lat: float, center_lng: float, category: str) -> dict[str, Any]:
        location = row.get("location", {})
        lat = float(location.get("latitude", center_lat))
        lng = float(location.get("longitude", center_lng))
        return {
            "place_id": str(row.get("id", "")),
            "name": str(row.get("displayName", {}).get("text", "未命名地點")),
            "lat": lat,
            "lng": lng,
            "address": str(row.get("formattedAddress", "")),
            "rating": float(row["rating"]) if row.get("rating") is not None else None,
            "user_rating_count": int(row.get("userRatingCount", 0)),
            "business_status": str(row.get("businessStatus", "UNKNOWN")),
            "distance_m": distance_meters(center_lat, center_lng, lat, lng),
            "types": list(row.get("types", [])),
            "category": category,
            "source": "google_places",
        }
