"""Market Insight API routes backed by traceable market aggregates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["market-insight"])


class MarketInsightQuery(BaseModel):
    """Region selector for Market Insight."""

    city: str
    district: str


@router.get("/market-insights")
def get_market_insights() -> dict[str, Any]:
    """Return available aggregate regions for selector controls."""

    from services.market_data_foundation import MarketDataContractError, market_catalog_unavailable
    from services.market_insight_service import list_market_regions

    try:
        return list_market_regions()
    except MarketDataContractError:
        return market_catalog_unavailable()


@router.post("/market-insights/query")
def post_market_insight_query(request: MarketInsightQuery) -> dict[str, Any]:
    """Return one traceable Market Insight summary, or unavailable."""

    from services.market_data_foundation import MarketDataContractError, market_unavailable_response
    from services.market_insight_service import get_market_summary

    try:
        return get_market_summary(request.city, request.district)
    except MarketDataContractError:
        return market_unavailable_response(city=request.city, district=request.district)
