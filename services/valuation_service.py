"""Explainable comparable-sales valuation using bundled sample transactions."""

from __future__ import annotations

import csv
import math
import statistics
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "real_price_sample.csv"
DISCLAIMER = (
    "本結果使用 real_price_sample.csv 展示樣本推估，不是完整實價登錄資料，"
    "不構成正式估價、銀行鑑價或投資建議。"
)
METHODOLOGY = [
    "優先挑選同路段、同行政區、同建物類型且面積與屋齡接近的可比成交。",
    "使用相似度與距離加權，並以 IQR 排除極端單價。",
    "以加權平均作為中位估計，P25 與 P75 顯示合理區間；樣本不足時降低信心。",
]


@lru_cache(maxsize=1)
def load_transactions() -> tuple[dict[str, Any], ...]:
    """Load bundled sample transactions without external dependencies."""

    try:
        with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            return tuple(_normalize(row) for row in csv.DictReader(handle))
    except OSError:
        return ()


def estimate_property(payload: dict[str, Any]) -> dict[str, Any]:
    """Estimate a price range from explainable, weighted comparable sales."""

    all_rows = list(load_transactions())
    if not all_rows:
        return _empty_result()

    scored = [{**row, **_score_comparable(row, payload)} for row in all_rows]
    city_rows = [row for row in scored if row["city"] == payload["city"]]
    candidates = city_rows or scored
    filtered = _filter_outliers(candidates)
    comparables = sorted(filtered, key=lambda row: (-row["similarity_score"], row["distance_m"]))[:10]
    if len(comparables) < 3:
        comparables = sorted(candidates, key=lambda row: (-row["similarity_score"], row["distance_m"]))[:10]
    if not comparables:
        return _empty_result()

    unit_prices = [row["unit_price_per_ping"] for row in comparables]
    ordered = sorted(unit_prices)
    weighted_mean = _weighted_mean(comparables)
    weighted_median = _weighted_median(comparables)
    mid = round((weighted_mean + weighted_median) / 2, 1)
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    explanation = _build_explanation(comparables, payload)
    confidence, confidence_score = _confidence(comparables, explanation)
    area = float(payload["area_ping"])
    return {
        "source": "real_price_sample",
        "source_details": {
            "file": "data/real_price_sample.csv",
            "nature": "展示型可比成交樣本",
            "complete_real_price_registry": False,
            "formal_appraisal": False,
            "bank_appraisal": False,
            "future_adapter": "PLVR 實價登錄 adapter 尚未啟用",
        },
        "estimate_total_price": round(mid * area, 1),
        "estimate_unit_price_per_ping": mid,
        "price_range": {
            "low": round(p25 * area, 1),
            "mid": round(mid * area, 1),
            "high": round(p75 * area, 1),
        },
        "unit_price_distribution": {
            "weighted_mean": round(weighted_mean, 1),
            "weighted_median": round(weighted_median, 1),
            "p25": round(p25, 1),
            "p75": round(p75, 1),
        },
        "confidence": confidence,
        "confidence_score": confidence_score,
        "comparables": comparables,
        "valuation_explanation": explanation,
        "methodology": METHODOLOGY,
        "disclaimer": DISCLAIMER,
    }


def _normalize(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    for key in ("area_ping", "unit_price_per_ping", "total_price", "building_age_years", "floor", "lat", "lng"):
        result[key] = float(row[key])
    return result


def _score_comparable(row: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    same_road = row["road"] == target["road"] and row["district"] == target["district"]
    same_district = row["district"] == target["district"]
    same_city = row["city"] == target["city"]
    same_type = row["building_type"] == target["building_type"]
    area_diff = abs(row["area_ping"] - float(target["area_ping"]))
    age_diff = abs(row["building_age_years"] - float(target["building_age_years"]))
    distance = _distance(target, row)
    recency = _recency_score(str(row.get("transaction_period", "")))
    score = (
        (35 if same_road else 0)
        + (20 if same_district else 0)
        + (10 if same_city else 0)
        + (15 if same_type else 0)
        + max(0, 10 - area_diff / max(float(target["area_ping"]), 1) * 20)
        + max(0, 8 - age_diff / 4)
        + max(0, 7 - distance / 800)
        + recency
    )
    score = round(min(100, score), 1)
    reasons = []
    if same_road:
        reasons.append("同路段")
    elif same_district:
        reasons.append("同行政區")
    elif same_city:
        reasons.append("同縣市")
    if same_type:
        reasons.append("同建物類型")
    reasons.append(f"面積差 {area_diff:.1f} 坪")
    return {
        "distance_m": distance,
        "similarity_score": score,
        "weight": round(max(score / 100, 0.05), 3),
        "note": "、".join(reasons),
    }


def _filter_outliers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) < 4:
        return rows
    prices = sorted(row["unit_price_per_ping"] for row in rows)
    q1, q3 = _percentile(prices, 0.25), _percentile(prices, 0.75)
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtered = [row for row in rows if low <= row["unit_price_per_ping"] <= high]
    return filtered or rows


def _weighted_mean(rows: list[dict[str, Any]]) -> float:
    total_weight = sum(row["weight"] for row in rows)
    return sum(row["unit_price_per_ping"] * row["weight"] for row in rows) / total_weight


def _weighted_median(rows: list[dict[str, Any]]) -> float:
    ordered = sorted(rows, key=lambda row: row["unit_price_per_ping"])
    half = sum(row["weight"] for row in ordered) / 2
    running = 0.0
    for row in ordered:
        running += row["weight"]
        if running >= half:
            return float(row["unit_price_per_ping"])
    return float(ordered[-1]["unit_price_per_ping"])


def _build_explanation(rows: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_count": len(rows),
        "same_road_count": sum(row["road"] == target["road"] and row["district"] == target["district"] for row in rows),
        "same_district_count": sum(row["district"] == target["district"] for row in rows),
        "same_city_count": sum(row["city"] == target["city"] for row in rows),
        "same_building_type_count": sum(row["building_type"] == target["building_type"] for row in rows),
        "nearest_distance_m": min(row["distance_m"] for row in rows),
        "average_area_difference_ping": round(
            statistics.mean(abs(row["area_ping"] - float(target["area_ping"])) for row in rows), 1
        ),
        "average_age_difference_years": round(
            statistics.mean(abs(row["building_age_years"] - float(target["building_age_years"])) for row in rows), 1
        ),
        "average_similarity_score": round(statistics.mean(row["similarity_score"] for row in rows), 1),
        "method": "IQR 排除極端值後，綜合相似度加權平均、加權中位數與 P25/P75。",
    }


def _confidence(rows: list[dict[str, Any]], explanation: dict[str, Any]) -> tuple[str, int]:
    score = min(
        95,
        round(
            20
            + len(rows) * 3
            + explanation["same_road_count"] * 6
            + explanation["same_building_type_count"] * 2
            + explanation["average_similarity_score"] * 0.25
        ),
    )
    if len(rows) >= 8 and explanation["same_road_count"] >= 4 and explanation["average_similarity_score"] >= 70:
        return "high", score
    if len(rows) >= 4 and explanation["same_district_count"] >= 2:
        return "medium", min(score, 79)
    return "low", min(score, 49)


def _distance(target: dict[str, Any], row: dict[str, Any]) -> int:
    if target.get("lat") is None or target.get("lng") is None:
        return 0
    return round(
        111000
        * math.sqrt(
            (float(target["lat"]) - row["lat"]) ** 2
            + ((float(target["lng"]) - row["lng"]) * 0.91) ** 2
        )
    )


def _recency_score(period: str) -> float:
    try:
        year, month = (int(part) for part in period[:7].split("-"))
        months_old = max(0, (date.today().year - year) * 12 + date.today().month - month)
        return max(0, 5 - months_old / 12)
    except (ValueError, TypeError):
        return 0


def _percentile(values: list[float], fraction: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _empty_result() -> dict[str, Any]:
    return {
        "source": "real_price_sample",
        "source_details": {
            "file": "data/real_price_sample.csv",
            "nature": "展示型可比成交樣本",
            "complete_real_price_registry": False,
            "formal_appraisal": False,
            "bank_appraisal": False,
            "future_adapter": "PLVR 實價登錄 adapter 尚未啟用",
        },
        "estimate_total_price": 0,
        "estimate_unit_price_per_ping": 0,
        "price_range": {"low": 0, "mid": 0, "high": 0},
        "unit_price_distribution": {"weighted_mean": 0, "weighted_median": 0, "p25": 0, "p75": 0},
        "confidence": "low",
        "confidence_score": 0,
        "comparables": [],
        "valuation_explanation": {
            "sample_count": 0,
            "same_road_count": 0,
            "same_district_count": 0,
            "same_city_count": 0,
            "same_building_type_count": 0,
            "nearest_distance_m": None,
            "average_area_difference_ping": None,
            "average_age_difference_years": None,
            "average_similarity_score": 0,
            "method": "無可用展示樣本。",
        },
        "methodology": METHODOLOGY + ["目前沒有可用展示樣本，無法產生估算。"],
        "disclaimer": DISCLAIMER,
    }
