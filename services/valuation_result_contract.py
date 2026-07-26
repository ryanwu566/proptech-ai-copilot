"""Public valuation result boundary and safe empty-result constructors."""

from __future__ import annotations

import math
from typing import Any

VALUATION_STATUSES = ("available", "no_data", "unavailable", "demo")
RESULT_ORIGINS = ("official", "demo", "none")
VALUATION_REASON_CODES = (
    "official_result_available", "demo_result_available", "official_comparables_insufficient",
    "official_data_missing", "provider_unavailable", "provider_query_failed", "invalid_request",
    "invalid_provider_result", "result_metrics_invalid", "result_contract_unavailable",
)
PUBLIC_SOURCE_DETAIL_KEYS = {
    "provider_active", "candidate_pool_size", "query_scope", "requested_city",
    "requested_district", "requested_road", "db_rows_returned", "query_status",
}


def finite_positive(value: Any) -> bool:
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def empty_estimate_result(
    data_status: dict[str, Any],
    *,
    status: str,
    reason_code: str,
    result_origin: str,
    provider_source: str,
    sample_count: int = 0,
    matched_community: dict[str, Any] | None = None,
    query_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a response with null valuation numbers for non-actionable states."""

    explanation = {
        "sample_count": max(0, int(sample_count)), "same_road_count": 0, "same_district_count": 0,
        "same_city_count": 0, "same_building_type_count": 0, "nearest_distance_m": None,
        "average_area_difference_ping": None, "average_age_difference_years": None,
        "average_similarity_score": None, "method": "目前沒有足夠資料形成估價。",
    }
    metadata = {key: value for key, value in (query_metadata or {}).items() if key in PUBLIC_SOURCE_DETAIL_KEYS}
    return {
        "source": provider_source,
        "data_status": data_status,
        "valuation_status": status,
        "valuation_reason_code": reason_code,
        "result_origin": result_origin,
        "is_actionable": False,
        "estimate_level": "none" if status != "demo" else "demo",
        "matched_community": matched_community,
        "confidence_reason": "目前無法提供可用的正式估價數字。",
        "estimate_data_composition": "unavailable" if status == "unavailable" else "official" if status == "no_data" else "sample",
        "data_composition": "unavailable" if status == "unavailable" else "official" if status == "no_data" else "sample",
        "estimate_source_label": "官方資料不足" if status == "no_data" else "估價資料不可用" if status == "unavailable" else "展示資料",
        "candidate_pool_size": metadata.get("candidate_pool_size", 0),
        "official_same_road_count": 0, "official_same_district_count": 0,
        "sample_same_road_count": 0, "sample_same_district_count": 0,
        "source_details": metadata,
        "estimate_total_price": None, "estimate_unit_price_per_ping": None,
        "price_range": {"low": None, "mid": None, "high": None},
        "unit_price_distribution": {"weighted_mean": None, "weighted_median": None, "p25": None, "p75": None},
        "confidence": None, "confidence_score": None, "comparables": [],
        "valuation_explanation": explanation,
        "methodology": ["至少需要三筆同一城市的有效官方 PLVR 可比成交，才會形成正式估價。"],
        "disclaimer": "資料不足或服務不可用時不提供估價數字；本結果不代表正式鑑價、核貸或投資建議。",
    }


def validate_official_result(result: dict[str, Any]) -> bool:
    """Validate the fields that make an estimate safe to call actionable."""

    if result.get("source") != "postgres" or result.get("result_origin") != "official":
        return False
    comparables = result.get("comparables")
    if not isinstance(comparables, list) or len(comparables) < 3:
        return False
    if not all(isinstance(item, dict) and item.get("source") == "official_plvr_opendata" for item in comparables):
        return False
    if not all(finite_positive(result.get(key)) for key in ("estimate_total_price", "estimate_unit_price_per_ping")):
        return False
    price_range = result.get("price_range") or {}
    values = [price_range.get(key) for key in ("low", "mid", "high")]
    if not all(finite_positive(value) for value in values) or values != sorted(values):
        return False
    score = result.get("confidence_score")
    if not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0 <= float(score) <= 100:
        return False
    return isinstance(result.get("methodology"), list) and bool(str(result.get("disclaimer", "")).strip())


def public_source_details(value: Any) -> dict[str, Any]:
    return {key: value[key] for key in PUBLIC_SOURCE_DETAIL_KEYS if isinstance(value, dict) and key in value}
