"""Mock-first Map Insight Lite service with stable frontend contracts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from services.adapters.geocoding_adapter import GeocodingAdapter, GoogleGeocodingAdapter, MockGeocodingAdapter
from services.adapters.google_places_adapter import GooglePlacesAdapter, distance_meters
from services.adapters.poi_adapter import MockPoiAdapter, PoiAdapter
from services.adapters.traffic_adapter import MockTrafficAdapter, TrafficAdapter


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_map_points.json"
SEARCH_DISCLAIMER = "展示型 mock data，不代表正式地址定位結果"
INSIGHT_DISCLAIMER = "展示型 mock data，不代表正式估價、投資或交通分析"
NEARBY_DISCLAIMER = "生活機能資料僅供展示與區域理解，不代表正式估價、投資或交通分析。"
CATEGORY_LABELS = {
    "transport": "交通",
    "school": "學校",
    "park": "公園",
    "medical": "醫療",
    "shopping": "商圈",
    "food": "餐飲",
}
CATEGORY_WEIGHTS = {"transport": 25, "food": 20, "shopping": 20, "school": 15, "medical": 10, "park": 10}
DEFAULT_GOOGLE_PLACES_ADAPTER = GooglePlacesAdapter()
GOOGLE_HEALTH_CACHE: tuple[float, dict[str, Any]] | None = None
GOOGLE_HEALTH_TTL_SECONDS = 300


def load_map_data() -> dict[str, Any]:
    """Load and minimally validate bundled map mock data."""

    try:
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Map Insight 展示資料無法載入。") from exc
    if not payload.get("regions") or not payload.get("categories"):
        raise ValueError("Map Insight 展示資料缺少區域或 POI 分類。")
    return payload


def list_regions() -> list[dict[str, Any]]:
    """Return searchable mock region metadata."""

    return [
        {"id": row["id"], "city": row["city"], "district": row["district"], "road": row["road"], "center": row["center"]}
        for row in load_map_data()["regions"]
    ]


def list_poi_categories() -> list[dict[str, str]]:
    """Return the stable POI category list."""

    return [{"category": key, "label": value} for key, value in CATEGORY_LABELS.items()]


def search_location(query: str, adapter: GeocodingAdapter | None = None) -> dict[str, Any]:
    """Use Google Geocoding first when configured, then safely fall back to mock."""

    regions = load_map_data()["regions"]
    source = "mock"
    google = adapter if adapter is not None else GoogleGeocodingAdapter()
    region = google.search(query, regions)
    if region is not None and isinstance(google, GoogleGeocodingAdapter):
        source = "google_geocoding"
    if region is None and adapter is None:
        region = MockGeocodingAdapter().search(query, regions)
    if region is None:
        return {
            "query": query, "matched": False, "center": None, "city": "", "district": "", "road": "",
            "source": "mock", "formatted_address": "", "place_id": "", "confidence": "mock",
            "location_note": "找不到符合的展示資料定位。", "disclaimer": SEARCH_DISCLAIMER,
        }
    formatted_address = region.get("formatted_address") or f"{region.get('city', '')}{region.get('district', '')}{region.get('road', '')}"
    return {
        "query": query,
        "matched": True,
        "center": region["center"],
        "city": region["city"],
        "district": region["district"],
        "road": region["road"],
        "source": source,
        "formatted_address": formatted_address,
        "place_id": region.get("place_id", ""),
        "confidence": "high" if source == "google_geocoding" else "mock",
        "location_note": "Google Geocoding 定位結果。" if source == "google_geocoding" else "展示資料定位，座標僅供操作示範。",
        "disclaimer": SEARCH_DISCLAIMER,
    }


def get_google_health(force_refresh: bool = False) -> dict[str, Any]:
    """Check backend-only Google integrations with a five-minute process cache."""

    global GOOGLE_HEALTH_CACHE
    now = time.monotonic()
    if not force_refresh and GOOGLE_HEALTH_CACHE and now - GOOGLE_HEALTH_CACHE[0] < GOOGLE_HEALTH_TTL_SECONDS:
        return GOOGLE_HEALTH_CACHE[1]

    geocoding = GoogleGeocodingAdapter()
    places = GooglePlacesAdapter()
    if not geocoding.available:
        result = {
            "google_key_configured": False, "geocoding_enabled": False, "places_enabled": False,
            "last_error": "", "mode": "mock", "safe_message": "目前使用展示資料",
        }
        GOOGLE_HEALTH_CACHE = (now, result)
        return result

    geocoding_enabled = geocoding.search("台北101", []) is not None
    places_enabled = False
    places_error = ""
    try:
        places.nearby(25.0330, 121.5654, 200, "transport", "zh-TW")
        places_enabled = True
    except httpx.TimeoutException:
        places_error = "Google Places 回應逾時"
    except httpx.HTTPStatusError:
        places_error = "Google Places 目前無法使用"
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        places_error = "Google Places 未回傳可用資料"
    enabled = geocoding_enabled and places_enabled
    errors = [message for message in [geocoding.last_error, places_error] if message]
    result = {
        "google_key_configured": True,
        "geocoding_enabled": geocoding_enabled,
        "places_enabled": places_enabled,
        "last_error": "；".join(errors),
        "mode": "google" if enabled else "mock",
        "safe_message": "目前使用 Google Places API" if enabled else "Google API 暫不可用，已切換展示資料",
    }
    GOOGLE_HEALTH_CACHE = (now, result)
    return result


def get_map_insight(query: str, geocoding: GeocodingAdapter | None = None, poi: PoiAdapter | None = None, traffic: TrafficAdapter | None = None) -> dict[str, Any] | None:
    """Build one Map Insight result using mock-first adapters."""

    region = (geocoding or MockGeocodingAdapter()).search(query, load_map_data()["regions"])
    if region is None:
        return None
    layers = (poi or MockPoiAdapter()).get_layers(region)
    (traffic or MockTrafficAdapter()).get_summary(region)
    return {
        "center": region["center"],
        "zoom": int(region["zoom"]),
        "area_summary": region["area_summary"],
        "poi_layers": layers,
        "livability_score": int(region["livability_score"]),
        "poi_summary": region["poi_summary"],
        "source": "mock",
        "disclaimer": INSIGHT_DISCLAIMER,
    }


def get_nearby_places(
    lat: float,
    lng: float,
    radius_m: int,
    categories: list[str],
    language_code: str = "zh-TW",
    adapter: GooglePlacesAdapter | None = None,
) -> dict[str, Any]:
    """Return Google Places nearby results or a normalized mock fallback."""

    supported = [category for category in categories if category in CATEGORY_LABELS]
    requested = supported or list(CATEGORY_LABELS)
    google = adapter or DEFAULT_GOOGLE_PLACES_ADAPTER
    grouped: list[dict[str, Any]] = []
    source = "google_places" if google.available else "mock"

    if google.available:
        try:
            for category in requested:
                places = google.nearby(lat, lng, radius_m, category, language_code)
                grouped.append(_category_result(category, places))
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            grouped = []
            source = "mock"

    if source == "mock":
        grouped = [_category_result(category, _mock_places(lat, lng, radius_m, category)) for category in requested]

    scoring = build_livability_scoring(grouped, radius_m)
    counts = "、".join(f"{row['label']} {row['count']} 處" for row in grouped)
    return {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius_m,
        "source": source,
        "categories": grouped,
        "livability_score": scoring["livability_score"],
        "livability_level": scoring["livability_level"],
        "score_summary": scoring["score_summary"],
        "category_scores": scoring["category_scores"],
        "category_score_map": scoring["category_score_map"],
        "nearest_places": scoring["nearest_places"],
        "recommendation_text": scoring["recommendation_text"],
        "score_explanation": scoring["score_explanation"],
        "scoring_criteria": {
            "radius_m": 800,
            "category_weights": CATEGORY_WEIGHTS,
            "distance_bands": [
                {"range": "0-300m", "weight": "high"},
                {"range": "300-800m", "weight": "medium"},
                {"range": "800m+", "weight": "excluded"},
            ],
            "disclaimer": NEARBY_DISCLAIMER,
        },
        "summary": scoring["summary"] or f"{radius_m} 公尺生活圈共涵蓋 {counts}；分數僅用於比較周遭設施完整度。",
        "disclaimer": NEARBY_DISCLAIMER,
    }


def calculate_livability_score(categories: list[dict[str, Any]], radius_m: int) -> int:
    """Return the overall score while preserving the original public helper."""

    return int(build_livability_scoring(categories, radius_m)["livability_score"])


def build_livability_scoring(categories: list[dict[str, Any]], radius_m: int) -> dict[str, Any]:
    """Score category coverage using both POI count and tiered walking distance."""

    total = 0.0
    category_score_map: dict[str, int] = {}
    category_metrics: list[dict[str, Any]] = []
    all_places: list[dict[str, Any]] = []
    for group in categories:
        category = group["category"]
        places = [place for place in group["places"] if place.get("distance_m", radius_m + 1) <= min(radius_m, 800)]
        all_places.extend({**place, "category": place.get("category", category)} for place in places)
        proximity_units = sum(_distance_weight(float(place["distance_m"])) for place in places)
        category_score = max(0, min(100, round(min(proximity_units / 4, 1) * 100)))
        category_score_map[category] = category_score
        nearest_distance = min((int(place["distance_m"]) for place in places), default=None)
        level = _score_level(category_score)
        category_metrics.append({
            "category": category,
            "label": CATEGORY_LABELS[category],
            "weight": CATEGORY_WEIGHTS.get(category, 0),
            "score": category_score,
            "level": level,
            "poi_count": len(places),
            "nearest_distance_m": nearest_distance,
            "explanation": _category_explanation(category, category_score, len(places), nearest_distance),
        })
        total += CATEGORY_WEIGHTS.get(category, 0) * category_score / 100

    for category in CATEGORY_LABELS:
        if category not in category_score_map:
            category_score_map[category] = 0
            category_metrics.append({
                "category": category, "label": CATEGORY_LABELS[category], "weight": CATEGORY_WEIGHTS.get(category, 0),
                "score": 0, "level": "不足", "poi_count": 0, "nearest_distance_m": None,
                "explanation": "800m 內未找到足夠資料，建議搭配實地確認。",
            })
    ordered = sorted(all_places, key=lambda place: float(place.get("distance_m", radius_m + 1)))
    nearest = ordered[:3]
    ranked = sorted(category_score_map, key=category_score_map.get, reverse=True)
    strongest = [CATEGORY_LABELS[key] for key in ranked[:2] if category_score_map[key] > 0]
    weakest = [CATEGORY_LABELS[key] for key in reversed(ranked) if category_score_map[key] < 65][:2]
    strength_text = "與".join(strongest) if strongest else "周遭設施"
    weak_text = "與".join(weakest) if weakest else "其他生活設施"
    summary = f"此區{strength_text}密度較高，適合展示生活便利性；{weak_text}資源可再搭配實地確認。"
    recommendation = f"若用於客戶溝通，可強調本區步行範圍內的{strength_text}機能，並將{weak_text}列為看屋時的補充確認項目。"
    overall = max(0, min(100, round(total)))
    level = _score_level(overall)
    return {
        "livability_score": overall,
        "livability_level": level,
        "score_summary": f"生活機能總分 {overall}，整體屬於「{level}」；{summary}",
        "category_scores": sorted(category_metrics, key=lambda item: item["weight"], reverse=True),
        "category_score_map": category_score_map,
        "nearest_places": nearest,
        "summary": summary,
        "recommendation_text": recommendation,
        "score_explanation": "分數依設施類別權重、數量與距離估算；300 公尺內權重最高，300–800 公尺採中等權重，800 公尺外不計。",
    }


def _score_level(score: int) -> str:
    """Translate a score into the user-facing five-level scale."""

    if score >= 90:
        return "極佳"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "普通"
    if score >= 40:
        return "偏弱"
    return "不足"


def _category_explanation(category: str, score: int, count: int, nearest_distance: int | None) -> str:
    """Explain one category score using visible POI evidence."""

    if not count or nearest_distance is None:
        return "800m 內未找到足夠資料，建議搭配實地確認。"
    subject = {"transport": "大眾運輸節點", "food": "餐飲選擇", "shopping": "採買與商圈", "school": "教育資源", "medical": "醫療資源", "park": "公園綠地"}[category]
    return f"800m 內找到 {count} 個{subject}，最近約 {nearest_distance}m，指標等級為{_score_level(score)}。"


def _distance_weight(distance_m: float) -> float:
    """Return a simple walking-distance weight for one POI."""

    if distance_m <= 300:
        return 1.0
    if distance_m <= 800:
        return 0.55
    return 0.0


def _category_result(category: str, places: list[dict[str, Any]]) -> dict[str, Any]:
    return {"category": category, "label": CATEGORY_LABELS[category], "count": len(places), "places": places}


def _mock_places(lat: float, lng: float, radius_m: int, category: str) -> list[dict[str, Any]]:
    """Normalize the closest bundled region's POIs into nearby-place schema."""

    regions = load_map_data()["regions"]
    region = min(regions, key=lambda row: distance_meters(lat, lng, row["center"]["lat"], row["center"]["lng"]))
    nearby_places = [
        {
            **place,
            "distance_m": distance_meters(lat, lng, place["lat"], place["lng"]),
            "types": place.get("types", [place["category"]]),
            "source": "mock",
        }
        for place in region.get("nearby_places", [])
        if place["category"] == category and distance_meters(lat, lng, place["lat"], place["lng"]) <= radius_m
    ]
    if nearby_places:
        return sorted(nearby_places, key=lambda place: place["distance_m"])

    source_category = "commerce" if category in {"shopping", "food"} else category
    layer = next((item for item in region["poi_layers"] if item["category"] == source_category), None)
    points = list(layer.get("points", [])) if layer else []
    if category == "food" and points:
        points = [{**points[0], "name": f"{region['district']}生活圈餐飲"}]
    return [
        {
            "place_id": f"mock-{region['id']}-{category}-{index}",
            "name": point["name"],
            "lat": point["lat"],
            "lng": point["lng"],
            "address": f"{region['city']}{region['district']}{region['road']}周邊",
            "rating": 4.2 if category in {"food", "shopping"} else None,
            "user_rating_count": 80 if category in {"food", "shopping"} else 0,
            "business_status": "OPERATIONAL",
            "distance_m": distance_meters(lat, lng, point["lat"], point["lng"]),
            "types": [source_category],
            "category": category,
            "source": "mock",
        }
        for index, point in enumerate(points)
        if distance_meters(lat, lng, point["lat"], point["lng"]) <= radius_m
    ]
