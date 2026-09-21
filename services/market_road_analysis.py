"""Pure, privacy-safe Market Insight road evidence rules."""

from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Iterable

from services.plvr_data_integrity import (
    current_transaction_period,
    is_valid_transaction_period,
    normalized_storage_key,
)
from services.plvr_data_freshness import evaluate_plvr_freshness
from services.taiwan_admin_registry import normalize_market_region


OFFICIAL_PLVR_SOURCE = "official_plvr_opendata"
MARKET_SOURCE_NAME = "Official PLVR OpenData aggregate"
ROAD_MINIMUM_SAMPLE = 10
MARKET_CAVEAT = "官方實價登錄歷史交易僅供市場背景參考，不代表目前有待售物件、正式鑑價或購買建議。"
ROAD_PATTERN = re.compile(
    r"^[\u4e00-\u9fffA-Za-z0-9]+(?:大道|路|街)(?:[一二三四五六七八九十百]+段)?$"
)
ROAD_ADDRESS_MARKERS = ("號", "樓", "室")
SECTION_NUMBERS = {
    "10": "十",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
}
SAFE_EVIDENCE_FIELDS = (
    "source",
    "transaction_period",
    "city",
    "district",
    "road",
    "unit_price_per_ping",
    "total_price",
    "area_ping",
    "imported_at",
)


def normalize_market_road(value: str) -> str:
    """Normalize only established spelling variants without fuzzy matching."""

    normalized = re.sub(r"\s+", "", str(value or "").strip()).replace("臺", "台")
    for number, chinese in SECTION_NUMBERS.items():
        normalized = normalized.replace(f"{number}段", f"{chinese}段")
    return normalized


def is_valid_market_road(value: str, *, county: str = "", district: str = "") -> bool:
    """Return whether a value is a bounded road/road-section identity."""

    raw = str(value or "")
    if len(raw) > 80:
        return False
    normalized = normalize_market_road(raw)
    if not normalized or any(marker in normalized for marker in ROAD_ADDRESS_MARKERS):
        return False
    if county:
        region = normalize_market_region(county, district)
        county_prefix = normalize_market_road(region.county) if region.valid else ""
        if county_prefix and normalized.startswith(county_prefix):
            return False
    return ROAD_PATTERN.fullmatch(normalized) is not None


def effective_window(as_of: date | datetime | None = None) -> tuple[str, str]:
    """Return the inclusive rolling 36-month PLVR analysis window."""

    current = current_transaction_period(as_of)
    return _shift_month(current, -35), current


def valid_market_rows(
    rows: Iterable[dict[str, Any]],
    county: str,
    district: str,
    *,
    as_of: date | datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Filter and sanitize official district evidence before sample counting."""

    requested = normalize_market_region(county, district)
    start, current = effective_window(as_of)
    valid: list[dict[str, Any]] = []
    quality = {
        "excluded_future_period_count": 0,
        "excluded_out_of_window_count": 0,
        "excluded_invalid_count": 0,
    }
    if not requested.valid or not requested.district:
        quality["excluded_invalid_count"] = sum(1 for _row in rows)
        return valid, quality

    requested_key = (
        normalized_storage_key(requested.county),
        normalized_storage_key(requested.district),
    )
    for row in rows:
        period = str(row.get("transaction_period") or "").strip()
        if not is_valid_transaction_period(period):
            quality["excluded_invalid_count"] += 1
            continue
        if period > current:
            quality["excluded_future_period_count"] += 1
            continue
        if period < start:
            quality["excluded_out_of_window_count"] += 1
            continue
        row_key = (
            normalized_storage_key(row.get("city")),
            normalized_storage_key(row.get("district")),
        )
        price = _positive_number(row.get("unit_price_per_ping"))
        total_price = _positive_number(row.get("total_price"))
        area = _positive_number(row.get("area_ping"))
        road = normalize_market_road(str(row.get("road") or ""))
        if (
            row.get("source") != OFFICIAL_PLVR_SOURCE
            or row_key != requested_key
            or price is None
            or price > 500
            or total_price is None
            or area is None
            or not is_valid_market_road(road)
        ):
            quality["excluded_invalid_count"] += 1
            continue
        safe = {key: row.get(key) for key in SAFE_EVIDENCE_FIELDS}
        safe.update(
            {
                "source": OFFICIAL_PLVR_SOURCE,
                "transaction_period": period,
                "city": normalized_storage_key(requested.county),
                "district": normalized_storage_key(requested.district),
                "road": road,
                "unit_price_per_ping": price,
                "total_price": total_price,
                "area_ping": area,
            }
        )
        valid.append(safe)
    return valid, quality


def analyze_market_road(
    rows: Iterable[dict[str, Any]],
    county: str,
    district: str,
    requested_road: str,
    *,
    latest_import_status: str | None = None,
    latest_imported_at: datetime | str | None = None,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Select one truthful evidence scope and calculate supported metrics."""

    raw_road = str(requested_road or "").strip()
    normalized_road = normalize_market_road(raw_road)
    normalized_region = normalize_market_region(county, district)
    requested_city = normalized_storage_key(normalized_region.county or county)
    requested_district = normalized_storage_key(normalized_region.district or district)
    requested_metadata = {
        "requested_scope": "ROAD",
        "requested_city": requested_city,
        "requested_district": requested_district,
        "requested_road": raw_road,
        "normalized_road": normalized_road,
        "road_minimum_sample": ROAD_MINIMUM_SAMPLE,
    }
    if (
        not normalized_region.valid
        or not normalized_region.district
        or not is_valid_market_road(raw_road, county=county, district=district)
    ):
        return _not_available_result(
            requested_metadata,
            road_count=0,
            district_count=0,
            fallback_reason="market_road_invalid",
            quality=_empty_quality(),
            latest_import_status=latest_import_status,
            latest_imported_at=latest_imported_at,
            as_of=as_of,
        )

    district_rows, quality = valid_market_rows(rows, county, district, as_of=as_of)
    road_rows = [row for row in district_rows if normalize_market_road(row["road"]) == normalized_road]
    if len(road_rows) >= ROAD_MINIMUM_SAMPLE:
        level = "ROAD"
        selected = road_rows
        fallback_reason = None
        fallback_applied = False
        effective_scope_label = f"{requested_city} / {requested_district} / {normalized_road}"
    elif len(district_rows) >= ROAD_MINIMUM_SAMPLE:
        level = "DISTRICT"
        selected = district_rows
        fallback_reason = "road_sample_below_threshold"
        fallback_applied = True
        effective_scope_label = f"{requested_city} / {requested_district}"
    else:
        return _not_available_result(
            requested_metadata,
            road_count=len(road_rows),
            district_count=len(district_rows),
            fallback_reason="district_sample_below_threshold",
            quality=quality,
            latest_import_status=latest_import_status,
            latest_imported_at=latest_imported_at or _latest_imported_at(district_rows),
            newest_period=max((row["transaction_period"] for row in district_rows), default=None),
            as_of=as_of,
        )

    metrics = _statistics(selected)
    imported_at = latest_imported_at or _latest_imported_at(selected)
    freshness = evaluate_plvr_freshness(
        official_records_count=len(selected),
        latest_import_status=latest_import_status,
        last_updated=imported_at,
        newest_effective_period=metrics["period_max"],
        provider_available=True,
        now=_freshness_now(as_of),
    )
    return {
        "city": requested_city,
        "county": requested_city,
        "district": requested_district,
        **requested_metadata,
        "analysis_level": level,
        "effective_analysis_level": level,
        "effective_scope_label": effective_scope_label,
        "effective_sample_count": len(selected),
        "road_sample_count": len(road_rows),
        "district_sample_count": len(district_rows),
        "fallback_applied": fallback_applied,
        "fallback_reason": fallback_reason,
        "period": metrics["period_max"],
        "period_min": metrics["period_min"],
        "period_max": metrics["period_max"],
        "newest_effective_period": metrics["period_max"],
        "average_unit_price": metrics["average_unit_price"],
        "avg_price_per_ping": metrics["average_unit_price"],
        "transaction_count": len(selected),
        "transaction_volume": len(selected),
        "record_count": len(selected),
        "median_unit_price_per_ping": metrics["median_unit_price_per_ping"],
        "p25_unit_price_per_ping": metrics["p25_unit_price_per_ping"],
        "p75_unit_price_per_ping": metrics["p75_unit_price_per_ping"],
        "median_total_price": metrics["median_total_price"],
        "median_area_ping": metrics["median_area_ping"],
        "monthly_series": metrics["monthly_series"],
        "yearly_series": metrics["yearly_series"],
        "year_over_year_change": metrics["year_over_year_change"],
        "volatility": metrics["volatility"],
        "history": metrics["history"],
        "source_name": MARKET_SOURCE_NAME,
        "source_updated_at": _source_updated_at(imported_at),
        "latest_imported_at": _datetime_text(imported_at),
        "coverage_status": "covered",
        "data_status": "available",
        "sample_status": "sufficient",
        "summary": (
            "本次使用同一路段官方實價登錄交易分析。"
            if level == "ROAD"
            else "指定路段樣本不足，本次使用同行政區官方實價登錄交易分析。"
        ),
        "caveat": MARKET_CAVEAT,
        "disclaimer": MARKET_CAVEAT,
        "aggregation_method": "official_plvr_rolling_36_month_scope_statistics",
        "methodology": "先套用官方來源、有效期別與市場品質規則，再依 ROAD → DISTRICT → NOT_AVAILABLE 選擇單一證據範圍。",
        "excluded_future_period_count": quality["excluded_future_period_count"],
        "excluded_out_of_window_count": quality["excluded_out_of_window_count"],
        "excluded_invalid_count": quality["excluded_invalid_count"],
        "trend": [],
        "livability_score": None,
        "esg_lite_score": None,
        "poi_breakdown": {},
        "sdg11_note": "",
        **freshness,
    }


def _statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [float(row["unit_price_per_ping"]) for row in rows]
    totals = [float(row["total_price"]) for row in rows]
    areas = [float(row["area_ping"]) for row in rows]
    periods = [str(row["transaction_period"]) for row in rows]
    monthly_groups: dict[str, list[float]] = defaultdict(list)
    yearly_groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        price = float(row["unit_price_per_ping"])
        period = str(row["transaction_period"])
        monthly_groups[period].append(price)
        yearly_groups[period[:4]].append(price)

    monthly_series = [
        {
            "period": period,
            "median_unit_price_per_ping": round(statistics.median(values), 2),
            "p25_unit_price_per_ping": round(_percentile(values, 0.25), 2),
            "p75_unit_price_per_ping": round(_percentile(values, 0.75), 2),
            "transaction_count": len(values),
        }
        for period, values in sorted(monthly_groups.items())
    ]
    history = [
        {
            "period": period,
            "average_unit_price": round(statistics.mean(values), 2),
            "transaction_count": len(values),
        }
        for period, values in sorted(monthly_groups.items(), reverse=True)[:6]
    ]
    yearly_series: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for year, values in sorted(yearly_groups.items()):
        median = round(statistics.median(values), 2)
        yoy_percent = None
        if (
            previous
            and int(year) == int(previous["year"]) + 1
            and previous["transaction_count"] >= ROAD_MINIMUM_SAMPLE
            and len(values) >= ROAD_MINIMUM_SAMPLE
            and previous["median_unit_price_per_ping"] > 0
        ):
            yoy_percent = round((median / previous["median_unit_price_per_ping"] - 1) * 100, 2)
        point = {
            "year": year,
            "median_unit_price_per_ping": median,
            "transaction_count": len(values),
            "yoy_change_percent": yoy_percent,
        }
        yearly_series.append(point)
        previous = point
    latest_yoy = yearly_series[-1]["yoy_change_percent"] if yearly_series else None
    return {
        "period_min": min(periods),
        "period_max": max(periods),
        "average_unit_price": round(statistics.mean(prices), 2),
        "median_unit_price_per_ping": round(statistics.median(prices), 2),
        "p25_unit_price_per_ping": round(_percentile(prices, 0.25), 2),
        "p75_unit_price_per_ping": round(_percentile(prices, 0.75), 2),
        "median_total_price": round(statistics.median(totals), 2),
        "median_area_ping": round(statistics.median(areas), 2),
        "monthly_series": monthly_series,
        "yearly_series": yearly_series,
        "year_over_year_change": round(latest_yoy / 100, 4) if latest_yoy is not None else None,
        "volatility": _volatility(monthly_series),
        "history": history,
    }


def _not_available_result(
    requested_metadata: dict[str, Any],
    *,
    road_count: int,
    district_count: int,
    fallback_reason: str,
    quality: dict[str, int],
    latest_import_status: str | None,
    latest_imported_at: datetime | str | None,
    newest_period: str | None = None,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    freshness = evaluate_plvr_freshness(
        official_records_count=district_count,
        latest_import_status=latest_import_status,
        last_updated=latest_imported_at,
        newest_effective_period=newest_period,
        provider_available=True,
        now=_freshness_now(as_of),
    )
    return {
        "city": requested_metadata["requested_city"],
        "county": requested_metadata["requested_city"],
        "district": requested_metadata["requested_district"],
        **requested_metadata,
        "analysis_level": "NOT_AVAILABLE",
        "effective_analysis_level": "NOT_AVAILABLE",
        "effective_scope_label": "",
        "effective_sample_count": 0,
        "road_sample_count": road_count,
        "district_sample_count": district_count,
        "fallback_applied": True,
        "fallback_reason": fallback_reason,
        "period": None,
        "period_min": None,
        "period_max": None,
        "newest_effective_period": newest_period,
        "average_unit_price": None,
        "avg_price_per_ping": None,
        "transaction_count": None,
        "transaction_volume": None,
        "record_count": None,
        "median_unit_price_per_ping": None,
        "p25_unit_price_per_ping": None,
        "p75_unit_price_per_ping": None,
        "median_total_price": None,
        "median_area_ping": None,
        "monthly_series": [],
        "yearly_series": [],
        "year_over_year_change": None,
        "volatility": None,
        "history": [],
        "source_name": MARKET_SOURCE_NAME,
        "source_updated_at": _source_updated_at(latest_imported_at),
        "latest_imported_at": _datetime_text(latest_imported_at),
        "coverage_status": "covered",
        "data_status": "no_data",
        "sample_status": "insufficient" if district_count else "no_data",
        "summary": "目前此行政區在有效 36 個月期間內沒有足夠的官方 PLVR 市場證據。",
        "caveat": MARKET_CAVEAT,
        "disclaimer": MARKET_CAVEAT,
        "excluded_future_period_count": quality["excluded_future_period_count"],
        "excluded_out_of_window_count": quality["excluded_out_of_window_count"],
        "excluded_invalid_count": quality["excluded_invalid_count"],
        "trend": [],
        **freshness,
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _volatility(monthly: list[dict[str, Any]]) -> float | None:
    if len(monthly) < 3:
        return None
    values = [float(item["median_unit_price_per_ping"]) for item in monthly[-24:]]
    changes = [values[index] / values[index - 1] - 1 for index in range(1, len(values)) if values[index - 1]]
    return round(min(0.10, statistics.pstdev(changes) * math.sqrt(12)), 4) if changes else None


def _latest_imported_at(rows: list[dict[str, Any]]) -> Any:
    values = [row.get("imported_at") for row in rows if row.get("imported_at") is not None]
    return max(values, key=lambda value: str(value)) if values else None


def _source_updated_at(value: datetime | str | None) -> str | None:
    text = _datetime_text(value)
    return text[:10] if text else None


def _datetime_text(value: datetime | str | None) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).strip() if value is not None and str(value).strip() else None


def _freshness_now(as_of: date | datetime | None) -> datetime | None:
    if isinstance(as_of, datetime):
        return as_of
    if isinstance(as_of, date):
        return datetime(as_of.year, as_of.month, as_of.day)
    return None


def _empty_quality() -> dict[str, int]:
    return {
        "excluded_future_period_count": 0,
        "excluded_out_of_window_count": 0,
        "excluded_invalid_count": 0,
    }


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _shift_month(period: str, offset: int) -> str:
    year, month = map(int, period.split("-"))
    total = year * 12 + month - 1 + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"
