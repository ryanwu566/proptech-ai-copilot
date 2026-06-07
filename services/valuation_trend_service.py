"""Explainable official-PLVR market trend and scenario analysis."""

from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from services.valuation_service import get_valuation_provider, normalize_building_type, normalize_city, normalize_road
from services.valuation_providers.postgres_provider import PostgresValuationProvider

DISCLAIMER = "此為依官方實價登錄歷史資料推估之情境參考，不代表成交保證、正式鑑價、銀行估價或投資建議。"
METHODOLOGY = [
    "僅使用官方 PLVR OpenData，排除展示樣本、未來月份與最近五年分析窗口外資料。",
    "依同路段、同行政區同建物型態、同行政區的順序選擇趨勢樣本。",
    "以每月中位數、IQR 控制極端值，使用簡單線性趨勢與月變動波動度建立保守、中性、樂觀情境。",
]


def analyze_valuation_trend(payload: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a conservative market-trend result from official transaction rows."""

    current = datetime.now(UTC).strftime("%Y-%m")
    window_start = _shift_month(current, -59)
    request = {**payload, "current_period": current, "window_start": window_start}
    provider = get_valuation_provider()
    if rows is None:
        rows = provider.query_trend_rows(request) if isinstance(provider, PostgresValuationProvider) else list(provider.load_transactions())
    official, quality = _valid_official_rows(rows, window_start, current)
    road_rows = [row for row in official if normalize_road(str(row.get("road", ""))) == normalize_road(str(payload.get("road", "")))]
    district_type_rows = [
        row for row in official
        if normalize_building_type(str(row.get("building_type", ""))) == normalize_building_type(str(payload.get("building_type", "")))
    ]
    if len(road_rows) >= 30:
        scope, selected = "road", road_rows
    elif len(district_type_rows) >= 100:
        scope, selected = "district_type", district_type_rows
    else:
        scope, selected = "district", official

    monthly = _monthly_series(selected)
    yearly = _yearly_series(selected)
    recent = _recent_median(monthly)
    annualized = _annualized_rate(monthly)
    volatility = _volatility(monthly)
    confidence, reason = _confidence(selected, monthly, scope, window_start)
    forecast = _scenario_forecast(
        recent,
        float(payload.get("area_ping", 0) or 0),
        payload.get("horizon_months") or [6, 12, 36],
        annualized,
        volatility,
        confidence,
    )
    return {
        "source": "official_plvr_opendata",
        "data_scope": scope,
        "raw_period_min": quality["raw_period_min"],
        "raw_period_max": quality["raw_period_max"],
        "effective_period_min": monthly[0]["period"] if monthly else None,
        "effective_period_max": monthly[-1]["period"] if monthly else None,
        "excluded_future_period_count": quality["excluded_future_period_count"],
        "excluded_out_of_window_count": quality["excluded_out_of_window_count"],
        "period_min": monthly[0]["period"] if monthly else None,
        "period_max": monthly[-1]["period"] if monthly else None,
        "sample_count": len(selected),
        "road_sample_count": len(road_rows),
        "district_sample_count": len(official),
        "monthly_series": monthly,
        "yearly_series": yearly,
        "recent_median_unit_price": recent,
        "trend_annualized_rate": annualized,
        "volatility": volatility,
        "confidence_level": confidence,
        "confidence_reason": reason,
        "scenario_forecast": forecast,
        "methodology": METHODOLOGY,
        "disclaimer": DISCLAIMER,
    }


def _valid_official_rows(
    rows: list[dict[str, Any]], start: str, current: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    valid = []
    raw_periods: list[str] = []
    excluded_future = 0
    excluded_out_of_window = 0
    for row in rows:
        period = str(row.get("transaction_period", ""))
        if row.get("source") != "official_plvr_opendata" or not _valid_period(period):
            continue
        raw_periods.append(period)
        if period > current:
            excluded_future += 1
            continue
        if period < start:
            excluded_out_of_window += 1
            continue
        price = float(row.get("unit_price_per_ping", 0) or 0)
        area = float(row.get("area_ping", 0) or 0)
        if price <= 0 or area <= 0 or price > 500:
            continue
        valid.append({**row, "unit_price_per_ping": price, "area_ping": area})
    return valid, {
        "raw_period_min": min(raw_periods) if raw_periods else None,
        "raw_period_max": max(raw_periods) if raw_periods else None,
        "excluded_future_period_count": excluded_future,
        "excluded_out_of_window_count": excluded_out_of_window,
    }


def _valid_period(period: str) -> bool:
    """Accept normalized calendar months only."""

    return re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period) is not None


def _monthly_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["transaction_period"])].append(float(row["unit_price_per_ping"]))
    result = []
    for period, values in sorted(grouped.items()):
        clean = _winsorized(values)
        result.append({
            "period": period,
            "median_unit_price_per_ping": round(statistics.median(clean), 2),
            "p25_unit_price_per_ping": round(_percentile(clean, 0.25), 2),
            "p75_unit_price_per_ping": round(_percentile(clean, 0.75), 2),
            "transaction_count": len(values),
        })
    return result


def _yearly_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["transaction_period"])[:4]].append(float(row["unit_price_per_ping"]))
    result = []
    previous = None
    for year, values in sorted(grouped.items()):
        median = round(statistics.median(_winsorized(values)), 2)
        yoy = round((median / previous - 1) * 100, 2) if previous else None
        result.append({"year": year, "median_unit_price_per_ping": median, "transaction_count": len(values), "yoy_change_percent": yoy})
        previous = median
    return result


def _annualized_rate(monthly: list[dict[str, Any]]) -> float:
    series = monthly[-24:]
    if len(series) < 2:
        return 0.0
    values = [item["median_unit_price_per_ping"] for item in series]
    x_mean = (len(values) - 1) / 2
    y_mean = statistics.mean(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    monthly_rate = (sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values)) / denominator / y_mean) if denominator and y_mean else 0
    return round(max(-0.10, min(0.10, monthly_rate * 12)), 4)


def _volatility(monthly: list[dict[str, Any]]) -> float | None:
    values = [item["median_unit_price_per_ping"] for item in monthly[-24:]]
    if len(values) < 3:
        return None
    changes = [(values[index] / values[index - 1] - 1) for index in range(1, len(values)) if values[index - 1]]
    return round(min(0.10, statistics.pstdev(changes) * math.sqrt(12)), 4) if changes else None


def _scenario_forecast(base_price: float, area: float, horizons: list[int], trend: float, volatility: float | None, confidence: str) -> dict[str, list[dict[str, Any]]]:
    vol = volatility or 0.03
    rates = {"conservative": max(-0.10, trend - vol), "base": max(-0.10, min(0.10, trend)), "optimistic": min(0.10, trend + vol)}
    explanations = {"conservative": "採用趨勢減去波動度的保守情境。", "base": "延續目前歷史趨勢的中性情境。", "optimistic": "採用趨勢加上波動度的樂觀情境。"}
    return {
        scenario: [
            {
                "horizon_months": int(months),
                "projected_unit_price_per_ping": round(base_price * (1 + rate) ** (int(months) / 12), 2),
                "projected_total_price": round(base_price * (1 + rate) ** (int(months) / 12) * area, 1),
                "growth_rate_used": round(rate, 4),
                "explanation": f"{explanations[scenario]}{' 低信心參考。' if confidence == 'low' else ''}",
            }
            for months in horizons
        ]
        for scenario, rate in rates.items()
    }


def _confidence(rows: list[dict[str, Any]], monthly: list[dict[str, Any]], scope: str, window_start: str) -> tuple[str, str]:
    if len(rows) < 30:
        return "low", "官方樣本少於 30 筆，僅提供低信心參考趨勢。"
    coverage_months = _month_distance(monthly[0]["period"], monthly[-1]["period"]) + 1 if monthly else 0
    if coverage_months < 48:
        return ("medium" if scope != "district" else "low"), "目前資料期間不足五年，情境估價採保守方式呈現。"
    return ("high" if scope == "road" else "medium"), "官方資料期間與樣本量足以形成歷史趨勢，但仍不代表未來成交結果。"


def _recent_median(monthly: list[dict[str, Any]]) -> float:
    values = [item["median_unit_price_per_ping"] for item in monthly[-12:]]
    return round(statistics.median(values), 2) if values else 0.0


def _winsorized(values: list[float]) -> list[float]:
    ordered = sorted(values)
    if len(ordered) < 4:
        return ordered
    q1, q3 = _percentile(ordered, 0.25), _percentile(ordered, 0.75)
    spread = q3 - q1
    lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
    return [max(lower, min(upper, value)) for value in ordered]


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _shift_month(period: str, offset: int) -> str:
    year, month = map(int, period.split("-"))
    total = year * 12 + month - 1 + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _month_distance(start: str, end: str) -> int:
    start_year, start_month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))
    return (end_year - start_year) * 12 + end_month - start_month
