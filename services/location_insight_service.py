"""Decision-oriented location insight built from existing map capabilities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from services.map_service import get_nearby_places, search_location


DISCLAIMER = "本區位分析僅供買房前生活機能檢查，不是精準地理評估、正式不動產鑑價或投資保證。"
POI_CATEGORIES = ["transport", "school", "park", "medical", "shopping", "food"]
SCORE_WEIGHTS = {"transit_score": 0.30, "convenience_score": 0.25, "education_score": 0.15, "green_space_score": 0.10, "medical_score": 0.10, "risk_score": 0.10}


def analyze_location(
    city: str = "",
    district: str = "",
    road: str = "",
    address: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: int = 800,
    property_price: float | None = None,
    area_ping: float | None = None,
    building_type: str = "",
    use_existing_poi_sources: bool = True,
    searcher: Callable[[str], dict[str, Any]] | None = None,
    nearby_fetcher: Callable[[float, float, int, list[str]], dict[str, Any]] | None = None,
    village_resolver: Any | None = None,
) -> dict[str, Any]:
    """Resolve a location and summarize existing POI evidence with explicit rules."""

    searcher = searcher or search_location
    nearby_fetcher = nearby_fetcher or get_nearby_places
    query = address.strip() or "".join(part.strip() for part in (city, district, road) if part.strip())
    resolved, geocoding_acceptance = _resolve_location(query, latitude, longitude, searcher)
    input_summary = {
        "city": city, "district": district, "road": road, "address": address,
        "latitude": latitude, "longitude": longitude, "radius_m": radius_m,
        "property_price_wan": property_price, "area_ping": area_ping, "building_type": building_type,
        "use_existing_poi_sources": use_existing_poi_sources,
    }
    if resolved is None:
        return _unavailable_result(input_summary, radius_m, geocoding_acceptance)

    village_resolution, demographics = _resolve_village(
        resolved["latitude"], resolved["longitude"], village_resolver
    )

    try:
        nearby = nearby_fetcher(resolved["latitude"], resolved["longitude"], radius_m, POI_CATEGORIES) if use_existing_poi_sources else _empty_nearby()
    except Exception:
        nearby = _empty_nearby()
    quality = _poi_quality(nearby)
    failed = set(quality["failed_categories"])
    counts = {group["category"]: int(group.get("count", 0)) for group in nearby.get("categories", [])}
    # A missing/failed category is unknown. Only a successful query can say zero.
    def count(category: str) -> int | None:
        return counts.get(category) if category not in failed or quality["source"] == "mock" else None

    score_map = nearby.get("category_score_map", {})
    def score(category: str) -> int | None:
        return _score(score_map.get(category)) if count(category) is not None else None

    category_scores = {
        "transit_score": score("transport"),
        "convenience_score": round((score("shopping") + score("food")) / 2) if score("shopping") is not None and score("food") is not None else None,
        "education_score": score("school"),
        "green_space_score": score("park"),
        "medical_score": score("medical"),
        "risk_score": None,
    }
    has_poi_evidence = any(group.get("count", 0) for group in nearby.get("categories", []))
    location_score = round(sum(category_scores[key] * weight for key, weight in SCORE_WEIGHTS.items())) if has_poi_evidence and all(value is not None for value in category_scores.values()) else None
    poi_summary = {
        "transit_count": count("transport"),
        "convenience_count": count("shopping") + count("food") if count("shopping") is not None and count("food") is not None else None,
        "school_count": count("school"),
        "park_count": count("park"),
        "medical_count": count("medical"),
        "risk_facility_count": None,
    }
    strengths, weaknesses = _strengths_and_weaknesses(category_scores, has_poi_evidence)
    source = nearby.get("source", "unavailable")
    missing_sources = ["risk_facilities", *[f"poi:{category}" for category in POI_CATEGORIES if category in failed or count(category) is None]]
    warnings = ["需留意設施來源目前無法取得；風險分數與區位總分資料不足，請實地確認。"]
    if source == "mock":
        warnings.append("附近 POI 使用既有展示資料 fallback，僅供流程與比較參考。")
    if not has_poi_evidence:
        warnings.append("目前資料不足，建議改用完整地址或手動查詢。")
    if quality["partial"]:
        warnings.append("部分 POI 類別目前無法取得；已成功類別保留，缺失類別不代表零處設施。")
    status = quality["status"]

    return {
        "input": input_summary,
        "resolved_location": resolved,
        "village_resolution": village_resolution,
        "demographics": demographics,
        "geocoding_acceptance": geocoding_acceptance,
        "radius_m": radius_m,
        "location_score": location_score,
        "category_scores": category_scores,
        "poi_summary": poi_summary,
        "risk_facility_evidence": {"status": "unavailable", "count": None, "source": None, "checked_at": None, "reason": "risk_facilities_source_unavailable", "limitation": "未知涵蓋不代表零處設施或安全。"},
        "nearest_pois": [
            {
                "category": item.get("category", ""),
                "name": item.get("name", "未命名地點"),
                "distance_m": round(float(item.get("distance_m", 0))),
                "source": item.get("source", source),
            }
            for item in nearby.get("nearest_places", [])[:8]
        ],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "buyer_fit": _buyer_fit(category_scores, has_poi_evidence),
        "valuation_context": {
            "supports_price_reasonableness": "unknown",
            "explanation": _valuation_context(property_price, area_ping, location_score),
        },
        "data_quality": {**quality, "status": status, "missing_sources": missing_sources, "warnings": warnings},
        "scoring_method": {"weights": SCORE_WEIGHTS, "explanation": "個別生活機能分數沿用既有 POI 數量與距離。風險來源缺失，未產生區位總分；不重新分配缺失維度的權重。"},
        "disclaimer": DISCLAIMER,
    }


def _resolve_location(query: str, latitude: float | None, longitude: float | None, searcher: Callable[[str], dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if latitude is not None and longitude is not None:
        acceptance = {
            "original_query": query,
            "normalized_address": query or "使用者提供座標",
            "resolved_lat": latitude,
            "resolved_lng": longitude,
            "geocoding_source": "provided_coordinates",
            "match_quality": "EXACT_OR_ACCEPTABLE",
            "accepted_for_analysis": True,
            "requires_confirmation": False,
            "mismatch_reasons": [],
            "message": "使用者提供座標，後續證據將綁定此座標。",
        }
        return {"address_label": query or "使用者提供座標", "latitude": latitude, "longitude": longitude, "geocoding_confidence": "provided_coordinates"}, acceptance
    if not query:
        return None, None
    found = searcher(query)
    acceptance = found.get("geocoding_acceptance") if isinstance(found.get("geocoding_acceptance"), dict) else None
    if acceptance and not acceptance.get("accepted_for_analysis"):
        return None, acceptance
    center = found.get("center") if found.get("matched") else None
    if not center:
        return None, acceptance
    return {
        "address_label": found.get("formatted_address") or query,
        "latitude": float(center["lat"]),
        "longitude": float(center["lng"]),
        "geocoding_confidence": found.get("confidence", "unknown"),
    }, acceptance


def _strengths_and_weaknesses(scores: dict[str, int | None], has_evidence: bool) -> tuple[list[str], list[str]]:
    if not has_evidence:
        return [], ["目前資料不足，建議改用完整地址或手動查詢。"]
    labels = {"transit_score": "交通便利", "convenience_score": "日常採買與餐飲", "education_score": "教育資源", "green_space_score": "公園綠地", "medical_score": "醫療資源"}
    strengths = [f"{labels[key]}覆蓋較完整（{scores[key]} 分）。" for key in labels if scores[key] is not None and scores[key] >= 65]
    weaknesses = [f"{labels[key]}覆蓋偏弱（{scores[key]} 分），建議實地確認。" for key in labels if scores[key] is not None and scores[key] < 40]
    weaknesses.extend(f"{labels[key]}資料目前無法取得。" for key in labels if scores[key] is None)
    if scores["risk_score"] is None:
        weaknesses.append("風險來源未取得，整體適用性資料不足。")
    return strengths, weaknesses


def _buyer_fit(scores: dict[str, int | None], has_evidence: bool) -> dict[str, str]:
    if not has_evidence or any(value is None for value in scores.values()):
        return {key: "資料不足" for key in ("self_use_family", "commuter", "investor", "elderly")}
    return {
        "self_use_family": "適合" if scores["education_score"] >= 60 and scores["green_space_score"] >= 50 else "需確認教育與休憩資源",
        "commuter": "適合" if scores["transit_score"] >= 60 else "需確認通勤方式",
        "investor": "可進一步評估" if scores["transit_score"] >= 60 and scores["convenience_score"] >= 60 else "生活機能支撐有限",
        "elderly": "適合" if scores["medical_score"] >= 60 and scores["convenience_score"] >= 50 else "需確認醫療與採買距離",
    }


def _valuation_context(property_price: float | None, area_ping: float | None, location_score: int | None) -> str:
    if property_price is None or area_ping is None:
        return "未提供完整價格與坪數，區位資料只能補充生活機能，不能判斷價格合理性。"
    return f"本物件約 {round(property_price / area_ping, 1)} 萬／坪；區位總分 {location_score if location_score is not None else '資料不足'}，仍需搭配可比成交判斷價格。"


def _unavailable_result(input_summary: dict[str, Any], radius_m: int, geocoding_acceptance: dict[str, Any] | None = None) -> dict[str, Any]:
    acceptance_warning = str((geocoding_acceptance or {}).get("message") or "找不到符合的地點，請輸入完整地址、路段或座標。")
    return {
        "input": input_summary, "resolved_location": None, "village_resolution": {"status": "unavailable", "reason": "location_not_resolved"}, "demographics": {"status": "no_data", "reason": "location_not_resolved"}, "geocoding_acceptance": geocoding_acceptance, "radius_m": radius_m, "location_score": None,
        "category_scores": {"transit_score": None, "convenience_score": None, "education_score": None, "green_space_score": None, "medical_score": None, "risk_score": None},
        "poi_summary": {"transit_count": None, "convenience_count": None, "school_count": None, "park_count": None, "medical_count": None, "risk_facility_count": None},
        "nearest_pois": [], "strengths": [], "weaknesses": ["目前資料不足，建議改用完整地址或手動查詢。"],
        "buyer_fit": {key: "資料不足" for key in ("self_use_family", "commuter", "investor", "elderly")},
        "valuation_context": {"supports_price_reasonableness": "unknown", "explanation": "定位失敗，無法提供價格合理性補充。"},
        "data_quality": {"status": "unavailable", "missing_sources": ["geocoding", "poi", "risk_facilities"], "warnings": [acceptance_warning]},
        "scoring_method": {"weights": SCORE_WEIGHTS, "explanation": "定位或資料不足，未產生區位總分。"}, "disclaimer": DISCLAIMER,
    }


def _resolve_village(
    latitude: float,
    longitude: float,
    village_resolver: Any | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        if village_resolver is None:
            from services.ris_village_resolver import get_default_ris_village_resolver

            village_resolver = get_default_ris_village_resolver()
        result = village_resolver.resolve(latitude=latitude, longitude=longitude)
        village = result.get("location") if isinstance(result, dict) else None
        demographics = result.get("demographics") if isinstance(result, dict) else None
        if not isinstance(village, dict) or not isinstance(demographics, dict):
            raise ValueError("invalid village resolver result")
        return village, demographics
    except Exception:
        return (
            {"status": "unavailable", "reason": "village_resolver_unavailable"},
            {"status": "no_data", "reason": "demographics_unavailable"},
        )


def _empty_nearby() -> dict[str, Any]:
    return {"source": "unavailable", "categories": [], "category_score_map": {}, "nearest_places": []}


def _poi_quality(nearby: dict[str, Any]) -> dict[str, Any]:
    source = str(nearby.get("source") or "unavailable")
    groups = {group["category"]: group for group in nearby.get("categories", [])}
    statuses = nearby.get("category_status") or {
        category: {"status": "available" if source == "google_places" else "fallback", "source": source}
        for category in groups
    }
    failed = [category for category in POI_CATEGORIES if category in nearby.get("failed_categories", []) or statuses.get(category, {}).get("status") == "error"]
    successful = sum(statuses.get(category, {}).get("status") == "available" and source == "google_places" for category in POI_CATEGORIES)
    partial = source == "google_places" and (bool(failed) or successful < len(POI_CATEGORIES) or nearby.get("partial") is True or nearby.get("evidence_quality", {}).get("status") == "partial")
    status = "good" if source == "google_places" and not partial else "limited" if source == "google_places" and successful or source == "mock" and groups else "unavailable"
    return {"status": status, "source": source, "partial": partial, "failed_categories": failed, "category_status": statuses, "coverage": {"requested": len(POI_CATEGORIES), "successful": successful, "failed": len(failed)}, "checked_at": nearby.get("checked_at") or datetime.now(UTC).isoformat()}


def _score(value: Any) -> int:
    return max(0, min(100, int(value or 0)))
