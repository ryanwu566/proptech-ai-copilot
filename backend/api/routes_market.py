"""Market Insight API routes backed by traceable market aggregates."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, ConfigDict, field_validator

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


class MarketCoverageReconcileRequest(BaseModel):
    """Bounded operator request for one county coverage reconcile."""

    model_config = ConfigDict(extra="forbid")

    county: str

    @field_validator("county")
    @classmethod
    def require_canonical_county(cls, value: str) -> str:
        from services.taiwan_admin_registry import normalize_market_region

        normalized = normalize_market_region(value)
        if not normalized.valid or normalized.district:
            raise ValueError("invalid county")
        return normalized.county


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


@router.post("/market-insights/coverage/bootstrap")
def post_market_coverage_bootstrap(
    response: Response,
    x_market_read_model_refresh_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Protected operator setup for market coverage metadata."""

    if not _authorized_market_operator(response, x_market_read_model_refresh_token):
        return _market_operator_auth_failure(response)

    from services.plvr_market_aggregate_service import bootstrap_market_coverage_metadata

    result = bootstrap_market_coverage_metadata()
    safe_result = {
        "status": result.get("status") or "unavailable",
        "operation": "bootstrap",
        "migration_status": result.get("migration_status") or "unavailable",
        "message": result.get("message") or "Market coverage metadata is temporarily unavailable.",
    }
    if safe_result["status"] != "resolved":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        from services.plvr_market_aggregate_service import safe_market_coverage_bootstrap_reason_code

        safe_result["reason_code"] = safe_market_coverage_bootstrap_reason_code(result.get("reason_code"))
    return safe_result


@router.post("/market-insights/coverage/reconcile")
def post_market_coverage_reconcile(
    request: MarketCoverageReconcileRequest,
    response: Response,
    x_market_read_model_refresh_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Protected operator coverage reconciliation for one county."""

    if not _authorized_market_operator(response, x_market_read_model_refresh_token):
        return _market_operator_auth_failure(response)

    from services.plvr_market_aggregate_service import reconcile_market_coverage, safe_market_coverage_reconcile_reason_code

    try:
        result = reconcile_market_coverage(request.county)
    except Exception:
        result = {
            "status": "unavailable",
            "operation": "reconcile",
            "county": request.county.strip(),
            "reason_code": "coverage_reconcile_unknown_safe_failure",
        }
    if not isinstance(result, dict) or result.get("status") != "resolved":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "operation": "reconcile",
            "county": result.get("county") if isinstance(result, dict) else request.county.strip(),
            "message": "Market coverage metadata is temporarily unavailable.",
            "reason_code": safe_market_coverage_reconcile_reason_code(
                result.get("reason_code") if isinstance(result, dict) else None
            ),
        }
    safe_result = {
        "status": result.get("status") or "unavailable",
        "operation": "reconcile",
        "county": result.get("county") or request.county.strip(),
        "coverage_status": result.get("coverage_status") or "coverage_unknown",
        "processed_region_count": _safe_non_negative_int(result.get("processed_region_count")),
        "covered_region_count": _safe_non_negative_int(result.get("covered_region_count")),
        "not_covered_region_count": _safe_non_negative_int(result.get("not_covered_region_count")),
        "unknown_region_count": _safe_non_negative_int(result.get("unknown_region_count")),
        "persistence_status": result.get("persistence_status") or "applied",
        "message": result.get("message") or "Market coverage metadata is temporarily unavailable.",
    }
    return safe_result


@router.post("/market-insights/coverage/audit")
def post_market_coverage_audit(
    response: Response,
    x_market_read_model_refresh_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Protected operator audit of coverage metadata against the canonical registry."""

    if not _authorized_market_operator(response, x_market_read_model_refresh_token):
        return _market_operator_auth_failure(response)

    from services.plvr_market_aggregate_service import audit_market_coverage

    result = audit_market_coverage()
    return {
        "MARKET_COVERAGE": result.get("status") or "UNKNOWN",
        "EXPECTED_REGION_COUNT": int(result.get("expected_region_count") or 0),
        "COVERED_REGION_COUNT": int(result.get("covered_region_count") or 0),
        "MISSING_REGION_COUNT": int(result.get("missing_region_count") or 0),
        "UNKNOWN_REGION_COUNT": int(result.get("unknown_region_count") or 0),
        "MISSING_REGIONS": result.get("missing_regions") if isinstance(result.get("missing_regions"), list) else [],
        "UNKNOWN_REGIONS": result.get("unknown_regions") if isinstance(result.get("unknown_regions"), list) else [],
    }


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


def _safe_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _authorized_market_operator(response: Response, token: str | None) -> bool:
    configured_token = os.getenv(MARKET_READ_MODEL_REFRESH_TOKEN_ENV, "").strip()
    if not configured_token:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return False
    if token != configured_token:
        response.status_code = status.HTTP_403_FORBIDDEN
        return False
    return True


def _market_operator_auth_failure(response: Response) -> dict[str, Any]:
    if response.status_code == status.HTTP_403_FORBIDDEN:
        return {
            "status": "unavailable",
            "data_status": "unavailable",
            "coverage_status": "unknown",
            "built_at": None,
            "message": MARKET_REFRESH_FORBIDDEN_MESSAGE,
        }
    return _safe_refresh_unavailable("refresh_runtime_not_configured", MARKET_REFRESH_TOKEN_UNAVAILABLE_MESSAGE)
