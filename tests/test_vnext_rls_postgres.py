"""Real disposable-PostgreSQL proof for the VNext request principal and RLS.

The test never reads the application DATABASE_URL or a project dotenv file. It
runs only when CI/operators provide a dedicated database whose name begins with
``vnext_rls_test`` and explicitly confirm that it is disposable.
"""

from __future__ import annotations

import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from scripts.validate_postgres_migration import _statements
from services.postgres_runtime import connect
from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.db_principal import DatabasePrincipalContext


DATABASE_ENV = "VNEXT_RLS_POSTGRES_URL"
DISPOSABLE_CONFIRMATION_ENV = "VNEXT_RLS_POSTGRES_DISPOSABLE"
DATABASE_URL = os.getenv(DATABASE_ENV, "").strip()

pytestmark = [
    pytest.mark.external_database,
    pytest.mark.skipif(
        not DATABASE_URL or os.getenv(DISPOSABLE_CONFIRMATION_ENV) != "1",
        reason="real VNext RLS test requires an explicitly confirmed disposable PostgreSQL target",
    ),
]

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/013_vnext_workspace_case_foundation.sql"

WORKSPACE_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
WORKSPACE_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
CASE_A = UUID("aaaaaaaa-cccc-4ccc-8ccc-cccccccccccc")
CASE_B = UUID("bbbbbbbb-cccc-4ccc-8ccc-cccccccccccc")
USERS = {
    "none": UUID("10000000-0000-4000-8000-000000000001"),
    "viewer": UUID("10000000-0000-4000-8000-000000000002"),
    "member": UUID("10000000-0000-4000-8000-000000000003"),
    "manager": UUID("10000000-0000-4000-8000-000000000004"),
    "admin": UUID("10000000-0000-4000-8000-000000000005"),
    "owner": UUID("10000000-0000-4000-8000-000000000006"),
    "revoked": UUID("10000000-0000-4000-8000-000000000007"),
    "workspace_b": UUID("20000000-0000-4000-8000-000000000001"),
}


def _principal(user_id: UUID) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user_id,
        token_subject=str(user_id),
        issuer="http://localhost/auth/v1",
        token_issued_at=datetime.now(timezone.utc),
    )


def _require_disposable_database(connection) -> None:
    database_name = connection.execute("SELECT current_database()").fetchone()[0]
    if not str(database_name).startswith("vnext_rls_test"):
        pytest.fail(
            "VNEXT_RLS_POSTGRES_URL must name a dedicated database beginning with vnext_rls_test"
        )


def _install_auth_contract(connection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS auth")
    connection.execute("CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY)")
    if connection.execute("SELECT to_regprocedure('auth.uid()')").fetchone()[0] is None:
        connection.execute(
            "CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE "
            "SET search_path = '' AS $$ SELECT COALESCE("
            "NULLIF(current_setting('request.jwt.claim.sub', true), ''), "
            "NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'"
            ")::uuid $$"
        )


def _seed(connection) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO auth.users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            [(user_id,) for user_id in USERS.values()],
        )
    connection.execute(
        "INSERT INTO vnext_core.workspaces ("
        "workspace_id, workspace_type, display_name, created_by_user_id, personal_owner_user_id"
        ") VALUES (%s, 'personal', 'Workspace A', %s, %s), "
        "(%s, 'team', 'Workspace B', %s, NULL)",
        (
            WORKSPACE_A,
            USERS["owner"],
            USERS["owner"],
            WORKSPACE_B,
            USERS["workspace_b"],
        ),
    )
    active_members = ["viewer", "member", "manager", "admin", "owner"]
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO vnext_core.workspace_members ("
            "workspace_id, user_id, role, status, joined_at"
            ") VALUES (%s, %s, %s, 'active', clock_timestamp())",
            [(WORKSPACE_A, USERS[role], role) for role in active_members]
            + [(WORKSPACE_B, USERS["workspace_b"], "member")],
        )
    connection.execute(
        "INSERT INTO vnext_core.workspace_members ("
        "workspace_id, user_id, role, status, revoked_at"
        ") VALUES (%s, %s, 'owner', 'removed', clock_timestamp())",
        (WORKSPACE_A, USERS["revoked"]),
    )
    connection.execute(
        "INSERT INTO vnext_core.cases ("
        "case_id, workspace_id, purpose, title, created_by_user_id"
        ") VALUES (%s, %s, 'buy_due_diligence', 'Case A', %s), "
        "(%s, %s, 'development', 'Case B', %s)",
        (
            CASE_A,
            WORKSPACE_A,
            USERS["owner"],
            CASE_B,
            WORKSPACE_B,
            USERS["workspace_b"],
        ),
    )


@contextmanager
def _prepared_database():
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    from psycopg_pool import ConnectionPool

    password = secrets.token_urlsafe(32)
    admin = connect(DATABASE_URL)
    pool = None
    try:
        _require_disposable_database(admin)
        admin.execute("DROP SCHEMA IF EXISTS vnext_private CASCADE")
        admin.execute("DROP SCHEMA IF EXISTS vnext_core CASCADE")
        _install_auth_contract(admin)
        for statement in _statements(MIGRATION):
            admin.execute(statement)
        _seed(admin)
        admin.execute(
            sql.SQL("ALTER ROLE vnext_api PASSWORD {}").format(sql.Literal(password))
        )
        admin.commit()

        parameters = conninfo_to_dict(DATABASE_URL)
        parameters["user"] = "vnext_api"
        parameters["password"] = password
        request_url = make_conninfo(**parameters)
        pool = ConnectionPool(
            conninfo=request_url,
            min_size=1,
            max_size=1,
            open=True,
            kwargs={"prepare_threshold": None},
        )
        pool.wait(timeout=10)
        yield admin, pool, DatabasePrincipalContext(pool)
    except psycopg.Error:
        raise
    finally:
        if pool is not None:
            pool.close()
        try:
            admin.rollback()
            role_exists = admin.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vnext_api')"
            ).fetchone()[0]
            if role_exists:
                admin.execute("ALTER ROLE vnext_api PASSWORD NULL")
            admin.execute("DROP SCHEMA IF EXISTS vnext_private CASCADE")
            admin.execute("DROP SCHEMA IF EXISTS vnext_core CASCADE")
            if admin.execute("SELECT to_regclass('auth.users')").fetchone()[0] is not None:
                admin.execute(
                    "DELETE FROM auth.users WHERE id = ANY(%s)",
                    (list(USERS.values()),),
                )
            admin.commit()
        finally:
            admin.close()


def _visible_case_count(context: DatabasePrincipalContext, user: str, workspace_id: UUID) -> int:
    with context.transaction(_principal(USERS[user])) as connection:
        return int(
            connection.execute(
                "SELECT count(*) FROM vnext_core.cases WHERE workspace_id = %s",
                (workspace_id,),
            ).fetchone()[0]
        )


def _assert_migration_catalog(admin) -> None:
    assert admin.execute("SELECT current_database()").fetchone()[0].startswith(
        "vnext_rls_test"
    )
    assert admin.execute(
        "SELECT nspname FROM pg_namespace "
        "WHERE nspname IN ('vnext_core', 'vnext_private') ORDER BY nspname"
    ).fetchall() == [("vnext_core",), ("vnext_private",)]

    tables = admin.execute(
        "SELECT namespace.nspname, relation.relname, relation.relrowsecurity, "
        "relation.relforcerowsecurity, owner.rolname "
        "FROM pg_class relation "
        "JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace "
        "JOIN pg_roles owner ON owner.oid = relation.relowner "
        "WHERE relation.relkind = 'r' "
        "AND namespace.nspname IN ('vnext_core', 'vnext_private') "
        "ORDER BY namespace.nspname, relation.relname"
    ).fetchall()
    assert [(schema, table, rls, forced) for schema, table, rls, forced, _ in tables] == [
        ("vnext_core", "cases", True, True),
        ("vnext_core", "workspace_members", True, True),
        ("vnext_core", "workspaces", True, True),
        ("vnext_private", "audit_events", True, True),
        ("vnext_private", "idempotency_records", True, True),
    ]
    assert all(owner != "vnext_api" for _, _, _, _, owner in tables)

    policies = admin.execute(
        "SELECT schemaname, tablename, policyname, cmd, roles "
        "FROM pg_policies "
        "WHERE schemaname IN ('vnext_core', 'vnext_private') "
        "ORDER BY schemaname, tablename, policyname"
    ).fetchall()
    assert policies == [
        ("vnext_core", "cases", "cases_active_member_select", "SELECT", ["vnext_api"]),
        ("vnext_core", "cases", "cases_active_writer_insert", "INSERT", ["vnext_api"]),
        ("vnext_core", "cases", "cases_active_writer_update", "UPDATE", ["vnext_api"]),
        (
            "vnext_core",
            "workspace_members",
            "workspace_members_self_select",
            "SELECT",
            ["vnext_api"],
        ),
        (
            "vnext_core",
            "workspaces",
            "workspaces_active_member_select",
            "SELECT",
            ["vnext_api"],
        ),
        (
            "vnext_private",
            "audit_events",
            "audit_actor_insert",
            "INSERT",
            ["vnext_api"],
        ),
        (
            "vnext_private",
            "idempotency_records",
            "idempotency_actor_insert",
            "INSERT",
            ["vnext_api"],
        ),
        (
            "vnext_private",
            "idempotency_records",
            "idempotency_actor_select",
            "SELECT",
            ["vnext_api"],
        ),
        (
            "vnext_private",
            "idempotency_records",
            "idempotency_actor_update",
            "UPDATE",
            ["vnext_api"],
        ),
    ]

    grants = admin.execute(
        "SELECT table_schema, table_name, privilege_type "
        "FROM information_schema.role_table_grants "
        "WHERE grantee = 'vnext_api' "
        "AND table_schema IN ('vnext_core', 'vnext_private') "
        "ORDER BY table_schema, table_name, privilege_type"
    ).fetchall()
    assert grants == [
        ("vnext_core", "cases", "INSERT"),
        ("vnext_core", "cases", "SELECT"),
        ("vnext_core", "cases", "UPDATE"),
        ("vnext_core", "workspace_members", "SELECT"),
        ("vnext_core", "workspaces", "SELECT"),
        ("vnext_private", "audit_events", "INSERT"),
        ("vnext_private", "idempotency_records", "INSERT"),
        ("vnext_private", "idempotency_records", "SELECT"),
        ("vnext_private", "idempotency_records", "UPDATE"),
    ]


def _insert_is_denied(context: DatabasePrincipalContext, user: str, workspace_id: UUID) -> None:
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with context.transaction(_principal(USERS[user])) as connection:
            connection.execute(
                "INSERT INTO vnext_core.cases ("
                "workspace_id, purpose, title, created_by_user_id"
                ") VALUES (%s, 'buy_due_diligence', 'Denied', %s)",
                (workspace_id, USERS[user]),
            )


def test_real_postgres_vnext_role_rls_and_pool_isolation() -> None:
    with _prepared_database() as (admin, pool, context):
        _assert_migration_catalog(admin)

        with context.transaction(_principal(USERS["owner"])) as connection:
            role = connection.execute(
                "SELECT current_user, rolsuper, rolbypassrls, rolinherit "
                "FROM pg_roles WHERE rolname = current_user"
            ).fetchone()
            owns_vnext = connection.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_class relation "
                "JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace "
                "WHERE namespace.nspname IN ('vnext_core', 'vnext_private') "
                "AND relation.relowner = (SELECT oid FROM pg_roles WHERE rolname = current_user))"
            ).fetchone()[0]
            assert role == ("vnext_api", False, False, False)
            assert owns_vnext is False
            assert connection.execute("SELECT auth.uid()").fetchone()[0] == USERS["owner"]

        assert _visible_case_count(context, "none", WORKSPACE_A) == 0
        _insert_is_denied(context, "none", WORKSPACE_A)
        with context.transaction(_principal(USERS["none"])) as connection:
            result = connection.execute(
                "UPDATE vnext_core.cases SET title = 'Denied' WHERE case_id = %s",
                (CASE_A,),
            )
            assert result.rowcount == 0

        assert _visible_case_count(context, "viewer", WORKSPACE_A) == 1
        _insert_is_denied(context, "viewer", WORKSPACE_A)
        with context.transaction(_principal(USERS["viewer"])) as connection:
            result = connection.execute(
                "UPDATE vnext_core.cases SET title = 'Viewer denied' WHERE case_id = %s",
                (CASE_A,),
            )
            assert result.rowcount == 0

        for role in ("member", "manager", "admin", "owner"):
            with context.transaction(_principal(USERS[role])) as connection:
                case_id = uuid4()
                inserted = connection.execute(
                    "INSERT INTO vnext_core.cases ("
                    "case_id, workspace_id, purpose, title, created_by_user_id"
                    ") VALUES (%s, %s, 'buy_due_diligence', %s, %s) RETURNING version",
                    (case_id, WORKSPACE_A, f"{role} case", USERS[role]),
                ).fetchone()
                assert inserted == (1,)
                updated = connection.execute(
                    "UPDATE vnext_core.cases SET title = %s, version = version + 1 "
                    "WHERE case_id = %s RETURNING version",
                    (f"{role} updated", case_id),
                ).fetchone()
                assert updated == (2,)

        assert _visible_case_count(context, "member", WORKSPACE_B) == 0
        _insert_is_denied(context, "member", WORKSPACE_B)
        with context.transaction(_principal(USERS["member"])) as connection:
            result = connection.execute(
                "UPDATE vnext_core.cases SET title = 'Cross tenant' WHERE case_id = %s",
                (CASE_B,),
            )
            assert result.rowcount == 0

        assert _visible_case_count(context, "revoked", WORKSPACE_A) == 0
        _insert_is_denied(context, "revoked", WORKSPACE_A)

        with context.transaction(_principal(USERS["owner"])) as connection:
            connection.execute(
                "INSERT INTO vnext_private.audit_events ("
                "workspace_id, actor_user_id, event_type, resource_type, resource_id, "
                "request_id, outcome"
                ") VALUES (%s, %s, 'case.updated', 'case', %s, 'real-rls-audit', 'succeeded')",
                (WORKSPACE_A, USERS["owner"], CASE_A),
            )
        audit_id = admin.execute(
            "SELECT audit_event_id FROM vnext_private.audit_events "
            "WHERE request_id = 'real-rls-audit'"
        ).fetchone()[0]
        admin.commit()

        import psycopg

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["owner"])) as connection:
                connection.execute(
                    "UPDATE vnext_private.audit_events SET event_type = 'rewritten' "
                    "WHERE audit_event_id = %s",
                    (audit_id,),
                )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["owner"])) as connection:
                connection.execute(
                    "DELETE FROM vnext_private.audit_events WHERE audit_event_id = %s",
                    (audit_id,),
                )

        # Commit clears the transaction-local principal before the sole pooled
        # connection is checked out again.
        with context.transaction(_principal(USERS["member"])) as connection:
            physical_connection = connection.execute("SELECT pg_backend_pid()").fetchone()[0]
            assert connection.execute("SELECT auth.uid()").fetchone()[0] == USERS["member"]
        with pool.connection() as connection:
            assert connection.execute("SELECT pg_backend_pid()").fetchone()[0] == physical_connection
            committed = connection.execute(
                "SELECT current_setting('request.jwt.claim.sub', true)"
            ).fetchone()[0]
            assert committed in (None, "")
            connection.rollback()

        class _RollbackProof(RuntimeError):
            pass

        with pytest.raises(_RollbackProof):
            with context.transaction(_principal(USERS["owner"])) as connection:
                assert connection.execute("SELECT pg_backend_pid()").fetchone()[0] == physical_connection
                assert connection.execute("SELECT auth.uid()").fetchone()[0] == USERS["owner"]
                raise _RollbackProof
        with pool.connection() as connection:
            assert connection.execute("SELECT pg_backend_pid()").fetchone()[0] == physical_connection
            rolled_back = connection.execute(
                "SELECT current_setting('request.jwt.claim.sub', true)"
            ).fetchone()[0]
            assert rolled_back in (None, "")
            connection.rollback()

        # The same physical connection now carries B, never A.
        with context.transaction(_principal(USERS["workspace_b"])) as connection:
            assert connection.execute("SELECT pg_backend_pid()").fetchone()[0] == physical_connection
            assert connection.execute("SELECT auth.uid()").fetchone()[0] == USERS["workspace_b"]
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.cases WHERE workspace_id = %s",
                (WORKSPACE_B,),
            ).fetchone()[0] == 1
