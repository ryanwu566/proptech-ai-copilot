"""Shared PLVR geography and transaction-period integrity rules."""

from __future__ import annotations

import re
from datetime import date, datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from services.taiwan_admin_registry import iter_taiwan_regions, normalize_market_region


TAIPEI_TIME_ZONE = ZoneInfo("Asia/Taipei")
PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
INVALID_CITY_DISTRICT_PAIR = "invalid_city_district_pair"
FUTURE_TRANSACTION_PERIOD = "future_transaction_period"
INVALID_TRANSACTION_PERIOD = "invalid_transaction_period"
OFFICIAL_CITY_LEVEL_GEOGRAPHIES = frozenset({"新竹市", "嘉義市"})


def taipei_as_of_date(as_of: date | datetime | None = None) -> date:
    """Return a deterministic calendar date in the Asia/Taipei timezone."""

    if as_of is None:
        return datetime.now(TAIPEI_TIME_ZONE).date()
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            return as_of.replace(tzinfo=TAIPEI_TIME_ZONE).date()
        return as_of.astimezone(TAIPEI_TIME_ZONE).date()
    return as_of


def current_transaction_period(as_of: date | datetime | None = None) -> str:
    """Return the latest transaction month that may be exposed or persisted."""

    return taipei_as_of_date(as_of).strftime("%Y-%m")


def first_day_after_current_period(as_of: date | datetime | None = None) -> date:
    current = taipei_as_of_date(as_of)
    if current.month == 12:
        return date(current.year + 1, 1, 1)
    return date(current.year, current.month + 1, 1)


def is_valid_transaction_period(period: Any) -> bool:
    return bool(PERIOD_PATTERN.fullmatch(str(period or "").strip()))


def is_future_transaction_period(period: Any, *, as_of: date | datetime | None = None) -> bool:
    clean_period = str(period or "").strip()
    return is_valid_transaction_period(clean_period) and clean_period > current_transaction_period(as_of)


def is_publishable_transaction_period(period: Any, *, as_of: date | datetime | None = None) -> bool:
    clean_period = str(period or "").strip()
    return is_valid_transaction_period(clean_period) and clean_period <= current_transaction_period(as_of)


def is_publishable_transaction_date(value: date | None, *, as_of: date | datetime | None = None) -> bool:
    return value is not None and is_publishable_transaction_period(value.strftime("%Y-%m"), as_of=as_of)


def normalized_storage_key(value: Any) -> str:
    """Match the existing database's 台/臺 and whitespace normalization."""

    return re.sub(r"\s+", "", str(value or "").strip()).replace("臺", "台")


@lru_cache(maxsize=1)
def canonical_region_storage_keys() -> tuple[str, ...]:
    """Return bounded canonical pair keys sourced from the checked-in registry."""

    return tuple(
        f"{normalized_storage_key(region.county)}|{normalized_storage_key(region.district)}"
        for region in iter_taiwan_regions()
    )


def normalized_row_integrity_reason(
    row: dict[str, Any],
    *,
    as_of: date | datetime | None = None,
    allow_official_city_level: bool = False,
) -> str | None:
    """Return a stable write-block reason for a normalized storage row."""

    region = normalize_market_region(str(row.get("city") or ""), str(row.get("district") or ""))
    unit_kind = str(row.get("geographic_unit_kind") or "district")
    city_level = (
        allow_official_city_level
        and unit_kind == "city_level"
        and region.valid
        and not region.district
        and region.county in OFFICIAL_CITY_LEVEL_GEOGRAPHIES
    )
    if (not region.valid or not region.district) and not city_level:
        return INVALID_CITY_DISTRICT_PAIR
    period = str(row.get("transaction_period") or "").strip()
    if not is_valid_transaction_period(period):
        return INVALID_TRANSACTION_PERIOD
    if is_future_transaction_period(period, as_of=as_of):
        return FUTURE_TRANSACTION_PERIOD
    return None
