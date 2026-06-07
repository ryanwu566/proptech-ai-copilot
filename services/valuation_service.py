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
from services.valuation_providers.postgres_provider import PostgresValuationProvider


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


class MockFallbackProvider:
    """Last-resort in-memory provider that keeps the endpoint usable."""

    source = "mock_fallback"
    is_demo_data = True
    is_full_taiwan = False

    def available(self) -> bool:
        return True

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        return (
            _normalize({"transaction_period": "2026-01", "city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "unit_price_per_ping": 75, "total_price": 2250, "building_age_years": 12, "floor": 8, "lat": 25.0254, "lng": 121.5434, "source": "mock_fallback"}),
            _normalize({"transaction_period": "2026-01", "city": "台北市", "district": "信義區", "road": "松仁路", "building_type": "住宅大樓", "area_ping": 32, "unit_price_per_ping": 96, "total_price": 3072, "building_age_years": 10, "floor": 10, "lat": 25.0338, "lng": 121.5687, "source": "mock_fallback"}),
            _normalize({"transaction_period": "2026-01", "city": "新北市", "district": "板橋區", "road": "文化路二段", "building_type": "華廈", "area_ping": 28, "unit_price_per_ping": 61, "total_price": 1708, "building_age_years": 16, "floor": 6, "lat": 25.0264, "lng": 121.4704, "source": "mock_fallback"}),
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
    all_rows = list(provider.query_comparables(payload) if isinstance(provider, PostgresValuationProvider) else provider.load_transactions())
    all_rows, selection = _prepare_candidate_pool(all_rows, payload, enforce_scope=isinstance(provider, PostgresValuationProvider))
    data_status = provider.data_status()
    query_metadata = provider.last_query_metadata if isinstance(provider, PostgresValuationProvider) else {
        "provider_active": provider.source,
        "candidate_pool_size": len(all_rows),
        "query_scope": "local_provider",
        "requested_city": payload.get("city", ""),
        "requested_district": payload.get("district", ""),
        "requested_road": payload.get("road", ""),
        "db_rows_returned": len(all_rows),
        "query_status": "ok",
    }
    community = (
        provider.match_community(payload)
        if isinstance(provider, PostgresValuationProvider)
        else match_community(
            str(payload.get("city", "")),
            str(payload.get("district", "")),
            str(payload.get("road", "")),
            str(payload.get("address_text", "")),
        )
    )
    estimate_level, candidates = (
        (selection["estimate_level"], all_rows)
        if selection["estimate_level"]
        else _select_estimate_level(all_rows, payload, community)
    )
    if not candidates:
        return _empty_result(data_status, community, query_metadata)

    scored = [{**row, **_score_comparable(row, payload, community)} for row in candidates]
    filtered = _filter_outliers(scored, preserve_official=any(row.get("_official_limited") for row in scored))
    comparables = sorted(filtered, key=_comparable_sort_key)[:10]
    if len(comparables) < 3:
        comparables = sorted(scored, key=_comparable_sort_key)[:10]
    unit_prices = [row["unit_price_per_ping"] for row in comparables]
    ordered = sorted(unit_prices)
    weighted_mean = _weighted_mean(comparables)
    weighted_median = _weighted_median(comparables)
    mid = round((weighted_mean + weighted_median) / 2, 1)
    p25, p75 = _percentile(ordered, 0.25), _percentile(ordered, 0.75)
    explanation = _build_explanation(comparables, payload)
    estimate_composition = selection["estimate_data_composition"] or _estimate_composition(comparables)
    confidence, confidence_score, confidence_caps = _confidence(comparables, explanation, estimate_level, community)
    area = float(payload["area_ping"])
    return {
        "source": provider.source,
        "data_status": data_status,
        "estimate_level": estimate_level,
        "matched_community": _public_community(community),
        "confidence_reason": _confidence_reason(estimate_level, confidence, explanation, community, estimate_composition, confidence_caps, data_status),
        "estimate_data_composition": estimate_composition,
        "data_composition": estimate_composition,
        "estimate_source_label": _estimate_source_label(estimate_composition),
        "candidate_pool_size": query_metadata.get("candidate_pool_size", len(all_rows)),
        "official_same_road_count": selection["official_same_road_count"],
        "official_same_district_count": selection["official_same_district_count"],
        "sample_same_road_count": selection["sample_same_road_count"],
        "sample_same_district_count": selection["sample_same_district_count"],
        "source_details": {**_source_details(provider), **query_metadata},
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
        community_rows = [row for row in rows if row["city"] == community["city"] and row["district"] == community["district"] and row["road"] == community["road"] and _distance(community, row) is not None and _distance(community, row) <= 600]
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


def _prepare_candidate_pool(rows: list[dict[str, Any]], target: dict[str, Any], enforce_scope: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose an explicit road-first valuation scope before scoring."""

    prepared = [{**row, "source": str(row.get("source") or "real_price_sample")} for row in rows if not _is_future_official(row)]
    target_road = normalize_road(str(target.get("road", "")))
    same_district = [
        row for row in prepared
        if normalize_city(str(row.get("city", ""))) == normalize_city(str(target.get("city", "")))
        and str(row.get("district", "")).strip() == str(target.get("district", "")).strip()
    ]
    official_same_road = [row for row in same_district if row["source"] == "official_plvr_opendata" and normalize_road(str(row.get("road", ""))) == target_road]
    official_same_district = [row for row in same_district if row["source"] == "official_plvr_opendata" and normalize_road(str(row.get("road", ""))) != target_road]
    sample_same_road = [row for row in same_district if row["source"] != "official_plvr_opendata" and normalize_road(str(row.get("road", ""))) == target_road]
    sample_same_district = [row for row in same_district if row["source"] != "official_plvr_opendata" and normalize_road(str(row.get("road", ""))) != target_road]
    selection = {
        "official_same_road_count": len(official_same_road),
        "official_same_district_count": len(official_same_district),
        "sample_same_road_count": len(sample_same_road),
        "sample_same_district_count": len(sample_same_district),
        "estimate_level": None,
        "estimate_data_composition": None,
    }
    if not enforce_scope:
        return prepared, selection
    if len(official_same_road) >= 5:
        selection.update({"estimate_level": "road", "estimate_data_composition": "official"})
        return official_same_road, selection
    if official_same_road:
        selection.update({"estimate_level": "road", "estimate_data_composition": "official_limited"})
        candidates = [{**row, "_official_limited": True} for row in [*official_same_road, *sample_same_road]]
        return candidates[:10], selection
    if len(official_same_district) >= 5:
        selection.update({"estimate_level": "district", "estimate_data_composition": "official_district"})
        return [{**row, "_official_district": True} for row in official_same_district], selection
    if sample_same_road:
        selection.update({"estimate_level": "road", "estimate_data_composition": "sample"})
        return sample_same_road, selection
    return prepared, selection


def _is_future_official(row: dict[str, Any]) -> bool:
    if row.get("source") != "official_plvr_opendata":
        return False
    try:
        year, month = (int(part) for part in str(row.get("transaction_period", ""))[:7].split("-"))
        return (year, month) > (date.today().year, date.today().month)
    except (TypeError, ValueError):
        return True


def _comparable_sort_key(row: dict[str, Any]) -> tuple[int, int, float, int, float]:
    """Sort by road scope, normalized type, area, recency, then similarity."""

    if row.get("_same_road"):
        scope_rank = 0 if row.get("source") == "official_plvr_opendata" else 1
    else:
        scope_rank = 2 if row.get("source") == "official_plvr_opendata" else 3
    type_rank = 0 if row.get("_same_building_type") else 1
    area_difference = float(row.get("_area_difference_ping") or 0)
    period_rank = -_period_number(str(row.get("transaction_period", "")))
    return scope_rank, type_rank, area_difference, period_rank, -float(row["similarity_score"])


def _estimate_composition(rows: list[dict[str, Any]]) -> str:
    if any(row.get("_official_district") for row in rows):
        return "official_district"
    if any(row.get("_official_limited") for row in rows):
        return "official_limited"
    sources = {row.get("source") for row in rows}
    has_official = "official_plvr_opendata" in sources
    has_non_official = bool(sources - {"official_plvr_opendata"})
    return "mixed" if has_official and has_non_official else "official" if has_official else "sample"


def _estimate_source_label(composition: str) -> str:
    return {
        "official": "官方 PLVR",
        "official_limited": "官方 PLVR（樣本較少）+ 展示樣本補充",
        "official_district": "同行政區官方 PLVR 參考",
        "mixed": "官方 PLVR + 展示樣本",
        "sample": "展示樣本",
    }[composition]


def _source_label(source: str) -> str:
    return {
        "official_plvr_opendata": "官方 PLVR",
        "real_price_sample": "展示樣本",
        "sample": "展示樣本",
        "mock_fallback": "展示資料",
    }.get(source, "其他資料")


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
    result.setdefault("source", "real_price_sample")
    return result


def _score_comparable(row: dict[str, Any], target: dict[str, Any], community: dict[str, Any] | None = None) -> dict[str, Any]:
    same_road = normalize_road(str(row["road"])) == normalize_road(str(target["road"])) and row["district"] == target["district"]
    same_district = row["district"] == target["district"]
    same_city = row["city"] == target["city"]
    normalized_type = normalize_building_type(str(row["building_type"]))
    target_type = normalize_building_type(str(target["building_type"]))
    same_type = normalized_type == target_type
    community_distance = _distance(community, row) if community else None
    probable_community = bool(community and same_road and community_distance is not None and community_distance <= 600)
    area_diff = abs(row["area_ping"] - float(target["area_ping"]))
    age_diff = abs(row["building_age_years"] - float(target["building_age_years"]))
    distance = _distance(target, row)
    distance_bonus = max(0, 7 - distance / 800) if distance is not None else 0
    score = (15 if probable_community else 0) + (35 if same_road else 0) + (20 if same_district else 0) + (10 if same_city else 0) + (15 if same_type else 0) + max(0, 10 - area_diff / max(float(target["area_ping"]), 1) * 20) + max(0, 8 - age_diff / 4) + distance_bonus + _recency_score(str(row.get("transaction_period", "")))
    reasons = ["可能同社區範圍"] if probable_community else []
    reasons.append("同路段" if same_road else "同行政區" if same_district else "同縣市" if same_city else "展示資料補充")
    if same_type:
        reasons.append("同建物類型")
    reasons.append(f"面積差 {area_diff:.1f} 坪")
    score = round(min(100, score), 1)
    source = str(row.get("source") or "mock_fallback")
    return {
        "distance_m": distance,
        "similarity_score": score,
        "weight": round(max(score / 100, 0.05), 3),
        "note": "、".join(reasons),
        "source": source,
        "source_label": _source_label(source),
        "normalized_building_type": normalized_type,
        "_same_road": same_road,
        "_same_building_type": same_type,
        "_area_difference_ping": area_diff,
    }


def _filter_outliers(rows: list[dict[str, Any]], preserve_official: bool = False) -> list[dict[str, Any]]:
    if len(rows) < 4:
        return rows
    prices = sorted(row["unit_price_per_ping"] for row in rows)
    q1, q3 = _percentile(prices, 0.25), _percentile(prices, 0.75)
    iqr = q3 - q1
    filtered = [
        row for row in rows
        if q1 - 1.5 * iqr <= row["unit_price_per_ping"] <= q3 + 1.5 * iqr
        or preserve_official and row.get("source") == "official_plvr_opendata"
    ]
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
        "same_road_count": sum(normalize_road(str(row["road"])) == normalize_road(str(target["road"])) and row["district"] == target["district"] for row in rows),
        "same_district_count": sum(row["district"] == target["district"] for row in rows),
        "same_city_count": sum(row["city"] == target["city"] for row in rows),
        "same_building_type_count": sum(normalize_building_type(str(row["building_type"])) == normalize_building_type(str(target["building_type"])) for row in rows),
        "nearest_distance_m": min((row["distance_m"] for row in rows if row["distance_m"] is not None), default=None),
        "average_area_difference_ping": round(statistics.mean(abs(row["area_ping"] - float(target["area_ping"])) for row in rows), 1),
        "average_age_difference_years": round(statistics.mean(abs(row["building_age_years"] - float(target["building_age_years"])) for row in rows), 1),
        "average_similarity_score": round(statistics.mean(row["similarity_score"] for row in rows), 1),
        "method": "依估價層級選擇可比成交，IQR 排除極端值後綜合相似度加權平均、加權中位數與 P25/P75。",
    }


def _confidence(rows: list[dict[str, Any]], explanation: dict[str, Any], level: str, community: dict[str, Any] | None) -> tuple[str, int, list[str]]:
    level_bonus = {"community": 15, "road": 10, "district": 5, "city": 0, "fallback": -10}[level]
    score = round(20 + len(rows) * 3 + explanation["same_road_count"] * 5 + explanation["same_building_type_count"] * 2 + explanation["average_similarity_score"] * 0.2 + level_bonus)
    composition = _estimate_composition(rows)
    caps: list[tuple[int, str]] = [(90, "官方同路段資料的最高信心上限為 90")]
    if composition == "mixed":
        caps.append((80, "本次混用官方與展示樣本"))
    elif composition == "official_limited":
        caps.append((70, "官方同路段可比成交筆數較少，已補充展示樣本"))
    elif composition == "official_district":
        caps.append((60, "指定路段官方資料不足，改以同行政區官方資料參考"))
    elif composition == "sample":
        caps.append((70, "本次僅使用展示樣本"))
    if not community:
        caps.append((85, "尚未命中特定社區"))
    if not any(row.get("distance_m") is not None for row in rows):
        caps.append((85, "可比成交缺少定位距離資訊"))
    if len(rows) < 5:
        caps.append((65, "可比成交少於 5 筆"))
    official_same_road = sum(row.get("source") == "official_plvr_opendata" for row in rows if "同路段" in row.get("note", ""))
    majority_same_type = explanation["same_building_type_count"] >= max(1, len(rows) / 2)
    high_eligible = composition == "official" and official_same_road >= 8 and majority_same_type
    if not high_eligible:
        caps.append((79, "尚未同時符合官方同路段至少 8 筆與建物型態多數一致"))
    cap = min(value for value, _reason in caps)
    score = min(score, cap)
    cap_reasons = [reason for value, reason in caps if value == cap]
    if high_eligible and score >= 80:
        return "high", score, cap_reasons
    if level in {"community", "road", "district"} and len(rows) >= 4:
        return "medium", min(score, 79), cap_reasons
    return "low", min(score, 49), cap_reasons


def _confidence_reason(level: str, confidence: str, explanation: dict[str, Any], community: dict[str, Any] | None, composition: str, caps: list[str], data_status: dict[str, Any]) -> str:
    labels = {"community": "可能同社區", "road": "同路段", "district": "同行政區", "city": "同縣市", "fallback": "展示資料補充"}
    community_note = f"，社區索引信心為 {community['confidence']}" if community else ""
    composition_note = {"official": "官方 PLVR", "official_limited": "官方 PLVR 同路段資料與展示樣本補充", "official_district": "同行政區官方 PLVR 參考", "mixed": "官方 PLVR 與展示樣本混合", "sample": "展示樣本"}[composition]
    limited_note = "；官方同路段資料較少，本次以官方 PLVR 為主，並補充展示樣本" if composition == "official_limited" else ""
    district_note = "；指定路段官方資料不足，本次改以同行政區官方資料參考，信心較低" if composition == "official_district" else ""
    coverage_note = "；目前資料尚非全台完整" if not data_status.get("is_full_taiwan", False) else ""
    cap_note = f"；保守上限原因：{'、'.join(caps)}" if caps else ""
    return f"本次以{labels[level]}可比成交估算，共採用 {explanation['sample_count']} 筆 {composition_note} 資料，信心為 {confidence}{community_note}{limited_note}{district_note}{coverage_note}{cap_note}。"


def _distance(target: dict[str, Any] | None, row: dict[str, Any]) -> int | None:
    if not target or target.get("lat") is None or target.get("lng") is None or row.get("lat") is None or row.get("lng") is None:
        return None
    return round(111000 * math.sqrt((float(target["lat"]) - row["lat"]) ** 2 + ((float(target["lng"]) - row["lng"]) * 0.91) ** 2))


def _recency_score(period: str) -> float:
    try:
        year, month = (int(part) for part in period[:7].split("-"))
        months_old = (date.today().year - year) * 12 + date.today().month - month
        if months_old < 0:
            return 0
        return max(0, 5 - months_old / 12)
    except (ValueError, TypeError):
        return 0


def _period_number(period: str) -> int:
    try:
        year, month = (int(part) for part in period[:7].split("-"))
        return year * 12 + month
    except (TypeError, ValueError):
        return 0


def normalize_building_type(value: str) -> str:
    """Normalize official PLVR building labels for comparable matching."""

    normalized = value.strip()
    mappings = {
        "住宅大樓(11層含以上有電梯)": "住宅大樓",
        "住宅大樓(11層含以上)": "住宅大樓",
        "華廈(10層含以下有電梯)": "華廈",
        "公寓(5樓含以下無電梯)": "公寓",
        "套房(1房1廳1衛)": "套房",
    }
    return mappings.get(normalized, normalized)


def normalize_road(value: str) -> str:
    """Normalize common road spelling variants before scope comparison."""

    normalized = value.strip().replace("臺", "台").replace(" ", "")
    segment_numbers = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九", "10": "十"}
    for number, chinese in sorted(segment_numbers.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(f"{number}段", f"{chinese}段")
    return normalized


def normalize_city(value: str) -> str:
    """Normalize Taiwan city character variants for grouping."""

    return value.strip().replace("臺", "台")


def _percentile(values: list[float], fraction: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _empty_result(data_status: dict[str, Any], community: dict[str, Any] | None, query_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source": data_status["active_source"],
        "data_status": data_status,
        "estimate_level": "fallback",
        "matched_community": _public_community(community),
        "confidence_reason": "目前查詢範圍內沒有可用的可比成交資料，請確認城市、行政區與路段資料覆蓋。",
        "estimate_data_composition": "sample",
        "data_composition": "sample",
        "estimate_source_label": "展示資料",
        "candidate_pool_size": (query_metadata or {}).get("candidate_pool_size", 0),
        "official_same_road_count": 0,
        "official_same_district_count": 0,
        "sample_same_road_count": 0,
        "sample_same_district_count": 0,
        "source_details": {"file": data_status["active_source"], "nature": "展示資料", "complete_real_price_registry": False, "formal_appraisal": False, "bank_appraisal": False, "future_adapter": "未來可切換 Supabase/Postgres 全台資料庫", **(query_metadata or {})},
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
