"""Read-model Market Insight service tests with fake repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from services.plvr_market_aggregate_service import (
    MARKET_REFRESH_REASON_CODES,
    DIRECT_HISTORY_COUNTY_SQL,
    DIRECT_HISTORY_DISTRICT_SQL,
    DIRECT_SUMMARY_COUNTY_FOR_PERIOD_SQL,
    DIRECT_SUMMARY_COUNTY_LATEST_SQL,
    DIRECT_SUMMARY_DISTRICT_FOR_PERIOD_SQL,
    DIRECT_SUMMARY_DISTRICT_LATEST_SQL,
    MarketReadModelRefreshError,
    MarketReadModelRefreshFailure,
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
    safe_market_refresh_reason_code,
)


class FakeReadModelRepository:
    def __init__(self, *, empty: bool = False, raise_error: bool = False, invalid_summary: bool = False) -> None:
        self.empty = empty
        self.raise_error = raise_error
        self.invalid_summary = invalid_summary
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
        return [{"county": "Demo County"}]

    def regions(self, county: str) -> list[dict[str, Any]]:
        self.calls.append(f"regions:{county}")
        return [
            {"county": county, "district": "North", "latest_period": "2025-07"},
            {"county": county, "district": "South", "latest_period": "2025-06"},
        ]

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        self.calls.append(f"summary:{period or 'latest'}")
        if district == "Missing":
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


def test_direct_query_sql_uses_only_plvr_transaction_table() -> None:
    direct_query_sql = "\n".join(
        [
            DIRECT_SUMMARY_COUNTY_LATEST_SQL,
            DIRECT_SUMMARY_COUNTY_FOR_PERIOD_SQL,
            DIRECT_SUMMARY_DISTRICT_LATEST_SQL,
            DIRECT_SUMMARY_DISTRICT_FOR_PERIOD_SQL,
            DIRECT_HISTORY_COUNTY_SQL,
            DIRECT_HISTORY_DISTRICT_SQL,
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
    assert catalog["available_counties"] == ["Demo County"]
    assert catalog["available_county_count"] == 1
    assert "raw_payload" not in catalog
    assert "database_url" not in catalog


def test_regions_filter_by_county() -> None:
    repo = FakeReadModelRepository()

    result = list_market_regions("Demo County", repo)

    assert [row["district"] for row in result["regions"]] == ["North", "South"]
    assert "regions:Demo County" in repo.calls


def test_query_without_period_uses_latest_and_returns_history_without_interpolation() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("Demo County", "North", repository=repo)

    assert result["data_status"] == "available"
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
    assert "refresh" not in repo.calls


def test_county_only_query_uses_direct_aggregate_without_district() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("Demo County", repository=repo)

    assert result["data_status"] == "available"
    assert result["city"] == "Demo County"
    assert result["district"] == ""
    assert "summary:latest" in repo.calls
    assert "history:6" in repo.calls
    assert "status" not in repo.calls


def test_query_for_period_passes_requested_period() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("Demo County", "North", period="2025-02", repository=repo)

    assert result["period"] == "2025-02"
    assert "summary:2025-02" in repo.calls


def test_missing_and_invalid_summary_returns_no_metrics_or_history() -> None:
    missing = get_market_summary("Demo County", "Missing", repository=FakeReadModelRepository())
    invalid = get_market_summary("Demo County", "North", repository=FakeReadModelRepository(invalid_summary=True))

    for result in (missing, invalid):
        assert result["data_status"] == "no_data"
        assert result["average_unit_price"] is None
        assert result["transaction_count"] is None
        assert result["history"] == []
        assert "0" not in result["summary"]


def test_direct_query_source_exception_is_unavailable_not_no_data() -> None:
    repo = SummaryFailureRepository()

    result = get_market_summary("Demo County", "North", repository=repo)

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
    assert "Demo County" not in str(result)


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
