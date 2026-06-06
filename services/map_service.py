"""Mock-first Map Insight Lite service with stable frontend contracts."""

from __future__ import annotations

import json
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
NEARBY_DISCLAIMER = "周遭設施資料來自 Google Places 或 mock fallback，僅供展示與區域理解，不代表正式估價或投資建議。"
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
    """Search bundled aliases first, then optionally use Google Geocoding."""

    regions = load_map_data()["regions"]
    source = "mock"
    region = (adapter or MockGeocodingAdapter()).search(query, regions)
    if region is None and adapter is None:
        region = GoogleGeocodingAdapter().search(query, regions)
        source = "google_geocoding"
    if region is None:
        return {"query": query, "matched": False, "center": None, "city": "", "district": "", "road": "", "source": "mock", "disclaimer": SEARCH_DISCLAIMER}
    return {
        "query": query,
        "matched": True,
        "center": region["center"],
        "city": region["city"],
        "district": region["district"],
        "road": region["road"],
        "source": source,
        "disclaimer": SEARCH_DISCLAIMER,
    }


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

    score = calculate_livability_score(grouped, radius_m)
    counts = "、".join(f"{row['label']} {row['count']} 處" for row in grouped)
    return {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius_m,
        "source": source,
        "categories": grouped,
        "livability_score": score,
        "summary": f"{radius_m} 公尺生活圈共涵蓋 {counts}；分數僅用於比較周遭設施完整度。",
        "disclaimer": NEARBY_DISCLAIMER,
    }


def calculate_livability_score(categories: list[dict[str, Any]], radius_m: int) -> int:
    """Score POI coverage and proximity using fixed category weights."""

    total = 0.0
    for group in categories:
        weight = CATEGORY_WEIGHTS.get(group["category"], 0)
        places = group["places"]
        if not places:
            continue
        count_factor = min(len(places) / 5, 1)
        proximity_factor = sum(max(0, 1 - place["distance_m"] / max(radius_m, 1)) for place in places) / len(places)
        total += weight * (count_factor * 0.65 + proximity_factor * 0.35)
    return max(0, min(100, round(total)))


def _category_result(category: str, places: list[dict[str, Any]]) -> dict[str, Any]:
    return {"category": category, "label": CATEGORY_LABELS[category], "count": len(places), "places": places}


def _mock_places(lat: float, lng: float, radius_m: int, category: str) -> list[dict[str, Any]]:
    """Normalize the closest bundled region's POIs into nearby-place schema."""

    regions = load_map_data()["regions"]
    region = min(regions, key=lambda row: distance_meters(lat, lng, row["center"]["lat"], row["center"]["lng"]))
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
