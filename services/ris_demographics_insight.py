"""Derived, fail-closed insight for RIS village demographics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


MONTH_GAP_LIMIT = 13
STALE_AFTER_MONTHS = 2


def build_demographics_insight(
    latest: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a bounded summary without filling or inventing missing months."""

    if latest is None:
        return {"status": "no_data", "reason": reason or "demographics_not_available_for_village_code"}
    if not _valid_observation(latest):
        return {"status": "no_data", "reason": "demographics_observation_invalid"}

    observations = [row for row in history or [] if _valid_observation(row)]
    if not observations:
        observations = [latest]
    observations.sort(key=lambda row: _month_key(row.get("statistic_yyymm")))
    first = observations[0]
    last = observations[-1]
    first_population = _number(first.get("total_population"))
    last_population = _number(last.get("total_population"))
    first_households = _number(first.get("household_count"))
    last_households = _number(last.get("household_count"))
    population_change = last_population - first_population
    household_change = last_households - first_households
    population_change_ratio = population_change / first_population if first_population else None

    return {
        **_freshness(latest),
        "status": "available",
        "reason": reason,
        "statistic_yyymm": latest.get("statistic_yyymm"),
        "statistic_month": latest.get("statistic_month"),
        "total_population": _number(latest.get("total_population")),
        "household_count": _number(latest.get("household_count")),
        "average_household_size": latest.get("average_household_size"),
        "child_ratio": latest.get("child_ratio"),
        "working_age_ratio": latest.get("working_age_ratio"),
        "elderly_ratio": latest.get("elderly_ratio"),
        "first_month": first.get("statistic_yyymm"),
        "last_month": last.get("statistic_yyymm"),
        "observed_month_count": len(observations),
        "population_change": population_change,
        "population_change_ratio": population_change_ratio,
        "household_change": household_change,
        "has_month_gaps": _has_month_gaps(observations),
        "trend_status": _trend_status(population_change),
        "source_provider": latest.get("source_provider", "RIS"),
        "source_dataset": latest.get("source_dataset", "ODRP014"),
    }


def _number(value: Any) -> int:
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite() or parsed < 0 or parsed != parsed.to_integral_value():
            raise ValueError("invalid demographic count")
        return int(parsed)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid demographic count") from exc


def _valid_observation(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict) or _month_key(row.get("statistic_yyymm")) == (0, 0):
        return False
    try:
        _number(row.get("total_population"))
        _number(row.get("household_count"))
        return True
    except ValueError:
        return False


def _freshness(latest: dict[str, Any]) -> dict[str, Any]:
    today = date.today()
    year, month = _month_key(latest.get("statistic_yyymm"))
    lag = (today.year - (year + 1911)) * 12 + today.month - month
    status = "unknown" if lag < 0 else "stale" if lag > STALE_AFTER_MONTHS else "current"
    return {"latest_statistic_yyymm": latest.get("statistic_yyymm"), "freshness_status": status, "freshness_reason_code": "statistical_month_future" if lag < 0 else "statistical_month_stale" if status == "stale" else "statistical_month_current", "statistical_month_lag": lag, "stale_after_months": STALE_AFTER_MONTHS, "freshness_as_of": today.isoformat()}


def _month_key(value: Any) -> tuple[int, int]:
    text = str(value or "")
    if 5 <= len(text) <= 6 and text.isdigit():
        year, month = int(text[:-2]), int(text[-2:])
        return (year, month) if year > 0 and 1 <= month <= 12 else (0, 0)
    if isinstance(value, date):
        return value.year - 1911, value.month
    return (0, 0)


def _has_month_gaps(observations: list[dict[str, Any]]) -> bool:
    months = [_month_key(row.get("statistic_yyymm")) for row in observations]
    if len(months) < 2:
        return False
    ordinal = [year * 12 + month for year, month in months]
    return any(right - left > 1 for left, right in zip(ordinal, ordinal[1:]))


def _trend_status(change: int) -> str:
    if change > 0:
        return "increasing"
    if change < 0:
        return "decreasing"
    return "stable"
