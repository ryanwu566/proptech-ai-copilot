"""Decision-oriented location insight built from existing map capabilities."""

from __future__ import annotations

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
) -> dict[str, Any]:
    """Resolve a location and summarize existing POI evidence with explicit rules."""

    searcher = searcher or search_location
    nearby_fetcher = nearby_fetcher or get_nearby_places
    query = address.strip() or "".join(part.strip() for part in (city, district, road) if part.strip())
    resolved = _resolve_location(query, latitude, longitude, searcher)
    input_summary = {
        "city": city, "district": district, "road": road, "address": address,
        "latitude": latitude, "longitude": longitude, "radius_m": radius_m,
        "property_price_wan": property_price, "area_ping": area_ping, "building_type": building_type,
        "use_existing_poi_sources": use_existing_poi_sources,
    }
    if resolved is None:
        return _unavailable_result(input_summary, radius_m)

    try:
        nearby = nearby_fetcher(resolved["latitude"], resolved["longitude"], radius_m, POI_CATEGORIES) if use_existing_poi_sources else _empty_nearby()
    except Exception:
        nearby = _empty_nearby()
    score_map = nearby.get("category_score_map", {})
    category_scores = {
        "transit_score": _score(score_map.get("transport")),
        "convenience_score": round((_score(score_map.get("shopping")) + _score(score_map.get("food"))) / 2),
        "education_score": _score(score_map.get("school")),
        "green_space_score": _score(score_map.get("park")),
        "medical_score": _score(score_map.get("medical")),
        "risk_score": 50,
    }
    has_poi_evidence = any(group.get("count", 0) for group in nearby.get("categories", []))
    location_score = round(sum(category_scores[key] * weight for key, weight in SCORE_WEIGHTS.items())) if has_poi_evidence else None
    counts = {group["category"]: int(group.get("count", 0)) for group in nearby.get("categories", [])}
    poi_summary = {
        "transit_count": counts.get("transport", 0),
        "convenience_count": counts.get("shopping", 0) + counts.get("food", 0),
        "school_count": counts.get("school", 0),
        "park_count": counts.get("park", 0),
        "medical_count": counts.get("medical", 0),
        "risk_facility_count": 0,
    }
    strengths, weaknesses = _strengths_and_weaknesses(category_scores, has_poi_evidence)
    source = nearby.get("source", "unavailable")
    missing_sources = ["risk_facilities"]
    warnings = ["目前沒有既有嫌惡設施資料來源，風險分數採中性 50，請實地確認。"]
    if source == "mock":
        warnings.append("附近 POI 使用既有展示資料 fallback，僅供流程與比較參考。")
    if not has_poi_evidence:
        warnings.append("目前資料不足，建議改用完整地址或手動查詢。")
    status = "good" if source == "google_places" and has_poi_evidence else "limited" if has_poi_evidence else "unavailable"

    return {
        "input": input_summary,
        "resolved_location": resolved,
        "radius_m": radius_m,
        "location_score": location_score,
        "category_scores": category_scores,
        "poi_summary": poi_summary,
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
        "data_quality": {"status": status, "missing_sources": missing_sources, "warnings": warnings},
        "scoring_method": {"weights": SCORE_WEIGHTS, "explanation": "沿用既有 POI 數量與距離分數，再依交通 30%、便利 25%、教育 15%、公園 10%、醫療 10%、風險 10% 加權。"},
        "disclaimer": DISCLAIMER,
    }


def _resolve_location(query: str, latitude: float | None, longitude: float | None, searcher: Callable[[str], dict[str, Any]]) -> dict[str, Any] | None:
    if latitude is not None and longitude is not None:
        return {"address_label": query or "使用者提供座標", "latitude": latitude, "longitude": longitude, "geocoding_confidence": "provided_coordinates"}
    if not query:
        return None
    found = searcher(query)
    center = found.get("center") if found.get("matched") else None
    if not center:
        return None
    return {
        "address_label": found.get("formatted_address") or query,
        "latitude": float(center["lat"]),
        "longitude": float(center["lng"]),
        "geocoding_confidence": found.get("confidence", "unknown"),
    }


def _strengths_and_weaknesses(scores: dict[str, int], has_evidence: bool) -> tuple[list[str], list[str]]:
    if not has_evidence:
        return [], ["目前資料不足，建議改用完整地址或手動查詢。"]
    labels = {"transit_score": "交通便利", "convenience_score": "日常採買與餐飲", "education_score": "教育資源", "green_space_score": "公園綠地", "medical_score": "醫療資源"}
    strengths = [f"{labels[key]}覆蓋較完整（{scores[key]} 分）。" for key in labels if scores[key] >= 65]
    weaknesses = [f"{labels[key]}覆蓋偏弱（{scores[key]} 分），建議實地確認。" for key in labels if scores[key] < 40]
    return strengths or ["各類生活機能分布相對均衡。"], weaknesses or ["未發現明顯弱項，但仍需實地確認尖峰交通與環境狀況。"]


def _buyer_fit(scores: dict[str, int], has_evidence: bool) -> dict[str, str]:
    if not has_evidence:
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


def _unavailable_result(input_summary: dict[str, Any], radius_m: int) -> dict[str, Any]:
    return {
        "input": input_summary, "resolved_location": None, "radius_m": radius_m, "location_score": None,
        "category_scores": {"transit_score": 0, "convenience_score": 0, "education_score": 0, "green_space_score": 0, "medical_score": 0, "risk_score": 50},
        "poi_summary": {"transit_count": 0, "convenience_count": 0, "school_count": 0, "park_count": 0, "medical_count": 0, "risk_facility_count": 0},
        "nearest_pois": [], "strengths": [], "weaknesses": ["目前資料不足，建議改用完整地址或手動查詢。"],
        "buyer_fit": {key: "資料不足" for key in ("self_use_family", "commuter", "investor", "elderly")},
        "valuation_context": {"supports_price_reasonableness": "unknown", "explanation": "定位失敗，無法提供價格合理性補充。"},
        "data_quality": {"status": "unavailable", "missing_sources": ["geocoding", "poi", "risk_facilities"], "warnings": ["找不到符合的地點，請輸入完整地址、路段或座標。"]},
        "scoring_method": {"weights": SCORE_WEIGHTS, "explanation": "定位或資料不足，未產生區位總分。"}, "disclaimer": DISCLAIMER,
    }


def _empty_nearby() -> dict[str, Any]:
    return {"source": "unavailable", "categories": [], "category_score_map": {}, "nearest_places": []}


def _score(value: Any) -> int:
    return max(0, min(100, int(value or 0)))
