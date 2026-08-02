"""Disposable PostgreSQL proof for the production direct Market Insight SQL."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.plvr_market_aggregate_service import PostgresMarketReadModelRepository, get_market_summary


pytestmark = pytest.mark.skipif(
    os.getenv("MARKET_DIRECT_QUERY_POSTGRES") != "1",
    reason="disposable PostgreSQL service is not enabled",
)

COUNTY = "臺北市"
DISTRICT = "中正區"


def _database_url() -> str:
    host = os.getenv("MARKET_DIRECT_QUERY_POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("MARKET_DIRECT_QUERY_POSTGRES_PORT", "5432")
    return f"postgresql://postgres@{host}:{port}/market_e2e"


def _apply_sql_file(cursor, path: Path) -> None:
    cursor.execute(path.read_text(encoding="utf-8"))


def _execute_fixture_insert(cursor, sql: str, values: tuple[object, ...]) -> None:
    expected_arity = sql.count("%s")
    if len(values) != expected_arity:
        raise AssertionError(f"synthetic transaction fixture arity mismatch: expected {expected_arity}")
    cursor.execute(sql, values)


def test_production_direct_query_sql_against_disposable_postgres(monkeypatch) -> None:
    import psycopg

    root = Path(__file__).resolve().parents[1]
    database_url = _database_url()
    with psycopg.connect(database_url, prepare_threshold=None) as connection:
        with connection.cursor() as cursor:
            _apply_sql_file(cursor, root / "database" / "valuation_schema.sql")
            _apply_sql_file(cursor, root / "database" / "migrations" / "001_add_dedupe_key_to_real_price_transactions.sql")
            _apply_sql_file(cursor, root / "database" / "migrations" / "002_add_market_direct_query_indexes.sql")
            _apply_sql_file(cursor, root / "database" / "migrations" / "003_add_market_region_coverage.sql")
            cursor.execute("delete from market_region_coverage")
            cursor.execute("delete from real_price_transactions")
            _execute_fixture_insert(
                cursor,
                """
                insert into real_price_transactions (
                    transaction_period, city, district, road, address_text, building_type,
                    area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
                    total_price, lat, lng, source, raw_note, dedupe_key, imported_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "2025-01", COUNTY, DISTRICT, "合成道路", "", "合成建物",
                    30, 0, 3, 12, 80, 2400, None, None, "official_plvr_opendata", "",
                    "synthetic-direct-query-1", datetime(2025, 2, 1, tzinfo=timezone.utc),
                ),
            )
            _execute_fixture_insert(
                cursor,
                """
                insert into real_price_transactions (
                    transaction_period, city, district, road, address_text, building_type,
                    area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
                    total_price, lat, lng, source, raw_note, dedupe_key, imported_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "2025-02", COUNTY, DISTRICT, "合成道路", "", "合成建物",
                    32, 0, 4, 12, 90, 2880, None, None, "official_plvr_opendata", "",
                    "synthetic-direct-query-2", datetime(2025, 3, 1, tzinfo=timezone.utc),
                ),
            )
            cursor.execute(
                """
                insert into market_region_coverage (
                    county, district, coverage_status, valid_market_candidate_count,
                    source_updated_at, reconciled_at
                ) values (%s, %s, %s, %s, %s, %s)
                """,
                ("台北市", DISTRICT, "covered", 2, "2025-03-01", datetime.now(timezone.utc)),
            )
        connection.commit()

        repository = PostgresMarketReadModelRepository(database_url)
        coverage = repository.coverage(COUNTY, DISTRICT)
        summary = repository.summary(COUNTY, DISTRICT)
        history = repository.history(COUNTY, DISTRICT)
        result = get_market_summary(COUNTY, DISTRICT, repository=repository)

        from backend.api_main import app
        from services import market_insight_service
        from fastapi.testclient import TestClient

        monkeypatch.setattr(
            market_insight_service,
            "get_market_summary",
            lambda city, district="", period=None: get_market_summary(
                city, district, period, repository=repository
            ),
        )
        with TestClient(app) as client:
            api_response = client.post(
                "/market-insights/query",
                json={"county": COUNTY, "district": DISTRICT},
            )

    assert coverage["coverage_status"] == "covered"
    assert summary is not None
    assert history
    assert len(history) >= 2
    assert summary["period"] == "2025-02"
    assert summary["period"] in {row["period"] for row in history}
    assert summary["county"] == "台北市"
    assert summary["transaction_count"] > 0
    assert summary["average_unit_price"] > 0
    assert result["data_status"] == "available"
    assert result["coverage_status"] == "covered"
    assert result["history"]
    assert api_response.status_code == 200
    assert api_response.json()["data_status"] == "available"
    assert api_response.json()["coverage_status"] == "covered"
    assert api_response.json()["history"]
