"""Disposable PostgreSQL proof for official market release publication.

The test is skipped locally unless the CI service explicitly opts in with
MARKET_E2E_POSTGRES=1. It uses synthetic rows only and never reads a project
dotenv file or a hosted database setting.
"""

from __future__ import annotations

import os
from datetime import date

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


def _database_url() -> str:
    host = os.getenv("MARKET_E2E_POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("MARKET_E2E_POSTGRES_PORT", "5432")
    return f"postgresql://postgres@{host}:{port}/market_e2e"


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
