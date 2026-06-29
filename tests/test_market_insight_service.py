"""Market data foundation service tests."""

from __future__ import annotations

import json
from pathlib import Path

from services.market_data_foundation import (
    build_market_region_record,
    get_market_summary,
    list_market_regions,
    market_unavailable_response,
)


def test_missing_aggregate_returns_unavailable(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    catalog = list_market_regions(missing)
    result = get_market_summary("Demo County", "Demo District", missing)

    assert catalog["data_status"] == "unavailable"
    assert catalog["regions"] == []
    assert result["data_status"] == "unavailable"
    assert result["avg_price_per_ping"] is None
    assert result["transaction_volume"] is None
    assert result["trend"] == []


def test_available_aggregate_uses_traceable_contract(tmp_path: Path) -> None:
    aggregate = tmp_path / "aggregate.json"
    aggregate.write_text(
        json.dumps(
            {
                "source_name": "Reviewed local aggregate",
                "source_updated_at": "2026-01-01",
                "coverage_status": "partial",
                "data_status": "available",
                "source_file_hash": "abc123",
                "aggregation_method": "mean_unit_price_per_ping_by_county_district_period",
                "record_count": 2,
                "regions": [
                    {
                        "county": "Demo County",
                        "district": "Demo District",
                        "period": "2026Q1",
                        "average_unit_price": 88.5,
                        "transaction_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    catalog = list_market_regions(aggregate)
    result = get_market_summary("Demo County", "Demo District", aggregate)

    assert catalog["data_status"] == "available"
    assert catalog["regions"] == [
        {
            "city": "Demo County",
            "county": "Demo County",
            "district": "Demo District",
            "period": "2026Q1",
            "data_status": "available",
        }
    ]
    assert result["data_status"] == "available"
    assert result["avg_price_per_ping"] == 88.5
    assert result["transaction_volume"] == 2
    assert result["source_name"] == "Reviewed local aggregate"
    assert result["source_updated_at"] == "2026-01-01"
    assert result["source_file_hash"] == "abc123"


def test_non_available_record_does_not_emit_fake_metrics() -> None:
    result = build_market_region_record(
        {
            "county": "Demo County",
            "district": "Demo District",
            "period": "2026Q1",
            "data_status": "incomplete",
        },
        {
            "source_name": "Reviewed local aggregate",
            "source_updated_at": "2026-01-01",
            "coverage_status": "unknown",
        },
    )

    assert result["data_status"] == "incomplete"
    assert result["avg_price_per_ping"] is None
    assert result["transaction_volume"] is None
    assert result["livability_score"] is None
    assert result["esg_lite_score"] is None


def test_unavailable_response_contains_no_raw_or_secret_fields() -> None:
    result = market_unavailable_response("Demo County", "Demo District")

    forbidden = {"raw_payload", "token", "api_key", "secret", "provider_url", "database_url"}
    assert forbidden.isdisjoint(result)
    assert result["data_status"] == "unavailable"
