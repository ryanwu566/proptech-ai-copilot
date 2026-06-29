"""Market Insight API routes backed by traceable market aggregates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["market-insight"])


class MarketInsightQuery(BaseModel):
    """Region selector for Market Insight."""

    county: str | None = None
    city: str | None = None
    district: str
    period: str | None = None


@router.get("/market-insights/status")
def get_market_insight_status() -> dict[str, Any]:
    """Return safe PLVR market aggregate status metadata."""

    from services.market_insight_service import get_market_status

    return get_market_status()


@router.get("/market-insights/regions")
def get_market_insight_regions(county: str = "") -> dict[str, Any]:
    """Return available PLVR aggregate regions, optionally filtered by county."""

    from services.market_insight_service import list_market_regions

    return list_market_regions(county=county)


@router.get("/market-insights")
def get_market_insights() -> dict[str, Any]:
    """Return available aggregate regions for selector controls."""

    from services.market_insight_service import list_market_regions

    return list_market_regions()


@router.post("/market-insights/query")
def post_market_insight_query(request: MarketInsightQuery) -> dict[str, Any]:
    """Return one traceable Market Insight summary, or unavailable."""

    from services.market_data_foundation import market_unavailable_response
    from services.market_insight_service import get_market_summary

    county = request.county or request.city or ""
    if not county.strip() or not request.district.strip():
        return market_unavailable_response(city=county, district=request.district)
    return get_market_summary(county, request.district, request.period)
