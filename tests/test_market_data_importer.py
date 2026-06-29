"""Offline market data importer tests."""

from __future__ import annotations

from pathlib import Path

from scripts.import_market_data import build_market_aggregate


def test_importer_builds_traceable_aggregate_without_raw_rows(tmp_path: Path) -> None:
    source = tmp_path / "market.csv"
    source.write_text(
        "\n".join(
            [
                "county,district,period,unit_price_per_ping,unused_address",
                "Demo County,Demo District,2026Q1,80,Hidden Address",
                "Demo County,Demo District,2026Q1,100,Hidden Address",
            ]
        ),
        encoding="utf-8",
    )

    aggregate = build_market_aggregate(
        source,
        source_name="Reviewed local aggregate",
        source_updated_at="2026-01-01",
        coverage_status="partial",
    )

    assert aggregate["data_status"] == "available"
    assert aggregate["coverage_status"] == "partial"
    assert aggregate["regions"][0]["average_unit_price"] == 90
    assert aggregate["regions"][0]["transaction_count"] == 2
    serialized = str(aggregate)
    assert "Hidden Address" not in serialized
    assert "unused_address" not in serialized
    assert "token" not in serialized.lower()


def test_importer_requires_minimum_columns(tmp_path: Path) -> None:
    source = tmp_path / "market.csv"
    source.write_text("county,district,period\nDemo County,Demo District,2026Q1\n", encoding="utf-8")

    try:
        build_market_aggregate(
            source,
            source_name="Reviewed local aggregate",
            source_updated_at="2026-01-01",
            coverage_status="partial",
        )
    except ValueError as exc:
        assert "unit_price_per_ping" in str(exc)
    else:
        raise AssertionError("missing unit_price_per_ping should fail")
