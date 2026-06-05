"""Mock-first Map Insight Lite service with stable frontend contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.adapters.geocoding_adapter import GeocodingAdapter, MockGeocodingAdapter
from services.adapters.poi_adapter import MockPoiAdapter, PoiAdapter
from services.adapters.traffic_adapter import MockTrafficAdapter, TrafficAdapter


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_map_points.json"
SEARCH_DISCLAIMER = "展示型 mock data，不代表正式地址定位結果"
INSIGHT_DISCLAIMER = "展示型 mock data，不代表正式估價、投資或交通分析"


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

    return load_map_data()["categories"]


def search_location(query: str, adapter: GeocodingAdapter | None = None) -> dict[str, Any]:
    """Search mock addresses, districts, and roads with a stable response."""

    region = (adapter or MockGeocodingAdapter()).search(query, load_map_data()["regions"])
    if region is None:
        return {"query": query, "matched": False, "center": None, "city": "", "district": "", "road": "", "source": "mock", "disclaimer": SEARCH_DISCLAIMER}
    return {
        "query": query,
        "matched": True,
        "center": region["center"],
        "city": region["city"],
        "district": region["district"],
        "road": region["road"],
        "source": "mock",
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
