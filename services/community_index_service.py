"""Lazy-loaded sample community and building index."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "community_building_sample.csv"


@lru_cache(maxsize=1)
def load_communities() -> tuple[dict[str, Any], ...]:
    """Load the small bundled community index on first use."""

    try:
        with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            return tuple(_normalize(row) for row in csv.DictReader(handle))
    except OSError:
        return ()


def match_community(
    city: str,
    district: str,
    road: str,
    address_text: str = "",
) -> dict[str, Any] | None:
    """Return the best probable community match without claiming certainty."""

    address = _compact(address_text)
    candidates = [
        row
        for row in load_communities()
        if row["city"] == city and row["district"] == district and row["road"] == road
    ]
    if not candidates:
        return None
    for row in candidates:
        if address and (_compact(row["community_name"]) in address or _compact(row["address_pattern"]) in address):
            return {**row, "confidence": "high", "match_reason": "輸入地址命中展示社區名稱或地址樣式"}
    if address:
        return None
    if len(candidates) == 1:
        return {**candidates[0], "confidence": "low", "match_reason": "同路段僅有一筆展示社區索引，僅作可能匹配"}
    return None


def _normalize(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    result["lat"] = float(row["lat"])
    result["lng"] = float(row["lng"])
    result["completed_year"] = int(row["completed_year"])
    result["total_floors"] = int(row["total_floors"])
    return result


def _compact(value: str) -> str:
    return "".join(str(value).lower().split())
