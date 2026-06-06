"""Lightweight comparable-sales valuation using bundled real-price sample data."""

from __future__ import annotations

import csv
import math
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "real_price_sample.csv"
DISCLAIMER = "此為實價登錄可比成交估算，不代表正式鑑價、銀行估價或成交保證。"
METHODOLOGY = ["以同縣市、行政區、路段附近可比成交為主", "優先選擇相近建物型態、坪數與屋齡", "使用中位數與四分位距估算價格區間"]


@lru_cache(maxsize=1)
def load_transactions() -> tuple[dict[str, Any], ...]:
    try:
        with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            return tuple(_normalize(row) for row in csv.DictReader(handle))
    except OSError:
        return ()


def estimate_property(payload: dict[str, Any]) -> dict[str, Any]:
    """Estimate a range from 3-10 ranked comparable transactions."""

    rows = list(load_transactions())
    ranked = sorted(rows, key=lambda row: _rank(row, payload))
    comparables = [row for row in ranked if row["city"] == payload["city"]][:10]
    if len(comparables) < 3:
        comparables = ranked[:10]
    unit_prices = [row["unit_price_per_ping"] for row in comparables]
    if not unit_prices:
        return _empty_result()
    median = statistics.median(unit_prices)
    ordered = sorted(unit_prices)
    low = _percentile(ordered, 0.25)
    high = _percentile(ordered, 0.75)
    same_road = sum(row["road"] == payload["road"] and row["district"] == payload["district"] for row in comparables)
    confidence = "high" if len(comparables) >= 8 and same_road >= 3 else "medium" if len(comparables) >= 4 else "low"
    confidence_score = min(95, 35 + len(comparables) * 6 + same_road * 4)
    result_comps = [{**row, "distance_m": _distance(payload, row), "note": "同路段可比" if row["road"] == payload["road"] else "同區域參考"} for row in comparables]
    area = float(payload["area_ping"])
    return {"source": "real_price_sample", "estimate_total_price": round(median * area, 1), "estimate_unit_price_per_ping": round(median, 1), "price_range": {"low": round(low * area, 1), "mid": round(median * area, 1), "high": round(high * area, 1)}, "confidence": confidence, "confidence_score": confidence_score, "comparables": result_comps, "methodology": METHODOLOGY, "disclaimer": DISCLAIMER}


def _normalize(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    for key in ("area_ping", "unit_price_per_ping", "total_price", "building_age_years", "floor", "lat", "lng"):
        result[key] = float(row[key])
    return result


def _rank(row: dict[str, Any], target: dict[str, Any]) -> tuple[float, ...]:
    return (0 if row["road"] == target["road"] and row["district"] == target["district"] else 1 if row["district"] == target["district"] else 2 if row["city"] == target["city"] else 3, 0 if row["building_type"] == target["building_type"] else 1, abs(row["area_ping"] - float(target["area_ping"])), abs(row["building_age_years"] - float(target["building_age_years"])), _distance(target, row))


def _distance(target: dict[str, Any], row: dict[str, Any]) -> int:
    if target.get("lat") is None or target.get("lng") is None:
        return 0
    return round(111000 * math.sqrt((float(target["lat"]) - row["lat"]) ** 2 + ((float(target["lng"]) - row["lng"]) * 0.91) ** 2))


def _percentile(values: list[float], fraction: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _empty_result() -> dict[str, Any]:
    return {"source": "real_price_sample", "estimate_total_price": 0, "estimate_unit_price_per_ping": 0, "price_range": {"low": 0, "mid": 0, "high": 0}, "confidence": "low", "confidence_score": 0, "comparables": [], "methodology": METHODOLOGY + ["目前 sample 資料不足，未產生價格推估"], "disclaimer": DISCLAIMER}
