"""PLVR Market aggregate bridge unit tests with fake repositories."""

from __future__ import annotations

from datetime import date
from typing import Any

from services.plvr_market_aggregate_service import (
    OFFICIAL_PLVR_SOURCE,
    PLVR_AGGREGATION_METHOD,
    get_market_status,
    get_market_summary,
    list_market_regions,
)


class FakeMarketRepository:
    def __init__(self, *, raise_error: bool = False, empty: bool = False) -> None:
        self.raise_error = raise_error
        self.empty = empty

    def status(self) -> dict[str, Any]:
        if self.raise_error:
            raise RuntimeError("raw database failure should not leak")
        if self.empty:
            return {"valid_market_aggregate_candidate_count": 0}
        return {
            "valid_market_aggregate_candidate_count": 3,
            "available_county_count": 1,
            "available_district_count": 2,
            "earliest_period": "2025-01",
            "latest_period": "2025-02",
            "latest_successful_import_at": date(2025, 3, 5),
            "city_scope": "Demo County",
        }

    def regions(self, county: str = "") -> list[dict[str, Any]]:
        if self.raise_error:
            raise RuntimeError("raw database failure should not leak")
        rows = [
            {"county": "Demo County", "district": "North", "latest_period": "2025-02"},
            {"county": "Demo County", "district": "South", "latest_period": "2025-01"},
        ]
        return [row for row in rows if not county or row["county"] == county]

    def summary(self, county: str, district: str, period: str | None = None) -> dict[str, Any] | None:
        if self.raise_error:
            raise RuntimeError("raw database failure should not leak")
        if county != "Demo County" or district != "North":
            return None
        return {
            "county": county,
            "district": district,
            "period": period or "2025-02",
            "average_unit_price": 72.5,
            "transaction_count": 3,
            "record_count": 3,
        }


def test_bridge_builds_available_aggregate_without_raw_fields() -> None:
    result = get_market_summary("Demo County", "North", repository=FakeMarketRepository())

    assert result["data_status"] == "available"
    assert result["source_name"]
    assert result["average_unit_price"] == 72.5
    assert result["transaction_count"] == 3
    assert result["aggregation_method"] == PLVR_AGGREGATION_METHOD
    assert "address_text" not in result
    assert "lat" not in result
    assert "lng" not in result
    assert "raw_error" not in result


def test_query_without_period_uses_latest_available_period() -> None:
    result = get_market_summary("Demo County", "North", repository=FakeMarketRepository())

    assert result["period"] == "2025-02"


def test_period_can_be_requested_explicitly() -> None:
    result = get_market_summary("Demo County", "North", period="2025-01", repository=FakeMarketRepository())

    assert result["period"] == "2025-01"


def test_regions_are_dynamic_and_filterable() -> None:
    result = list_market_regions("Demo County", repository=FakeMarketRepository())

    assert result["data_status"] == "available"
    assert result["available_district_count"] == 2
    assert [row["district"] for row in result["regions"]] == ["North", "South"]


def test_unavailable_and_errors_do_not_emit_metrics_or_raw_errors() -> None:
    result = get_market_summary("Demo County", "North", repository=FakeMarketRepository(raise_error=True))

    assert result["data_status"] == "unavailable"
    assert result["average_unit_price"] is None
    assert result["transaction_count"] is None
    assert "raw database failure" not in str(result)


def test_empty_repository_is_unavailable() -> None:
    status = get_market_status(FakeMarketRepository(empty=True))

    assert status["data_status"] == "unavailable"
    assert status["coverage_status"] == "unknown"


def test_only_official_plvr_source_is_market_candidate() -> None:
    assert OFFICIAL_PLVR_SOURCE == "official_plvr_opendata"
