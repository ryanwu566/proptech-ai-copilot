"""Market Insight service backed by traceable PLVR aggregate queries.

Bundled mock CSV data is not used by the production Market Insight API.
When no read-only PLVR aggregate is available, the service returns conservative
``unavailable`` responses instead of demo metrics.
"""

from __future__ import annotations

from typing import Any

from services.plvr_market_aggregate_service import (
    get_market_catalog as _get_market_catalog,
    get_market_status as _get_market_status,
    get_market_summary as _get_market_summary,
    list_market_regions as _list_market_regions,
    refresh_market_read_model as _refresh_market_read_model,
)


def get_market_status() -> dict[str, Any]:
    """Return safe aggregate status metadata."""

    return _get_market_status()


def get_market_catalog() -> dict[str, Any]:
    """Return safe read model catalog metadata."""

    return _get_market_catalog()


def list_market_regions(county: str = "") -> dict[str, Any]:
    """Return selector metadata for traceable market aggregate data."""

    return _list_market_regions(county=county)


def get_market_summary(city: str, district: str, period: str | None = None) -> dict[str, Any]:
    """Return a market summary or a safe unavailable response."""

    return _get_market_summary(county=city, district=district, period=period)


def refresh_market_read_model() -> dict[str, Any]:
    """Refresh protected market read model aggregates."""

    return _refresh_market_read_model()
