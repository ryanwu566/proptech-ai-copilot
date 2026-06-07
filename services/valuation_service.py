"""Provider-based, explainable comparable-sales valuation service."""

from __future__ import annotations

import csv
import math
import os
import sqlite3
import statistics
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from services.community_index_service import match_community


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "data" / "real_price_sample.csv"
SQLITE_PATH = ROOT / "data" / "processed" / "valuation_index.sqlite"
DISCLAIMER = (
    "本結果為可比成交估算，不是正式鑑價、銀行估價、成交保證或投資建議。"
)
UPDATE_FREQUENCY_NOTE = "實價登錄官方資料約每月 1、11、21 日定期更新，系統資料需由後台排程同步。"
USER_MESSAGE = "使用者不需要下載資料；估價資料由系統後台資料管線維護。"
METHODOLOGY = [
    "依同社區、同路段、同行政區、同縣市的順序尋找可比成交。",
    "使用相似度與距離加權，並以 IQR 排除極端單價。",
    "以加權平均與加權中位數估算中位值，P25 與 P75 顯示估值區間。",
]


class ValuationProvider(Protocol):
    """Contract for current and future valuation data sources."""

    source: str
    is_demo_data: bool
    is_full_taiwan: bool

    def available(self) -> bool: ...
    def load_transactions(self) -> tuple[dict[str, Any], ...]: ...
    def data_status(self) -> dict[str, Any]: ...


class SampleValuationProvider:
    """Lazy provider for the bundled comparable-sales sample."""

    source = "real_price_sample"
    is_demo_data = True
    is_full_taiwan = False

    def __init__(self, path: Path = SAMPLE_PATH) -> None:
        self.path = path

    def available(self) -> bool:
        return self.path.is_file()

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        return _load_csv(str(self.path))

    def data_status(self) -> dict[str, Any]:
        return _build_data_status(self, self.load_transactions(), self.path)


class SQLiteValuationProvider:
    """Lazy provider for a future locally indexed SQLite transaction table."""

    source = "sqlite_index"
    is_demo_data = False
    is_full_taiwan = False

    def __init__(self, path: Path = SQLITE_PATH) -> None:
        self.path = path

    def available(self) -> bool:
        return self.path.is_file()

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        if not self.available():
            return ()
        try:
            with sqlite3.connect(self.path) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute("SELECT * FROM transactions").fetchall()
            return tuple(_normalize(dict(row)) for row in rows)
        except (sqlite3.Error, OSError, KeyError, TypeError, ValueError):
            return ()

    def data_status(self) -> dict[str, Any]:
        return _build_data_status(self, self.load_transactions(), self.path)


class PostgresValuationProvider:
    """Placeholder for a future Supabase/Postgres provider; never connects at import."""

    source = "postgres"
    is_demo_data = False
    is_full_taiwan = False

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def available(self) -> bool:
        return False

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        return ()

    def data_status(self) -> dict[str, Any]:
        return _build_data_status(self, (), None)


class MockFallbackProvider:
    """Last-resort in-memory provider that keeps the endpoint usable."""

    source = "mock_fallback"
    is_demo_data = True
    is_full_taiwan = False

    def available(self) -> bool:
        return True

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        return (
            _normalize({"transaction_period": "2026-01", "city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "unit_price_per_ping": 75, "total_price": 2250, "building_age_years": 12, "floor": 8, "lat": 25.0254, "lng": 121.5434}),
            _normalize({"transaction_period": "2026-01", "city": "台北市", "district": "信義區", "road": "松仁路", "building_type": "住宅大樓", "area_ping": 32, "unit_price_per_ping": 96, "total_price": 3072, "building_age_years": 10, "floor": 10, "lat": 25.0338, "lng": 121.5687}),
            _normalize({"transaction_period": "2026-01", "city": "新北市", "district": "板橋區", "road": "文化路二段", "building_type": "華廈", "area_ping": 28, "unit_price_per_ping": 61, "total_price": 1708, "building_age_years": 16, "floor": 6, "lat": 25.0264, "lng": 121.4704}),
        )

    def data_status(self) -> dict[str, Any]:
        return _build_data_status(self, self.load_transactions(), None)


@lru_cache(maxsize=8)
def _load_csv(path: str) -> tuple[dict[str, Any], ...]:
    """Read a selected CSV only on first provider use."""

    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            return tuple(_normalize(row) for row in csv.DictReader(handle))
    except (OSError, KeyError, TypeError, ValueError):
        return ()


def load_transactions() -> tuple[dict[str, Any], ...]:
    """Backward-compatible helper returning the active provider transactions."""

    return get_valuation_provider().load_transactions()


def get_valuation_provider(
    database_url: str | None = None,
    sqlite_path: Path = SQLITE_PATH,
    sample_path: Path = SAMPLE_PATH,
) -> ValuationProvider:
    """Select a provider lazily, falling through unavailable placeholders."""

    configured_url = os.getenv("VALUATION_DATABASE_URL", "") if database_url is None else database_url
    providers: list[ValuationProvider] = []
    if configured_url.strip():
        providers.append(PostgresValuationProvider(configured_url.strip()))
    providers.extend([SQLiteValuationProvider(sqlite_path), SampleValuationProvider(sample_path), MockFallbackProvider()])
    for provider in providers:
        if provider.available():
            return provider
    return MockFallbackProvider()


def get_valuation_data_status() -> dict[str, Any]:
    """Return a user-safe summary of the active valuation data source."""

    return get_valuation_provider().data_status()


def estimate_property(payload: dict[str, Any]) -> dict[str, Any]:
    """Estimate a range using the best available provider and comparison level."""

    provider = get_valuation_provider()
    all_rows = list(provider.load_transactions())
    data_status = provider.data_status()
    community = match_community(
        str(payload.get("city", "")),
        str(payload.get("district", "")),
        str(payload.get("road", "")),
        str(payload.get("address_text", "")),
    )
    estimate_level, candidates = _select_estimate_level(all_rows, payload, community)
    if not candidates:
        return _empty_result(data_status, community)

    scored = [{**row, **_score_comparable(row, payload, community)} for row in candidates]
    filtered = _filter_outliers(scored)
    comparables = sorted(filtered, key=lambda row: (-row["similarity_score"], row["distance_m"]))[:10]
    if len(comparables) < 3:
        comparables = sorted(scored, key=lambda row: (-row["similarity_score"], row["distance_m"]))[:10]
    unit_prices = [row["unit_price_per_ping"] for row in comparables]
    ordered = sorted(unit_prices)
    weighted_mean = _weighted_mean(comparables)
    weighted_median = _weighted_median(comparables)
    mid = round((weighted_mean + weighted_median) / 2, 1)
    p25, p75 = _percentile(ordered, 0.25), _percentile(ordered, 0.75)
    explanation = _build_explanation(comparables, payload)
    confidence, confidence_score = _confidence(comparables, explanation, estimate_level)
    area = float(payload["area_ping"])
    return {
        "source": provider.source,
        "data_status": data_status,
        "estimate_level": estimate_level,
        "matched_community": _public_community(community),
        "confidence_reason": _confidence_reason(estimate_level, confidence, explanation, community),
        "source_details": _source_details(provider),
        "estimate_total_price": round(mid * area, 1),
        "estimate_unit_price_per_ping": mid,
        "price_range": {"low": round(p25 * area, 1), "mid": round(mid * area, 1), "high": round(p75 * area, 1)},
        "unit_price_distribution": {"weighted_mean": round(weighted_mean, 1), "weighted_median": round(weighted_median, 1), "p25": round(p25, 1), "p75": round(p75, 1)},
        "confidence": confidence,
        "confidence_score": confidence_score,
        "comparables": comparables,
        "valuation_explanation": explanation,
        "methodology": METHODOLOGY,
        "disclaimer": DISCLAIMER,
    }


def _select_estimate_level(rows: list[dict[str, Any]], target: dict[str, Any], community: dict[str, Any] | None) -> tuple[str, list[dict[str, Any]]]:
    if community:
        community_rows = [row for row in rows if row["city"] == community["city"] and row["district"] == community["district"] and row["road"] == community["road"] and _distance(community, row) <= 600]
        if len(community_rows) >= 3:
            return "community", community_rows
    hierarchy = [
        ("road", [row for row in rows if row["city"] == target["city"] and row["district"] == target["district"] and row["road"] == target["road"]]),
        ("district", [row for row in rows if row["city"] == target["city"] and row["district"] == target["district"]]),
        ("city", [row for row in rows if row["city"] == target["city"]]),
    ]
    for level, candidates in hierarchy:
        if len(candidates) >= 3:
            return level, candidates
    return "fallback", rows


def _build_data_status(provider: ValuationProvider, rows: tuple[dict[str, Any], ...], path: Path | None) -> dict[str, Any]:
    last_updated = None
    if path and path.exists():
        last_updated = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    return {
        "active_source": provider.source,
        "is_demo_data": provider.is_demo_data,
        "is_full_taiwan": provider.is_full_taiwan,
        "coverage": {
            "cities": sorted({row["city"] for row in rows}),
            "districts": sorted({row["district"] for row in rows}),
            "roads_count": len({(row["city"], row["district"], row["road"]) for row in rows}),
            "records_count": len(rows),
        },
        "last_updated": last_updated,
        "update_frequency_note": UPDATE_FREQUENCY_NOTE,
        "source_note": (
            "目前使用展示用可比成交樣本，未來可切換至 Supabase/Postgres 全台資料庫。"
            if provider.is_demo_data
            else "目前使用已建立索引的估價資料來源。"
        ),
        "user_message": USER_MESSAGE,
    }


def _source_details(provider: ValuationProvider) -> dict[str, Any]:
    return {
        "file": "data/real_price_sample.csv" if provider.source == "real_price_sample" else provider.source,
        "nature": "展示型可比成交樣本" if provider.is_demo_data else "索引化可比成交資料",
        "complete_real_price_registry": provider.is_full_taiwan,
        "formal_appraisal": False,
        "bank_appraisal": False,
        "future_adapter": "未來可切換 Supabase/Postgres 全台資料庫",
    }


def _public_community(community: dict[str, Any] | None) -> dict[str, Any] | None:
    if not community:
        return None
    return {"community_id": community["community_id"], "community_name": community["community_name"], "confidence": community["confidence"]}


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    for key in ("area_ping", "unit_price_per_ping", "total_price", "building_age_years", "floor", "lat", "lng"):
        result[key] = float(row[key])
    return result


def _score_comparable(row: dict[str, Any], target: dict[str, Any], community: dict[str, Any] | None = None) -> dict[str, Any]:
    same_road = row["road"] == target["road"] and row["district"] == target["district"]
    same_district = row["district"] == target["district"]
    same_city = row["city"] == target["city"]
    same_type = row["building_type"] == target["building_type"]
    probable_community = bool(community and same_road and _distance(community, row) <= 600)
    area_diff = abs(row["area_ping"] - float(target["area_ping"]))
    age_diff = abs(row["building_age_years"] - float(target["building_age_years"]))
    distance = _distance(target, row)
    score = (15 if probable_community else 0) + (35 if same_road else 0) + (20 if same_district else 0) + (10 if same_city else 0) + (15 if same_type else 0) + max(0, 10 - area_diff / max(float(target["area_ping"]), 1) * 20) + max(0, 8 - age_diff / 4) + max(0, 7 - distance / 800) + _recency_score(str(row.get("transaction_period", "")))
    reasons = ["可能同社區範圍"] if probable_community else []
    reasons.append("同路段" if same_road else "同行政區" if same_district else "同縣市" if same_city else "展示資料補充")
    if same_type:
        reasons.append("同建物類型")
    reasons.append(f"面積差 {area_diff:.1f} 坪")
    score = round(min(100, score), 1)
    return {"distance_m": distance, "similarity_score": score, "weight": round(max(score / 100, 0.05), 3), "note": "、".join(reasons)}


def _filter_outliers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) < 4:
        return rows
    prices = sorted(row["unit_price_per_ping"] for row in rows)
    q1, q3 = _percentile(prices, 0.25), _percentile(prices, 0.75)
    iqr = q3 - q1
    filtered = [row for row in rows if q1 - 1.5 * iqr <= row["unit_price_per_ping"] <= q3 + 1.5 * iqr]
    return filtered or rows


def _weighted_mean(rows: list[dict[str, Any]]) -> float:
    total_weight = sum(row["weight"] for row in rows)
    return sum(row["unit_price_per_ping"] * row["weight"] for row in rows) / total_weight


def _weighted_median(rows: list[dict[str, Any]]) -> float:
    ordered = sorted(rows, key=lambda row: row["unit_price_per_ping"])
    half, running = sum(row["weight"] for row in ordered) / 2, 0.0
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
        "average_area_difference_ping": round(statistics.mean(abs(row["area_ping"] - float(target["area_ping"])) for row in rows), 1),
        "average_age_difference_years": round(statistics.mean(abs(row["building_age_years"] - float(target["building_age_years"])) for row in rows), 1),
        "average_similarity_score": round(statistics.mean(row["similarity_score"] for row in rows), 1),
        "method": "依估價層級選擇可比成交，IQR 排除極端值後綜合相似度加權平均、加權中位數與 P25/P75。",
    }


def _confidence(rows: list[dict[str, Any]], explanation: dict[str, Any], level: str) -> tuple[str, int]:
    level_bonus = {"community": 15, "road": 10, "district": 5, "city": 0, "fallback": -10}[level]
    score = min(95, round(20 + len(rows) * 3 + explanation["same_road_count"] * 5 + explanation["same_building_type_count"] * 2 + explanation["average_similarity_score"] * 0.2 + level_bonus))
    if level in {"community", "road"} and len(rows) >= 8 and explanation["average_similarity_score"] >= 70:
        return "high", score
    if level in {"community", "road", "district"} and len(rows) >= 4:
        return "medium", min(score, 79)
    return "low", min(score, 49)


def _confidence_reason(level: str, confidence: str, explanation: dict[str, Any], community: dict[str, Any] | None) -> str:
    labels = {"community": "可能同社區", "road": "同路段", "district": "同行政區", "city": "同縣市", "fallback": "展示資料補充"}
    community_note = f"，社區索引信心為 {community['confidence']}" if community else ""
    return f"本次以{labels[level]}可比成交估算，共採用 {explanation['sample_count']} 筆，信心為 {confidence}{community_note}。"


def _distance(target: dict[str, Any], row: dict[str, Any]) -> int:
    if target.get("lat") is None or target.get("lng") is None:
        return 0
    return round(111000 * math.sqrt((float(target["lat"]) - row["lat"]) ** 2 + ((float(target["lng"]) - row["lng"]) * 0.91) ** 2))


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


def _empty_result(data_status: dict[str, Any], community: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "source": data_status["active_source"],
        "data_status": data_status,
        "estimate_level": "fallback",
        "matched_community": _public_community(community),
        "confidence_reason": "目前資料不足，無法形成可靠的可比成交估算。",
        "source_details": {"file": data_status["active_source"], "nature": "展示資料", "complete_real_price_registry": False, "formal_appraisal": False, "bank_appraisal": False, "future_adapter": "未來可切換 Supabase/Postgres 全台資料庫"},
        "estimate_total_price": 0,
        "estimate_unit_price_per_ping": 0,
        "price_range": {"low": 0, "mid": 0, "high": 0},
        "unit_price_distribution": {"weighted_mean": 0, "weighted_median": 0, "p25": 0, "p75": 0},
        "confidence": "low",
        "confidence_score": 0,
        "comparables": [],
        "valuation_explanation": {"sample_count": 0, "same_road_count": 0, "same_district_count": 0, "same_city_count": 0, "same_building_type_count": 0, "nearest_distance_m": None, "average_area_difference_ping": None, "average_age_difference_years": None, "average_similarity_score": 0, "method": "無可用資料。"},
        "methodology": METHODOLOGY,
        "disclaimer": DISCLAIMER,
    }
