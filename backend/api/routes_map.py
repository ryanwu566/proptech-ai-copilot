"""Map Insight Lite API routes backed only by bundled mock data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.map_service import get_google_health, get_map_insight, get_nearby_places, list_poi_categories, list_regions, search_location


router = APIRouter(prefix="/map", tags=["map-insight"])


class MapQuery(BaseModel):
    """Text query accepted by mock map search and insight endpoints."""

    query: str


class NearbyQuery(BaseModel):
    """Nearby POI query centered on a WGS84 coordinate."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=800, ge=100, le=5000)
    categories: list[str] = Field(default_factory=lambda: ["transport", "school", "park", "medical", "shopping", "food"])
    language_code: str = "zh-TW"


@router.get("/regions")
def get_regions() -> list[dict[str, Any]]:
    """Return available mock map regions."""

    return list_regions()


@router.get("/poi-categories")
def get_poi_categories() -> list[dict[str, str]]:
    """Return supported mock POI categories."""

    return list_poi_categories()


@router.get("/google-health")
def get_map_google_health() -> dict[str, Any]:
    """Return a safe Google integration status without exposing credentials."""

    return get_google_health()


@router.post("/search")
def post_map_search(request: MapQuery) -> dict[str, Any]:
    """Resolve a mock address, district, or road query."""

    return search_location(request.query)


@router.post("/insight")
def post_map_insight(request: MapQuery) -> dict[str, Any]:
    """Return map center, POI layers, and livability summary."""

    result = get_map_insight(request.query)
    if result is None:
        raise HTTPException(status_code=404, detail="找不到符合的 Map Insight 展示資料。")
    return result


@router.post("/nearby")
def post_map_nearby(request: NearbyQuery) -> dict[str, Any]:
    """Return normalized nearby amenities with automatic mock fallback."""

    return get_nearby_places(request.lat, request.lng, request.radius_m, request.categories, request.language_code)
