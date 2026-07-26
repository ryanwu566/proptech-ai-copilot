"""Comparable-sales valuation API."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.valuation_result_contract import empty_estimate_result, public_source_details

router = APIRouter(prefix="/valuation", tags=["valuation"])


class ValuationRequest(BaseModel):
    city: str
    district: str
    road: str
    building_type: str
    area_ping: float = Field(gt=0)
    building_age_years: float = Field(ge=0)
    floor: int = Field(ge=0)
    lat: float | None = None
    lng: float | None = None
    address_text: str = ""


class ValuationTrendRequest(BaseModel):
    city: str
    district: str
    road: str
    building_type: str
    area_ping: float = Field(gt=0)
    building_age_years: float = Field(ge=0)
    horizon_months: list[int] = Field(default_factory=lambda: [6, 12, 36])


class PropertySearchRequest(BaseModel):
    city: str = ""
    districts: list[str] = Field(default_factory=list)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float = Field(gt=0)
    area_ping_min: float | None = Field(default=None, ge=0)
    area_ping_max: float | None = Field(default=None, ge=0)
    building_type: str = ""
    building_age_max: float | None = Field(default=None, ge=0)
    floor_min: int | None = Field(default=None, ge=0)
    period_since: str = ""
    limit: int = Field(default=50, ge=1, le=100)


@router.get("/data-status")
def data_status() -> dict[str, Any]:
    """Return the active valuation provider and coverage summary."""

    from services.valuation_service import get_valuation_data_status
    try:
        return _safe_data_status(get_valuation_data_status())
    except Exception:
        return _unavailable_data_status()


_DATA_STATUS_FIELDS = {
    "active_source", "is_demo_data", "is_full_taiwan", "data_composition", "official_records_count",
    "sample_records_count", "official_period_min", "official_period_max", "raw_official_period_min",
    "raw_official_period_max", "effective_trend_period_min", "effective_trend_period_max",
    "excluded_future_period_count", "excluded_too_old_period_count", "data_quality_note",
    "retention_policy_years", "retention_cutoff_period", "records_outside_retention_count",
    "oldest_effective_period", "newest_effective_period", "retention_note", "official_coverage_note",
    "coverage_city_count", "coverage_district_count", "coverage_road_count", "coverage_cities",
    "coverage_summary", "coverage_note_short", "latest_import_status", "latest_import_scope",
    "latest_import_inserted_rows", "latest_import_skipped_duplicates", "coverage", "last_updated",
    "update_frequency_note", "source_note", "user_message", "freshness_status", "freshness_reason_code",
    "freshness_as_of", "latest_import_at", "latest_import_age_days", "newest_effective_period_lag_months",
    "operator_attention_required", "freshness_user_message",
}


def _safe_data_status(status: Any) -> dict[str, Any]:
    """Keep the public status contract explicit and discard provider internals."""

    if not isinstance(status, dict):
        return _unavailable_data_status()
    safe = {key: status[key] for key in _DATA_STATUS_FIELDS if key in status}
    coverage = safe.get("coverage")
    if not isinstance(coverage, dict):
        coverage = {"cities": [], "districts": [], "roads_count": 0, "records_count": 0}
    safe["coverage"] = {
        "cities": coverage.get("cities") if isinstance(coverage.get("cities"), list) else [],
        "districts": coverage.get("districts") if isinstance(coverage.get("districts"), list) else [],
        "roads_count": _safe_nonnegative_int(coverage.get("roads_count")),
        "records_count": _safe_nonnegative_int(coverage.get("records_count")),
    }
    safe.setdefault("active_source", "unknown")
    safe.setdefault("freshness_status", "unavailable")
    safe.setdefault("freshness_reason_code", "provider_unavailable")
    safe.setdefault("freshness_as_of", None)
    safe.setdefault("latest_import_at", None)
    safe.setdefault("latest_import_age_days", None)
    safe.setdefault("newest_effective_period_lag_months", None)
    safe.setdefault("operator_attention_required", True)
    safe.setdefault("freshness_user_message", "目前無法讀取官方 PLVR 資料新鮮度，請稍後再試。")
    return safe


def _unavailable_data_status() -> dict[str, Any]:
    return _safe_data_status(
        {
            "active_source": "unavailable",
            "is_demo_data": False,
            "is_full_taiwan": False,
            "official_records_count": 0,
            "sample_records_count": 0,
            "coverage": {"cities": [], "districts": [], "roads_count": 0, "records_count": 0},
            "latest_import_status": None,
            "last_updated": None,
            "source_note": "估價資料狀態暫時無法讀取。",
            "user_message": "估價資料狀態暫時無法讀取，請稍後再試。",
            "freshness_status": "unavailable",
            "freshness_reason_code": "provider_unavailable",
            "freshness_as_of": None,
            "latest_import_at": None,
            "latest_import_age_days": None,
            "newest_effective_period_lag_months": None,
            "operator_attention_required": True,
            "freshness_user_message": "目前無法讀取官方 PLVR 資料新鮮度，請稍後再試。",
        }
    )


def _safe_estimate_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return empty_estimate_result(_unavailable_data_status(), status="unavailable", reason_code="result_contract_unavailable", result_origin="none", provider_source="unavailable")
    safe = {key: value[key] for key in {
        "source", "valuation_status", "valuation_reason_code", "result_origin", "is_actionable",
        "estimate_level", "matched_community", "confidence_reason", "estimate_data_composition",
        "data_composition", "estimate_source_label", "candidate_pool_size", "official_same_road_count",
        "official_same_district_count", "sample_same_road_count", "sample_same_district_count",
        "estimate_total_price", "estimate_unit_price_per_ping", "price_range", "unit_price_distribution",
        "confidence", "confidence_score", "comparables", "valuation_explanation", "methodology", "disclaimer",
    } if key in value}
    safe["data_status"] = _safe_data_status(value.get("data_status"))
    safe["source_details"] = public_source_details(value.get("source_details"))
    return safe


def _safe_trend_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _empty_trend_response("unavailable", "result_contract_unavailable")
    fields = {
        "source", "trend_status", "trend_reason_code", "is_actionable", "data_scope", "raw_period_min",
        "raw_period_max", "effective_period_min", "effective_period_max", "excluded_future_period_count",
        "excluded_out_of_window_count", "period_min", "period_max", "sample_count", "road_sample_count",
        "district_sample_count", "monthly_series", "yearly_series", "recent_median_unit_price",
        "trend_annualized_rate", "volatility", "confidence_level", "confidence_reason", "scenario_forecast",
        "methodology", "disclaimer",
    }
    return {key: value[key] for key in fields if key in value}


def _empty_trend_response(status: str, reason_code: str) -> dict[str, Any]:
    return {
        "source": "official_plvr_opendata", "trend_status": status, "trend_reason_code": reason_code,
        "is_actionable": False, "data_scope": "none", "raw_period_min": None, "raw_period_max": None,
        "effective_period_min": None, "effective_period_max": None, "excluded_future_period_count": 0,
        "excluded_out_of_window_count": 0, "period_min": None, "period_max": None, "sample_count": 0,
        "road_sample_count": 0, "district_sample_count": 0, "monthly_series": [], "yearly_series": [],
        "recent_median_unit_price": None, "trend_annualized_rate": None, "volatility": None,
        "confidence_level": "unknown", "confidence_reason": "估價趨勢資料目前無法使用，請稍後再試。",
        "scenario_forecast": {"conservative": [], "base": [], "optimistic": []}, "methodology": [], "disclaimer": "",
    }


def _safe_property_search_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _empty_property_search_response("unavailable", "result_contract_unavailable")
    safe = {key: value[key] for key in {"search_status", "search_reason_code", "is_actionable", "summary", "district_suggestions", "road_suggestions", "matched_transactions", "methodology", "disclaimer"} if key in value}
    summary = value.get("summary")
    if not isinstance(summary, dict):
        return _empty_property_search_response("unavailable", "result_contract_unavailable")
    safe["summary"] = {key: summary.get(key) for key in {"matched_count", "city_count", "district_count", "road_count", "budget_min", "budget_max", "period_min", "period_max", "data_source_label", "message", "disclaimer"}}
    return safe


def _empty_property_search_response(status: str, reason_code: str) -> dict[str, Any]:
    return {
        "search_status": status, "search_reason_code": reason_code, "is_actionable": False,
        "summary": {"matched_count": None, "city_count": None, "district_count": None, "road_count": None, "budget_min": None, "budget_max": None, "period_min": None, "period_max": None, "data_source_label": "官方 PLVR", "message": "市場資料目前無法使用，請稍後再試。", "disclaimer": ""},
        "district_suggestions": [], "road_suggestions": [], "matched_transactions": [], "methodology": "", "disclaimer": "",
    }


def _safe_nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


@router.post("/estimate")
def estimate(request: ValuationRequest) -> dict[str, Any]:
    from services.valuation_service import estimate_property
    try:
        return _safe_estimate_response(estimate_property(request.model_dump()))
    except Exception:
        return _safe_estimate_response(None)


@router.post("/trend")
def trend(request: ValuationTrendRequest) -> dict[str, Any]:
    """Return official-PLVR historical trends and bounded scenarios."""

    from services.valuation_trend_service import analyze_valuation_trend
    try:
        return _safe_trend_response(analyze_valuation_trend(request.model_dump()))
    except Exception:
        return _empty_trend_response("unavailable", "result_contract_unavailable")


@router.post("/property-search")
def property_search(request: PropertySearchRequest) -> dict[str, Any]:
    """Return official historical transaction directions, not live listings."""

    from services.property_search_service import search_properties
    try:
        return _safe_property_search_response(search_properties(request.model_dump()))
    except Exception:
        return _empty_property_search_response("unavailable", "result_contract_unavailable")
