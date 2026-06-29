"""Read-only PLVR aggregate bridge for Market Insight.

The bridge reads prepared official PLVR valuation rows and returns district
level aggregates. It never runs imports, never writes to the database, and
never exposes raw transaction rows.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from services.market_data_foundation import (
    MARKET_DATA_CAVEAT,
    build_market_region_record,
    market_catalog_unavailable,
    market_unavailable_response,
)


OFFICIAL_PLVR_SOURCE = "official_plvr_opendata"
PLVR_MARKET_SOURCE_NAME = "Official PLVR OpenData aggregate"
PLVR_AGGREGATION_METHOD = "avg_unit_price_per_ping_by_city_district_period"
PLVR_MARKET_CAVEAT = (
    "行政區行情由既有官方 PLVR 實價登錄交易資料彙整，僅供市場背景參考；資料不足、涵蓋不完整或暫時不可用時，"
    "不代表價格較低、風險較低或適合購買。"
)


class MarketAggregateRepository(Protocol):
    """Safe read-only repository contract for aggregate queries."""

    def status(self) -> dict[str, Any]:
        """Return aggregate status metadata."""

    def regions(self, county: str = "") -> list[dict[str, Any]]:
        """Return available county/district region pairs."""

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        """Return one aggregate summary, selecting the latest period when omitted."""


@dataclass(frozen=True)
class PostgresMarketAggregateRepository:
    """Postgres-backed read-only aggregate repository."""

    database_url: str
    connect_timeout: int = 5

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(_STATUS_SQL)
                status = dict(cursor.fetchone() or {})
                cursor.execute(_IMPORT_SQL)
                latest_import = dict(cursor.fetchone() or {})
        return {**status, **latest_import}

    def regions(self, county: str = "") -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                params: list[Any] = []
                where = [_VALID_MARKET_WHERE]
                if county.strip():
                    where.append("replace(trim(city), '臺', '台') = %s")
                    params.append(_normalize_county(county))
                cursor.execute(
                    f"""
                    select city as county, district, max(transaction_period) as latest_period,
                           count(*)::bigint as transaction_count
                    from real_price_transactions
                    where {' and '.join(where)}
                    group by city, district
                    order by city, district
                    """,
                    params,
                )
                return [dict(row) for row in cursor.fetchall()]

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                params: list[Any] = [_normalize_county(county), district.strip()]
                period_clause = ""
                if period and period.strip():
                    period_clause = "and transaction_period = %s"
                    params.append(period.strip())
                cursor.execute(
                    f"""
                    select city as county, district, transaction_period as period,
                           round(avg(unit_price_per_ping)::numeric, 2)::float as average_unit_price,
                           count(*)::bigint as transaction_count,
                           count(*)::bigint as record_count
                    from real_price_transactions
                    where {_VALID_MARKET_WHERE}
                      and replace(trim(city), '臺', '台') = %s
                      and trim(district) = %s
                      {period_clause}
                    group by city, district, transaction_period
                    order by transaction_period desc
                    limit 1
                    """,
                    params,
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout,
            prepare_threshold=None,
            row_factory=dict_row,
        )


def get_market_status(repository: MarketAggregateRepository | None = None) -> dict[str, Any]:
    """Return safe Market Insight status metadata."""

    repo = repository or _repository_from_env()
    if repo is None:
        return _unavailable_status()
    try:
        raw = repo.status()
    except Exception:
        return _unavailable_status()
    return _status_from_raw(raw)


def list_market_regions(county: str = "", repository: MarketAggregateRepository | None = None) -> dict[str, Any]:
    """Return safe available county/district pairs."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo)
    if status["data_status"] != "available" or repo is None:
        return {**market_catalog_unavailable(), **status, "regions": []}
    try:
        regions = repo.regions(county)
    except Exception:
        return {**market_catalog_unavailable(), **_unavailable_status(), "regions": []}
    public_regions = [
        {
            "city": str(row.get("county") or ""),
            "county": str(row.get("county") or ""),
            "district": str(row.get("district") or ""),
            "period": _optional_text(row.get("latest_period")),
            "data_status": "available",
        }
        for row in regions
        if _optional_text(row.get("county")) and _optional_text(row.get("district"))
    ]
    return {
        "regions": public_regions,
        "data_status": "available" if public_regions else "unavailable",
        "coverage_status": status["coverage_status"],
        "source_name": status["source_name"],
        "source_updated_at": status["source_updated_at"],
        "available_county_count": status["available_county_count"],
        "available_district_count": len(public_regions),
        "earliest_period": status["earliest_period"],
        "latest_period": status["latest_period"],
        "caveat": status["caveat"],
    }


def get_market_summary(
    county: str,
    district: str,
    period: str | None = None,
    repository: MarketAggregateRepository | None = None,
) -> dict[str, Any]:
    """Return a district-period PLVR aggregate or a safe unavailable response."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo)
    county = county.strip()
    district = district.strip()
    if status["data_status"] != "available" or repo is None or not county or not district:
        return _unavailable_summary(county, district, status)
    try:
        row = repo.summary(county, district, period)
    except Exception:
        return _unavailable_summary(county, district, _unavailable_status())
    if not row:
        return _unavailable_summary(county, district, {**status, "data_status": "unavailable"})
    try:
        return build_market_region_record(
            {
                "county": row.get("county"),
                "district": row.get("district"),
                "period": row.get("period"),
                "average_unit_price": row.get("average_unit_price"),
                "transaction_count": row.get("transaction_count"),
                "record_count": row.get("record_count"),
                "source_name": status["source_name"],
                "source_updated_at": status["source_updated_at"],
                "coverage_status": status["coverage_status"],
                "data_status": "available",
                "caveat": status["caveat"],
                "aggregation_method": PLVR_AGGREGATION_METHOD,
            },
            status,
        )
    except Exception:
        return _unavailable_summary(county, district, {**status, "data_status": "invalid"})


def _repository_from_env() -> MarketAggregateRepository | None:
    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    return PostgresMarketAggregateRepository(database_url) if database_url else None


def _status_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    candidate_count = _int_value(raw.get("valid_market_aggregate_candidate_count"))
    county_count = _int_value(raw.get("available_county_count"))
    district_count = _int_value(raw.get("available_district_count"))
    latest_import_at = _date_text(raw.get("latest_successful_import_at"))
    earliest_period = _optional_text(raw.get("earliest_period"))
    latest_period = _optional_text(raw.get("latest_period"))
    data_status = "available" if candidate_count > 0 and earliest_period and latest_period else "unavailable"
    if data_status == "available" and not latest_import_at:
        data_status = "incomplete"
    return {
        "data_status": data_status,
        "coverage_status": _coverage_status(county_count, district_count, raw),
        "source_name": PLVR_MARKET_SOURCE_NAME if data_status in {"available", "incomplete"} else None,
        "source_updated_at": latest_import_at,
        "available_county_count": county_count,
        "available_district_count": district_count,
        "earliest_period": earliest_period,
        "latest_period": latest_period,
        "caveat": PLVR_MARKET_CAVEAT,
    }


def _coverage_status(county_count: int, district_count: int, raw: dict[str, Any]) -> str:
    if county_count <= 0 or district_count <= 0:
        return "unknown"
    scope_text = " ".join(
        str(raw.get(key) or "") for key in ("city_scope", "district_scope", "latest_import_scope")
    ).strip()
    return "partial" if scope_text or county_count > 0 else "unknown"


def _unavailable_status() -> dict[str, Any]:
    return {
        "data_status": "unavailable",
        "coverage_status": "unknown",
        "source_name": None,
        "source_updated_at": None,
        "available_county_count": 0,
        "available_district_count": 0,
        "earliest_period": None,
        "latest_period": None,
        "caveat": MARKET_DATA_CAVEAT,
    }


def _unavailable_summary(county: str, district: str, status: dict[str, Any]) -> dict[str, Any]:
    result = market_unavailable_response(county, district)
    return {
        **result,
        "data_status": status.get("data_status", "unavailable"),
        "coverage_status": status.get("coverage_status", "unknown"),
        "source_name": status.get("source_name"),
        "source_updated_at": status.get("source_updated_at"),
        "caveat": status.get("caveat") or MARKET_DATA_CAVEAT,
        "disclaimer": status.get("caveat") or MARKET_DATA_CAVEAT,
    }


def _set_read_only(cursor: Any) -> None:
    cursor.execute("set transaction read only")
    cursor.execute("set local statement_timeout = '15s'")


def _normalize_county(value: str) -> str:
    return value.strip().replace("臺", "台")


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


_VALID_MARKET_WHERE = """
source = 'official_plvr_opendata'
and nullif(trim(city), '') is not null
and nullif(trim(district), '') is not null
and transaction_period ~ '^\\d{4}-(0[1-9]|1[0-2])$'
and unit_price_per_ping > 0
and unit_price_per_ping <= 500
and total_price > 0
and area_ping > 0
"""

_STATUS_SQL = f"""
select
  count(distinct city) filter (where {_VALID_MARKET_WHERE}) as available_county_count,
  count(distinct (city, district)) filter (where {_VALID_MARKET_WHERE}) as available_district_count,
  min(transaction_period) filter (where {_VALID_MARKET_WHERE}) as earliest_period,
  max(transaction_period) filter (where {_VALID_MARKET_WHERE}) as latest_period,
  count(*) filter (where {_VALID_MARKET_WHERE}) as valid_market_aggregate_candidate_count
from real_price_transactions
"""

_IMPORT_SQL = """
select imported_at::date as latest_successful_import_at,
       city_scope,
       district_scope
from valuation_import_runs
where status = 'completed'
order by imported_at desc
limit 1
"""
