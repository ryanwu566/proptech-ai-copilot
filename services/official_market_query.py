"""Read-only query adapter for the official PLVR pipeline tables."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from services.plvr_data_integrity import (
    current_transaction_period,
    first_day_after_current_period,
    is_publishable_transaction_period,
)
from services.taiwan_admin_registry import normalize_market_region


SAFE_QUERY_FIELDS = (
    "county", "district", "period", "transaction_type", "sample_status", "transaction_count", "source_name",
    "valid_comparable_count", "median_unit_price_ntd_sqm", "mean_unit_price_ntd_sqm",
    "lower_quartile_unit_price_ntd_sqm", "upper_quartile_unit_price_ntd_sqm", "median_total_price_ntd",
    "median_area_sqm", "total_transaction_value_ntd", "source_release_id", "source_updated_at",
    "coverage_status", "data_status", "aggregation_version", "methodology", "caveat",
)


def _connect():
    import psycopg

    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    if not database_url:
        return None
    return psycopg.connect(database_url, connect_timeout=5, prepare_threshold=None)


def query_aggregate(
    county: str,
    district: str = "",
    period: str | None = None,
    transaction_type: str = "existing_sale",
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    normalized = normalize_market_region(county, district)
    if not normalized.valid:
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "reason": "invalid_region"}
    if period and not is_publishable_transaction_period(period, as_of=as_of):
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "reason": "future_period_excluded"}
    connection = _connect()
    if connection is None:
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "reason": "configuration_required"}
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("set transaction read only")
                sql = "select " + ", ".join(SAFE_QUERY_FIELDS) + " from market_region_period_aggregates where county = %s and (%s = '' or district = %s) and period <= %s and (%s is null or period = %s) and transaction_type = %s order by period desc limit 1"
                cursor.execute(
                    sql,
                    [
                        normalized.county,
                        normalized.district,
                        normalized.district,
                        current_transaction_period(as_of),
                        period,
                        period,
                        transaction_type,
                    ],
                )
                row = cursor.fetchone()
                if not row:
                    return {"data_status": "no_data", "coverage_status": "covered", "county": normalized.county, "district": normalized.district}
                columns = [description.name for description in cursor.description]
                return {key: value for key, value in zip(columns, row) if key in SAFE_QUERY_FIELDS}
    except Exception:
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "reason": "query_unavailable"}
    finally:
        connection.close()


def query_comparables(
    county: str,
    district: str,
    transaction_type: str = "existing_sale",
    limit: int = 10,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    normalized = normalize_market_region(county, district)
    if not normalized.valid:
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "comparables": []}
    connection = _connect()
    if connection is None:
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "comparables": []}
    bounded_limit = max(1, min(int(limit), 10))
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("set transaction read only")
                cursor.execute("select county, district, transaction_date, area_sqm, total_price_ntd, unit_price_ntd_sqm, unit_price_ntd_ping, building_type, special_transaction_flags, release_id from market_transactions where county = %s and district = %s and transaction_type = %s and validation_status in ('valid','valid_with_warning') and transaction_date < %s order by transaction_date desc nulls last limit %s", [normalized.county, normalized.district, transaction_type, first_day_after_current_period(as_of), bounded_limit])
                rows = cursor.fetchall()
                return {"data_status": "available" if rows else "no_data", "coverage_status": "covered", "comparables": [
                    {"county": row[0], "district": row[1], "transaction_month": row[2].strftime("%Y-%m") if row[2] else None, "area_sqm": row[3], "total_price_ntd": row[4], "unit_price_ntd_sqm": row[5], "unit_price_ntd_ping": row[6], "building_type": row[7], "special_transaction_flags": row[8] if isinstance(row[8], list) else [], "source_release_id": row[9], "limitation": "Comparable reference only; not an appraisal."}
                    for row in rows
                ]}
    except Exception:
        return {"data_status": "unavailable", "coverage_status": "coverage_unknown", "comparables": []}
    finally:
        connection.close()


def release_status() -> dict[str, Any]:
    connection = _connect()
    if connection is None:
        return {"releases": [], "active_release_id": None, "freshness_status": "configuration_required", "status": "unavailable"}
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("set transaction read only")
                cursor.execute("select release_id, publication_date, discovered_at, schema_version, status, is_active, input_rows, accepted_rows, quarantined_rows from official_market_releases order by publication_date desc nulls last, discovered_at desc limit 12")
                rows = cursor.fetchall()
                releases = [{"release_id": row[0], "publication_date": row[1].isoformat() if row[1] else None, "discovered_at": row[2].isoformat() if row[2] else None, "schema_version": row[3], "status": row[4], "is_active": bool(row[5]), "input_rows": row[6], "accepted_rows": row[7], "quarantined_rows": row[8]} for row in rows]
                active = next((row for row in releases if row["is_active"]), None)
                return {"releases": releases, "active_release_id": active["release_id"] if active else None, "freshness_status": "current" if active else "unknown", "status": "ready" if active else "no_data"}
    except Exception:
        return {"releases": [], "active_release_id": None, "freshness_status": "unknown", "status": "unavailable"}
    finally:
        connection.close()


def methodology() -> dict[str, Any]:
    return {
        "methodology_version": "median-quartiles-v1",
        "primary_metric": "median_unit_price_ntd_sqm",
        "default_transaction_type": "existing_sale",
        "sample_thresholds": {"sufficient": 10, "limited": 3, "insufficient": 1, "no_data": 0},
        "disclaimer": "Market Insight is an aggregated reference, not an appraisal or purchase recommendation.",
    }
