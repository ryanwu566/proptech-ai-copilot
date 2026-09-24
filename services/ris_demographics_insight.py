"""Derived, fail-closed insight for RIS village demographics."""

from __future__ import annotations

from datetime import date
from typing import Any


MONTH_GAP_LIMIT = 13


def build_demographics_insight(
    latest: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a bounded summary without filling or inventing missing months."""

    if latest is None:
        return {"status": "no_data", "reason": reason or "demographics_not_available_for_village_code"}

    observations = list(history or [])
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
        "status": "available",
        "reason": reason,
        "statistic_yyymm": latest.get("statistic_yyymm"),
        "statistic_month": latest.get("statistic_month"),
        "total_population": last_population,
        "household_count": last_households,
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
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _month_key(value: Any) -> tuple[int, int]:
    text = str(value or "")
    if len(text) >= 5 and text.isdigit():
        return int(text[:-2]), int(text[-2:])
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
