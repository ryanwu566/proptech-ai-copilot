"""Market Insight Lite API routes using offline mock CSV data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.data_service import MockDataError
from services.market_insight_service import get_market_summary, load_market_insights


router = APIRouter(tags=["market-insight"])


class MarketInsightQuery(BaseModel):
    """Region selector for Market Insight Lite."""

    city: str
    district: str


@router.get("/market-insights")
def get_market_insights() -> list[dict[str, Any]]:
    """Return available mock regions for selector controls."""

    try:
        rows = load_market_insights()
    except MockDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return rows[["city", "district"]].to_dict("records")


@router.post("/market-insights/query")
def post_market_insight_query(request: MarketInsightQuery) -> dict[str, Any]:
    """Return one offline Market Insight Lite summary."""

    try:
        result = get_market_summary(request.city, request.district)
    except MockDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="找不到該區域的展示資料。")
    return result
