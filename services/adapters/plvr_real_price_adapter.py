"""Inactive PLVR adapter contract prepared for a future OpenData integration."""

from __future__ import annotations

from typing import Any

from services.valuation_service import load_transactions


class PlvrRealPriceAdapter:
    """Define a future PLVR integration without downloading external data."""

    enabled = False

    def load_transactions(self, city: str, district: str, road: str) -> list[dict[str, Any]]:
        """Return bundled sample rows until a reviewed PLVR source is enabled."""

        return [
            row
            for row in load_transactions()
            if row["city"] == city and row["district"] == district and (not road or row["road"] == road)
        ]

    def normalize_transaction(self, row: dict[str, Any]) -> dict[str, Any]:
        """Return a stable normalized transaction shape."""

        return dict(row)

    def filter_comparables(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """Filter sample transactions using the future adapter interface."""

        return self.load_transactions(str(request["city"]), str(request["district"]), str(request.get("road", "")))
