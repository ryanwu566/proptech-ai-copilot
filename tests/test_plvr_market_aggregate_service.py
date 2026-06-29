"""Read-model Market Insight service tests with fake repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from services.plvr_market_aggregate_service import (
    READ_MODEL_CATALOG_SQL,
    READ_MODEL_HISTORY_SQL,
    READ_MODEL_REGIONS_SQL,
    READ_MODEL_STATUS_SQL,
    READ_MODEL_SUMMARY_FOR_PERIOD_SQL,
    READ_MODEL_SUMMARY_LATEST_SQL,
    REFRESH_TEMP_AGGREGATES_SQL,
    get_market_catalog,
    get_market_status,
    get_market_summary,
    list_market_regions,
    refresh_market_read_model,
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


def test_read_only_sql_uses_read_model_tables_only() -> None:
    read_sql = "\n".join(
        [
            READ_MODEL_STATUS_SQL,
            READ_MODEL_CATALOG_SQL,
            READ_MODEL_REGIONS_SQL,
            READ_MODEL_SUMMARY_LATEST_SQL,
            READ_MODEL_SUMMARY_FOR_PERIOD_SQL,
            READ_MODEL_HISTORY_SQL,
        ]
    )

    assert "market_district_period_aggregates" in read_sql
    assert "market_read_model_metadata" in read_sql
    assert "real_price_transactions" not in read_sql
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
    result = get_market_summary("Demo County", "North", repository=FakeReadModelRepository())

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


def test_query_for_period_passes_requested_period() -> None:
    repo = FakeReadModelRepository()

    result = get_market_summary("Demo County", "North", period="2025-02", repository=repo)

    assert result["period"] == "2025-02"
    assert "summary:2025-02" in repo.calls


def test_missing_and_invalid_summary_returns_no_metrics_or_history() -> None:
    missing = get_market_summary("Demo County", "Missing", repository=FakeReadModelRepository())
    invalid = get_market_summary("Demo County", "North", repository=FakeReadModelRepository(invalid_summary=True))

    for result in (missing, invalid):
        assert result["data_status"] in {"unavailable", "invalid"}
        assert result["average_unit_price"] is None
        assert result["transaction_count"] is None
        assert result["history"] == []


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
    assert "database details" not in str(result)


def test_datetime_status_is_serialized_safely() -> None:
    class DatetimeRepository(FakeReadModelRepository):
        def status(self) -> dict[str, Any]:
            raw = super().status()
            raw["built_at"] = datetime(2025, 3, 6, 1, 2, 3)
            return raw

    status = get_market_status(DatetimeRepository())

    assert status["built_at"].startswith("2025-03-06")
