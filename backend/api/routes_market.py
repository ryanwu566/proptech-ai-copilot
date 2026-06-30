"""Market Insight API routes backed by traceable market aggregates."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, ConfigDict

router = APIRouter(tags=["market-insight"])
MARKET_READ_MODEL_REFRESH_TOKEN_ENV = "MARKET_READ_MODEL_REFRESH_TOKEN"
MARKET_REFRESH_503_FIELDS = ("status", "data_status", "coverage_status", "built_at", "message", "reason_code")
MARKET_REFRESH_UNAVAILABLE_MESSAGE = "市場讀取模型暫時無法刷新，請稍後再試。"
MARKET_REFRESH_TOKEN_UNAVAILABLE_MESSAGE = "市場讀取模型刷新設定尚未完成。"
MARKET_REFRESH_FORBIDDEN_MESSAGE = "沒有權限刷新市場讀取模型。"


class MarketInsightQuery(BaseModel):
    """Region selector for Market Insight."""

    model_config = ConfigDict(extra="forbid")

    county: str | None = None
    city: str | None = None
    district: str = ""
    period: str | None = None


@router.get("/market-insights/status")
def get_market_insight_status() -> dict[str, Any]:
    """Return safe PLVR market aggregate status metadata."""

    from services.market_insight_service import get_market_status

    return get_market_status()


@router.get("/market-insights/catalog")
def get_market_insight_catalog() -> dict[str, Any]:
    """Return available counties and read model metadata."""

    from services.market_insight_service import get_market_catalog

    return get_market_catalog()


@router.get("/market-insights/regions")
def get_market_insight_regions(county: str = "") -> dict[str, Any]:
    """Return available PLVR aggregate regions, optionally filtered by county."""

    from services.market_insight_service import list_market_regions

    return list_market_regions(county=county)


@router.get("/market-insights")
def get_market_insights() -> dict[str, Any]:
    """Return available aggregate regions for selector controls."""

    from services.market_insight_service import get_market_catalog

    return get_market_catalog()


@router.post("/market-insights/query")
def post_market_insight_query(request: MarketInsightQuery) -> dict[str, Any]:
    """Return one traceable Market Insight summary, or unavailable."""

    from services.market_data_foundation import market_unavailable_response
    from services.market_insight_service import get_market_summary

    county = request.county or request.city or ""
    if not county.strip():
        return market_unavailable_response(city=county, district=request.district)
    return get_market_summary(county, request.district, request.period)


@router.post("/market-insights/refresh")
def post_market_read_model_refresh(
    response: Response,
    x_market_read_model_refresh_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Protected manual read model refresh for operators."""

    configured_token = os.getenv(MARKET_READ_MODEL_REFRESH_TOKEN_ENV, "").strip()
    if not configured_token:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return _safe_refresh_unavailable("refresh_runtime_not_configured", MARKET_REFRESH_TOKEN_UNAVAILABLE_MESSAGE)
    if x_market_read_model_refresh_token != configured_token:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            "status": "unavailable",
            "data_status": "unavailable",
            "coverage_status": "unknown",
            "built_at": None,
            "message": MARKET_REFRESH_FORBIDDEN_MESSAGE,
        }

    from services.market_insight_service import refresh_market_read_model
    from services.plvr_market_aggregate_service import safe_market_refresh_reason_code

    try:
        result = refresh_market_read_model()
    except Exception:
        result = _safe_refresh_unavailable("unknown_safe_failure", MARKET_REFRESH_UNAVAILABLE_MESSAGE)

    if result.get("status") != "resolved":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        reason_code = safe_market_refresh_reason_code(result.get("reason_code"))
        safe_result = {key: result.get(key) for key in MARKET_REFRESH_503_FIELDS}
        safe_result["status"] = safe_result.get("status") or "unavailable"
        safe_result["data_status"] = safe_result.get("data_status") or "unavailable"
        safe_result["coverage_status"] = safe_result.get("coverage_status") or "unknown"
        safe_result["built_at"] = safe_result.get("built_at")
        safe_result["message"] = MARKET_REFRESH_UNAVAILABLE_MESSAGE
        safe_result["reason_code"] = reason_code
        return safe_result

    return {key: result.get(key) for key in ("status", "data_status", "coverage_status", "built_at", "message")}


def _safe_refresh_unavailable(reason_code: str, message: str) -> dict[str, Any]:
    from services.plvr_market_aggregate_service import safe_market_refresh_reason_code

    return {
        "status": "unavailable",
        "data_status": "unavailable",
        "coverage_status": "unknown",
        "built_at": None,
        "message": message,
        "reason_code": safe_market_refresh_reason_code(reason_code),
    }
