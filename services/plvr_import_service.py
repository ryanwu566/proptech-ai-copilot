"""Normalize manually supplied PLVR OpenData sale CSV rows for valuation storage."""

from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


PING_PER_SQM = 0.3025
OFFICIAL_SOURCE = "official_plvr_opendata"
ENCODINGS = ("utf-8-sig", "utf-8", "cp950", "big5")
EXCLUDED_NAME_HINTS = ("schema", "manifest", "presale", "rent", "預售", "租賃", "租屋", "欄位")

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "city": ("縣市", "city"),
    "district": ("鄉鎮市區", "district"),
    "address_text": ("土地區段位置建物區段門牌", "rps02", "address_text"),
    "transaction_date": ("交易年月日", "rps07", "transaction_date"),
    "floor": ("移轉層次", "rps09", "floor"),
    "total_floor": ("總樓層數", "rps10", "total_floor"),
    "building_type": ("建物型態", "rps11", "building_type"),
    "completion_date": ("建築完成年月", "rps14", "completion_date"),
    "area_sqm": ("建物移轉總面積平方公尺", "rps15", "area_sqm"),
    "total_price_ntd": ("總價元", "rps21", "total_price_ntd"),
    "unit_price_sqm": ("單價元平方公尺", "rps22", "unit_price_sqm"),
}

REQUIRED_HEADER_GROUPS = ("district", "address_text", "transaction_date", "area_sqm", "total_price_ntd")
ROAD_PATTERN = re.compile(r"([\u4e00-\u9fffA-Za-z0-9]+(?:大道|路|街)(?:[一二三四五六七八九十百0-9]+段)?)")
FLOOR_NUMBERS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15, "十六": 16, "十七": 17,
    "十八": 18, "十九": 19, "二十": 20, "二十一": 21, "二十二": 22, "二十三": 23,
    "二十四": 24, "二十五": 25, "二十六": 26, "二十七": 27, "二十八": 28, "二十九": 29,
    "三十": 30, "地下": -1,
}


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    """Read a CSV with the common encodings used by PLVR downloads."""

    last_error: UnicodeError | None = None
    for encoding in ENCODINGS:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle)), encoding
        except UnicodeError as error:
            last_error = error
    raise ValueError(f"無法辨識 CSV 編碼：{path.name}") from last_error


def is_sale_transaction_csv(path: Path) -> bool:
    """Return whether a CSV looks like a sale transaction main table."""

    if any(hint.lower() in path.name.lower() for hint in EXCLUDED_NAME_HINTS):
        return False
    try:
        rows, _ = read_csv_rows(path)
    except (OSError, ValueError, csv.Error):
        return False
    if not rows:
        return False
    headers = set(rows[0])
    return all(any(alias in headers for alias in FIELD_ALIASES[field]) for field in REQUIRED_HEADER_GROUPS)


def normalize_rows(
    rows: Iterable[dict[str, Any]],
    *,
    city_hint: str = "",
    city_filter: str = "",
    district_filter: str = "",
    road_filter: str = "",
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize rows and return accepted rows plus a transparent QC report."""

    accepted: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    total = 0
    for row in rows:
        total += 1
        normalized, reason = normalize_row(row, city_hint=city_hint)
        if reason:
            exclusions[reason] += 1
            continue
        assert normalized is not None
        if city_filter and normalized["city"] != city_filter:
            exclusions["filtered_city"] += 1
            continue
        if district_filter and normalized["district"] != district_filter:
            exclusions["filtered_district"] += 1
            continue
        if road_filter and normalized["road"] != road_filter:
            exclusions["filtered_road"] += 1
            continue
        accepted.append(normalized)
        if limit is not None and len(accepted) >= limit:
            break
    periods = sorted({row["transaction_period"] for row in accepted})
    return accepted, {
        "read_rows": total,
        "accepted_rows": len(accepted),
        "excluded_rows": sum(exclusions.values()),
        "exclusion_reasons": dict(sorted(exclusions.items())),
        "periods": periods,
        "cities": sorted({row["city"] for row in accepted}),
        "districts": sorted({row["district"] for row in accepted}),
        "roads_count": len({(row["city"], row["district"], row["road"]) for row in accepted}),
    }


def normalize_row(row: dict[str, Any], *, city_hint: str = "") -> tuple[dict[str, Any] | None, str | None]:
    """Normalize one official row, returning an exclusion reason when invalid."""

    address = _text(row, "address_text")
    city = _text(row, "city") or city_hint.strip() or _city_from_address(address)
    district = _text(row, "district")
    road = parse_road(address)
    period = roc_date_to_period(_text(row, "transaction_date"))
    area_sqm = _number(row, "area_sqm")
    total_price_ntd = _number(row, "total_price_ntd")
    unit_price_sqm = _number(row, "unit_price_sqm")
    if not city or not district or not road:
        return None, "missing_location"
    if not period:
        return None, "invalid_transaction_date"
    if area_sqm <= 0:
        return None, "invalid_area"
    if total_price_ntd <= 0:
        return None, "invalid_total_price"
    area_ping = area_sqm * PING_PER_SQM
    total_price = total_price_ntd / 10_000
    unit_price_per_ping = (unit_price_sqm / PING_PER_SQM / 10_000) if unit_price_sqm > 0 else total_price / area_ping
    if unit_price_per_ping < 1 or unit_price_per_ping > 500:
        return None, "abnormal_unit_price"
    completion_period = roc_date_to_period(_text(row, "completion_date"))
    completion_year = int(completion_period[:4]) if completion_period else 0
    building_type = _text(row, "building_type") or "未分類"
    return {
        "transaction_period": period,
        "city": city,
        "district": district,
        "road": road,
        "address_text": address,
        "building_type": building_type,
        "area_ping": round(area_ping, 2),
        "building_age_years": max(0, date.today().year - completion_year) if completion_year else 0,
        "floor": parse_floor(_text(row, "floor")),
        "total_floor": parse_floor(_text(row, "total_floor")) or None,
        "unit_price_per_ping": round(unit_price_per_ping, 2),
        "total_price": round(total_price, 2),
        "lat": None,
        "lng": None,
        "source": OFFICIAL_SOURCE,
        "raw_note": "" if _text(row, "building_type") else "PLVR 原始資料未提供建物型態",
    }, None


def roc_date_to_period(value: str) -> str:
    """Convert ROC or Gregorian date-like values to YYYY-MM."""

    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 5:
        return ""
    if len(digits) >= 7 and int(digits[:4]) >= 1900:
        year, month = int(digits[:4]), int(digits[4:6])
    else:
        year, month = int(digits[:-4]) + 1911, int(digits[-4:-2])
    return f"{year:04d}-{month:02d}" if 1 <= month <= 12 else ""


def parse_road(address: str) -> str:
    """Extract a road or street segment from a PLVR address string."""

    location = re.sub(r"^.*?[市縣]", "", address or "", count=1)
    location = re.sub(r"^.*?[區鄉鎮市]", "", location, count=1)
    match = ROAD_PATTERN.search(location)
    return match.group(1) if match else ""


def parse_floor(value: str) -> int:
    """Parse Arabic or common Chinese floor values."""

    text = (value or "").replace("層", "").replace("樓", "").strip()
    if not text:
        return 0
    match = re.search(r"-?\d+", text)
    if match:
        return int(match.group())
    for label, number in sorted(FLOOR_NUMBERS.items(), key=lambda item: len(item[0]), reverse=True):
        if label in text:
            return number
    return 0


def _text(row: dict[str, Any], field: str) -> str:
    for alias in FIELD_ALIASES[field]:
        value = row.get(alias)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _number(row: dict[str, Any], field: str) -> float:
    value = _text(row, field).replace(",", "")
    try:
        return float(value)
    except ValueError:
        return 0.0


def _city_from_address(address: str) -> str:
    match = re.match(r"(.{2,3}[市縣])", address or "")
    return match.group(1) if match else ""
