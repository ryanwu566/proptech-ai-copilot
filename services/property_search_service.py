"""Explainable property-direction suggestions from official PLVR transactions."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from services.valuation_service import get_valuation_provider, normalize_building_type, normalize_city
from services.valuation_providers.postgres_provider import PostgresValuationProvider

DISCLAIMER = "這是歷史成交資料篩選，不代表目前有待售物件，亦非正式鑑價、投資建議或成交保證。"


def search_properties(payload: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Filter official transactions and build explainable district and road suggestions."""

    request = {**payload, "limit": max(1, min(int(payload.get("limit") or 50), 100))}
    provider = get_valuation_provider()
    if rows is None:
        rows = provider.query_property_search_rows(request) if isinstance(provider, PostgresValuationProvider) else []
    selected = _filter_rows(rows, request)
    periods = sorted(str(row["transaction_period"]) for row in selected)
    return {
        "summary": {
            "matched_count": len(selected),
            "city_count": len({normalize_city(str(row["city"])) for row in selected}),
            "district_count": len({(normalize_city(str(row["city"])), str(row["district"])) for row in selected}),
            "road_count": len({(normalize_city(str(row["city"])), str(row["district"]), str(row["road"])) for row in selected}),
            "budget_min": request.get("budget_min"),
            "budget_max": request.get("budget_max"),
            "period_min": periods[0] if periods else None,
            "period_max": periods[-1] if periods else None,
            "data_source_label": "官方 PLVR 實價登錄",
            "message": "找到符合條件的歷史成交方向。" if selected else "目前沒有符合條件的官方歷史成交，請放寬預算或篩選條件。",
            "disclaimer": DISCLAIMER,
        },
        "district_suggestions": _suggestions(selected, request, ("city", "district"), 20),
        "road_suggestions": _suggestions(selected, request, ("city", "district", "road"), 30),
        "matched_transactions": [_public_row(row) for row in _sort_rows(selected)[: request["limit"]]],
        "methodology": "分數由預算貼近度 60%、樣本量 25%、近一年成交比例 15% 組成；不使用黑箱 AI。",
        "disclaimer": DISCLAIMER,
    }


def _filter_rows(rows: list[dict[str, Any]], request: dict[str, Any]) -> list[dict[str, Any]]:
    current = datetime.now(UTC).strftime("%Y-%m")
    start = str(request.get("period_since") or _shift_month(current, -35))
    districts = {str(item).strip() for item in request.get("districts") or [] if str(item).strip()}
    result = []
    for row in rows:
        period = str(row.get("transaction_period") or "")
        total, area, unit = _number(row, "total_price"), _number(row, "area_ping"), _number(row, "unit_price_per_ping")
        if row.get("source") != "official_plvr_opendata" or not (start <= period <= current):
            continue
        if total <= 0 or area <= 0 or not (0 < unit <= 500):
            continue
        if request.get("city") and normalize_city(str(row.get("city", ""))) != normalize_city(str(request["city"])):
            continue
        if districts and str(row.get("district", "")).strip() not in districts:
            continue
        if request.get("building_type") and normalize_building_type(str(row.get("building_type", ""))) != normalize_building_type(str(request["building_type"])):
            continue
        if not _between(total, request.get("budget_min"), request.get("budget_max")) or not _between(area, request.get("area_ping_min"), request.get("area_ping_max")):
            continue
        if request.get("building_age_max") is not None and _number(row, "building_age_years") > float(request["building_age_max"]):
            continue
        if request.get("floor_min") is not None and _number(row, "floor") < float(request["floor_min"]):
            continue
        result.append({**row, "total_price": total, "area_ping": area, "unit_price_per_ping": unit})
    return result


def _suggestions(rows: list[dict[str, Any]], request: dict[str, Any], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(key, "")) for key in keys)].append(row)
    result = []
    for group, items in grouped.items():
        totals = sorted(_number(row, "total_price") for row in items)
        units = sorted(_number(row, "unit_price_per_ping") for row in items)
        areas = sorted(_number(row, "area_ping") for row in items)
        median_total = statistics.median(totals)
        item = {
            **dict(zip(keys, group)), "sample_count": len(items),
            "median_total_price": round(median_total, 1),
            "median_unit_price_per_ping": round(statistics.median(units), 2),
            "median_area_ping": round(statistics.median(areas), 2),
            "common_building_type": Counter(normalize_building_type(str(row.get("building_type", ""))) for row in items).most_common(1)[0][0],
            "score": _score(items, median_total, request),
            "reason": _reason(items, median_total, request),
        }
        if len(keys) == 2:
            item.update({
                "p25_total_price": round(_percentile(totals, 0.25), 1),
                "p75_total_price": round(_percentile(totals, 0.75), 1),
                "period_min": min(str(row["transaction_period"]) for row in items),
                "period_max": max(str(row["transaction_period"]) for row in items),
            })
        result.append(item)
    return sorted(result, key=lambda item: (-float(item["score"]), -int(item["sample_count"])))[:limit]


def _score(rows: list[dict[str, Any]], median_total: float, request: dict[str, Any]) -> float:
    lower, upper = float(request.get("budget_min") or 0), float(request.get("budget_max") or max(median_total, 1))
    center = (lower + upper) / 2 if lower else upper * 0.85
    budget_score = max(0, 1 - abs(median_total - center) / max(upper - lower, upper * 0.5, 1))
    volume_score = min(1, len(rows) / 20)
    current_year = datetime.now(UTC).year
    recent_score = sum(str(row["transaction_period"]).startswith(str(current_year)) for row in rows) / len(rows)
    return round((budget_score * 0.60 + volume_score * 0.25 + recent_score * 0.15) * 100, 1)


def _reason(rows: list[dict[str, Any]], median_total: float, request: dict[str, Any]) -> str:
    upper = request.get("budget_max")
    note = "總價中位數接近預算上限" if upper and median_total >= float(upper) * 0.8 else "總價中位數保留預算空間"
    return f"符合條件成交 {len(rows)} 筆，{note}；分數綜合成交量、預算貼近度與近一年資料比例。"


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = ("transaction_period", "city", "district", "road", "building_type", "area_ping", "total_price", "unit_price_per_ping", "building_age_years", "floor")
    return {key: row.get(key) for key in keys} | {"source_label": "官方 PLVR"}


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (str(row["transaction_period"]), _number(row, "total_price")), reverse=True)


def _between(value: float, lower: Any, upper: Any) -> bool:
    return (lower is None or value >= float(lower)) and (upper is None or value <= float(upper))


def _number(row: dict[str, Any], key: str) -> float:
    return float(row.get(key) or 0)


def _percentile(values: list[float], fraction: float) -> float:
    position = (len(values) - 1) * fraction
    lower, upper = int(position), min(len(values) - 1, int(position) + 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _shift_month(period: str, offset: int) -> str:
    year, month = map(int, period.split("-"))
    total = year * 12 + month - 1 + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"
