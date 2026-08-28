from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.validate_postgres_migration import MIGRATIONS, _statements
from services.plvr_cutover_rehearsal import (
    DRY_RUN_DATABASE_NAME,
    reset_rehearsal_schema,
    resolve_dry_run_url,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database" / "migrations" / "010_add_plvr_generation_schema.sql"
TABLES = {
    "plvr_dataset_generations",
    "plvr_generation_transactions",
    "plvr_generation_market_aggregates",
    "plvr_generation_region_coverage",
    "plvr_active_dataset",
    "plvr_generation_load_checkpoints",
}
VIEWS = {
    "plvr_active_transactions",
    "plvr_active_market_aggregates",
    "plvr_active_region_coverage",
}
INDEXES = {
    "idx_plvr_dataset_generations_state",
    "idx_plvr_generation_transactions_region_period",
    "idx_plvr_generation_transactions_business_key",
    "idx_plvr_generation_market_aggregates_region_period",
    "idx_plvr_generation_region_coverage_region_period",
    "idx_plvr_generation_load_checkpoints_updated_at",
}


def test_generation_schema_migration_is_registered_and_additive_only() -> None:
    # 010 must remain registered and additive-only. It is no longer required to
    # be the last entry: the Stage -1 security hotfix appends 012 after it.
    assert MIGRATION in MIGRATIONS
    statements = _statements(MIGRATION)
    assert statements
    assert all(statement.lstrip().lower().startswith(("create ", "alter ", "comment ")) for statement in statements)

    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create or replace" not in sql
    assert "drop table" not in sql
    assert "drop schema" not in sql
    assert "drop column" not in sql
    assert "truncate" not in sql
    assert "delete from" not in sql
    assert "insert into" not in sql
    assert "update public." not in sql
    assert "failure_fixture" not in sql


def test_generation_schema_has_rehearsed_guards_without_activation() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for table in TABLES:
        assert f"create table public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
    for view in VIEWS:
        assert f"create view public.{view}" in sql
    assert sql.count("with (security_invoker = true)") == len(VIEWS)
    assert "metadata-backed active generation pointer" in sql
    assert "active_generation_must_be_validated" in sql
    assert "candidate_publishability_guard_failed" in sql
    assert "values ('official_plvr'" not in sql


@pytest.mark.skipif(
    not os.environ.get("PLVR_DRY_RUN_DATABASE_URL"),
    reason="isolated Phase 2F PostgreSQL target is not configured",
)
def test_generation_schema_applies_to_clean_local_postgres_and_rolls_back() -> None:
    import psycopg

    database_url = resolve_dry_run_url(
        {"PLVR_DRY_RUN_DATABASE_URL": os.environ["PLVR_DRY_RUN_DATABASE_URL"]}
    )
    connection = psycopg.connect(database_url, connect_timeout=10, prepare_threshold=None)
    try:
        connection.execute("set local lock_timeout = '5s'")
        connection.execute("set local statement_timeout = '60s'")
        reset_rehearsal_schema(connection)

        legacy_exists = connection.execute(
            "select to_regclass('public.real_price_transactions') is not null"
        ).fetchone()[0]
        if not legacy_exists:
            connection.execute(
                "create table public.real_price_transactions "
                "(id bigint primary key, source text not null)"
            )
            connection.execute(
                "insert into public.real_price_transactions (id, source) "
                "values (1, 'local_schema_fixture')"
            )
        legacy_before = connection.execute(
            "select count(*) from public.real_price_transactions"
        ).fetchone()[0]

        for statement in _statements(MIGRATION):
            connection.execute(statement)

        tables = {
            row[0]
            for row in connection.execute(
                "select table_name from information_schema.tables "
                "where table_schema = 'public' and table_name = any(%s)",
                (list(TABLES),),
            ).fetchall()
        }
        views = {
            row[0]
            for row in connection.execute(
                "select viewname from pg_views "
                "where schemaname = 'public' and viewname = any(%s)",
                (list(VIEWS),),
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "select indexname from pg_indexes "
                "where schemaname = 'public' and indexname = any(%s)",
                (list(INDEXES),),
            ).fetchall()
        }
        rls_tables = {
            row[0]
            for row in connection.execute(
                "select relname from pg_class "
                "where relnamespace = 'public'::regnamespace "
                "and relname = any(%s) and relrowsecurity",
                (list(TABLES),),
            ).fetchall()
        }
        security_invoker_views = {
            row[0]
            for row in connection.execute(
                "select relname from pg_class "
                "where relnamespace = 'public'::regnamespace "
                "and relname = any(%s) "
                "and coalesce(reloptions, array[]::text[]) @> array['security_invoker=true']",
                (list(VIEWS),),
            ).fetchall()
        }
        foreign_keys = connection.execute(
            "select count(*) from information_schema.table_constraints "
            "where constraint_schema = 'public' "
            "and table_name = any(%s) and constraint_type = 'FOREIGN KEY'",
            (list(TABLES),),
        ).fetchone()[0]

        assert tables == TABLES
        assert views == VIEWS
        assert indexes == INDEXES
        assert rls_tables == TABLES
        assert security_invoker_views == VIEWS
        assert foreign_keys == 6
        assert all(
            connection.execute(f"select count(*) from public.{table}").fetchone()[0] == 0
            for table in TABLES
        )

        connection.execute(
            "insert into public.plvr_dataset_generations ("
            "dataset_key, generation_id, generation_role, state, "
            "source_manifest_sha256, dataset_sha256, expected_transaction_count, "
            "expected_aggregate_count, expected_period_min, expected_period_max, "
            "expected_city_count, expected_geographic_unit_count"
            ") values ("
            "'official_plvr', 'local-empty-candidate', 'candidate', 'registered', "
            "'local-manifest', 'local-dataset', 0, 0, '2023-09', '2026-07', 0, 0"
            ")"
        )
        assert connection.execute(
            "select count(*) from public.plvr_active_dataset"
        ).fetchone()[0] == 0
        assert connection.execute(
            "select count(*) from public.real_price_transactions"
        ).fetchone()[0] == legacy_before
        assert connection.execute("select current_database()").fetchone()[0] == DRY_RUN_DATABASE_NAME
    finally:
        connection.rollback()
        connection.close()
