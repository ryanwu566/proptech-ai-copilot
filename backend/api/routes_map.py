"""Map Insight Lite API routes backed only by bundled mock data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.map_service import get_map_insight, list_poi_categories, list_regions, search_location


router = APIRouter(prefix="/map", tags=["map-insight"])


class MapQuery(BaseModel):
    """Text query accepted by mock map search and insight endpoints."""

    query: str


@router.get("/regions")
def get_regions() -> list[dict[str, Any]]:
    """Return available mock map regions."""

    return list_regions()


@router.get("/poi-categories")
def get_poi_categories() -> list[dict[str, str]]:
    """Return supported mock POI categories."""

    return list_poi_categories()


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
