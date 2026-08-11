"""PLVR market aggregates for Market Insight.

Interactive Market Insight queries read official PLVR transaction rows through
safe district/county aggregates. The protected read model refresh path remains
available for operator diagnostics, but user queries do not depend on refresh
or prepared read model tables.
"""

from __future__ import annotations

from contextlib import contextmanager
import math
import os
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Protocol

from services.market_data_foundation import MARKET_DATA_CAVEAT, market_unavailable_response
from services.plvr_data_integrity import (
    canonical_region_storage_keys,
    current_transaction_period,
    is_future_transaction_period,
    is_publishable_transaction_period,
    normalized_storage_key,
)
from services.taiwan_admin_registry import audit_region_coverage, iter_taiwan_regions, normalize_market_region


logger = logging.getLogger("proptech.market")


OFFICIAL_PLVR_SOURCE = "official_plvr_opendata"
PLVR_MARKET_SOURCE_NAME = "Official PLVR OpenData aggregate"
PLVR_AGGREGATION_METHOD = "avg_unit_price_per_ping_by_city_district_period"
MARKET_NO_DATA_SUMMARY = "目前此區域尚無足夠的官方 PLVR 市場資料。"
MARKET_UNAVAILABLE_SUMMARY = "市場資料目前無法使用，請稍後再試。"
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

COVERAGE_BOOTSTRAP_REASON_CODES = {
    "coverage_bootstrap_route_unavailable",
    "coverage_bootstrap_migration_unavailable",
    "coverage_bootstrap_runtime_unavailable",
    "coverage_bootstrap_unknown_safe_failure",
}

COVERAGE_RECONCILE_REASON_CODES = {
    "coverage_reconcile_route_unavailable",
    "coverage_reconcile_request_invalid",
    "coverage_reconcile_metadata_unavailable",
    "coverage_reconcile_runtime_unavailable",
    "coverage_reconcile_unknown_safe_failure",
}

MARKET_QUERY_REASON_CODES = {
    "market_runtime_not_configured",
    "market_region_invalid",
    "market_coverage_query_unavailable",
    "market_coverage_not_confirmed",
    "market_summary_query_unavailable",
    "market_history_query_unavailable",
    "market_summary_missing",
    "market_history_invalid",
    "market_result_contract_invalid",
    "market_unknown_safe_failure",
}


class MarketReadModelRefreshFailure(RuntimeError):
    """Internal refresh failure with a safe public reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = safe_market_refresh_reason_code(reason_code)
        super().__init__(self.reason_code)


MarketReadModelRefreshError = MarketReadModelRefreshFailure


class MarketCoverageBootstrapFailure(RuntimeError):
    """Internal bootstrap failure with a safe public reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = safe_market_coverage_bootstrap_reason_code(reason_code)
        super().__init__(self.reason_code)


class MarketCoverageReconcileFailure(RuntimeError):
    """Internal reconcile failure with a safe public reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = safe_market_coverage_reconcile_reason_code(reason_code)
        super().__init__(self.reason_code)


class MarketQueryFailure(RuntimeError):
    """Internal direct-query failure with a safe reason and phase."""

    def __init__(self, reason_code: str, phase: str) -> None:
        self.reason_code = safe_market_query_reason_code(reason_code)
        self.phase = phase if phase in {
            "connection",
            "cursor",
            "transaction_read_only",
            "statement_timeout",
            "coverage_sql",
            "summary_sql",
            "history_sql",
            "row_conversion",
            "result_contract",
        } else "query"
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

    def coverage(self, county: str, district: str) -> dict[str, Any]:
        """Return bounded region coverage metadata for direct queries."""

    def refresh(self) -> dict[str, Any]:
        """Rebuild read model tables from official PLVR transaction rows."""


@dataclass(frozen=True)
class PostgresMarketReadModelRepository:
    """Postgres-backed repository for the market read model."""

    database_url: str
    connect_timeout: int = 5
    as_of: date | datetime | None = None

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(
                    READ_MODEL_STATUS_SQL,
                    [list(canonical_region_storage_keys()), current_transaction_period(self.as_of)],
                )
                return dict(cursor.fetchone() or {})

    def catalog(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(
                    READ_MODEL_CATALOG_SQL,
                    [list(canonical_region_storage_keys()), current_transaction_period(self.as_of)],
                )
                return [dict(row) for row in cursor.fetchall()]

    def regions(self, county: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(
                    READ_MODEL_REGIONS_SQL,
                    [
                        list(canonical_region_storage_keys()),
                        current_transaction_period(self.as_of),
                        _normalize_county(county),
                    ],
                )
                return [dict(row) for row in cursor.fetchall()]

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        with _market_query_cursor(self, "market_summary_query_unavailable") as cursor:
            normalized_county = _normalize_county(county)
            clean_district = normalized_storage_key(district)
            clean_period = (period or "").strip()
            base_params: list[Any] = [
                list(canonical_region_storage_keys()),
                current_transaction_period(self.as_of),
                normalized_county,
            ]
            try:
                if clean_district and clean_period:
                    cursor.execute(DIRECT_SUMMARY_DISTRICT_FOR_PERIOD_SQL, [*base_params, clean_district, clean_period])
                elif clean_district:
                    cursor.execute(DIRECT_SUMMARY_DISTRICT_LATEST_SQL, [*base_params, clean_district])
                elif clean_period:
                    cursor.execute(DIRECT_SUMMARY_COUNTY_FOR_PERIOD_SQL, [*base_params, clean_period])
                else:
                    cursor.execute(DIRECT_SUMMARY_COUNTY_LATEST_SQL, base_params)
            except Exception as exc:
                raise MarketQueryFailure("market_summary_query_unavailable", "summary_sql") from exc
            try:
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception as exc:
                raise MarketQueryFailure("market_summary_query_unavailable", "row_conversion") from exc

    def history(self, county: str, district: str, limit: int = 6) -> list[dict[str, Any]]:
        with _market_query_cursor(self, "market_history_query_unavailable") as cursor:
            normalized_county = _normalize_county(county)
            clean_district = normalized_storage_key(district)
            clean_limit = max(1, min(int(limit), 6))
            base_params: list[Any] = [
                list(canonical_region_storage_keys()),
                current_transaction_period(self.as_of),
                normalized_county,
            ]
            try:
                if clean_district:
                    cursor.execute(DIRECT_HISTORY_DISTRICT_SQL, [*base_params, clean_district, clean_limit])
                else:
                    cursor.execute(DIRECT_HISTORY_COUNTY_SQL, [*base_params, clean_limit])
            except Exception as exc:
                raise MarketQueryFailure("market_history_query_unavailable", "history_sql") from exc
            try:
                return [dict(row) for row in cursor.fetchall()]
            except Exception as exc:
                raise MarketQueryFailure("market_history_query_unavailable", "row_conversion") from exc

    def coverage(self, county: str, district: str) -> dict[str, Any]:
        with _market_query_cursor(self, "market_coverage_query_unavailable") as cursor:
            normalized_county = _normalize_county(county)
            metadata_district = district.strip()
            clean_district = normalized_storage_key(district)
            ceiling = current_transaction_period(self.as_of)
            try:
                if metadata_district:
                    cursor.execute(MARKET_COVERAGE_METADATA_DISTRICT_SQL, [normalized_county, metadata_district])
                else:
                    cursor.execute(MARKET_COVERAGE_METADATA_COUNTY_SQL, [normalized_county])
                metadata_row = dict(cursor.fetchone() or {})
            except Exception as exc:
                raise MarketQueryFailure("market_coverage_query_unavailable", "coverage_sql") from exc
            metadata_result: dict[str, Any] | None = None
            if metadata_row:
                metadata_result = {
                    "coverage_status": _direct_coverage_status(metadata_row.get("coverage_status")),
                    "valid_market_candidate_count": _int_value(metadata_row.get("valid_market_candidate_count")),
                    "source_updated_at": _date_text(metadata_row.get("source_updated_at")),
                }
            try:
                source_params: list[Any] = [
                    ceiling,
                    ceiling,
                    ceiling,
                    list(canonical_region_storage_keys()),
                    normalized_county,
                ]
                if clean_district:
                    cursor.execute(DIRECT_COVERAGE_DISTRICT_SQL, [*source_params, clean_district])
                else:
                    cursor.execute(DIRECT_COVERAGE_COUNTY_SQL, source_params)
                row = dict(cursor.fetchone() or {})
            except Exception as exc:
                raise MarketQueryFailure("market_coverage_query_unavailable", "coverage_sql") from exc
            try:
                valid_count = _int_value(row.get("valid_market_candidate_count"))
                excluded_future_count = _int_value(row.get("excluded_future_period_count"))
                source_updated_at = _date_text(row.get("source_updated_at"))
            except Exception as exc:
                raise MarketQueryFailure("market_coverage_query_unavailable", "row_conversion") from exc
            if valid_count > 0:
                return {
                    "coverage_status": "covered",
                    "valid_market_candidate_count": valid_count,
                    "source_updated_at": source_updated_at,
                }
            if excluded_future_count > 0:
                return {
                    "coverage_status": "coverage_unknown",
                    "valid_market_candidate_count": 0,
                    "source_updated_at": source_updated_at,
                }
            if metadata_result is not None:
                return metadata_result
            return {
                "coverage_status": "coverage_unknown",
                "valid_market_candidate_count": valid_count,
                "source_updated_at": source_updated_at,
            }

    def refresh(self) -> dict[str, Any]:
        built_at = datetime.now(timezone.utc)
        connection_context = _run_refresh_phase("valuation_database_unavailable", self._connect)
        with connection_context as connection:
            with connection.cursor() as cursor:
                cursor.execute("set local statement_timeout = '120s'")
                _run_refresh_phase("read_model_initialization_unavailable", lambda: cursor.execute(READ_MODEL_SCHEMA_SQL))

                def build_source_aggregates() -> None:
                    cursor.execute(
                        REFRESH_TEMP_AGGREGATES_SQL,
                        [built_at, list(canonical_region_storage_keys()), current_transaction_period(self.as_of)],
                    )
                    cursor.execute(READ_MODEL_NEXT_AGGREGATE_COUNT_SQL)
                    aggregate_count = _int_value((cursor.fetchone() or {}).get("aggregate_count"))
                    if aggregate_count <= 0:
                        raise MarketReadModelRefreshFailure("read_model_no_eligible_source_records")

                _run_refresh_phase("read_model_source_aggregate_unavailable", build_source_aggregates)
                _run_refresh_phase("read_model_metadata_unavailable", lambda: cursor.execute(REFRESH_TEMP_METADATA_SQL, [built_at]))

                def replace_aggregates() -> None:
                    cursor.execute("delete from market_district_period_aggregates")
                    cursor.execute(REFRESH_INSERT_AGGREGATES_SQL)

                _run_refresh_phase("read_model_write_unavailable", replace_aggregates)

                def replace_metadata() -> None:
                    cursor.execute("delete from market_read_model_metadata")
                    cursor.execute(REFRESH_INSERT_METADATA_SQL)

                _run_refresh_phase("read_model_metadata_unavailable", replace_metadata)
            _run_refresh_phase("read_model_write_unavailable", connection.commit)
        return _run_refresh_phase("read_model_refresh_unavailable", self.status)

    def bootstrap_coverage_metadata(self) -> dict[str, Any]:
        connection_context = _run_bootstrap_phase("coverage_bootstrap_runtime_unavailable", self._connect)
        with connection_context as connection:
            with connection.cursor() as cursor:
                _run_bootstrap_phase(
                    "coverage_bootstrap_migration_unavailable",
                    lambda: cursor.execute("set local statement_timeout = '60s'"),
                )
                _run_bootstrap_phase(
                    "coverage_bootstrap_migration_unavailable",
                    lambda: cursor.execute(MARKET_DIRECT_QUERY_INDEX_SCHEMA_SQL),
                )
                _run_bootstrap_phase(
                    "coverage_bootstrap_migration_unavailable",
                    lambda: cursor.execute(MARKET_COVERAGE_METADATA_SCHEMA_SQL),
                )
            _run_bootstrap_phase("coverage_bootstrap_migration_unavailable", connection.commit)
        return {"migration_status": "applied_or_already_present"}

    def reconcile_coverage(self, county: str) -> dict[str, Any]:
        normalized = normalize_market_region(county)
        if not normalized.valid:
            raise MarketCoverageReconcileFailure("coverage_reconcile_request_invalid")
        county_regions = _run_reconcile_phase(
            "coverage_reconcile_runtime_unavailable",
            lambda: [region for region in iter_taiwan_regions() if region.county == normalized.county],
        )
        if not county_regions:
            raise MarketCoverageReconcileFailure("coverage_reconcile_request_invalid")
        reconciled_at = datetime.now(timezone.utc)
        degraded_rows = [
            {"coverage_status": "coverage_unknown", "valid_market_candidate_count": 0}
            for _region in county_regions
        ]
        try:
            connection_context = self._connect()
            with connection_context as connection:
                with connection.cursor() as cursor:
                    try:
                        cursor.execute("set local statement_timeout = '90s'")
                        cursor.execute(MARKET_COVERAGE_METADATA_SCHEMA_SQL)
                    except Exception:
                        return _coverage_reconcile_response(normalized.county, degraded_rows, persistence_status="degraded")
                    counts: list[dict[str, Any]] = []
                    for region in county_regions:
                        try:
                            ceiling = current_transaction_period(self.as_of)
                            cursor.execute(
                                DIRECT_COVERAGE_DISTRICT_SQL,
                                [
                                    ceiling,
                                    ceiling,
                                    ceiling,
                                    list(canonical_region_storage_keys()),
                                    _normalize_county(region.county),
                                    normalized_storage_key(region.district),
                                ],
                            )
                            coverage = dict(cursor.fetchone() or {})
                            valid_count = _int_value(coverage.get("valid_market_candidate_count"))
                            source_updated_at = _date_text(coverage.get("source_updated_at"))
                            coverage_status = "covered"
                        except Exception:
                            return _coverage_reconcile_response(normalized.county, degraded_rows, persistence_status="degraded")
                        try:
                            cursor.execute(
                                MARKET_COVERAGE_METADATA_UPSERT_SQL,
                                [
                                    region.county,
                                    region.district,
                                    coverage_status,
                                    valid_count,
                                    source_updated_at,
                                    reconciled_at,
                                ],
                            )
                        except Exception:
                            return _coverage_reconcile_response(normalized.county, degraded_rows, persistence_status="degraded")
                        counts.append({"coverage_status": coverage_status, "valid_market_candidate_count": valid_count})
                try:
                    connection.commit()
                except Exception:
                    return _coverage_reconcile_response(normalized.county, degraded_rows, persistence_status="degraded")
            return _coverage_reconcile_response(normalized.county, counts)
        except Exception:
            return _coverage_reconcile_response(normalized.county, degraded_rows, persistence_status="degraded")

    def audit_coverage(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _set_read_only(cursor)
                cursor.execute(MARKET_COVERAGE_METADATA_AUDIT_SQL)
                rows = [dict(row) for row in cursor.fetchall()]
        covered = [
            (_optional_text(row.get("county")) or "", _optional_text(row.get("district")) or "")
            for row in rows
            if _direct_coverage_status(row.get("coverage_status")) == "covered"
        ]
        unknown = [
            (_optional_text(row.get("county")) or "", _optional_text(row.get("district")) or "")
            for row in rows
            if _direct_coverage_status(row.get("coverage_status")) == "coverage_unknown"
        ]
        return audit_region_coverage(covered, unknown_regions=unknown)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout,
            prepare_threshold=None,
            row_factory=dict_row,
        )


@contextmanager
def _market_query_cursor(repository: PostgresMarketReadModelRepository, reason_code: str):
    """Open a read-only query cursor while preserving the failing phase."""

    try:
        connection = repository._connect()
    except Exception as exc:
        raise MarketQueryFailure(reason_code, "connection") from exc
    try:
        with connection:
            try:
                cursor = connection.cursor()
            except Exception as exc:
                raise MarketQueryFailure(reason_code, "cursor") from exc
            with cursor:
                try:
                    cursor.execute("set transaction read only")
                except Exception as exc:
                    raise MarketQueryFailure(reason_code, "transaction_read_only") from exc
                try:
                    cursor.execute("set local statement_timeout = '15s'")
                except Exception as exc:
                    raise MarketQueryFailure(reason_code, "statement_timeout") from exc
                yield cursor
    except MarketQueryFailure:
        raise
    except Exception as exc:
        raise MarketQueryFailure(reason_code, "query") from exc


def get_market_status(
    repository: MarketReadModelRepository | None = None,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Return safe Market Insight status metadata from the read model."""

    repo = repository or _repository_from_env()
    if repo is None:
        return _missing_status()
    try:
        raw = repo.status()
    except Exception:
        return _unavailable_status()
    return _status_from_raw(raw, as_of=as_of)


def get_market_catalog(
    repository: MarketReadModelRepository | None = None,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Return read model catalog metadata and available counties."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo, as_of=as_of)
    if repo is None or status["read_model_status"] != "ready":
        return {**status, "available_counties": []}
    try:
        counties = [_optional_text(row.get("county")) for row in repo.catalog()]
    except Exception:
        return {**_unavailable_status(), "available_counties": []}
    return {**status, "available_counties": [county for county in counties if county]}


def list_market_regions(
    county: str = "",
    repository: MarketReadModelRepository | None = None,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Return read model districts for one county."""

    repo = repository or _repository_from_env()
    status = get_market_status(repo, as_of=as_of)
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
        if _optional_text(row.get("county"))
        and _optional_text(row.get("district"))
        and is_publishable_transaction_period(row.get("latest_period"), as_of=as_of)
    ]
    return {**status, "regions": regions}


def get_market_summary(
    county: str,
    district: str = "",
    period: str | None = None,
    repository: MarketReadModelRepository | None = None,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Return one direct county/district aggregate and recent real history."""

    support_reference = _new_support_reference()
    repo = repository or _repository_from_env()
    normalized = normalize_market_region(county, district)
    county = normalized.county
    district = normalized.district
    _log_market_query_event(
        "query_started",
        support_reference=support_reference,
        operation="query",
        county=county,
        district=district,
    )
    if repo is None:
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_runtime_not_configured",
        )
    if not normalized.valid:
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_region_invalid",
        )
    if period and not is_publishable_transaction_period(period, as_of=as_of):
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_summary_missing",
        )
    try:
        _log_market_query_event(
            "coverage_started",
            support_reference=support_reference,
            operation="coverage",
            county=county,
            district=district,
        )
        coverage = _coverage_for_region(repo, county, district)
        _log_market_query_event(
            "coverage_resolved",
            support_reference=support_reference,
            operation="coverage",
            county=county,
            district=district,
            reason_code=None,
            coverage_status=coverage.get("coverage_status"),
        )
    except MarketQueryFailure as exc:
        _log_repository_failure(
            "coverage",
            exc,
            exc.reason_code,
            support_reference,
            county=county,
            district=district,
            phase=exc.phase,
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            exc.reason_code,
        )
    except Exception as exc:
        _log_repository_failure(
            "coverage",
            exc,
            "market_coverage_query_unavailable",
            support_reference,
            county=county,
            district=district,
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_coverage_query_unavailable",
        )
    if coverage["coverage_status"] != "covered":
        return _query_unavailable(
            county,
            district,
            _direct_query_status(
                data_status="unavailable",
                coverage_status=coverage["coverage_status"],
                source_updated_at=coverage.get("source_updated_at"),
            ),
            support_reference,
            "market_coverage_not_confirmed",
        )
    try:
        _log_market_query_event(
            "summary_started",
            support_reference=support_reference,
            operation="summary",
            county=county,
            district=district,
        )
        row = repo.summary(county, district, period)
        _log_market_query_event(
            "summary_resolved",
            support_reference=support_reference,
            operation="summary",
            county=county,
            district=district,
            has_row=isinstance(row, dict),
        )
    except MarketQueryFailure as exc:
        _log_repository_failure(
            "summary",
            exc,
            exc.reason_code,
            support_reference,
            county=county,
            district=district,
            phase=exc.phase,
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            exc.reason_code,
        )
    except Exception as exc:
        _log_repository_failure(
            "summary",
            exc,
            "market_summary_query_unavailable",
            support_reference,
            county=county,
            district=district,
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_summary_query_unavailable",
        )
    try:
        _log_market_query_event(
            "history_started",
            support_reference=support_reference,
            operation="history",
            county=county,
            district=district,
        )
        history = repo.history(county, district, limit=6) if row else []
        _log_market_query_event(
            "history_resolved",
            support_reference=support_reference,
            operation="history",
            county=county,
            district=district,
            history_count=len(history) if isinstance(history, list) else None,
        )
    except MarketQueryFailure as exc:
        _log_repository_failure(
            "history",
            exc,
            exc.reason_code,
            support_reference,
            county=county,
            district=district,
            phase=exc.phase,
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            exc.reason_code,
        )
    except Exception as exc:
        _log_repository_failure(
            "history",
            exc,
            "market_history_query_unavailable",
            support_reference,
            county=county,
            district=district,
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_history_query_unavailable",
        )
    if not isinstance(row, dict):
        result = _no_data_summary(
            county,
            district,
            _direct_query_status(data_status="no_data", coverage_status="covered", source_updated_at=coverage.get("source_updated_at")),
        )
        _log_market_query_event(
            "query_unavailable",
            support_reference=support_reference,
            operation="summary",
            county=county,
            district=district,
            reason_code="market_summary_missing",
        )
        return _with_query_diagnostics(result, support_reference, "market_summary_missing")
    if not isinstance(history, list):
        result = _no_data_summary(
            county,
            district,
            _direct_query_status(data_status="no_data", coverage_status="covered", source_updated_at=coverage.get("source_updated_at")),
        )
        _log_market_query_event(
            "query_unavailable",
            support_reference=support_reference,
            operation="history",
            county=county,
            district=district,
            reason_code="market_history_invalid",
        )
        return _with_query_diagnostics(result, support_reference, "market_history_invalid")

    if is_future_transaction_period(row.get("period"), as_of=as_of):
        return _query_unavailable(
            county,
            district,
            _direct_query_status(
                data_status="unavailable",
                coverage_status="coverage_unknown",
                source_updated_at=coverage.get("source_updated_at"),
            ),
            support_reference,
            "market_summary_missing",
        )
    history = [
        item
        for item in history
        if not isinstance(item, dict)
        or not is_future_transaction_period(item.get("period"), as_of=as_of)
    ]

    try:
        result = _summary_from_row(
            row,
            history,
            _direct_query_status(coverage_status="covered", source_updated_at=coverage.get("source_updated_at")),
            as_of=as_of,
        )
    except Exception as exc:
        _log_repository_failure(
            "result_contract",
            exc,
            "market_result_contract_invalid",
            support_reference,
            county=county,
            district=district,
            phase="result_contract",
        )
        return _query_unavailable(
            county,
            district,
            _direct_query_status(data_status="unavailable", coverage_status="coverage_unknown"),
            support_reference,
            "market_result_contract_invalid",
        )
    if result.get("data_status") == "available":
        _log_market_query_event(
            "result_contract_checked",
            support_reference=support_reference,
            operation="result_contract",
            county=county,
            district=district,
            contract_valid=True,
        )
        return _with_query_diagnostics(result, support_reference)

    reason_code = "market_summary_missing" if str(row.get("data_status") or "").strip() == "no_data" else "market_result_contract_invalid"
    _log_market_query_event(
        "query_unavailable",
        support_reference=support_reference,
        operation="result_contract",
        county=county,
        district=district,
        reason_code=reason_code,
    )
    return _with_query_diagnostics(result, support_reference, reason_code)


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


def bootstrap_market_coverage_metadata(repository: Any | None = None) -> dict[str, Any]:
    """Apply or verify the operator coverage metadata schema safely."""

    repo = repository or _repository_from_env()
    if repo is None or not hasattr(repo, "bootstrap_coverage_metadata"):
        return {
            "status": "unavailable",
            "operation": "bootstrap",
            "migration_status": "unavailable",
            "message": "Market coverage metadata is temporarily unavailable.",
            "reason_code": "coverage_bootstrap_runtime_unavailable",
        }
    try:
        raw = repo.bootstrap_coverage_metadata()
    except MarketCoverageBootstrapFailure as exc:
        return {
            "status": "unavailable",
            "operation": "bootstrap",
            "migration_status": "unavailable",
            "message": "Market coverage metadata is temporarily unavailable.",
            "reason_code": exc.reason_code,
        }
    except Exception:
        return {
            "status": "unavailable",
            "operation": "bootstrap",
            "migration_status": "unavailable",
            "message": "Market coverage metadata is temporarily unavailable.",
            "reason_code": "coverage_bootstrap_unknown_safe_failure",
        }
    migration_status = _optional_text(raw.get("migration_status")) or "applied_or_already_present"
    return {
        "status": "resolved",
        "operation": "bootstrap",
        "migration_status": migration_status,
        "message": "Market coverage metadata is ready.",
    }


def reconcile_market_coverage(county: str, repository: Any | None = None) -> dict[str, Any]:
    """Reconcile one canonical county into safe coverage metadata."""

    repo = repository or _repository_from_env()
    clean_county = (county or "").strip()
    if not clean_county:
        return _coverage_reconcile_unavailable(clean_county, "coverage_reconcile_request_invalid")
    if repo is None or not hasattr(repo, "reconcile_coverage"):
        return _coverage_reconcile_unavailable(clean_county, "coverage_reconcile_route_unavailable")
    try:
        raw = repo.reconcile_coverage(clean_county)
    except MarketCoverageReconcileFailure as exc:
        if exc.reason_code in {"coverage_reconcile_metadata_unavailable", "coverage_reconcile_runtime_unavailable"}:
            return _coverage_reconcile_degraded(clean_county)
        return _coverage_reconcile_unavailable(clean_county, exc.reason_code)
    except Exception:
        return _coverage_reconcile_degraded(clean_county)
    if "processed_region_count" in raw:
        return _safe_coverage_reconcile_result(raw, clean_county)
    return _coverage_reconcile_response(
        _optional_text(raw.get("county")) or clean_county,
        [
            {
                "coverage_status": _direct_coverage_status(row.get("coverage_status")),
                "valid_market_candidate_count": _int_value(row.get("valid_market_candidate_count")),
            }
            for row in raw.get("regions", [])
            if isinstance(row, dict)
        ],
    )


def audit_market_coverage(repository: Any | None = None) -> dict[str, Any]:
    """Audit nationwide coverage metadata against the canonical registry."""

    repo = repository or _repository_from_env()
    if repo is None or not hasattr(repo, "audit_coverage"):
        audit = audit_region_coverage([], unknown_regions=[])
        return {**audit, "status": "UNKNOWN", "unknown_region_count": audit["expected_region_count"]}
    try:
        raw = repo.audit_coverage()
    except Exception:
        audit = audit_region_coverage([], unknown_regions=[])
        return {**audit, "status": "UNKNOWN", "unknown_region_count": audit["expected_region_count"]}
    return {
        "status": str(raw.get("status") or "UNKNOWN"),
        "expected_region_count": _int_value(raw.get("expected_region_count")),
        "covered_region_count": _int_value(raw.get("covered_region_count")),
        "missing_region_count": _int_value(raw.get("missing_region_count")),
        "unknown_region_count": _int_value(raw.get("unknown_region_count")),
        "missing_regions": _safe_region_labels(raw.get("missing_regions")),
        "unknown_regions": _safe_region_labels(raw.get("unknown_regions")),
    }


def _repository_from_env() -> MarketReadModelRepository | None:
    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    return PostgresMarketReadModelRepository(database_url) if database_url else None


def _coverage_reconcile_response(
    county: str,
    rows: list[dict[str, Any]],
    *,
    persistence_status: str = "applied",
) -> dict[str, Any]:
    processed = len(rows)
    covered = sum(1 for row in rows if _direct_coverage_status(row.get("coverage_status")) == "covered")
    not_covered = sum(1 for row in rows if _direct_coverage_status(row.get("coverage_status")) == "not_covered")
    unknown = max(0, processed - covered - not_covered)
    coverage_status = "coverage_unknown"
    if processed > 0 and unknown == 0 and covered > 0:
        coverage_status = "covered"
    elif not_covered > 0 and covered == 0 and unknown == 0:
        coverage_status = "not_covered"
    return {
        "status": "resolved" if processed > 0 else "unavailable",
        "operation": "reconcile",
        "county": county,
        "coverage_status": coverage_status,
        "processed_region_count": processed,
        "covered_region_count": covered,
        "not_covered_region_count": not_covered,
        "unknown_region_count": unknown,
        "persistence_status": _persistence_status(persistence_status),
        "message": "Market coverage metadata reconciled." if processed > 0 else "Market coverage metadata is temporarily unavailable.",
    }


def _safe_coverage_reconcile_result(raw: dict[str, Any], fallback_county: str) -> dict[str, Any]:
    processed = _int_value(raw.get("processed_region_count"))
    covered = _int_value(raw.get("covered_region_count"))
    not_covered = _int_value(raw.get("not_covered_region_count"))
    unknown = _int_value(raw.get("unknown_region_count"))
    coverage_status = _direct_coverage_status(raw.get("coverage_status"))
    return {
        "status": "resolved" if processed > 0 else "unavailable",
        "operation": "reconcile",
        "county": _optional_text(raw.get("county")) or fallback_county,
        "coverage_status": coverage_status,
        "processed_region_count": processed,
        "covered_region_count": covered,
        "not_covered_region_count": not_covered,
        "unknown_region_count": unknown,
        "persistence_status": _persistence_status(raw.get("persistence_status")),
        "message": "Market coverage metadata reconciled." if processed > 0 else "Market coverage metadata is temporarily unavailable.",
    }


def _coverage_reconcile_degraded(county: str) -> dict[str, Any]:
    normalized = normalize_market_region(county)
    if not normalized.valid:
        return _coverage_reconcile_unavailable(county, "coverage_reconcile_request_invalid")
    try:
        rows = [
            {"coverage_status": "coverage_unknown", "valid_market_candidate_count": 0}
            for region in iter_taiwan_regions()
            if region.county == normalized.county
        ]
    except Exception:
        return _coverage_reconcile_unavailable(county, "coverage_reconcile_unknown_safe_failure")
    return _coverage_reconcile_response(normalized.county, rows, persistence_status="degraded")


def _coverage_reconcile_unavailable(
    county: str,
    reason_code: str = "coverage_reconcile_unknown_safe_failure",
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "operation": "reconcile",
        "county": county,
        "coverage_status": "coverage_unknown",
        "processed_region_count": 0,
        "covered_region_count": 0,
        "not_covered_region_count": 0,
        "unknown_region_count": 0,
        "persistence_status": "unavailable",
        "message": "Market coverage metadata is temporarily unavailable.",
        "reason_code": safe_market_coverage_reconcile_reason_code(reason_code),
    }


def _safe_region_labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for item in value:
        text = _optional_text(item)
        if text:
            labels.append(text)
    return labels


def _status_from_raw(
    raw: dict[str, Any],
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    if not raw:
        return _missing_status()
    refresh_status = _optional_text(raw.get("refresh_status"))
    latest_period = _optional_text(raw.get("latest_period"))
    earliest_period = _optional_text(raw.get("earliest_period"))
    aggregate_count = _int_value(raw.get("aggregate_region_count"))
    future_period_excluded = False
    if latest_period and not is_publishable_transaction_period(latest_period, as_of=as_of):
        future_period_excluded = True
        latest_period = None
        earliest_period = None
        aggregate_count = 0
    raw_data_status = raw.get("data_status")
    if raw_data_status is None:
        data_status = (
            "available"
            if refresh_status == "ready" and aggregate_count > 0 and latest_period
            else "unavailable"
        )
    else:
        data_status = _data_status(raw_data_status)
    coverage_status = _coverage_status(raw.get("coverage_status"))
    built_at = _date_time_text(raw.get("built_at"))
    read_model_status = "ready"
    if refresh_status != "ready":
        read_model_status = "unavailable"
    elif future_period_excluded:
        read_model_status = "unavailable"
    elif aggregate_count <= 0:
        read_model_status = "missing"
    elif not latest_period or data_status != "available":
        read_model_status = "unavailable"
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


def _summary_from_row(
    row: dict[str, Any],
    history_rows: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(row, dict) or not isinstance(history_rows, list):
        return _no_data_summary(
            _optional_text(row.get("county")) if isinstance(row, dict) else "",
            _optional_text(row.get("district")) if isinstance(row, dict) else "",
            {**status, "data_status": "no_data", "coverage_status": "covered"},
        )
    data_status = _data_status(row.get("data_status"))
    coverage_status = _direct_coverage_status(row.get("coverage_status") or status.get("coverage_status"))
    county = _optional_text(row.get("county")) or ""
    district = _optional_text(row.get("district")) or ""
    if not is_publishable_transaction_period(row.get("period"), as_of=as_of):
        return _unavailable_summary(
            county,
            district,
            {**status, "data_status": "unavailable", "coverage_status": "coverage_unknown"},
        )
    if coverage_status != "covered":
        return _unavailable_summary(county, district, {**status, "data_status": "unavailable", "coverage_status": coverage_status})
    if data_status != "available":
        if data_status == "no_data":
            return _no_data_summary(county, district, {**status, "data_status": "no_data"})
        return _unavailable_summary(county, district, {**status, "data_status": data_status})
    average_unit_price = _float_value(row.get("average_unit_price"))
    transaction_count = _int_value(row.get("transaction_count"))
    record_count = _int_value(row.get("record_count"))
    source_name = _optional_text(row.get("source_name"))
    if (
        average_unit_price is None
        or not math.isfinite(average_unit_price)
        or average_unit_price <= 0
        or transaction_count <= 0
        or record_count <= 0
        or not source_name
    ):
        return _no_data_summary(county, district, {**status, "data_status": "no_data"})
    history = [
        _history_item(item)
        for item in history_rows
        if not is_future_transaction_period(item.get("period"), as_of=as_of)
    ][:6]
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
        "source_name": source_name,
        "source_updated_at": _date_text(row.get("source_updated_at")) or status["source_updated_at"],
        "coverage_status": coverage_status,
        "data_status": "available",
        "caveat": _optional_text(row.get("caveat")) or status["caveat"],
        "disclaimer": _optional_text(row.get("caveat")) or status["caveat"],
        "aggregation_method": _optional_text(row.get("aggregation_method")) or PLVR_AGGREGATION_METHOD,
        "median_unit_price_ntd_sqm": _float_value(row.get("median_unit_price_ntd_sqm")),
        "mean_unit_price_ntd_sqm": _float_value(row.get("mean_unit_price_ntd_sqm")),
        "lower_quartile_unit_price_ntd_sqm": _float_value(row.get("lower_quartile_unit_price_ntd_sqm")),
        "upper_quartile_unit_price_ntd_sqm": _float_value(row.get("upper_quartile_unit_price_ntd_sqm")),
        "median_total_price_ntd": _float_value(row.get("median_total_price_ntd")),
        "median_area_sqm": _float_value(row.get("median_area_sqm")),
        "sample_status": _optional_text(row.get("sample_status")),
        "aggregation_version": _optional_text(row.get("aggregation_version")),
        "source_release_id": _optional_text(row.get("source_release_id")),
        "freshness_status": _optional_text(row.get("freshness_status")),
        "period_change": _float_value(row.get("period_change")),
        "year_over_year_change": _float_value(row.get("year_over_year_change")),
        "price_distribution": _safe_distribution(row.get("price_distribution")),
        "building_type_distribution": _safe_distribution(row.get("building_type_distribution")),
        "age_band_distribution": _safe_distribution(row.get("age_band_distribution")),
        "inclusion_count": _int_value(row.get("inclusion_count")),
        "exclusion_count": _int_value(row.get("exclusion_count")),
        "methodology": _optional_text(row.get("methodology")),
        "latest_imported_at": _date_time_text(row.get("latest_imported_at")),
        "history": history,
        "summary": "此為官方實價登錄行政區期別彙整資料，僅供市場背景參考。",
        "trend": [],
        "livability_score": None,
        "esg_lite_score": None,
        "poi_breakdown": {},
        "sdg11_note": "",
    }


def _safe_distribution(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    safe: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        label = _optional_text(item.get("label"))
        count = _int_value(item.get("count"))
        if label and count > 0:
            safe.append({"label": label[:160], "count": count})
    return safe


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
        "summary": MARKET_UNAVAILABLE_SUMMARY,
        "caveat": status.get("caveat") or MARKET_DATA_CAVEAT,
        "disclaimer": status.get("caveat") or MARKET_DATA_CAVEAT,
        "history": [],
        "record_count": None,
    }


def _no_data_summary(county: str, district: str, status: dict[str, Any]) -> dict[str, Any]:
    result = market_unavailable_response(county, district)
    return {
        **result,
        "data_status": "no_data",
        "coverage_status": status.get("coverage_status", "partial"),
        "source_name": status.get("source_name"),
        "source_updated_at": status.get("source_updated_at"),
        "caveat": status.get("caveat") or MARKET_DATA_CAVEAT,
        "disclaimer": status.get("caveat") or MARKET_DATA_CAVEAT,
        "summary": "目前此區域尚無足夠的官方 PLVR 市場資料可供查詢。",
        "summary": MARKET_NO_DATA_SUMMARY,
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


def _coverage_for_region(repo: MarketReadModelRepository, county: str, district: str) -> dict[str, Any]:
    raw = repo.coverage(county, district)
    coverage_status = _direct_coverage_status(raw.get("coverage_status"))
    return {
        "coverage_status": coverage_status,
        "source_updated_at": _date_text(raw.get("source_updated_at")),
        "valid_market_candidate_count": _int_value(raw.get("valid_market_candidate_count")),
    }


def _direct_query_status(
    data_status: str = "available",
    *,
    coverage_status: str = "covered",
    source_updated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "data_status": _data_status(data_status),
        "coverage_status": _direct_coverage_status(coverage_status),
        "source_name": PLVR_MARKET_SOURCE_NAME,
        "source_updated_at": source_updated_at,
        "caveat": PLVR_MARKET_CAVEAT,
    }


def _new_support_reference() -> str:
    """Return a request reference that contains no user or infrastructure data."""

    return uuid.uuid4().hex[:16]


def _with_query_diagnostics(
    result: dict[str, Any],
    support_reference: str,
    reason_code: str | None = None,
) -> dict[str, Any]:
    safe_result = dict(result)
    safe_result["support_reference"] = support_reference
    if reason_code:
        safe_result["reason_code"] = safe_market_query_reason_code(reason_code)
    return safe_result


def _query_unavailable(
    county: str,
    district: str,
    status: dict[str, Any],
    support_reference: str,
    reason_code: str,
) -> dict[str, Any]:
    _log_market_query_event(
        "query_unavailable",
        support_reference=support_reference,
        operation="query",
        county=county,
        district=district,
        reason_code=reason_code,
    )
    return _with_query_diagnostics(
        _unavailable_summary(county, district, status),
        support_reference,
        reason_code,
    )


def _log_market_query_event(
    event: str,
    *,
    support_reference: str,
    operation: str,
    county: str,
    district: str,
    reason_code: str | None = None,
    **details: Any,
) -> None:
    safe_events = {
        "query_started",
        "coverage_started",
        "coverage_resolved",
        "summary_started",
        "summary_resolved",
        "history_started",
        "history_resolved",
        "result_contract_checked",
        "query_unavailable",
    }
    safe_operations = {"query", "coverage", "summary", "history", "result_contract"}
    payload: dict[str, Any] = {
        "event": event if event in safe_events else "query_unavailable",
        "support_reference": support_reference[:32],
        "operation": operation if operation in safe_operations else "query",
        "reason_code": safe_market_query_reason_code(reason_code) if reason_code else None,
        "exception_class": None,
        "normalized_county": _optional_text(county),
        "normalized_district": _optional_text(district),
    }
    for key in ("coverage_status", "has_row", "history_count", "contract_valid"):
        if key in details:
            payload[key] = details[key]
    line = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if payload["event"] == "query_unavailable":
        logger.warning("market_query_event %s", line)
    else:
        logger.info("market_query_event %s", line)


def safe_market_query_reason_code(reason_code: Any) -> str:
    """Return an allowlisted public reason code for query failures."""

    text = str(reason_code or "").strip()
    return text if text in MARKET_QUERY_REASON_CODES else "market_unknown_safe_failure"


def safe_market_refresh_reason_code(reason_code: Any) -> str:
    """Return an allowlisted public reason code for refresh failures."""

    text = str(reason_code or "").strip()
    return text if text in MARKET_REFRESH_REASON_CODES else "unknown_safe_failure"


def safe_market_coverage_bootstrap_reason_code(reason_code: Any) -> str:
    """Return an allowlisted public reason code for bootstrap failures."""

    text = str(reason_code or "").strip()
    return text if text in COVERAGE_BOOTSTRAP_REASON_CODES else "coverage_bootstrap_unknown_safe_failure"


def safe_market_coverage_reconcile_reason_code(reason_code: Any) -> str:
    """Return an allowlisted public reason code for reconcile failures."""

    text = str(reason_code or "").strip()
    return text if text in COVERAGE_RECONCILE_REASON_CODES else "coverage_reconcile_unknown_safe_failure"


def _run_refresh_phase(reason_code: str, operation: Any) -> Any:
    try:
        return operation()
    except MarketReadModelRefreshFailure:
        raise
    except Exception as exc:
        raise MarketReadModelRefreshFailure(reason_code) from exc


def _run_bootstrap_phase(reason_code: str, operation: Any) -> Any:
    try:
        return operation()
    except MarketCoverageBootstrapFailure:
        raise
    except Exception as exc:
        raise MarketCoverageBootstrapFailure(reason_code) from exc


def _run_reconcile_phase(reason_code: str, operation: Any) -> Any:
    try:
        return operation()
    except MarketCoverageReconcileFailure:
        raise
    except Exception as exc:
        raise MarketCoverageReconcileFailure(reason_code) from exc


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


def _log_repository_failure(
    operation: str,
    exc: Exception,
    reason_code: str,
    support_reference: str | None = None,
    *,
    county: str = "",
    district: str = "",
    phase: str = "query",
) -> None:
    """Log only bounded categories; never include SQL, parameters, or raw errors."""

    safe_operation = operation if operation in {"coverage", "summary", "history", "result_contract"} else "unknown"
    root_exception = exc.__cause__ or exc
    safe_exception_class = type(root_exception).__name__[:80] or "Exception"
    payload = {
        "operation": safe_operation,
        "exception_class": safe_exception_class,
        "support_reference": _optional_text(support_reference),
        "reason_code": safe_market_query_reason_code(reason_code),
        "phase": phase if phase in {
            "connection",
            "cursor",
            "transaction_read_only",
            "statement_timeout",
            "coverage_sql",
            "summary_sql",
            "history_sql",
            "row_conversion",
            "result_contract",
        } else "query",
        "normalized_county": _optional_text(county),
        "normalized_district": _optional_text(district),
    }
    logger.exception(
        "market_repository_failure %s",
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
    )


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
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _data_status(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"available", "no_data", "unavailable", "incomplete", "invalid"} else "unavailable"


def _coverage_status(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"covered", "not_covered", "coverage_unknown", "nationwide", "partial", "unknown"} else "coverage_unknown"


def _direct_coverage_status(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"covered", "not_covered", "coverage_unknown"}:
        return text
    if text in {"nationwide", "partial"}:
        return "covered"
    return "coverage_unknown"


def _persistence_status(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"applied", "degraded", "unavailable"} else "applied"


MARKET_COVERAGE_METADATA_SCHEMA_SQL = """
create table if not exists market_region_coverage (
    county text not null,
    district text not null,
    coverage_status text not null,
    valid_market_candidate_count integer not null default 0,
    source_updated_at date,
    reconciled_at timestamptz not null,
    primary key (county, district)
);
create index if not exists idx_market_region_coverage_county on market_region_coverage (county);
create index if not exists idx_market_region_coverage_status on market_region_coverage (coverage_status);
"""

MARKET_COVERAGE_METADATA_UPSERT_SQL = """
insert into market_region_coverage (
  county, district, coverage_status, valid_market_candidate_count, source_updated_at, reconciled_at
)
values (%s, %s, %s, %s, %s, %s)
on conflict (county, district) do update set
  coverage_status = excluded.coverage_status,
  valid_market_candidate_count = excluded.valid_market_candidate_count,
  source_updated_at = excluded.source_updated_at,
  reconciled_at = excluded.reconciled_at
"""

MARKET_COVERAGE_METADATA_DISTRICT_SQL = """
select coverage_status, valid_market_candidate_count, source_updated_at
from market_region_coverage
where replace(trim(county), '臺', '台') = %s
  and trim(district) = %s
limit 1
"""

MARKET_COVERAGE_METADATA_COUNTY_SQL = """
select
  case
    when count(*) = 0 then null
    when count(*) filter (where coverage_status = 'coverage_unknown') > 0 then 'coverage_unknown'
    when count(*) filter (where coverage_status = 'covered') > 0 then 'covered'
    when count(*) filter (where coverage_status = 'not_covered') > 0 then 'not_covered'
    else 'coverage_unknown'
  end as coverage_status,
  coalesce(sum(valid_market_candidate_count), 0)::integer as valid_market_candidate_count,
  max(source_updated_at)::date as source_updated_at
from market_region_coverage
where replace(trim(county), '臺', '台') = %s
"""

MARKET_COVERAGE_METADATA_AUDIT_SQL = """
select county, district, coverage_status
from market_region_coverage
"""

MARKET_DIRECT_QUERY_INDEX_SCHEMA_SQL = """
create index if not exists idx_market_direct_query_county_period
    on real_price_transactions (city, transaction_period desc)
    where source = 'official_plvr_opendata'
      and unit_price_per_ping > 0
      and area_ping > 0;
create index if not exists idx_market_direct_query_county_district_period
    on real_price_transactions (city, district, transaction_period desc)
    where source = 'official_plvr_opendata'
      and unit_price_per_ping > 0
      and area_ping > 0;
"""


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
with eligible as (
  select min(period)::varchar(7) as earliest_period,
         max(period)::varchar(7) as latest_period,
         max(source_updated_at)::date as source_updated_at,
         count(distinct county)::integer as available_county_count,
         count(distinct (county, district))::integer as available_district_count,
         count(*)::integer as aggregate_region_count
  from market_district_period_aggregates
  where data_status = 'available'
    and (
      replace(regexp_replace(trim(county), '\\s+', '', 'g'), '臺', '台') || '|' ||
      replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台')
    ) = any(%s)
    and period <= %s
)
select metadata.read_model_version, metadata.refresh_status,
       case when eligible.aggregate_region_count > 0 then metadata.coverage_status else 'unknown' end as coverage_status,
       metadata.source_name, eligible.source_updated_at,
       eligible.earliest_period, eligible.latest_period,
       eligible.available_county_count, eligible.available_district_count,
       eligible.aggregate_region_count,
       case
         when metadata.refresh_status = 'ready'
          and eligible.aggregate_region_count > 0
          and eligible.latest_period is not null
         then 'available'
         else 'unavailable'
       end as data_status,
       metadata.built_at, metadata.caveat
from market_read_model_metadata metadata
cross join eligible
where metadata.read_model_version = 'v1'
limit 1
"""

READ_MODEL_CATALOG_SQL = """
select distinct county
from market_district_period_aggregates
where data_status = 'available'
  and (
    replace(regexp_replace(trim(county), '\\s+', '', 'g'), '臺', '台') || '|' ||
    replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台')
  ) = any(%s)
  and period <= %s
order by county
"""

READ_MODEL_REGIONS_SQL = """
select county, district, max(period) as latest_period
from market_district_period_aggregates
where data_status = 'available'
  and (
    replace(regexp_replace(trim(county), '\\s+', '', 'g'), '臺', '台') || '|' ||
    replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台')
  ) = any(%s)
  and period <= %s
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
  and period <= %s
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
  and period <= %s
limit 1
"""

READ_MODEL_HISTORY_SQL = """
select period, average_unit_price, transaction_count
from market_district_period_aggregates
where replace(trim(county), '臺', '台') = %s
  and trim(district) = %s
  and data_status = 'available'
  and period <= %s
order by period desc
limit %s
"""

_VALID_PLVR_BASE_WHERE = """
source = 'official_plvr_opendata'
and nullif(trim(city), '') is not null
and nullif(trim(district), '') is not null
and transaction_period ~ '^\\d{4}-(0[1-9]|1[0-2])$'
and unit_price_per_ping > 0
and unit_price_per_ping <= 500
and total_price > 0
and area_ping > 0
and (
  replace(regexp_replace(trim(city), '\\s+', '', 'g'), '臺', '台') || '|' ||
  replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台')
) = any(%s)
"""
_VALID_PLVR_WHERE = _VALID_PLVR_BASE_WHERE + "and transaction_period <= %s\n"
_VALID_PLVR_WHERE_FORMAT = _VALID_PLVR_WHERE.replace("{", "{{").replace("}", "}}")
_VALID_PLVR_BASE_WHERE_FORMAT = _VALID_PLVR_BASE_WHERE.replace("{", "{{").replace("}", "}}")

_DIRECT_SUMMARY_SELECT = f"""
select
  replace(trim(city), '臺', '台') as county,
  {{district_expression}} as district,
  transaction_period as period,
  round(avg(unit_price_per_ping)::numeric, 2) as average_unit_price,
  count(*)::integer as transaction_count,
  count(*)::integer as record_count,
  '{PLVR_MARKET_SOURCE_NAME}'::text as source_name,
  max(imported_at)::date as source_updated_at,
  'partial'::text as coverage_status,
  'available'::text as data_status,
  '{PLVR_AGGREGATION_METHOD}'::text as aggregation_method
from real_price_transactions
where {_VALID_PLVR_WHERE_FORMAT}
  and replace(trim(city), '臺', '台') = %s
  {{district_filter}}
  {{period_filter}}
group by replace(trim(city), '臺', '台'), {{district_group}}, transaction_period
order by transaction_period desc
limit 1
"""

DIRECT_SUMMARY_DISTRICT_LATEST_SQL = _DIRECT_SUMMARY_SELECT.format(
    district_expression="trim(district)",
    district_filter="and replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台') = %s",
    period_filter="",
    district_group="trim(district)",
)

DIRECT_SUMMARY_DISTRICT_FOR_PERIOD_SQL = _DIRECT_SUMMARY_SELECT.format(
    district_expression="trim(district)",
    district_filter="and replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台') = %s",
    period_filter="and transaction_period = %s",
    district_group="trim(district)",
)

DIRECT_SUMMARY_COUNTY_LATEST_SQL = _DIRECT_SUMMARY_SELECT.format(
    district_expression="''::text",
    district_filter="",
    period_filter="",
    district_group="''::text",
)

DIRECT_SUMMARY_COUNTY_FOR_PERIOD_SQL = _DIRECT_SUMMARY_SELECT.format(
    district_expression="''::text",
    district_filter="",
    period_filter="and transaction_period = %s",
    district_group="''::text",
)

_DIRECT_HISTORY_SELECT = """
select transaction_period as period,
       round(avg(unit_price_per_ping)::numeric, 2) as average_unit_price,
       count(*)::integer as transaction_count
from real_price_transactions
where {valid_where}
  and replace(trim(city), '臺', '台') = %s
  {district_filter}
group by transaction_period
order by transaction_period desc
limit %s
"""

DIRECT_HISTORY_DISTRICT_SQL = _DIRECT_HISTORY_SELECT.format(
    valid_where=_VALID_PLVR_WHERE,
    district_filter="and replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台') = %s",
)

DIRECT_HISTORY_COUNTY_SQL = _DIRECT_HISTORY_SELECT.format(
    valid_where=_VALID_PLVR_WHERE,
    district_filter="",
)

_DIRECT_COVERAGE_SELECT = """
select count(*) filter (where transaction_period <= %s)::integer as valid_market_candidate_count,
       count(*) filter (where transaction_period > %s)::integer as excluded_future_period_count,
       max(imported_at) filter (where transaction_period <= %s)::date as source_updated_at
from real_price_transactions
where {valid_where}
  and replace(trim(city), '臺', '台') = %s
  {district_filter}
"""

DIRECT_COVERAGE_DISTRICT_SQL = _DIRECT_COVERAGE_SELECT.format(
    valid_where=_VALID_PLVR_BASE_WHERE,
    district_filter="and replace(regexp_replace(trim(district), '\\s+', '', 'g'), '臺', '台') = %s",
)

DIRECT_COVERAGE_COUNTY_SQL = _DIRECT_COVERAGE_SELECT.format(
    valid_where=_VALID_PLVR_BASE_WHERE,
    district_filter="",
)

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
