"""Market Insight API routes backed by traceable market aggregates."""

from __future__ import annotations

import math
import os
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, ConfigDict, field_validator

router = APIRouter(tags=["market-insight"])
logger = logging.getLogger("proptech.market")
MARKET_READ_MODEL_REFRESH_TOKEN_ENV = "MARKET_READ_MODEL_REFRESH_TOKEN"
MARKET_REFRESH_503_FIELDS = ("status", "data_status", "coverage_status", "built_at", "message", "reason_code")
MARKET_NO_DATA_SUMMARY = "目前此區域尚無足夠的官方 PLVR 市場資料。"
MARKET_UNAVAILABLE_SUMMARY = "市場資料目前無法使用，請稍後再試。"
MARKET_QUERY_SAFE_FIELDS = (
    "city", "county", "district", "period", "average_unit_price", "avg_price_per_ping",
    "transaction_count", "transaction_volume", "record_count", "summary", "source_name",
    "source_updated_at", "coverage_status", "data_status", "caveat", "disclaimer",
    "source_file_hash", "aggregation_method", "history", "trend", "livability_score",
    "esg_lite_score", "poi_breakdown", "sdg11_note",
    "median_unit_price_ntd_sqm", "mean_unit_price_ntd_sqm", "lower_quartile_unit_price_ntd_sqm",
    "upper_quartile_unit_price_ntd_sqm", "median_total_price_ntd", "median_area_sqm", "sample_status",
    "aggregation_version", "source_release_id", "freshness_status",
    "period_change", "year_over_year_change", "price_distribution", "building_type_distribution",
    "age_band_distribution", "inclusion_count", "exclusion_count", "methodology", "latest_imported_at",
    "reason_code", "support_reference",
)
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


class MarketComparableRequest(BaseModel):
    """Bounded aggregate/comparable query; raw address and arbitrary SQL are forbidden."""

    model_config = ConfigDict(extra="forbid")

    county: str
    district: str
    transaction_type: str = "existing_sale"
    limit: int = 10

    @field_validator("limit")
    @classmethod
    def bound_limit(cls, value: int) -> int:
        if value < 1 or value > 10:
            raise ValueError("limit out of range")
        return value

    @field_validator("transaction_type")
    @classmethod
    def allowed_type(cls, value: str) -> str:
        if value not in {"existing_sale", "presale", "rental"}:
            raise ValueError("unsupported transaction type")
        return value


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


@router.get("/market-insights/methodology")
def get_market_insight_methodology() -> dict[str, Any]:
    from services.official_market_query import methodology

    return methodology()


@router.get("/market-insights/releases")
def get_market_insight_releases() -> dict[str, Any]:
    from services.official_market_query import release_status

    return release_status()


@router.post("/market-insights/comparables")
def post_market_insight_comparables(request: MarketComparableRequest) -> dict[str, Any]:
    from services.official_market_query import query_comparables

    return query_comparables(request.county, request.district, request.transaction_type, request.limit)


@router.post("/market-insights/query")
def post_market_insight_query(request: MarketInsightQuery) -> dict[str, Any]:
    """Return one traceable Market Insight summary, or unavailable."""

    from services.market_insight_service import get_market_summary

    support_reference = _new_market_support_reference()
    county = request.county or request.city or ""
    if not county.strip():
        return _safe_market_unavailable(
            county,
            request.district,
            "coverage_unknown",
            "market_region_invalid",
            support_reference,
        )
    try:
        result = get_market_summary(county, request.district, request.period)
    except Exception as exc:
        logger.exception(
            "market_query_unavailable %s",
            json.dumps(
                {
                    "event": "query_unavailable",
                    "support_reference": support_reference,
                    "operation": "route",
                    "reason_code": "market_unknown_safe_failure",
                    "exception_class": type(exc).__name__[:80] or "Exception",
                    "normalized_county": county.strip(),
                    "normalized_district": request.district.strip(),
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        return _safe_market_unavailable(
            county,
            request.district,
            "coverage_unknown",
            "market_unknown_safe_failure",
            support_reference,
        )
    return _safe_market_query_result(result, county, request.district, support_reference)


def _safe_market_query_result(
    raw: Any,
    county: str,
    district: str,
    fallback_support_reference: str | None = None,
) -> dict[str, Any]:
    """Allowlist and validate the public Market Insight result contract."""

    from services.plvr_market_aggregate_service import safe_market_query_reason_code

    support_reference = _safe_market_support_reference(
        raw.get("support_reference") if isinstance(raw, dict) else None,
        fallback_support_reference,
    )
    if not isinstance(raw, dict):
        return _safe_market_unavailable(
            county,
            district,
            "coverage_unknown",
            "market_result_contract_invalid",
            support_reference,
        )

    coverage_status = _safe_market_coverage(raw.get("coverage_status"))
    data_status = raw.get("data_status")
    raw_reason_code = raw.get("reason_code")
    if coverage_status == "covered":
        if data_status == "available" and _market_result_has_valid_metrics(raw):
            result = {key: raw.get(key) for key in MARKET_QUERY_SAFE_FIELDS}
            result["support_reference"] = support_reference
            if raw_reason_code:
                result["reason_code"] = safe_market_query_reason_code(raw_reason_code)
            return result
        reason_code = (
            safe_market_query_reason_code(raw_reason_code)
            if raw_reason_code
            else ("market_summary_missing" if data_status == "no_data" else "market_result_contract_invalid")
        )
        return _safe_market_no_data(raw, county, district, reason_code, support_reference)
    reason_code = safe_market_query_reason_code(raw_reason_code) if raw_reason_code else "market_coverage_not_confirmed"
    return _safe_market_unavailable(county, district, coverage_status, reason_code, support_reference)


def _market_result_has_valid_metrics(result: dict[str, Any]) -> bool:
    average = result.get("average_unit_price")
    average_alias = result.get("avg_price_per_ping")
    transaction_count = result.get("transaction_count")
    transaction_volume = result.get("transaction_volume")
    record_count = result.get("record_count")
    history = result.get("history")
    return (
        _positive_finite_number(average)
        and _positive_finite_number(average_alias)
        and average == average_alias
        and _positive_finite_number(transaction_count)
        and _positive_finite_number(transaction_volume)
        and transaction_count == transaction_volume
        and (_positive_finite_number(record_count) or _positive_finite_number(transaction_count))
        and bool(str(result.get("source_name") or "").strip())
        and isinstance(history, list)
    )


def _positive_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _safe_market_coverage(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"covered", "partial", "nationwide"}:
        return "covered"
    if text == "not_covered":
        return text
    return "coverage_unknown"


def _safe_market_no_data(
    raw: dict[str, Any],
    county: str,
    district: str,
    reason_code: str = "market_summary_missing",
    support_reference: str | None = None,
) -> dict[str, Any]:
    from services.plvr_market_aggregate_service import safe_market_query_reason_code

    result = {key: raw.get(key) for key in MARKET_QUERY_SAFE_FIELDS}
    result.update(
        {
            "city": raw.get("city") or county,
            "county": raw.get("county") or county,
            "district": raw.get("district") or district,
            "average_unit_price": None,
            "avg_price_per_ping": None,
            "transaction_count": None,
            "transaction_volume": None,
            "record_count": None,
            "coverage_status": "covered",
            "data_status": "no_data",
            "summary": MARKET_NO_DATA_SUMMARY,
            "history": [],
            "reason_code": safe_market_query_reason_code(reason_code),
            "support_reference": _safe_market_support_reference(raw.get("support_reference"), support_reference),
        }
    )
    return result


def _safe_market_unavailable(
    county: str,
    district: str,
    coverage_status: str,
    reason_code: str = "market_unknown_safe_failure",
    support_reference: str | None = None,
) -> dict[str, Any]:
    from services.plvr_market_aggregate_service import safe_market_query_reason_code
    from services.market_data_foundation import market_unavailable_response

    result = market_unavailable_response(city=county, district=district)
    result.update(
        {
            "average_unit_price": None,
            "avg_price_per_ping": None,
            "transaction_count": None,
            "transaction_volume": None,
            "record_count": None,
            "coverage_status": coverage_status if coverage_status in {"not_covered", "coverage_unknown"} else "coverage_unknown",
            "data_status": "unavailable",
            "summary": MARKET_UNAVAILABLE_SUMMARY,
            "history": [],
            "reason_code": safe_market_query_reason_code(reason_code),
            "support_reference": _safe_market_support_reference(None, support_reference),
        }
    )
    return {key: result.get(key) for key in MARKET_QUERY_SAFE_FIELDS}


def _new_market_support_reference() -> str:
    return uuid.uuid4().hex[:16]


def _safe_market_support_reference(value: Any, fallback: str | None = None) -> str:
    for candidate in (value, fallback):
        text = str(candidate or "").strip().lower()
        if len(text) == 16 and all(char in "0123456789abcdef" for char in text):
            return text
    return _new_market_support_reference()


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

    result = reconcile_market_coverage(request.county)
    if result.get("status") != "resolved":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "operation": "reconcile",
            "county": result.get("county") or request.county.strip(),
            "message": "Market coverage metadata is temporarily unavailable.",
            "reason_code": safe_market_coverage_reconcile_reason_code(result.get("reason_code")),
        }
    safe_result = {
        "status": result.get("status") or "unavailable",
        "operation": "reconcile",
        "county": result.get("county") or request.county.strip(),
        "coverage_status": result.get("coverage_status") or "coverage_unknown",
        "processed_region_count": int(result.get("processed_region_count") or 0),
        "covered_region_count": int(result.get("covered_region_count") or 0),
        "not_covered_region_count": int(result.get("not_covered_region_count") or 0),
        "unknown_region_count": int(result.get("unknown_region_count") or 0),
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
