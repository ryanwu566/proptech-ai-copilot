"""Read-model backed PLVR market aggregates for Market Insight.

Read APIs only query the prepared market read model. The raw PLVR transaction
table is used exclusively by the protected refresh path that rebuilds the
aggregate tables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Protocol

from services.market_data_foundation import MARKET_DATA_CAVEAT, market_unavailable_response


OFFICIAL_PLVR_SOURCE = "official_plvr_opendata"
PLVR_MARKET_SOURCE_NAME = "Official PLVR OpenData aggregate"
PLVR_AGGREGATION_METHOD = "avg_unit_price_per_ping_by_city_district_period"
PLVR_MARKET_CAVEAT = (
    "市場行情資料來自後台建立的官方實價登錄行政區期別彙整，只供區域背景參考；"
    "資料不足、未涵蓋或暫時不可用時，不代表該區沒有交易或風險。"
)
REFRESH_SUCCESS_MESSAGE = "市場 read model 已完成刷新。"
REFRESH_UNAVAILABLE_MESSAGE = "市場 read model 暫時無法刷新。"


MARKET_REFRESH_REASON_CODES = {
    "refresh_runtime_not_configured",
    "valuation_database_unavailable",
    "read_model_initialization_unavailable",
    "read_model_source_aggregate_unavailable",
    "read_model_write_unavailable",
    "read_model_metadata_unavailable",
    "read_model_no_eligible_source_records",
    "read_model_refresh_unavailable",
    "unknown_safe_failure",
}


class MarketReadModelRefreshError(RuntimeError):
    """Internal refresh failure with a safe public reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = safe_market_refresh_reason_code(reason_code)
        super().__init__(self.reason_code)


class MarketReadModelRepository(Protocol):
    """Repository contract for market read model operations."""

    def status(self) -> dict[str, Any]:
        """Return read model metadata."""

    def catalog(self) -> list[dict[str, Any]]:
        """Return available counties from aggregate rows."""

    def regions(self, county: str) -> list[dict[str, Any]]:
        """Return available districts for one county."""

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        """Return one aggregate row, selecting latest period when omitted."""

    def history(self, county: str, district: str, limit: int = 6) -> list[dict[str, Any]]:
        """Return recent real aggregate periods for chart/table display."""

    def refresh(self) -> dict[str, Any]:
        """Rebuild read model tables from official PLVR transaction rows."""


@dataclass(frozen=True)
class PostgresMarketReadModelRepository:
    """Postgres-backed repository for the market read model."""

    database_url: str
    connect_timeout: int = 5

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(READ_MODEL_STATUS_SQL)
                return dict(cursor.fetchone() or {})

    def catalog(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(READ_MODEL_CATALOG_SQL)
                return [dict(row) for row in cursor.fetchall()]

    def regions(self, county: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(READ_MODEL_REGIONS_SQL, [_normalize_county(county)])
                return [dict(row) for row in cursor.fetchall()]

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                if period and period.strip():
                    cursor.execute(
                        READ_MODEL_SUMMARY_FOR_PERIOD_SQL,
                        [_normalize_county(county), district.strip(), period.strip()],
                    )
                else:
                    cursor.execute(READ_MODEL_SUMMARY_LATEST_SQL, [_normalize_county(county), district.strip()])
                row = cursor.fetchone()
                return dict(row) if row else None

    def history(self, county: str, district: str, limit: int = 6) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(
                    READ_MODEL_HISTORY_SQL,
                    [_normalize_county(county), district.strip(), max(1, min(int(limit), 6))],
                )
                return [dict(row) for row in cursor.fetchall()]

    def refresh(self) -> dict[str, Any]:
        built_at = datetime.now(timezone.utc)
        try:
            connection_context = self._connect()
        except Exception as exc:
            raise MarketReadModelRefreshError("valuation_database_unavailable") from exc
        with connection_context as connection:
            with connection.cursor() as cursor:
                cursor.execute("set local statement_timeout = '120s'")
                try:
                    cursor.execute(READ_MODEL_SCHEMA_SQL)
                except Exception as exc:
                    raise MarketReadModelRefreshError("read_model_initialization_unavailable") from exc
                try:
                    cursor.execute(REFRESH_TEMP_AGGREGATES_SQL, [built_at])
                    cursor.execute(READ_MODEL_NEXT_AGGREGATE_COUNT_SQL)
                    aggregate_count = _int_value((cursor.fetchone() or {}).get("aggregate_count"))
                    if aggregate_count <= 0:
                        raise MarketReadModelRefreshError("read_model_no_eligible_source_records")
                except MarketReadModelRefreshError:
                    raise
                except Exception as exc:
                    raise MarketReadModelRefreshError("read_model_source_aggregate_unavailable") from exc
                try:
                    cursor.execute(REFRESH_TEMP_METADATA_SQL, [built_at])
                except Exception as exc:
                    raise MarketReadModelRefreshError("read_model_metadata_unavailable") from exc
                try:
                    cursor.execute("delete from market_district_period_aggregates")
                    cursor.execute(REFRESH_INSERT_AGGREGATES_SQL)
                except Exception as exc:
                    raise MarketReadModelRefreshError("read_model_write_unavailable") from exc
                try:
                    cursor.execute("delete from market_read_model_metadata")
                    cursor.execute(REFRESH_INSERT_METADATA_SQL)
                except Exception as exc:
                    raise MarketReadModelRefreshError("read_model_metadata_unavailable") from exc
            try:
                connection.commit()
            except Exception as exc:
                raise MarketReadModelRefreshError("read_model_write_unavailable") from exc
        try:
            return self.status()
        except Exception as exc:
            raise MarketReadModelRefreshError("read_model_refresh_unavailable") from exc

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout,
            prepare_threshold=None,
            row_factory=dict_row,
        )


def get_market_status(repository: MarketReadModelRepository | None = None) -> dict[str, Any]:
    """Return safe Market Insight status metadata from the read model."""

    repo = repository or _repository_from_env()
    if repo is None:
        return _missing_status()
    try:
        raw = repo.status()
    except Exception:
        return _unavailable_status()
    return _status_from_raw(raw)


def get_market_catalog(repository: MarketReadModelRepository | None = None) -> dict[str, Any]:
    """Return read model catalog metadata and available counties."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo)
    if repo is None or status["read_model_status"] != "ready":
        return {**status, "available_counties": []}
    try:
        counties = [_optional_text(row.get("county")) for row in repo.catalog()]
    except Exception:
        return {**_unavailable_status(), "available_counties": []}
    return {**status, "available_counties": [county for county in counties if county]}


def list_market_regions(county: str = "", repository: MarketReadModelRepository | None = None) -> dict[str, Any]:
    """Return read model districts for one county."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo)
    county = county.strip()
    if repo is None or status["read_model_status"] != "ready" or not county:
        return {**status, "regions": []}
    try:
        rows = repo.regions(county)
    except Exception:
        return {**_unavailable_status(), "regions": []}
    regions = [
        {
            "city": _optional_text(row.get("county")) or "",
            "county": _optional_text(row.get("county")) or "",
            "district": _optional_text(row.get("district")) or "",
            "period": _optional_text(row.get("latest_period")),
            "data_status": "available",
        }
        for row in rows
        if _optional_text(row.get("county")) and _optional_text(row.get("district"))
    ]
    return {**status, "regions": regions}


def get_market_summary(
    county: str,
    district: str,
    period: str | None = None,
    repository: MarketReadModelRepository | None = None,
) -> dict[str, Any]:
    """Return one district-period aggregate and recent real history."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo)
    county = county.strip()
    district = district.strip()
    if repo is None or status["read_model_status"] != "ready" or not county or not district:
        return _unavailable_summary(county, district, status)
    try:
        row = repo.summary(county, district, period)
        history = repo.history(county, district, limit=6) if row else []
    except Exception:
        return _unavailable_summary(county, district, _unavailable_status())
    if not row:
        return _unavailable_summary(county, district, {**status, "data_status": "unavailable"})
    return _summary_from_row(row, history, status)


def refresh_market_read_model(repository: MarketReadModelRepository | None = None) -> dict[str, Any]:
    """Rebuild read model tables and return a safe refresh response."""

    repo = repository or _repository_from_env()
    if repo is None:
        return _refresh_unavailable(_missing_status(), "valuation_database_unavailable")
    try:
        status = _status_from_raw(repo.refresh())
    except MarketReadModelRefreshError as exc:
        return _refresh_unavailable(_unavailable_status(), exc.reason_code)
    except Exception:
        return _refresh_unavailable(_unavailable_status(), "read_model_refresh_unavailable")
    if status["read_model_status"] == "ready":
        return {
            "status": "resolved",
            "data_status": status["data_status"],
            "coverage_status": status["coverage_status"],
            "built_at": status["built_at"],
            "message": REFRESH_SUCCESS_MESSAGE,
        }
    return _refresh_unavailable(status, "read_model_refresh_unavailable")


def _repository_from_env() -> MarketReadModelRepository | None:
    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    return PostgresMarketReadModelRepository(database_url) if database_url else None


def _status_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return _missing_status()
    data_status = _data_status(raw.get("data_status"))
    coverage_status = _coverage_status(raw.get("coverage_status"))
    refresh_status = _optional_text(raw.get("refresh_status"))
    latest_period = _optional_text(raw.get("latest_period"))
    earliest_period = _optional_text(raw.get("earliest_period"))
    aggregate_count = _int_value(raw.get("aggregate_region_count"))
    built_at = _date_time_text(raw.get("built_at"))
    read_model_status = "ready"
    if refresh_status != "ready" or data_status != "available" or aggregate_count <= 0 or not latest_period:
        read_model_status = "missing" if aggregate_count <= 0 else "unavailable"
    return {
        "read_model_status": read_model_status,
        "data_status": data_status,
        "coverage_status": coverage_status,
        "source_name": _optional_text(raw.get("source_name")) or PLVR_MARKET_SOURCE_NAME,
        "source_updated_at": _date_text(raw.get("source_updated_at")),
        "earliest_period": earliest_period,
        "latest_period": latest_period,
        "available_county_count": _int_value(raw.get("available_county_count")),
        "available_district_count": _int_value(raw.get("available_district_count")),
        "built_at": built_at,
        "caveat": _optional_text(raw.get("caveat")) or PLVR_MARKET_CAVEAT,
    }


def _summary_from_row(row: dict[str, Any], history_rows: list[dict[str, Any]], status: dict[str, Any]) -> dict[str, Any]:
    data_status = _data_status(row.get("data_status"))
    coverage_status = _coverage_status(row.get("coverage_status") or status.get("coverage_status"))
    county = _optional_text(row.get("county")) or ""
    district = _optional_text(row.get("district")) or ""
    if data_status != "available":
        return _unavailable_summary(county, district, {**status, "data_status": data_status})
    average_unit_price = _float_value(row.get("average_unit_price"))
    transaction_count = _int_value(row.get("transaction_count"))
    record_count = _int_value(row.get("record_count"))
    if average_unit_price is None or average_unit_price <= 0 or transaction_count <= 0 or record_count <= 0:
        return _unavailable_summary(county, district, {**status, "data_status": "invalid"})
    history = [_history_item(item) for item in history_rows[:6]]
    return {
        "city": county,
        "county": county,
        "district": district,
        "period": _optional_text(row.get("period")),
        "average_unit_price": average_unit_price,
        "avg_price_per_ping": average_unit_price,
        "transaction_count": transaction_count,
        "transaction_volume": transaction_count,
        "record_count": record_count,
        "source_name": _optional_text(row.get("source_name")) or status["source_name"],
        "source_updated_at": _date_text(row.get("source_updated_at")) or status["source_updated_at"],
        "coverage_status": coverage_status,
        "data_status": "available",
        "caveat": _optional_text(row.get("caveat")) or status["caveat"],
        "disclaimer": _optional_text(row.get("caveat")) or status["caveat"],
        "aggregation_method": _optional_text(row.get("aggregation_method")) or PLVR_AGGREGATION_METHOD,
        "history": history,
        "summary": "此為官方實價登錄行政區期別彙整資料，僅供市場背景參考。",
        "trend": [],
        "livability_score": None,
        "esg_lite_score": None,
        "poi_breakdown": {},
        "sdg11_note": "",
    }


def _history_item(row: dict[str, Any]) -> dict[str, Any]:
    average_unit_price = _float_value(row.get("average_unit_price"))
    return {
        "period": _optional_text(row.get("period")),
        "average_unit_price": average_unit_price,
        "transaction_count": _int_value(row.get("transaction_count")),
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
        "history": [],
        "record_count": None,
    }


def _missing_status() -> dict[str, Any]:
    return {
        "read_model_status": "missing",
        "data_status": "unavailable",
        "coverage_status": "unknown",
        "source_name": None,
        "source_updated_at": None,
        "earliest_period": None,
        "latest_period": None,
        "available_county_count": 0,
        "available_district_count": 0,
        "built_at": None,
        "caveat": MARKET_DATA_CAVEAT,
    }


def _unavailable_status() -> dict[str, Any]:
    return {**_missing_status(), "read_model_status": "unavailable"}


def safe_market_refresh_reason_code(reason_code: Any) -> str:
    """Return an allowlisted public reason code for refresh failures."""

    text = str(reason_code or "").strip()
    return text if text in MARKET_REFRESH_REASON_CODES else "unknown_safe_failure"


def _refresh_unavailable(status: dict[str, Any], reason_code: str = "unknown_safe_failure") -> dict[str, Any]:
    return {
        "status": "unavailable",
        "data_status": status.get("data_status", "unavailable"),
        "coverage_status": status.get("coverage_status", "unknown"),
        "built_at": status.get("built_at"),
        "message": REFRESH_UNAVAILABLE_MESSAGE,
        "reason_code": safe_market_refresh_reason_code(reason_code),
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


def _date_time_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return _optional_text(value)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _data_status(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"available", "unavailable", "incomplete", "invalid"} else "unavailable"


def _coverage_status(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"nationwide", "partial", "unknown"} else "unknown"


READ_MODEL_SCHEMA_SQL = """
create table if not exists market_district_period_aggregates (
    county text not null,
    district text not null,
    period varchar(7) not null,
    average_unit_price numeric(14, 2),
    transaction_count integer not null default 0,
    record_count integer not null default 0,
    source_name text not null,
    source_updated_at date,
    coverage_status text not null default 'unknown',
    data_status text not null default 'unavailable',
    aggregation_method text not null,
    built_at timestamptz not null,
    primary key (county, district, period)
);
create index if not exists idx_market_read_model_county on market_district_period_aggregates (county);
create index if not exists idx_market_read_model_county_district on market_district_period_aggregates (county, district);
create index if not exists idx_market_read_model_county_district_period on market_district_period_aggregates (county, district, period desc);
create index if not exists idx_market_read_model_period on market_district_period_aggregates (period desc);
create table if not exists market_read_model_metadata (
    read_model_version text primary key,
    refresh_status text not null,
    coverage_status text not null default 'unknown',
    source_name text not null,
    source_updated_at date,
    earliest_period varchar(7),
    latest_period varchar(7),
    available_county_count integer not null default 0,
    available_district_count integer not null default 0,
    aggregate_region_count integer not null default 0,
    built_at timestamptz not null,
    caveat text not null
);
"""

READ_MODEL_STATUS_SQL = """
select read_model_version, refresh_status, coverage_status, source_name, source_updated_at,
       earliest_period, latest_period, available_county_count, available_district_count,
       aggregate_region_count, built_at, caveat
from market_read_model_metadata
where read_model_version = 'v1'
limit 1
"""

READ_MODEL_CATALOG_SQL = """
select distinct county
from market_district_period_aggregates
where data_status = 'available'
order by county
"""

READ_MODEL_REGIONS_SQL = """
select county, district, max(period) as latest_period
from market_district_period_aggregates
where data_status = 'available'
  and replace(trim(county), '臺', '台') = %s
group by county, district
order by district
"""

READ_MODEL_SUMMARY_LATEST_SQL = """
select county, district, period, average_unit_price, transaction_count, record_count,
       source_name, source_updated_at, coverage_status, data_status, aggregation_method
from market_district_period_aggregates
where replace(trim(county), '臺', '台') = %s
  and trim(district) = %s
order by period desc
limit 1
"""

READ_MODEL_SUMMARY_FOR_PERIOD_SQL = """
select county, district, period, average_unit_price, transaction_count, record_count,
       source_name, source_updated_at, coverage_status, data_status, aggregation_method
from market_district_period_aggregates
where replace(trim(county), '臺', '台') = %s
  and trim(district) = %s
  and period = %s
limit 1
"""

READ_MODEL_HISTORY_SQL = """
select period, average_unit_price, transaction_count
from market_district_period_aggregates
where replace(trim(county), '臺', '台') = %s
  and trim(district) = %s
  and data_status = 'available'
order by period desc
limit %s
"""

_VALID_PLVR_WHERE = """
source = 'official_plvr_opendata'
and nullif(trim(city), '') is not null
and nullif(trim(district), '') is not null
and transaction_period ~ '^\\d{4}-(0[1-9]|1[0-2])$'
and unit_price_per_ping > 0
and unit_price_per_ping <= 500
and total_price > 0
and area_ping > 0
"""

REFRESH_TEMP_AGGREGATES_SQL = f"""
create temporary table market_read_model_next_aggregates on commit drop as
select
  replace(trim(city), '臺', '台') as county,
  trim(district) as district,
  transaction_period as period,
  round(avg(unit_price_per_ping)::numeric, 2) as average_unit_price,
  count(*)::integer as transaction_count,
  count(*)::integer as record_count,
  '{PLVR_MARKET_SOURCE_NAME}'::text as source_name,
  max(imported_at)::date as source_updated_at,
  'partial'::text as coverage_status,
  'available'::text as data_status,
  '{PLVR_AGGREGATION_METHOD}'::text as aggregation_method,
  %s::timestamptz as built_at
from real_price_transactions
where {_VALID_PLVR_WHERE}
group by replace(trim(city), '臺', '台'), trim(district), transaction_period
"""

REFRESH_TEMP_METADATA_SQL = f"""
create temporary table market_read_model_next_metadata on commit drop as
select
  'v1'::text as read_model_version,
  case when count(*) > 0 then 'ready' else 'empty' end::text as refresh_status,
  case when count(*) > 0 then 'partial' else 'unknown' end::text as coverage_status,
  '{PLVR_MARKET_SOURCE_NAME}'::text as source_name,
  max(source_updated_at)::date as source_updated_at,
  min(period)::varchar(7) as earliest_period,
  max(period)::varchar(7) as latest_period,
  count(distinct county)::integer as available_county_count,
  count(distinct (county, district))::integer as available_district_count,
  count(*)::integer as aggregate_region_count,
  %s::timestamptz as built_at,
  '{PLVR_MARKET_CAVEAT}'::text as caveat
from market_read_model_next_aggregates
"""

READ_MODEL_NEXT_AGGREGATE_COUNT_SQL = """
select count(*)::integer as aggregate_count
from market_read_model_next_aggregates
"""

REFRESH_INSERT_AGGREGATES_SQL = """
insert into market_district_period_aggregates (
  county, district, period, average_unit_price, transaction_count, record_count,
  source_name, source_updated_at, coverage_status, data_status, aggregation_method, built_at
)
select county, district, period, average_unit_price, transaction_count, record_count,
       source_name, source_updated_at, coverage_status, data_status, aggregation_method, built_at
from market_read_model_next_aggregates
"""

REFRESH_INSERT_METADATA_SQL = """
insert into market_read_model_metadata (
  read_model_version, refresh_status, coverage_status, source_name, source_updated_at,
  earliest_period, latest_period, available_county_count, available_district_count,
  aggregate_region_count, built_at, caveat
)
select read_model_version, refresh_status, coverage_status, source_name, source_updated_at,
       earliest_period, latest_period, available_county_count, available_district_count,
       aggregate_region_count, built_at, caveat
from market_read_model_next_metadata
"""
