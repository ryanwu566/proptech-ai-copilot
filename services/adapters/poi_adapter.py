"""POI adapter contract with an offline mock implementation."""

from __future__ import annotations

from typing import Any, Protocol


class PoiAdapter(Protocol):
    """Provide normalized POI layers for a selected map region."""

    def get_layers(self, region: dict[str, Any]) -> list[dict[str, Any]]:
        """Return categorized POI layers."""


class MockPoiAdapter:
    """Return POI layers bundled with the mock region."""

    def get_layers(self, region: dict[str, Any]) -> list[dict[str, Any]]:
        return list(region.get("poi_layers", []))
