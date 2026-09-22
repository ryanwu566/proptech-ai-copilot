"""Pure normalization for MOI RIS village population rows (ODRP014).

This module contains *no* I/O. It transforms already-collected raw rows
(strings, exactly as returned by the API) into normalized demographic metrics
required by the product:

* ROC ``yyymm`` -> Gregorian ``YYYY-MM``.
* Age aggregation into 0-14, 15-64 and 65+ (65+ includes the ``100up`` bucket).
* Dependency ratios (child / working-age / elderly) as fractions of the total
  population.
* Average household size.
* Required-field validation and negative-value rejection.
* Consistency checks (``male + female == total``; age-bucket sum not greater
  than total). Discrepancies are recorded as *audit reasons*; the module never
  silently rewrites the reported numbers.

Ratios and average household size are ``None`` when their denominator is zero;
they are never coerced to ``0``.
"""

from __future__ import annotations

from typing import Any

# Age-bucket boundaries (inclusive).
CHILD_MAX_AGE = 14          # 0..14  -> age_0_14
WORKING_AGE_MIN = 15        # 15..64 -> age_15_64
WORKING_AGE_MAX = 64
ELDERLY_MIN_AGE = 65        # 65..99 and the 100up bucket -> age_65_plus
MAX_SINGLE_AGE = 99         # single-year buckets run 000..099
TOP_AGE_BUCKET = "100up"    # people_age_100up_m / _f

IDENTITY_FIELDS = ("statistic_yyymm", "district_code", "site_id", "village")
TOTAL_FIELDS = ("household_no", "people_total", "people_total_m", "people_total_f")

# ROC year offset: ROC year + 1911 == Gregorian year.
ROC_YEAR_OFFSET = 1911


class RisNormalizationError(ValueError):
    """A raw row could not be normalized (missing field, non-numeric, negative)."""


def roc_yyymm_to_gregorian(yyymm: str) -> str:
    """Convert a ROC ``yyymm`` string to Gregorian ``YYYY-MM``.

    Example: ``"11507"`` -> ``"2026-07"`` (ROC 115 == 2026, month 07).
    The ROC year portion is all leading digits except the final two, which are
    the month; this supports 2- and 3-digit ROC years.
    """

    cleaned = str(yyymm).strip()
    if not cleaned.isdigit() or len(cleaned) < 3:
        raise RisNormalizationError(f"invalid ROC yyymm: {yyymm!r}")
    roc_year = int(cleaned[:-2])
    month = int(cleaned[-2:])
    if not 1 <= month <= 12:
        raise RisNormalizationError(f"invalid month in ROC yyymm: {yyymm!r}")
    gregorian_year = roc_year + ROC_YEAR_OFFSET
    return f"{gregorian_year:04d}-{month:02d}"


def _age_key(age: int, sex: str) -> str:
    return f"people_age_{age:03d}_{sex}"


def _require_int(row: dict[str, Any], field: str) -> int:
    if field not in row:
        raise RisNormalizationError(f"missing required field {field!r}")
    raw = row[field]
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise RisNormalizationError(f"field {field!r} is not an integer: {raw!r}") from exc
    if value < 0:
        raise RisNormalizationError(f"field {field!r} is negative: {value}")
    return value


def _sum_age_range(row: dict[str, Any], start: int, end: int) -> int:
    total = 0
    for age in range(start, end + 1):
        total += _require_int(row, _age_key(age, "m"))
        total += _require_int(row, _age_key(age, "f"))
    return total


def _sum_top_bucket(row: dict[str, Any]) -> int:
    total = 0
    for sex in ("m", "f"):
        total += _require_int(row, f"people_age_{TOP_AGE_BUCKET}_{sex}")
    return total


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single raw RIS row into product demographic metrics.

    Raises :class:`RisNormalizationError` for missing fields, non-integer
    values, or negative values. Consistency discrepancies do not raise; they
    are recorded in ``audit_reasons`` and the reported numbers are preserved.
    """

    for field in IDENTITY_FIELDS:
        if not str(row.get(field, "")).strip():
            raise RisNormalizationError(f"missing or empty identity field {field!r}")

    household_count = _require_int(row, "household_no")
    total_population = _require_int(row, "people_total")
    male_population = _require_int(row, "people_total_m")
    female_population = _require_int(row, "people_total_f")

    age_0_14 = _sum_age_range(row, 0, CHILD_MAX_AGE)
    age_15_64 = _sum_age_range(row, WORKING_AGE_MIN, WORKING_AGE_MAX)
    # 65+ combines single-year buckets 65..99 plus the 100up bucket.
    age_65_plus = _sum_age_range(row, ELDERLY_MIN_AGE, MAX_SINGLE_AGE) + _sum_top_bucket(row)

    audit_reasons: list[str] = []
    if male_population + female_population != total_population:
        audit_reasons.append(
            "sex_total_mismatch: people_total_m + people_total_f "
            f"({male_population} + {female_population} = {male_population + female_population}) "
            f"!= people_total ({total_population})"
        )
    age_bucket_sum = age_0_14 + age_15_64 + age_65_plus
    if age_bucket_sum > total_population:
        audit_reasons.append(
            "age_bucket_overflow: age_0_14 + age_15_64 + age_65_plus "
            f"({age_bucket_sum}) > people_total ({total_population})"
        )

    return {
        "statistic_yyymm": str(row["statistic_yyymm"]).strip(),
        "statistic_month": roc_yyymm_to_gregorian(row["statistic_yyymm"]),
        "district_code": str(row["district_code"]).strip(),
        "site_id": str(row["site_id"]).strip(),
        "village": str(row["village"]).strip(),
        "household_count": household_count,
        "total_population": total_population,
        "male_population": male_population,
        "female_population": female_population,
        "age_0_14": age_0_14,
        "age_15_64": age_15_64,
        "age_65_plus": age_65_plus,
        "child_ratio": _ratio(age_0_14, total_population),
        "working_age_ratio": _ratio(age_15_64, total_population),
        "elderly_ratio": _ratio(age_65_plus, total_population),
        "average_household_size": _ratio(total_population, household_count),
        "audit_reasons": audit_reasons,
    }


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a list of raw rows, preserving order."""

    return [normalize_row(row) for row in rows]


def summarize_identity(normalized: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize village identity within a single statistic month.

    Reports duplicate composite keys and coverage without building any alias or
    history system. The composite key is ``(district_code, site_id, village)``;
    ``district_code`` alone is also checked for duplicates because it is the
    candidate unique per-village identifier observed within the current
    statistic month. Cross-month stability is not asserted here and must be
    validated separately (Phase 2).
    """

    composite_seen: dict[tuple[str, str, str], int] = {}
    district_code_seen: dict[str, int] = {}
    null_identity_rows = 0
    cities: set[str] = set()
    districts: set[str] = set()

    for item in normalized:
        district_code = item["district_code"]
        site_id = item["site_id"]
        village = item["village"]
        if not district_code or not site_id or not village:
            null_identity_rows += 1
        composite = (district_code, site_id, village)
        composite_seen[composite] = composite_seen.get(composite, 0) + 1
        district_code_seen[district_code] = district_code_seen.get(district_code, 0) + 1
        # site_id is a "city+district" name string; expose both the full label
        # and coverage counts without parsing it into structured admin fields.
        districts.add(site_id)
        cities.add(site_id[:3] if len(site_id) >= 3 else site_id)

    duplicate_composite_keys = {
        key: count for key, count in composite_seen.items() if count > 1
    }
    duplicate_district_codes = {
        code: count for code, count in district_code_seen.items() if count > 1
    }

    return {
        "row_count": len(normalized),
        "unique_composite_keys": len(composite_seen),
        "unique_district_codes": len(district_code_seen),
        "duplicate_composite_key_count": len(duplicate_composite_keys),
        "duplicate_district_code_count": len(duplicate_district_codes),
        "duplicate_composite_keys": duplicate_composite_keys,
        "duplicate_district_codes": duplicate_district_codes,
        "null_identity_rows": null_identity_rows,
        "city_label_count": len(cities),
        "district_label_count": len(districts),
    }
