"""Road selection APIs backed by the bundled Taiwan road dataset."""

from __future__ import annotations

from fastapi import APIRouter, Query

from services.road_data_service import list_cities, list_districts, list_roads


router = APIRouter(prefix="/roads", tags=["roads"])


@router.get("/cities")
def get_cities() -> dict[str, object]:
    """Return available cities."""

    cities = list_cities()
    return {"cities": cities, "message": "" if cities else "目前沒有可用的縣市資料。"}


@router.get("/districts")
def get_districts(city: str = Query(min_length=1)) -> dict[str, object]:
    """Return districts for a city without failing on unknown values."""

    districts = list_districts(city)
    return {"city": city, "districts": districts, "message": "" if districts else "找不到此縣市的鄉鎮市區資料。"}


@router.get("/roads")
def get_roads(city: str = Query(min_length=1), district: str = Query(min_length=1)) -> dict[str, object]:
    """Return roads for a city and district without failing on unknown values."""

    roads = list_roads(city, district)
    return {"city": city, "district": district, "roads": roads, "message": "" if roads else "找不到此區域的路段資料。"}
