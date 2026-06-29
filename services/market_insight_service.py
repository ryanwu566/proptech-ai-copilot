"""Market Insight service backed by traceable aggregate artifacts.

Bundled mock CSV data is no longer used by the production Market Insight API.
When no aggregate artifact has been prepared, the service returns conservative
``unavailable`` responses instead of demo metrics.
"""

from __future__ import annotations

from typing import Any

from services.market_data_foundation import (
    get_market_summary as _get_market_summary,
    list_market_regions as _list_market_regions,
)


def list_market_regions() -> dict[str, Any]:
    """Return selector metadata for traceable market aggregate data."""

    return _list_market_regions()


def get_market_summary(city: str, district: str) -> dict[str, Any]:
    """Return a market summary or a safe unavailable response."""

    return _get_market_summary(city=city, district=district)
