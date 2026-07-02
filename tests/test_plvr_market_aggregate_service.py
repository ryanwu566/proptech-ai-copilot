"""Read-model Market Insight service tests with fake repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from services.plvr_market_aggregate_service import (
    COVERAGE_RECONCILE_REASON_CODES,
    MARKET_REFRESH_REASON_CODES,
    DIRECT_HISTORY_COUNTY_SQL,
    DIRECT_HISTORY_DISTRICT_SQL,
    DIRECT_COVERAGE_COUNTY_SQL,
    DIRECT_COVERAGE_DISTRICT_SQL,
    DIRECT_SUMMARY_COUNTY_FOR_PERIOD_SQL,
    DIRECT_SUMMARY_COUNTY_LATEST_SQL,
    DIRECT_SUMMARY_DISTRICT_FOR_PERIOD_SQL,
    DIRECT_SUMMARY_DISTRICT_LATEST_SQL,
    MarketReadModelRefreshError,
    MarketReadModelRefreshFailure,
    MarketCoverageReconcileFailure,
    PostgresMarketReadModelRepository,
    READ_MODEL_CATALOG_SQL,
    READ_MODEL_HISTORY_SQL,
    READ_MODEL_NEXT_AGGREGATE_COUNT_SQL,
    READ_MODEL_REGIONS_SQL,
    READ_MODEL_SCHEMA_SQL,
    READ_MODEL_STATUS_SQL,
    READ_MODEL_SUMMARY_FOR_PERIOD_SQL,
    READ_MODEL_SUMMARY_LATEST_SQL,
    REFRESH_INSERT_AGGREGATES_SQL,
    REFRESH_INSERT_METADATA_SQL,
    REFRESH_TEMP_AGGREGATES_SQL,
    REFRESH_TEMP_METADATA_SQL,
    get_market_catalog,
    get_market_status,
    get_market_summary,
    list_market_regions,
    refresh_market_read_model,
    audit_market_coverage,
    bootstrap_market_coverage_metadata,
    reconcile_market_coverage,
    safe_market_coverage_bootstrap_reason_code,
    safe_market_coverage_reconcile_reason_code,
    safe_market_refresh_reason_code,
)


class FakeReadModelRepository:
    def __init__(
        self,
        *,
        empty: bool = False,
        raise_error: bool = False,
        invalid_summary: bool = False,
        coverage_status: str = "covered",
    ) -> None:
        self.empty = empty
        self.raise_error = raise_error
        self.invalid_summary = invalid_summary
        self.coverage_status = coverage_status
        self.calls: list[str] = []

    def status(self) -> dict[str, Any]:
        self.calls.append("status")
        if self.raise_error:
            raise RuntimeError("database details must not leak")
        if self.empty:
            return {}
        return {
            "refresh_status": "ready",
            "coverage_status": "partial",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "earliest_period": "2025-01",
            "latest_period": "2025-07",
            "available_county_count": 1,
            "available_district_count": 2,
            "aggregate_region_count": 7,
            "built_at": "2025-03-06T00:00:00+00:00",
            "caveat": "market caveat",
            "data_status": "available",
        }

    def catalog(self) -> list[dict[str, Any]]:
        self.calls.append("catalog")
        return [{"county": "臺北市"}]

    def regions(self, county: str) -> list[dict[str, Any]]:
        self.calls.append(f"regions:{county}")
        return [
            {"county": county, "district": "信義區", "latest_period": "2025-07"},
            {"county": county, "district": "大安區", "latest_period": "2025-06"},
        ]

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        self.calls.append(f"summary:{period or 'latest'}")
        if district == "萬華區":
            return None
        return {
            "county": county,
            "district": district,
            "period": period or "2025-07",
            "average_unit_price": None if self.invalid_summary else 72.5,
            "transaction_count": 0 if self.invalid_summary else 3,
            "record_count": 0 if self.invalid_summary else 3,
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "coverage_status": "partial",
            "data_status": "available",
            "aggregation_method": "avg_unit_price_per_ping_by_city_district_period",
        }

    def history(self, county: str, district: str, limit: int = 6) -> list[dict[str, Any]]:
        self.calls.append(f"history:{limit}")
        periods = ["2025-07", "2025-05", "2025-04", "2025-02", "2025-01", "2024-12", "2024-11"]
        return [
            {"period": period, "average_unit_price": 70 + index, "transaction_count": index + 1}
            for index, period in enumerate(periods[:limit])
        ]

    def coverage(self, county: str, district: str) -> dict[str, Any]:
        self.calls.append(f"coverage:{district or 'county'}")
        return {
            "coverage_status": self.coverage_status,
            "valid_market_candidate_count": 1 if self.coverage_status == "covered" else 0,
            "source_updated_at": "2025-03-05",
        }

    def refresh(self) -> dict[str, Any]:
        self.calls.append("refresh")
        return self.status()


class InitFailureRepository(FakeReadModelRepository):
    def refresh(self) -> dict[str, Any]:
        self.calls.append("refresh")
        raise MarketReadModelRefreshError("read_model_initialization_unavailable")


class RefreshFailureRepository(FakeReadModelRepository):
    def refresh(self) -> dict[str, Any]:
        self.calls.append("refresh")
        raise MarketReadModelRefreshError("read_model_refresh_unavailable")


class SummaryFailureRepository(FakeReadModelRepository):
    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        self.calls.append("summary:failure")
        raise RuntimeError("database table sql detail must not leak")

    def history(self, county: str, district: str, limit: int = 6) -> list[dict[str, Any]]:
        self.calls.append("history:unexpected")
        raise RuntimeError("history should not be called after summary failure")


class PhaseRefreshCursor:
    def __init__(self, *, failure: str | None = None, aggregate_count: int = 1) -> None:
        self.failure = failure
        self.aggregate_count = aggregate_count
        self.row: dict[str, Any] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, sql: str, _params: list[Any] | None = None) -> None:
        if sql == READ_MODEL_SCHEMA_SQL and self.failure == "schema":
            raise RuntimeError("schema detail must not leak")
        if sql == REFRESH_TEMP_AGGREGATES_SQL and self.failure == "source":
            raise RuntimeError("source detail must not leak")
        if sql == READ_MODEL_NEXT_AGGREGATE_COUNT_SQL:
            self.row = {"aggregate_count": self.aggregate_count}
            return
        if sql == REFRESH_TEMP_METADATA_SQL and self.failure == "metadata":
            raise RuntimeError("metadata detail must not leak")
        if sql in {"delete from market_district_period_aggregates", REFRESH_INSERT_AGGREGATES_SQL} and self.failure == "write":
            raise RuntimeError("write detail must not leak")
        if sql in {"delete from market_read_model_metadata", REFRESH_INSERT_METADATA_SQL} and self.failure == "metadata_write":
            raise RuntimeError("metadata write detail must not leak")
        if sql == READ_MODEL_STATUS_SQL:
            if self.failure == "finalization":
                raise RuntimeError("finalization detail must not leak")
            self.row = FakeReadModelRepository().status()

    def fetchone(self) -> dict[str, Any] | None:
        return self.row


class PhaseRefreshConnection:
    def __init__(self, *, failure: str | None = None, aggregate_count: int = 1) -> None:
        self.failure = failure
        self.aggregate_count = aggregate_count

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> PhaseRefreshCursor:
        return PhaseRefreshCursor(failure=self.failure, aggregate_count=self.aggregate_count)

    def commit(self) -> None:
        if self.failure == "commit":
            raise RuntimeError("commit detail must not leak")


class PhaseRefreshRepository(PostgresMarketReadModelRepository):
    def __init__(self, *, failure: str | None = None, aggregate_count: int = 1) -> None:
        super().__init__("unused")
        object.__setattr__(self, "failure", failure)
        object.__setattr__(self, "aggregate_count", aggregate_count)

    def _connect(self):
        if self.failure == "connect":
            raise RuntimeError("connection detail must not leak")
        return PhaseRefreshConnection(failure=self.failure, aggregate_count=self.aggregate_count)


class CoverageOperationsRepository:
    def __init__(self, *, fail: str | None = None) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def bootstrap_coverage_metadata(self) -> dict[str, Any]:
        self.calls.append("bootstrap")
        if self.fail == "bootstrap":
            raise RuntimeError("schema detail must not leak")
        return {"migration_status": "applied_or_already_present"}

    def reconcile_coverage(self, county: str) -> dict[str, Any]:
        self.calls.append(f"reconcile:{county}")
        if self.fail == "reconcile":
            raise RuntimeError("raw database detail must not leak")
        if self.fail == "metadata":
            raise MarketCoverageReconcileFailure("coverage_reconcile_metadata_unavailable")
        return {
            "status": "resolved",
            "operation": "reconcile",
            "county": county,
            "coverage_status": "covered",
            "processed_region_count": 2,
            "covered_region_count": 2,
            "not_covered_region_count": 0,
            "unknown_region_count": 0,
            "message": "internal message must be replaced",
        }

    def audit_coverage(self) -> dict[str, Any]:
        self.calls.append("audit")
        if self.fail == "audit":
            raise RuntimeError("raw database detail must not leak")
        return {
            "status": "FULL",
            "expected_region_count": 2,
            "covered_region_count": 2,
            "missing_region_count": 0,
            "unknown_region_count": 0,
            "missing_regions": [],
            "unknown_regions": [],
        }


class CoverageConnectionFailureRepository:
    def reconcile_coverage(self, county: str) -> dict[str, Any]:
        raise RuntimeError("connection detail must not leak")


def test_direct_query_sql_uses_only_plvr_transaction_table() -> None:
    direct_query_sql = "\n".join(
        [
            DIRECT_SUMMARY_COUNTY_LATEST_SQL,
            DIRECT_SUMMARY_COUNTY_FOR_PERIOD_SQL,
            DIRECT_SUMMARY_DISTRICT_LATEST_SQL,
            DIRECT_SUMMARY_DISTRICT_FOR_PERIOD_SQL,
            DIRECT_HISTORY_COUNTY_SQL,
            DIRECT_HISTORY_DISTRICT_SQL,
            DIRECT_COVERAGE_COUNTY_SQL,
            DIRECT_COVERAGE_DISTRICT_SQL,
        ]
    )
    read_model_sql = "\n".join(
        [
            READ_MODEL_STATUS_SQL,
            READ_MODEL_CATALOG_SQL,
            READ_MODEL_REGIONS_SQL,
            READ_MODEL_SUMMARY_LATEST_SQL,
            READ_MODEL_SUMMARY_FOR_PERIOD_SQL,
            READ_MODEL_HISTORY_SQL,
        ]
    )

    assert "real_price_transactions" in direct_query_sql
    assert "market_district_period_aggregates" not in direct_query_sql
    assert "market_read_model_metadata" not in direct_query_sql
    assert "market_district_period_aggregates" in read_model_sql
    assert "market_read_model_metadata" in read_model_sql
    assert "real_price_transactions" in REFRESH_TEMP_AGGREGATES_SQL


def test_status_and_catalog_return_safe_read_model_metadata() -> None:
    repo = FakeReadModelRepository()

    status = get_market_status(repo)
    catalog = get_market_catalog(repo)

    assert status["read_model_status"] == "ready"
    assert catalog["available_counties"] == ["臺北市"]
    assert catalog["available_county_count"] == 1
    assert "raw_payload" not in catalog
    assert "database_url" not in catalog


def test_regions_filter_by_county() -> None:
    repo = FakeReadModelRepository()

    result = list_market_regions("臺北市", repo)

    assert [row["district"] for row in result["regions"]] == ["信義區", "大安區"]
    assert "regions:臺北市" in repo.calls


def test_query_without_period_uses_latest_and_returns_history_without_interpolation() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("臺北市", "信義區", repository=repo)

    assert result["data_status"] == "available"
    assert result["coverage_status"] == "covered"
    assert result["period"] == "2025-07"
    assert result["average_unit_price"] == 72.5
    assert len(result["history"]) == 6
    assert [row["period"] for row in result["history"]] == [
        "2025-07",
        "2025-05",
        "2025-04",
        "2025-02",
        "2025-01",
        "2024-12",
    ]
    assert "status" not in repo.calls
    assert "coverage:信義區" in repo.calls
    assert "refresh" not in repo.calls


def test_county_only_query_uses_direct_aggregate_without_district() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("臺北市", repository=repo)

    assert result["data_status"] == "available"
    assert result["city"] == "臺北市"
    assert result["district"] == ""
    assert "summary:latest" in repo.calls
    assert "history:6" in repo.calls
    assert "status" not in repo.calls


def test_query_for_period_passes_requested_period() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("臺北市", "信義區", period="2025-02", repository=repo)

    assert result["period"] == "2025-02"
    assert "summary:2025-02" in repo.calls


def test_missing_and_invalid_summary_returns_no_metrics_or_history() -> None:
    missing = get_market_summary("臺北市", "萬華區", repository=FakeReadModelRepository())
    invalid = get_market_summary("臺北市", "信義區", repository=FakeReadModelRepository(invalid_summary=True))

    for result in (missing, invalid):
        assert result["data_status"] == "no_data"
        assert result["coverage_status"] == "covered"
        assert result["average_unit_price"] is None
        assert result["transaction_count"] is None
        assert result["history"] == []
        assert "0" not in result["summary"]


def test_direct_query_source_exception_is_unavailable_not_no_data() -> None:
    repo = SummaryFailureRepository()

    result = get_market_summary("臺北市", "信義區", repository=repo)

    assert result["data_status"] == "unavailable"
    assert result["data_status"] != "no_data"
    assert result["average_unit_price"] is None
    assert result["transaction_count"] is None
    assert result["history"] == []
    assert "database table sql detail" not in str(result)
    assert "summary:failure" in repo.calls
    assert "history:unexpected" not in repo.calls
    assert "status" not in repo.calls
    assert "refresh" not in repo.calls


def test_unknown_coverage_is_unavailable_without_source_query() -> None:
    repo = FakeReadModelRepository(coverage_status="coverage_unknown")

    result = get_market_summary("臺北市", "信義區", repository=repo)

    assert result["data_status"] == "unavailable"
    assert result["coverage_status"] == "coverage_unknown"
    assert "coverage:信義區" in repo.calls
    assert "summary:latest" not in repo.calls
    assert "history:6" not in repo.calls


def test_not_covered_region_is_unavailable_not_no_data() -> None:
    repo = FakeReadModelRepository(coverage_status="not_covered")

    result = get_market_summary("臺北市", "信義區", repository=repo)

    assert result["data_status"] == "unavailable"
    assert result["coverage_status"] == "not_covered"
    assert result["data_status"] != "no_data"


def test_empty_repository_is_missing_not_nationwide() -> None:
    status = get_market_status(FakeReadModelRepository(empty=True))

    assert status["read_model_status"] == "missing"
    assert status["coverage_status"] == "unknown"


def test_refresh_returns_safe_response_without_counts_or_raw_details() -> None:
    result = refresh_market_read_model(FakeReadModelRepository())

    assert result["status"] == "resolved"
    assert result["data_status"] == "available"
    assert "available_county_count" not in result
    assert "database details" not in str(result)
    assert "real_price_transactions" not in str(result)


def test_refresh_failure_is_safely_unavailable() -> None:
    result = refresh_market_read_model(FakeReadModelRepository(raise_error=True))

    assert result["status"] == "unavailable"
    assert result["built_at"] is None
    assert result["reason_code"] == "read_model_refresh_unavailable"
    assert "database details" not in str(result)


def test_refresh_without_repository_reports_database_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)

    result = refresh_market_read_model(repository=None)

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "valuation_database_unavailable"


def test_refresh_initialization_failure_has_safe_reason() -> None:
    result = refresh_market_read_model(InitFailureRepository())

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "read_model_initialization_unavailable"
    assert "database details" not in str(result)


def test_refresh_service_failure_has_safe_reason() -> None:
    result = refresh_market_read_model(RefreshFailureRepository())

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "read_model_refresh_unavailable"
    assert "database details" not in str(result)


def test_postgres_refresh_phase_failures_have_safe_reason_codes() -> None:
    cases = {
        "connect": "valuation_database_unavailable",
        "schema": "read_model_initialization_unavailable",
        "source": "read_model_source_aggregate_unavailable",
        "metadata": "read_model_metadata_unavailable",
        "write": "read_model_write_unavailable",
        "metadata_write": "read_model_metadata_unavailable",
        "commit": "read_model_write_unavailable",
        "finalization": "read_model_refresh_unavailable",
    }

    for failure, reason in cases.items():
        result = refresh_market_read_model(PhaseRefreshRepository(failure=failure))
        assert result["status"] == "unavailable"
        assert result["reason_code"] == reason
        assert "detail must not leak" not in str(result)


def test_postgres_refresh_no_eligible_source_records_is_explicit() -> None:
    result = refresh_market_read_model(PhaseRefreshRepository(aggregate_count=0))

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "read_model_no_eligible_source_records"
    assert "臺北市" not in str(result)


def test_refresh_reason_code_allowlist_normalizes_unknown_values() -> None:
    assert safe_market_refresh_reason_code("valuation_database_unavailable") == "valuation_database_unavailable"
    assert safe_market_refresh_reason_code("read_model_source_aggregate_unavailable") == "read_model_source_aggregate_unavailable"
    assert safe_market_refresh_reason_code("read_model_write_unavailable") == "read_model_write_unavailable"
    assert safe_market_refresh_reason_code("read_model_metadata_unavailable") == "read_model_metadata_unavailable"
    assert safe_market_refresh_reason_code("read_model_no_eligible_source_records") == "read_model_no_eligible_source_records"
    assert safe_market_refresh_reason_code("raw_exception") == "unknown_safe_failure"
    assert "unknown_safe_failure" in MARKET_REFRESH_REASON_CODES


def test_typed_refresh_failure_is_not_downgraded_to_generic_refresh_failure() -> None:
    class TypedFailureRepository(FakeReadModelRepository):
        def refresh(self) -> dict[str, Any]:
            raise MarketReadModelRefreshFailure("read_model_source_aggregate_unavailable")

    result = refresh_market_read_model(TypedFailureRepository())

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "read_model_source_aggregate_unavailable"
    assert result["reason_code"] != "read_model_refresh_unavailable"


def test_datetime_status_is_serialized_safely() -> None:
    class DatetimeRepository(FakeReadModelRepository):
        def status(self) -> dict[str, Any]:
            raw = super().status()
            raw["built_at"] = datetime(2025, 3, 6, 1, 2, 3)
            return raw

    status = get_market_status(DatetimeRepository())

    assert status["built_at"].startswith("2025-03-06")


def test_coverage_bootstrap_returns_safe_status_without_raw_details() -> None:
    repo = CoverageOperationsRepository()

    result = bootstrap_market_coverage_metadata(repo)

    assert result == {
        "status": "resolved",
        "operation": "bootstrap",
        "migration_status": "applied_or_already_present",
        "message": "Market coverage metadata is ready.",
    }
    assert repo.calls == ["bootstrap"]


def test_coverage_reconcile_preserves_safe_counts_and_status() -> None:
    repo = CoverageOperationsRepository()

    result = reconcile_market_coverage("Demo County", repo)

    assert result["status"] == "resolved"
    assert result["operation"] == "reconcile"
    assert result["county"] == "Demo County"
    assert result["coverage_status"] == "covered"
    assert result["processed_region_count"] == 2
    assert result["covered_region_count"] == 2
    assert result["not_covered_region_count"] == 0
    assert result["unknown_region_count"] == 0
    assert result["persistence_status"] == "applied"
    assert "internal message" not in str(result)


def test_coverage_reconcile_zero_record_regions_are_safe_not_failures() -> None:
    class ZeroRecordCoveredRepository:
        def reconcile_coverage(self, county: str) -> dict[str, Any]:
            return {
                "county": county,
                "regions": [{"coverage_status": "covered", "valid_market_candidate_count": 0}],
            }

    covered_result = reconcile_market_coverage("Demo County", ZeroRecordCoveredRepository())
    assert covered_result["status"] == "resolved"
    assert covered_result["coverage_status"] == "covered"
    assert covered_result["covered_region_count"] == 1
    assert covered_result["not_covered_region_count"] == 0

    class ZeroRecordCoverageRepository:
        def reconcile_coverage(self, county: str) -> dict[str, Any]:
            return {
                "county": county,
                "regions": [
                    {"coverage_status": "not_covered", "valid_market_candidate_count": 0},
                    {"coverage_status": "coverage_unknown", "valid_market_candidate_count": 0},
                ],
            }

    result = reconcile_market_coverage("Demo County", ZeroRecordCoverageRepository())

    assert result["status"] == "resolved"
    assert result["processed_region_count"] == 2
    assert result["not_covered_region_count"] == 1
    assert result["unknown_region_count"] == 1
    assert result["persistence_status"] == "applied"
    assert "reason_code" not in result


def test_coverage_operations_fail_safely_without_raw_details() -> None:
    bootstrap = bootstrap_market_coverage_metadata(CoverageOperationsRepository(fail="bootstrap"))
    assert bootstrap["status"] == "unavailable"
    assert bootstrap["reason_code"] == "coverage_bootstrap_unknown_safe_failure"
    assert "schema detail" not in str(bootstrap)

    reconcile = reconcile_market_coverage("臺北市", CoverageOperationsRepository(fail="reconcile"))
    assert reconcile["status"] == "resolved"
    assert reconcile["coverage_status"] == "coverage_unknown"
    assert reconcile["persistence_status"] == "degraded"
    assert reconcile["processed_region_count"] > 0
    assert "reason_code" not in reconcile
    assert "raw database detail" not in str(reconcile)

    audit = audit_market_coverage(CoverageOperationsRepository(fail="audit"))
    assert audit["status"] == "UNKNOWN"
    assert audit["covered_region_count"] == 0
    assert "raw database detail" not in str(audit)


def test_coverage_reconcile_failure_reasons_are_safe_and_specific() -> None:
    missing_repo = reconcile_market_coverage("Demo County", repository=object())
    invalid_request = reconcile_market_coverage("   ", CoverageOperationsRepository())
    metadata_failure = reconcile_market_coverage("臺北市", CoverageOperationsRepository(fail="metadata"))

    assert missing_repo["reason_code"] == "coverage_reconcile_route_unavailable"
    assert invalid_request["reason_code"] == "coverage_reconcile_request_invalid"
    assert metadata_failure["status"] == "resolved"
    assert metadata_failure["coverage_status"] == "coverage_unknown"
    assert metadata_failure["persistence_status"] == "degraded"
    assert "reason_code" not in metadata_failure
    assert "raw database detail" not in str(metadata_failure)


def test_coverage_reconcile_degraded_fallback_uses_canonical_registry() -> None:
    result = reconcile_market_coverage("臺北市", CoverageConnectionFailureRepository())

    assert result["status"] == "resolved"
    assert result["county"] == "臺北市"
    assert result["coverage_status"] == "coverage_unknown"
    assert result["persistence_status"] == "degraded"
    assert result["processed_region_count"] == 12
    assert result["unknown_region_count"] == 12
    assert "reason_code" not in result
    assert "connection detail" not in str(result)


def test_coverage_audit_returns_only_canonical_aggregate_counts() -> None:
    result = audit_market_coverage(CoverageOperationsRepository())

    assert result["status"] == "FULL"
    assert result["expected_region_count"] == 2
    assert result["covered_region_count"] == 2
    assert "database_url" not in str(result)
    assert "real_price_transactions" not in str(result)


def test_coverage_bootstrap_reason_code_allowlist_normalizes_unknown_values() -> None:
    assert (
        safe_market_coverage_bootstrap_reason_code("coverage_bootstrap_migration_unavailable")
        == "coverage_bootstrap_migration_unavailable"
    )
    assert (
        safe_market_coverage_bootstrap_reason_code("coverage_bootstrap_runtime_unavailable")
        == "coverage_bootstrap_runtime_unavailable"
    )
    assert safe_market_coverage_bootstrap_reason_code("raw_exception") == "coverage_bootstrap_unknown_safe_failure"


def test_coverage_reconcile_reason_code_allowlist_normalizes_unknown_values() -> None:
    assert (
        safe_market_coverage_reconcile_reason_code("coverage_reconcile_metadata_unavailable")
        == "coverage_reconcile_metadata_unavailable"
    )
    assert (
        safe_market_coverage_reconcile_reason_code("coverage_reconcile_runtime_unavailable")
        == "coverage_reconcile_runtime_unavailable"
    )
    assert safe_market_coverage_reconcile_reason_code("raw_exception") == "coverage_reconcile_unknown_safe_failure"
    assert "coverage_reconcile_request_invalid" in COVERAGE_RECONCILE_REASON_CODES
