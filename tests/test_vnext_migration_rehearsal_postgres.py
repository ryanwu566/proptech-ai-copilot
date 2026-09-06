"""Production-runner rehearsal on the explicitly disposable Slice 9 database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import apply_production_migrations as runner
from scripts.migration_registry import load_registry, next_safe_sequence
from scripts.validate_postgres_migration import _statements
from services.postgres_runtime import connect


DATABASE_URL = os.getenv("VNEXT_RLS_POSTGRES_URL", "").strip()
DISPOSABLE = os.getenv("VNEXT_RLS_POSTGRES_DISPOSABLE") == "1"
pytestmark = [
    pytest.mark.external_database,
    pytest.mark.skipif(
        not DATABASE_URL or not DISPOSABLE,
        reason="real migration rehearsal requires the explicitly disposable VNext database",
    ),
]


def _assert_disposable(connection) -> None:
    name = str(connection.execute("SELECT current_database()").fetchone()[0])
    assert name.startswith("vnext_rls_test")


def _reset_database(connection) -> None:
    _assert_disposable(connection)
    connection.execute("DROP SCHEMA IF EXISTS vnext_private CASCADE")
    connection.execute("DROP SCHEMA IF EXISTS vnext_core CASCADE")
    connection.execute("DROP SCHEMA IF EXISTS auth CASCADE")
    connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
    connection.execute("CREATE SCHEMA public")
    connection.execute("CREATE SCHEMA auth")
    connection.execute("CREATE TABLE auth.users (id uuid PRIMARY KEY)")
    connection.execute(
        "CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE "
        "SET search_path = '' AS $$ SELECT COALESCE("
        "NULLIF(current_setting('request.jwt.claim.sub', true), ''), "
        "NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'"
        ")::uuid $$"
    )
    connection.commit()


def _assert_ledger(connection) -> None:
    expected = {
        path.stem: runner._checksum(path)
        for path in runner.MIGRATIONS
    }
    actual = dict(
        connection.execute(
            "SELECT migration_id, checksum FROM public.schema_migration_ledger"
        ).fetchall()
    )
    assert actual == expected
    assert len(actual) == 13
    assert not any(migration_id.startswith("018_") for migration_id in actual)


def _assert_catalog(connection) -> None:
    tables = connection.execute(
        "SELECT namespace.nspname, relation.relname, relation.relrowsecurity, "
        "relation.relforcerowsecurity, owner.rolname "
        "FROM pg_class relation "
        "JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace "
        "JOIN pg_roles owner ON owner.oid = relation.relowner "
        "WHERE namespace.nspname IN ('vnext_core', 'vnext_private') "
        "AND relation.relkind = 'r' ORDER BY 1, 2"
    ).fetchall()
    assert len(tables) == 19
    assert all(row[2] is True and row[3] is True for row in tables)
    assert all(row[4] != "vnext_api" for row in tables)

    role = connection.execute(
        "SELECT rolsuper, rolbypassrls, rolinherit FROM pg_roles "
        "WHERE rolname = 'vnext_api'"
    ).fetchone()
    assert role == (False, False, False)

    foreign_keys = connection.execute(
        "SELECT count(*) FROM information_schema.table_constraints "
        "WHERE constraint_schema IN ('vnext_core', 'vnext_private') "
        "AND constraint_type = 'FOREIGN KEY'"
    ).fetchone()[0]
    assert foreign_keys >= 69

    grants = connection.execute(
        "SELECT table_schema, table_name, privilege_type "
        "FROM information_schema.role_table_grants "
        "WHERE grantee = 'vnext_api' "
        "AND table_schema IN ('vnext_core', 'vnext_private')"
    ).fetchall()
    assert grants
    assert all(privilege != "DELETE" for _schema, _table, privilege in grants)
    mutable = {
        (schema, table)
        for schema, table, privilege in grants
        if privilege == "UPDATE"
    }
    assert mutable <= {
        ("vnext_core", "cases"),
        ("vnext_core", "identity_resolutions"),
        ("vnext_private", "idempotency_records"),
    }

    trigger_functions = connection.execute(
        "SELECT DISTINCT namespace.nspname, procedure.proname, procedure.proconfig "
        "FROM pg_trigger trigger "
        "JOIN pg_proc procedure ON procedure.oid = trigger.tgfoid "
        "JOIN pg_namespace namespace ON namespace.oid = procedure.pronamespace "
        "WHERE NOT trigger.tgisinternal "
        "AND namespace.nspname IN ('vnext_core', 'vnext_private')"
    ).fetchall()
    assert len(trigger_functions) >= 14
    assert all(
        settings is not None
        and any(str(setting).startswith("search_path=") for setting in settings)
        for _schema, _name, settings in trigger_functions
    )


def _install_existing_production_prefix(connection) -> None:
    runner._ensure_ledger(connection)
    prefix = [
        path
        for path in runner.MIGRATIONS
        if int(path.name.split("_", 1)[0]) < 13
    ]
    assert len(prefix) == 8
    for path in prefix:
        for statement in _statements(Path(path)):
            connection.execute(statement)
        connection.execute(
            "INSERT INTO public.schema_migration_ledger "
            "(migration_id, schema_version, release_version, checksum) "
            "VALUES (%s, %s, 'slice9-prefix', %s)",
            (path.stem, runner._schema_version(path), runner._checksum(path)),
        )
    connection.commit()


def test_clean_apply_existing_prefix_upgrade_repeat_and_catalog_rehearsal() -> None:
    registrations = load_registry()
    assert next_safe_sequence(registrations) == 18
    assert len(runner.MIGRATIONS) == 13

    with connect(DATABASE_URL) as connection:
        _reset_database(connection)

    clean = runner.apply(
        DATABASE_URL,
        release_version="slice9-clean-rehearsal",
    )
    assert clean == {
        "status": "pass",
        "migration_count": 13,
        "registry_count": 18,
        "next_migration_sequence": "018",
        "ledger": "applied",
        "verification": "tables_indexes_foreign_keys",
    }
    repeat_clean = runner.apply(
        DATABASE_URL,
        release_version="slice9-clean-repeat",
    )
    assert repeat_clean["status"] == "pass"
    with connect(DATABASE_URL) as connection:
        _assert_ledger(connection)
        _assert_catalog(connection)
        _reset_database(connection)
        _install_existing_production_prefix(connection)
        assert connection.execute(
            "SELECT to_regnamespace('vnext_core')"
        ).fetchone()[0] is None
        assert connection.execute(
            "SELECT count(*) FROM public.schema_migration_ledger"
        ).fetchone()[0] == 8

    upgraded = runner.apply(
        DATABASE_URL,
        release_version="slice9-prefix-upgrade",
    )
    assert upgraded["status"] == "pass"
    repeat_upgrade = runner.apply(
        DATABASE_URL,
        release_version="slice9-upgrade-repeat",
    )
    assert repeat_upgrade["status"] == "pass"
    with connect(DATABASE_URL) as connection:
        _assert_ledger(connection)
        _assert_catalog(connection)
