"""Cached access to the bundled Taiwan city, district, and road dataset."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "taiwan_roads.csv"
DEMO_ROADS = (
    ("台北市", "大安區", "和平東路二段"),
    ("新北市", "板橋區", "文化路二段"),
    ("台北市", "信義區", "松仁路"),
)


@lru_cache(maxsize=1)
def load_road_rows() -> tuple[tuple[str, str, str], ...]:
    """Load normalized road rows once per process."""

    try:
        with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = []
            for row in csv.DictReader(handle):
                city = row.get("city", "").strip().replace("臺", "台")
                site_id = row.get("site_id", "").strip().replace("臺", "台")
                road = row.get("road", "").strip()
                district = site_id.removeprefix(city).strip()
                if city and district and road:
                    rows.append((city, district, road))
    except OSError as exc:
        raise ValueError("路名資料目前無法載入。") from exc
    rows.extend(DEMO_ROADS)
    return tuple(rows)


def list_cities() -> list[str]:
    """Return sorted city names."""

    return sorted({city for city, _, _ in load_road_rows()})


def list_districts(city: str) -> list[str]:
    """Return districts for one city, or an empty list."""

    return sorted({district for row_city, district, _ in load_road_rows() if row_city == city})


def list_roads(city: str, district: str) -> list[str]:
    """Return roads for one city and district, or an empty list."""

    return sorted({road for row_city, row_district, road in load_road_rows() if row_city == city and row_district == district})
