"""Traffic adapter contract with an offline mock implementation."""

from __future__ import annotations

from typing import Any, Protocol


class TrafficAdapter(Protocol):
    """Provide a normalized traffic summary for a selected map region."""

    def get_summary(self, region: dict[str, Any]) -> dict[str, Any]:
        """Return mock or external traffic information."""


class MockTrafficAdapter:
    """Return the bundled transport layer as a stable traffic summary."""

    def get_summary(self, region: dict[str, Any]) -> dict[str, Any]:
        transport = next((layer for layer in region.get("poi_layers", []) if layer["category"] == "transport"), None)
        return {"source": "mock", "point_count": len(transport["points"]) if transport else 0}
