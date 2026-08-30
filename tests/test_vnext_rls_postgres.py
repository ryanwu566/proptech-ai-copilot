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
MIGRATIONS = (
    ROOT / "database/migrations/013_vnext_workspace_case_foundation.sql",
    ROOT / "database/migrations/014_vnext_property_graph_evidence_foundation.sql",
)

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
PROPERTY_A = UUID("aaaaaaaa-1111-4111-8111-111111111111")
PROPERTY_B = UUID("bbbbbbbb-1111-4111-8111-111111111111")
ADDRESS_A_1 = UUID("aaaaaaaa-2222-4222-8222-222222222221")
ADDRESS_A_2 = UUID("aaaaaaaa-2222-4222-8222-222222222222")
ADDRESS_B = UUID("bbbbbbbb-2222-4222-8222-222222222221")
PARCEL_A_1 = UUID("aaaaaaaa-3333-4333-8333-333333333331")
PARCEL_A_2 = UUID("aaaaaaaa-3333-4333-8333-333333333332")
BUILDING_A_1 = UUID("aaaaaaaa-4444-4444-8444-444444444441")
BUILDING_A_2 = UUID("aaaaaaaa-4444-4444-8444-444444444442")
EVIDENCE_AVAILABLE = UUID("aaaaaaaa-5555-4555-8555-555555555551")
EVIDENCE_UNKNOWN = UUID("aaaaaaaa-5555-4555-8555-555555555552")
EVIDENCE_LIMITED = UUID("aaaaaaaa-5555-4555-8555-555555555553")
EVIDENCE_STALE = UUID("aaaaaaaa-5555-4555-8555-555555555554")
EVIDENCE_DERIVED = UUID("aaaaaaaa-5555-4555-8555-555555555555")


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
        for migration in MIGRATIONS:
            for statement in _statements(migration):
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
        "AND relation.relname IN ('cases', 'workspace_members', 'workspaces', "
        "'audit_events', 'idempotency_records') "
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
        "AND tablename IN ('cases', 'workspace_members', 'workspaces', "
        "'audit_events', 'idempotency_records') "
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
        "AND table_name IN ('cases', 'workspace_members', 'workspaces', "
        "'audit_events', 'idempotency_records') "
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


def _graph_node(connection, workspace_id: UUID, node_type: str, record_id: UUID) -> UUID:
    return connection.execute(
        "SELECT property_graph_node_id FROM vnext_core.property_graph_nodes "
        "WHERE workspace_id = %s AND node_type = %s AND record_id = %s",
        (workspace_id, node_type, record_id),
    ).fetchone()[0]


def _seed_property_graph_and_evidence(connection) -> dict[str, UUID]:
    connection.execute(
        "INSERT INTO vnext_core.property_entities ("
        "property_entity_id, workspace_id, display_label, created_by_user_id"
        ") VALUES (%s, %s, 'Property A', %s), (%s, %s, 'Property B', %s)",
        (
            PROPERTY_A,
            WORKSPACE_A,
            USERS["owner"],
            PROPERTY_B,
            WORKSPACE_B,
            USERS["workspace_b"],
        ),
    )
    references = (
        (ADDRESS_A_1, WORKSPACE_A, "address", "address-a-1", "Address A One", "tgos-address", "address-a-1"),
        (ADDRESS_A_2, WORKSPACE_A, "address", "address-a-2", "Address A Two", "tgos-address", "address-a-2"),
        (ADDRESS_B, WORKSPACE_B, "address", "address-b", "Address B", "tgos-address", "address-b"),
        (PARCEL_A_1, WORKSPACE_A, "parcel", "parcel-a-1", "Parcel A One", "nlsc-cadastral", "parcel-a-1"),
        (PARCEL_A_2, WORKSPACE_A, "parcel", "parcel-a-2", "Parcel A Two", "nlsc-cadastral", "parcel-a-2"),
        (BUILDING_A_1, WORKSPACE_A, "building", "building-a-1", "Building A One", "nlsc-cadastral", "building-a-1"),
        (BUILDING_A_2, WORKSPACE_A, "building", "building-a-2", "Building A Two", "nlsc-cadastral", "building-a-2"),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO vnext_core.property_identity_references ("
            "identity_reference_id, workspace_id, reference_type, normalized_key, "
            "display_value, source_id, source_type, source_environment, source_record_id, "
            "confidence, confidence_method, reference_status, created_by_user_id"
            ") VALUES (%s, %s, %s, %s, %s, %s, 'official', 'production', "
            "%s, 0.8, 'fixture-seed', 'observed', %s)",
            [row + (USERS["owner"] if row[1] == WORKSPACE_A else USERS["workspace_b"],) for row in references],
        )

    nodes = {
        "property_a": _graph_node(connection, WORKSPACE_A, "property", PROPERTY_A),
        "property_b": _graph_node(connection, WORKSPACE_B, "property", PROPERTY_B),
        "address_a_1": _graph_node(connection, WORKSPACE_A, "address", ADDRESS_A_1),
        "address_a_2": _graph_node(connection, WORKSPACE_A, "address", ADDRESS_A_2),
        "address_b": _graph_node(connection, WORKSPACE_B, "address", ADDRESS_B),
        "parcel_a_1": _graph_node(connection, WORKSPACE_A, "parcel", PARCEL_A_1),
        "parcel_a_2": _graph_node(connection, WORKSPACE_A, "parcel", PARCEL_A_2),
        "building_a_1": _graph_node(connection, WORKSPACE_A, "building", BUILDING_A_1),
        "building_a_2": _graph_node(connection, WORKSPACE_A, "building", BUILDING_A_2),
    }

    relation_rows = (
        (nodes["property_a"], nodes["address_a_1"], "property_address", "directed", "proposed"),
        (nodes["property_a"], nodes["address_a_2"], "property_address", "directed", "disputed"),
        (nodes["property_a"], nodes["parcel_a_1"], "property_parcel", "directed", "proposed"),
        (nodes["property_a"], nodes["parcel_a_2"], "property_parcel", "directed", "proposed"),
        (nodes["parcel_a_1"], nodes["building_a_1"], "parcel_building", "bidirectional", "proposed"),
        (nodes["parcel_a_1"], nodes["building_a_2"], "parcel_building", "bidirectional", "proposed"),
        (nodes["parcel_a_2"], nodes["building_a_1"], "parcel_building", "bidirectional", "proposed"),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO vnext_core.property_relations ("
            "workspace_id, from_node_id, to_node_id, relation_type, direction, source_id, "
            "source_type, source_environment, relation_status, valid_from, created_by_user_id"
            ") VALUES (%s, %s, %s, %s, %s, 'tgos-address', 'official', 'production', "
            "%s, timestamptz '2025-01-01 00:00:00+00', %s)",
            [(WORKSPACE_A,) + row + (USERS["owner"],) for row in relation_rows],
        )
    earlier_relation = connection.execute(
        "INSERT INTO vnext_core.property_relations ("
        "workspace_id, from_node_id, to_node_id, relation_type, direction, source_id, "
        "source_type, source_environment, relation_status, valid_from, created_by_user_id"
        ") VALUES (%s, %s, %s, 'property_address', 'directed', 'tgos-address', "
        "'official', 'production', 'proposed', timestamptz '2024-01-01 00:00:00+00', %s) "
        "RETURNING property_relation_id",
        (WORKSPACE_A, nodes["property_a"], nodes["address_a_1"], USERS["owner"]),
    ).fetchone()[0]
    connection.execute(
        "INSERT INTO vnext_core.property_relations ("
        "workspace_id, from_node_id, to_node_id, relation_type, direction, source_id, "
        "source_type, source_environment, relation_status, valid_from, valid_to, "
        "supersedes_relation_id, created_by_user_id"
        ") VALUES (%s, %s, %s, 'property_address', 'directed', 'tgos-address', "
        "'official', 'production', 'superseded', timestamptz '2024-01-01 00:00:00+00', "
        "timestamptz '2024-12-31 23:59:59+00', %s, %s)",
        (
            WORKSPACE_A,
            nodes["property_a"],
            nodes["address_a_1"],
            earlier_relation,
            USERS["owner"],
        ),
    )

    evidence_rows = (
        (
            EVIDENCE_AVAILABLE,
            "property.official_value",
            '{"amount":12500000}',
            "available",
            "known",
            "moi-dla-plvr",
            "official",
            "production",
            1,
            None,
        ),
        (
            EVIDENCE_UNKNOWN,
            "property.terrain_risk",
            None,
            "unknown",
            "unknown",
            "moi-dla-plvr",
            "official",
            "production",
            1,
            None,
        ),
        (
            EVIDENCE_LIMITED,
            "property.market_range",
            '{"low":11000000,"high":14000000}',
            "limited",
            "partial",
            "moi-dla-plvr",
            "official",
            "production",
            1,
            None,
        ),
        (
            EVIDENCE_STALE,
            "property.official_value",
            '{"amount":12500000}',
            "stale",
            "known",
            "moi-dla-plvr",
            "official",
            "production",
            2,
            EVIDENCE_AVAILABLE,
        ),
        (
            EVIDENCE_DERIVED,
            "property.value_signal",
            '{"amount":12600000}',
            "limited",
            "partial",
            "vnext-deterministic",
            "deterministic",
            "production",
            1,
            None,
        ),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO vnext_core.evidence_items ("
            "evidence_id, workspace_id, fact_type, value, source_id, source_type, "
            "source_environment, retrieved_at, coverage_status, coverage, evidence_status, "
            "effective_from, effective_to, "
            "quality_status, quality, license_status, license, lineage, content_hash, "
            "evidence_version, supersedes_evidence_id, created_by_user_id"
            ") VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, clock_timestamp(), %s, "
            "'{\"scope\":\"fixture\"}'::jsonb, %s, timestamptz '2025-01-01 00:00:00+00', "
            "timestamptz '2025-12-31 23:59:59+00', 'passed', '{}'::jsonb, 'approved', "
            "'{}'::jsonb, '{}'::jsonb, %s, %s, %s, %s)",
            [
                (
                    row[0],
                    WORKSPACE_A,
                    row[1],
                    row[2],
                    row[5],
                    row[6],
                    row[7],
                    row[4],
                    row[3],
                    f"{index:064x}",
                    row[8],
                    row[9],
                    USERS["owner"],
                )
                for index, row in enumerate(evidence_rows, start=1)
            ],
        )
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO vnext_core.evidence_lineage ("
            "workspace_id, child_evidence_id, parent_evidence_id, lineage_type, "
            "transformation, transformation_version, created_by_user_id"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    WORKSPACE_A,
                    EVIDENCE_STALE,
                    EVIDENCE_AVAILABLE,
                    "supersedes",
                    "none",
                    None,
                    USERS["owner"],
                ),
                (
                    WORKSPACE_A,
                    EVIDENCE_DERIVED,
                    EVIDENCE_AVAILABLE,
                    "calculated_from",
                    "calculation",
                    "fixture-v1",
                    USERS["owner"],
                ),
                (
                    WORKSPACE_A,
                    EVIDENCE_DERIVED,
                    EVIDENCE_LIMITED,
                    "calculated_from",
                    "calculation",
                    "fixture-v1",
                    USERS["owner"],
                ),
            ],
        )
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO vnext_core.evidence_links ("
            "workspace_id, evidence_id, subject_node_id, link_type, fact_scope, created_by_user_id"
            ") VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (
                    WORKSPACE_A,
                    EVIDENCE_AVAILABLE,
                    nodes["property_a"],
                    "supports",
                    "property.official_value",
                    USERS["owner"],
                ),
                (
                    WORKSPACE_A,
                    EVIDENCE_UNKNOWN,
                    nodes["property_a"],
                    "limits",
                    "property.terrain_risk",
                    USERS["owner"],
                ),
                (
                    WORKSPACE_A,
                    EVIDENCE_LIMITED,
                    nodes["parcel_a_1"],
                    "describes",
                    "property.market_range",
                    USERS["owner"],
                ),
            ],
        )
    return nodes


def _assert_graph_evidence_catalog(admin) -> None:
    table_names = (
        "evidence_items",
        "evidence_lineage",
        "evidence_links",
        "property_entities",
        "property_graph_nodes",
        "property_identity_references",
        "property_relations",
    )
    tables = admin.execute(
        "SELECT relation.relname, relation.relrowsecurity, relation.relforcerowsecurity, "
        "owner.rolname FROM pg_class relation "
        "JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace "
        "JOIN pg_roles owner ON owner.oid = relation.relowner "
        "WHERE namespace.nspname = 'vnext_core' AND relation.relkind = 'r' "
        "AND relation.relname = ANY(%s) ORDER BY relation.relname",
        (list(table_names),),
    ).fetchall()
    assert [(table, rls, forced) for table, rls, forced, _ in tables] == [
        (table, True, True) for table in table_names
    ]
    assert all(owner != "vnext_api" for _, _, _, owner in tables)

    policies = admin.execute(
        "SELECT tablename, policyname, cmd, roles FROM pg_policies "
        "WHERE schemaname = 'vnext_core' AND tablename = ANY(%s) "
        "ORDER BY tablename, policyname",
        (list(table_names),),
    ).fetchall()
    assert len(policies) == 14
    for table in table_names:
        selected = [row for row in policies if row[0] == table]
        assert [(row[2], row[3]) for row in selected] == [
            ("SELECT", ["vnext_api"]),
            ("INSERT", ["vnext_api"]),
        ]

    grants = admin.execute(
        "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
        "WHERE grantee = 'vnext_api' AND table_schema = 'vnext_core' "
        "AND table_name = ANY(%s) ORDER BY table_name, privilege_type",
        (list(table_names),),
    ).fetchall()
    assert grants == [
        (table, privilege)
        for table in table_names
        for privilege in ("INSERT", "SELECT")
    ]


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


def test_real_postgres_property_graph_evidence_rls_history_and_cardinality() -> None:
    import psycopg

    with _prepared_database() as (admin, _pool, context):
        nodes = _seed_property_graph_and_evidence(admin)
        admin.commit()
        _assert_graph_evidence_catalog(admin)

        assert admin.execute(
            "SELECT reference_type, count(*) FROM vnext_core.property_identity_references "
            "WHERE workspace_id = %s GROUP BY reference_type ORDER BY reference_type",
            (WORKSPACE_A,),
        ).fetchall() == [("address", 2), ("building", 2), ("parcel", 2)]
        assert admin.execute(
            "SELECT count(*) FROM vnext_core.property_relations "
            "WHERE workspace_id = %s AND relation_type = 'parcel_building'",
            (WORKSPACE_A,),
        ).fetchone()[0] == 3
        assert admin.execute(
            "SELECT count(*) FROM vnext_core.property_relations "
            "WHERE workspace_id = %s AND relation_type = 'parcel_building' "
            "AND to_node_id = %s",
            (WORKSPACE_A, nodes["building_a_1"]),
        ).fetchone()[0] == 2
        assert set(
            row[0]
            for row in admin.execute(
                "SELECT relation_status FROM vnext_core.property_relations "
                "WHERE workspace_id = %s AND relation_type = 'property_address'",
                (WORKSPACE_A,),
            ).fetchall()
        ) == {"proposed", "disputed", "superseded"}
        assert admin.execute(
            "SELECT evidence_status, count(*) FROM vnext_core.evidence_items "
            "WHERE workspace_id = %s GROUP BY evidence_status ORDER BY evidence_status",
            (WORKSPACE_A,),
        ).fetchall() == [
            ("available", 1),
            ("limited", 2),
            ("stale", 1),
            ("unknown", 1),
        ]
        source_contract = admin.execute(
            "SELECT source_id, source_type, retrieved_at, effective_from, effective_to, "
            "coverage_status, coverage, quality_status, quality, license_status, license "
            "FROM vnext_core.evidence_items WHERE evidence_id = %s",
            (EVIDENCE_AVAILABLE,),
        ).fetchone()
        assert source_contract[0:2] == ("moi-dla-plvr", "official")
        assert source_contract[2] is not None
        assert source_contract[3] == datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert source_contract[4] == datetime(
            2025,
            12,
            31,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        )
        assert source_contract[5:] == (
            "known",
            {"scope": "fixture"},
            "passed",
            {},
            "approved",
            {},
        )
        assert admin.execute(
            "SELECT coverage_status FROM vnext_core.evidence_items WHERE evidence_id = %s",
            (EVIDENCE_LIMITED,),
        ).fetchone() == ("partial",)
        assert admin.execute(
            "SELECT count(*) FROM vnext_core.evidence_lineage "
            "WHERE workspace_id = %s AND child_evidence_id = %s",
            (WORKSPACE_A, EVIDENCE_DERIVED),
        ).fetchone()[0] == 2
        assert admin.execute(
            "SELECT evidence_version, supersedes_evidence_id FROM vnext_core.evidence_items "
            "WHERE evidence_id = %s",
            (EVIDENCE_STALE,),
        ).fetchone() == (2, EVIDENCE_AVAILABLE)

        with context.transaction(_principal(USERS["none"])) as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.property_entities"
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.evidence_items"
            ).fetchone()[0] == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["none"])) as connection:
                connection.execute(
                    "INSERT INTO vnext_core.property_entities ("
                    "workspace_id, display_label, created_by_user_id"
                    ") VALUES (%s, 'Denied', %s)",
                    (WORKSPACE_A, USERS["none"]),
                )

        with context.transaction(_principal(USERS["viewer"])) as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.property_entities WHERE workspace_id = %s",
                (WORKSPACE_A,),
            ).fetchone()[0] == 1
            assert connection.execute(
                "SELECT source_type, evidence_status FROM vnext_core.evidence_items "
                "WHERE evidence_id = %s",
                (EVIDENCE_AVAILABLE,),
            ).fetchone() == ("official", "available")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["viewer"])) as connection:
                connection.execute(
                    "INSERT INTO vnext_core.property_entities ("
                    "workspace_id, display_label, created_by_user_id"
                    ") VALUES (%s, 'Viewer denied', %s)",
                    (WORKSPACE_A, USERS["viewer"]),
                )

        for role in ("member", "manager", "admin", "owner"):
            with context.transaction(_principal(USERS[role])) as connection:
                property_id = uuid4()
                inserted = connection.execute(
                    "INSERT INTO vnext_core.property_entities ("
                    "property_entity_id, workspace_id, display_label, created_by_user_id"
                    ") VALUES (%s, %s, %s, %s) RETURNING entity_status, version",
                    (property_id, WORKSPACE_A, f"{role} unverified", USERS[role]),
                ).fetchone()
                assert inserted == ("unverified", 1)
                assert connection.execute(
                    "SELECT count(*) FROM vnext_core.property_graph_nodes "
                    "WHERE workspace_id = %s AND node_type = 'property' AND record_id = %s",
                    (WORKSPACE_A, property_id),
                ).fetchone()[0] == 1

        with context.transaction(_principal(USERS["member"])) as connection:
            inserted = connection.execute(
                "INSERT INTO vnext_core.evidence_items ("
                "workspace_id, fact_type, source_id, source_type, source_environment, "
                "retrieved_at, coverage_status, coverage, evidence_status, quality_status, "
                "quality, license_status, license, lineage, content_hash, created_by_user_id"
                ") VALUES (%s, 'property.test_signal', 'vnext-test', 'test', 'test', "
                "clock_timestamp(), 'unknown', '{}'::jsonb, 'unknown', 'not_checked', "
                "'{}'::jsonb, 'not_applicable', '{}'::jsonb, '{}'::jsonb, %s, %s) "
                "RETURNING evidence_status",
                (WORKSPACE_A, "f" * 64, USERS["member"]),
            ).fetchone()
            assert inserted == ("unknown",)

        with context.transaction(_principal(USERS["member"])) as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.property_entities WHERE workspace_id = %s",
                (WORKSPACE_B,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.property_graph_nodes WHERE workspace_id = %s",
                (WORKSPACE_B,),
            ).fetchone()[0] == 0
        with pytest.raises(psycopg.Error):
            with context.transaction(_principal(USERS["member"])) as connection:
                connection.execute(
                    "INSERT INTO vnext_core.property_relations ("
                    "workspace_id, from_node_id, to_node_id, relation_type, direction, "
                    "source_id, source_type, source_environment, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'property_address', 'directed', "
                    "'vnext-test', 'test', 'test', %s)",
                    (
                        WORKSPACE_A,
                        nodes["property_a"],
                        nodes["address_b"],
                        USERS["member"],
                    ),
                )

        with context.transaction(_principal(USERS["revoked"])) as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext_core.evidence_items WHERE workspace_id = %s",
                (WORKSPACE_A,),
            ).fetchone()[0] == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["revoked"])) as connection:
                connection.execute(
                    "INSERT INTO vnext_core.property_entities ("
                    "workspace_id, display_label, created_by_user_id"
                    ") VALUES (%s, 'Revoked denied', %s)",
                    (WORKSPACE_A, USERS["revoked"]),
                )

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["owner"])) as connection:
                connection.execute(
                    "UPDATE vnext_core.evidence_items SET evidence_status = 'stale' "
                    "WHERE evidence_id = %s",
                    (EVIDENCE_AVAILABLE,),
                )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with context.transaction(_principal(USERS["owner"])) as connection:
                connection.execute(
                    "DELETE FROM vnext_core.evidence_items WHERE evidence_id = %s",
                    (EVIDENCE_AVAILABLE,),
                )
