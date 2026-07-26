"""Pure freshness rules for official PLVR data operations."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

FRESHNESS_STATUSES = ("fresh", "aging", "stale", "unknown", "no_official_data", "unavailable")
FRESHNESS_REASON_CODES = (
    "freshness_confirmed",
    "import_aging",
    "period_aging",
    "import_and_period_aging",
    "import_stale",
    "period_stale",
    "import_and_period_stale",
    "official_data_missing",
    "latest_import_missing",
    "effective_period_missing",
    "latest_import_not_completed",
    "freshness_input_invalid",
    "provider_unavailable",
)
PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
FRESH_IMPORT_AGE_DAYS = 120
AGING_IMPORT_AGE_DAYS = 210
FRESH_PERIOD_LAG_MONTHS = 4
AGING_PERIOD_LAG_MONTHS = 7
FRESHNESS_USER_MESSAGE = "資料新鮮度僅描述官方 PLVR 維運狀態，請搭配資料來源與限制說明解讀。"


def evaluate_plvr_freshness(
    *,
    official_records_count: int | None,
    latest_import_status: str | None,
    last_updated: datetime | str | None,
    newest_effective_period: str | None,
    provider_available: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate freshness without connecting to a provider or persisting data."""

    base = {
        "freshness_as_of": None,
        "latest_import_at": _format_datetime(last_updated),
        "latest_import_age_days": None,
        "newest_effective_period": newest_effective_period if isinstance(newest_effective_period, str) else None,
        "newest_effective_period_lag_months": None,
        "official_records_count": _safe_count(official_records_count),
        "latest_import_status": latest_import_status if isinstance(latest_import_status, str) else None,
        "operator_attention_required": True,
        "freshness_user_message": FRESHNESS_USER_MESSAGE,
    }
    if not provider_available:
        return {**base, "latest_import_at": None, "latest_import_status": None, "freshness_status": "unavailable", "freshness_reason_code": "provider_unavailable"}
    if base["official_records_count"] == 0:
        return {**base, "latest_import_at": None, "latest_import_status": None, "freshness_status": "no_official_data", "freshness_reason_code": "official_data_missing"}

    as_of = _as_utc(now or datetime.now(UTC))
    base["freshness_as_of"] = as_of.isoformat()
    imported_at = _parse_datetime(last_updated)
    period = newest_effective_period if isinstance(newest_effective_period, str) else ""
    if last_updated is None:
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "latest_import_missing"}
    if imported_at is None or imported_at > as_of:
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "freshness_input_invalid"}
    if not period:
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "effective_period_missing"}
    if not PERIOD_PATTERN.fullmatch(period):
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "freshness_input_invalid"}
    if _month_difference(as_of.strftime("%Y-%m"), period) > 0:
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "freshness_input_invalid"}
    if latest_import_status is None:
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "latest_import_missing"}
    if latest_import_status != "completed":
        return {**base, "freshness_status": "unknown", "freshness_reason_code": "latest_import_not_completed"}

    age_days = max(0, (as_of.date() - imported_at.date()).days)
    lag_months = _month_difference(period, as_of.strftime("%Y-%m"))
    base["latest_import_age_days"] = age_days
    base["newest_effective_period_lag_months"] = lag_months
    import_stale = age_days > AGING_IMPORT_AGE_DAYS
    period_stale = lag_months > AGING_PERIOD_LAG_MONTHS
    import_aging = age_days > FRESH_IMPORT_AGE_DAYS
    period_aging = lag_months > FRESH_PERIOD_LAG_MONTHS
    if import_stale or period_stale:
        reason = "import_and_period_stale" if import_stale and period_stale else "import_stale" if import_stale else "period_stale"
        return {**base, "freshness_status": "stale", "freshness_reason_code": reason, "operator_attention_required": True}
    if import_aging or period_aging:
        reason = "import_and_period_aging" if import_aging and period_aging else "import_aging" if import_aging else "period_aging"
        return {**base, "freshness_status": "aging", "freshness_reason_code": reason, "operator_attention_required": True}
    return {**base, "freshness_status": "fresh", "freshness_reason_code": "freshness_confirmed", "operator_attention_required": False}


def _safe_count(value: int | None) -> int:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return count if count >= 0 else 0


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except (TypeError, ValueError):
        return None


def _format_datetime(value: datetime | str | None) -> str | None:
    parsed = _parse_datetime(value)
    return parsed.isoformat() if parsed else value if isinstance(value, str) and value else None


def _month_difference(older: str, newer: str) -> int:
    old_year, old_month = (int(part) for part in older.split("-"))
    new_year, new_month = (int(part) for part in newer.split("-"))
    return max(0, (new_year - old_year) * 12 + new_month - old_month)
