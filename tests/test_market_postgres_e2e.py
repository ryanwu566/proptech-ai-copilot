"""Disposable PostgreSQL proof for official market release publication.

The test is skipped locally unless the CI service explicitly opts in with
MARKET_E2E_POSTGRES=1. It uses synthetic rows only and never reads a project
dotenv file or a hosted database setting.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from scripts.apply_production_migrations import apply
from services.official_plvr_market_pipeline import (
    NormalizedTransaction,
    publish_release,
    rollback_release,
)
from services.official_plvr_market_pipeline import aggregate_transactions


pytestmark = pytest.mark.skipif(
    os.getenv("MARKET_E2E_POSTGRES") != "1",
    reason="disposable PostgreSQL service is not enabled",
)

ROOT = Path(__file__).resolve().parents[1]


def _database_url() -> str:
    host = os.getenv("MARKET_E2E_POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("MARKET_E2E_POSTGRES_PORT", "5432")
    return f"postgresql://postgres@{host}:{port}/market_e2e"


def _apply_migration_file(cursor, filename: str) -> None:
    cursor.execute((ROOT / "database" / "migrations" / filename).read_text(encoding="utf-8"))


def _table_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public' and table_name = %s
        """,
        (table_name,),
    )
    return {row[0] for row in cursor.fetchall()}


class _RollbackSchemaContract(Exception):
    pass


def test_market_coverage_schema_contract_is_non_destructive_and_idempotent() -> None:
    import psycopg

    database_url = _database_url()
    try:
        connection = psycopg.connect(database_url, prepare_threshold=None)
    except psycopg.Error as exc:
        pytest.skip(f"disposable PostgreSQL unavailable: {type(exc).__name__}")

    with connection:
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute("drop table if exists official_market_region_coverage")
                    cursor.execute("drop table if exists market_region_coverage")

                    _apply_migration_file(cursor, "003_add_market_region_coverage.sql")
                    _apply_migration_file(cursor, "008_add_official_market_pipeline.sql")
                    _apply_migration_file(cursor, "009_separate_official_market_region_coverage.sql")

                    legacy_columns = _table_columns(cursor, "market_region_coverage")
                    official_columns = _table_columns(cursor, "official_market_region_coverage")
                    assert "valid_market_candidate_count" in legacy_columns
                    assert "release_id" not in legacy_columns
                    assert {"release_id", "latest_period", "record_count"}.issubset(official_columns)
                    assert "valid_market_candidate_count" not in official_columns

                    cursor.execute("drop table official_market_region_coverage")
                    cursor.execute("drop table market_region_coverage")
                    _apply_migration_file(cursor, "008_add_official_market_pipeline.sql")
                    cursor.execute(
                        "insert into official_market_releases (release_id, source_id, status) values (%s, %s, %s)",
                        ("synthetic-coverage-release", "synthetic-coverage-source", "published"),
                    )
                    cursor.execute(
                        """
                        insert into market_region_coverage (
                            release_id, county, district, coverage_status, latest_period,
                            record_count, source_updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        ("synthetic-coverage-release", "Synthetic County", "Synthetic District", "covered", "2025-02", 3, "2025-03-01"),
                    )
                    _apply_migration_file(cursor, "009_separate_official_market_region_coverage.sql")
                    cursor.execute("select record_count from official_market_region_coverage")
                    assert cursor.fetchone()[0] == 3

                    _apply_migration_file(cursor, "009_separate_official_market_region_coverage.sql")
                    cursor.execute("select count(*) from official_market_region_coverage")
                    assert cursor.fetchone()[0] == 1
                raise _RollbackSchemaContract
        except _RollbackSchemaContract:
            pass


def _transaction(index: int, price: float, release_id: str) -> NormalizedTransaction:
    return NormalizedTransaction(
        transaction_id=f"synthetic-{release_id}-{index}",
        source_id="synthetic-official-fixture",
        source_release_id=release_id,
        transaction_type="existing_sale",
        county="Synthetic County",
        district="Synthetic District",
        transaction_date=date(2025, 1, 15),
        area_sqm=30,
        total_price_ntd=price * 30,
        unit_price_ntd_sqm=price,
        unit_price_ntd_ping=price * 3.305785,
        building_type="Synthetic building",
        source_record_id=f"synthetic-record-{release_id}-{index}",
        validation_status="valid",
        dedupe_fingerprint=f"synthetic-fingerprint-{release_id}-{index}",
    )


def _publish(connection, release_id: str, prices: list[float]) -> None:
    transactions = [_transaction(index, price, release_id) for index, price in enumerate(prices)]
    aggregates = aggregate_transactions(
        transactions,
        source_name="Synthetic official fixture",
        source_release_id=release_id,
        source_updated_at="2025-02-01",
    )
    with connection.transaction():
        result = publish_release(
            connection,
            release={"release_id": release_id, "source_id": "synthetic-official-fixture", "schema_version": "fixture-v1", "archive_sha256": f"sha-{release_id}"},
            transactions=transactions,
            aggregates=aggregates,
        )
    assert result["status"] == "published"


def test_disposable_postgres_market_release_lifecycle() -> None:
    database_url = _database_url()
    migration = apply(database_url, release_version="market-e2e")
    assert migration["status"] == "pass"

    import psycopg

    with psycopg.connect(database_url, prepare_threshold=None) as connection:
        _publish(connection, "release-a", [100, 200, 300])
        with connection.cursor() as cursor:
            cursor.execute("select median_unit_price_ntd_sqm, mean_unit_price_ntd_sqm, transaction_count from market_region_period_aggregates where release_id = 'release-a'")
            median, mean, count = cursor.fetchone()
            assert median == 200
            assert mean == 200
            assert count == 3

        _publish(connection, "release-a", [100, 200, 300])
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from market_transactions where release_id = 'release-a'")
            assert cursor.fetchone()[0] == 3

        _publish(connection, "release-b", [400, 500, 600])
        with connection.cursor() as cursor:
            cursor.execute("select release_id from official_market_releases where is_active")
            assert cursor.fetchone()[0] == "release-b"

        with pytest.raises(Exception):
            with connection.transaction():
                publish_release(
                    connection,
                    release={"release_id": "release-c", "source_id": "synthetic-official-fixture"},
                    transactions=[],
                    aggregates=[{"county": "Synthetic County"}],
                )
        with connection.cursor() as cursor:
            cursor.execute("select release_id from official_market_releases where is_active")
            assert cursor.fetchone()[0] == "release-b"

        with connection.transaction():
            result = rollback_release(connection, release_id="release-a")
            assert result["status"] == "rolled_back"
        with connection.cursor() as cursor:
            cursor.execute("select release_id from official_market_releases where is_active")
            assert cursor.fetchone()[0] == "release-a"
