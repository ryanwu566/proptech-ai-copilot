"""Geocoding adapter contract with an offline mock implementation."""

from __future__ import annotations

from typing import Any, Protocol


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
