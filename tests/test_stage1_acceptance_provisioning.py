"""Offline safety contract for Stage 1 production acceptance provisioning."""

from __future__ import annotations

import importlib
import re
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from scripts.migration_registry import load_registry


ROOT = Path(__file__).resolve().parents[1]
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("22222222-2222-4222-8222-222222222222")
PROPERTY_ID = UUID("33333333-3333-4333-8333-333333333333")
NODE_ID = UUID("44444444-4444-4444-8444-444444444444")
NOW = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def provision():
    return importlib.import_module("scripts.provision_stage1_acceptance")


def config(p):
    return p.AcceptanceConfig(USER_ID, WORKSPACE_ID, PROPERTY_ID)


def prerequisites(p, **changes):
    base = p.PrerequisiteSnapshot(
        migrations=dict(p.REQUIRED_MIGRATIONS),
        terminal_migration_id=p.REQUIRED_MIGRATIONS[-1][0],
        tables=frozenset(p.REQUIRED_TABLES),
        graph_trigger_enabled=True,
        operator_role="postgres",
        operator_bypasses_rls=True,
        operator_privileges=True,
        request_role_safe=True,
        request_rls_safe=True,
    )
    return replace(base, **changes)


def empty_snapshot(p, **changes):
    counts = {table: 0 for table in p.ATTACHED_TABLES}
    base = p.BundleSnapshot(
        auth_user_exists=True,
        workspace=None,
        workspace_marker_ids=(),
        memberships=(),
        property=None,
        workspace_properties=(),
        property_marker_ids=(),
        graph_nodes=(),
        attached_counts=counts,
    )
    return replace(base, **changes)


def active_snapshot(p, **changes):
    cfg = config(p)
    workspace = p.WorkspaceRow(
        WORKSPACE_ID,
        "team",
        p.WORKSPACE_LABEL,
        "active",
        1,
        USER_ID,
        None,
        None,
    )
    membership = p.MembershipRow(
        cfg.membership_id,
        WORKSPACE_ID,
        USER_ID,
        "viewer",
        "active",
        NOW,
        None,
        None,
    )
    property_row = p.PropertyRow(
        PROPERTY_ID,
        WORKSPACE_ID,
        "unverified",
        p.PROPERTY_LABEL,
        1,
        USER_ID,
        None,
    )
    node = p.GraphNodeRow(NODE_ID, WORKSPACE_ID, "property", PROPERTY_ID, USER_ID)
    counts = {table: 0 for table in p.ATTACHED_TABLES}
    counts.update(
        {
            "vnext_core.workspace_members": 1,
            "vnext_core.property_entities": 1,
            "vnext_core.property_graph_nodes": 1,
        }
    )
    base = p.BundleSnapshot(
        auth_user_exists=True,
        workspace=workspace,
        workspace_marker_ids=(WORKSPACE_ID,),
        memberships=(membership,),
        property=property_row,
        workspace_properties=(property_row,),
        property_marker_ids=(PROPERTY_ID,),
        graph_nodes=(node,),
        attached_counts=counts,
    )
    return replace(base, **changes)


def archived_snapshot(p, **changes):
    snapshot = active_snapshot(p)
    workspace = replace(snapshot.workspace, status="archived", archived_at=NOW)
    membership = replace(snapshot.memberships[0], status="removed", revoked_at=NOW)
    property_row = replace(snapshot.property, entity_status="archived", archived_at=NOW)
    base = replace(
        snapshot,
        workspace=workspace,
        memberships=(membership,),
        property=property_row,
        workspace_properties=(property_row,),
    )
    return replace(base, **changes)


class MemoryStore:
    def __init__(self, p, snapshot, *, prerequisite_snapshot=None):
        self.p = p
        self.current = snapshot
        self.prerequisite_snapshot = prerequisite_snapshot or prerequisites(p)
        self.transactions: list[bool] = []
        self.lock_count = 0
        self.mutations: list[str] = []
        self.raise_after_mutation = False

    @contextmanager
    def transaction(self, *, read_only: bool):
        original = self.current
        self.transactions.append(read_only)
        try:
            yield
        except Exception:
            self.current = original
            raise

    def acquire_lock(self) -> None:
        self.lock_count += 1

    def inspect_prerequisites(self):
        return self.prerequisite_snapshot

    def inspect_bundle(self, _config, *, lock_rows: bool):
        return self.current

    def provision(self, cfg) -> None:
        self.mutations.append("provision")
        self.current = active_snapshot(self.p)
        if self.raise_after_mutation:
            raise RuntimeError("private database detail")

    def archive(self, cfg) -> None:
        self.mutations.append("archive")
        self.current = archived_snapshot(self.p)
        if self.raise_after_mutation:
            raise RuntimeError("private database detail")

    def reactivate(self, cfg) -> None:
        self.mutations.append("reactivate")
        archived_node = self.current.graph_nodes[0].property_graph_node_id
        self.current = active_snapshot(self.p)
        assert self.current.graph_nodes[0].property_graph_node_id == archived_node
        if self.raise_after_mutation:
            raise RuntimeError("private database detail")


class RecordingCursor:
    rowcount = 1


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, object]] = []

    def execute(self, statement: str, parameters=None):
        self.statements.append((statement, parameters))
        return RecordingCursor()

    @contextmanager
    def transaction(self):
        yield


def test_required_migration_checksums_match_the_immutable_registry(provision) -> None:
    registry = {item.path.stem: item.sha256 for item in load_registry()}

    assert dict(provision.REQUIRED_MIGRATIONS) == {
        name: registry[name] for name, _checksum in provision.REQUIRED_MIGRATIONS
    }


def test_required_rls_policy_names_match_all_vnext_migrations(provision) -> None:
    migrations = [
        ROOT / "database" / "migrations" / f"{name}.sql"
        for name, _checksum in provision.REQUIRED_MIGRATIONS
    ]
    policy_names = {
        match.group(1)
        for migration in migrations
        for match in re.finditer(
            r"^create policy ([a-z0-9_]+)$",
            migration.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    }

    assert set(provision.EXPECTED_POLICY_COMMANDS) == policy_names


def _policy_catalog_rows(provision):
    return [
        (
            expected.schema,
            expected.table,
            expected.name,
            "PERMISSIVE",
            ["vnext_api"],
            expected.command,
            expected.qual,
            expected.with_check,
        )
        for expected in provision._expected_policy_specs().values()
    ]


def _owned_rls_rows(provision, *, owner="postgres"):
    return [(table, True, True, owner) for table in sorted(provision.REQUIRED_TABLES)]


def test_policy_preflight_keys_binding_predicates_and_non_api_ownership(
    provision,
) -> None:
    policy_rows = _policy_catalog_rows(provision)
    relation_rows = _owned_rls_rows(provision)

    assert provision._policy_catalog_is_safe(policy_rows, relation_rows) is True

    broadened = list(policy_rows)
    target = next(
        index
        for index, row in enumerate(broadened)
        if row[2] == "property_entities_active_writer_insert"
    )
    broadened[target] = (*broadened[target][:7], "true")
    assert provision._policy_catalog_is_safe(broadened, relation_rows) is False

    rebound = list(policy_rows)
    rebound[target] = ("vnext_core", "cases", *rebound[target][2:])
    assert provision._policy_catalog_is_safe(rebound, relation_rows) is False

    api_owned = list(relation_rows)
    api_owned[0] = (*api_owned[0][:3], "vnext_api")
    assert provision._policy_catalog_is_safe(policy_rows, api_owned) is False


def test_policy_preflight_rejects_case_sensitive_literal_drift(provision) -> None:
    policy_rows = _policy_catalog_rows(provision)
    target = next(
        index
        for index, row in enumerate(policy_rows)
        if row[2] == "workspaces_active_member_select"
    )
    row = policy_rows[target]
    policy_rows[target] = (
        *row[:6],
        row[6].replace("'active'", "'ACTIVE'"),
        row[7],
    )

    assert provision._policy_catalog_is_safe(
        policy_rows,
        _owned_rls_rows(provision),
    ) is False


def test_policy_predicate_signature_normalizes_postgres_deparser_noise(
    provision,
) -> None:
    migration_expression = (
        "member.user_id = (select auth.uid()) "
        "and member.role in ('owner', 'admin', 'manager', 'member')"
    )
    catalog_expression = (
        "((member.user_id = ( SELECT auth.uid() AS uid)) AND "
        "(member.role = ANY (ARRAY['owner'::text, 'admin'::text, "
        "'manager'::text, 'member'::text])))"
    )

    assert provision._policy_predicate_signature(
        migration_expression
    ) == provision._policy_predicate_signature(catalog_expression)


def test_policy_preflight_query_reads_predicates_binding_and_owner(provision) -> None:
    source = (ROOT / "scripts" / "provision_stage1_acceptance.py").read_text(
        encoding="utf-8"
    )

    assert "schemaname, tablename, policyname" in source
    assert "qual, with_check" in source
    assert "owner.rolname" in source


def test_postgres_dry_run_transaction_is_explicitly_read_only(provision) -> None:
    connection = RecordingConnection()
    store = provision.PostgresAcceptanceStore(connection)

    with store.transaction(read_only=True):
        pass

    assert [statement for statement, _parameters in connection.statements] == [
        "SET TRANSACTION READ ONLY"
    ]


def test_postgres_provision_relies_on_trigger_for_the_only_graph_node(
    provision,
) -> None:
    connection = RecordingConnection()
    store = provision.PostgresAcceptanceStore(connection)

    store.provision(config(provision))

    statements = [statement for statement, _parameters in connection.statements]
    assert len(statements) == 3
    assert statements[0].startswith("INSERT INTO vnext_core.workspaces")
    assert statements[1].startswith("INSERT INTO vnext_core.workspace_members")
    assert statements[2].startswith("INSERT INTO vnext_core.property_entities")
    assert all("property_graph_nodes" not in statement for statement in statements)


def test_default_operation_is_read_only_and_dry_run(provision) -> None:
    store = MemoryStore(provision, empty_snapshot(provision))

    result = provision.execute(store, config(provision), mode="dry_run")

    assert result == {
        "status": "ready",
        "mode": "dry_run",
        "bundle_state": "empty",
        "next_action": "provision",
    }
    assert store.transactions == [True]
    assert store.lock_count == 0
    assert store.mutations == []


def test_missing_auth_user_fails_closed_without_mutation(provision) -> None:
    store = MemoryStore(
        provision,
        empty_snapshot(provision, auth_user_exists=False),
    )

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": "auth_user_missing"}
    assert store.lock_count == 1
    assert store.mutations == []


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"graph_trigger_enabled": False}, "graph_trigger_missing"),
        ({"terminal_migration_id": "018_unreviewed"}, "migration_state_invalid"),
        ({"tables": frozenset()}, "schema_objects_missing"),
        ({"operator_privileges": False}, "operator_privileges_missing"),
        ({"operator_bypasses_rls": False}, "operator_rls_bypass_required"),
        ({"operator_role": "vnext_api"}, "operator_role_invalid"),
        ({"request_role_safe": False}, "request_role_unsafe"),
        ({"request_rls_safe": False}, "request_rls_unsafe"),
    ],
)
def test_schema_trigger_and_privilege_drift_refuses_before_mutation(
    provision, change, reason
) -> None:
    store = MemoryStore(
        provision,
        empty_snapshot(provision),
        prerequisite_snapshot=prerequisites(provision, **change),
    )

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": reason}
    assert store.mutations == []


def test_conflicting_workspace_uuid_refuses(provision) -> None:
    conflict = replace(
        active_snapshot(provision).workspace,
        display_name="Real customer workspace",
    )
    store = MemoryStore(
        provision,
        empty_snapshot(provision, workspace=conflict),
    )

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": "workspace_conflict"}
    assert store.mutations == []


def test_conflicting_property_uuid_refuses(provision) -> None:
    conflict = replace(
        active_snapshot(provision).property,
        workspace_id=UUID("99999999-9999-4999-8999-999999999999"),
        display_label="Unrelated property",
    )
    store = MemoryStore(
        provision,
        empty_snapshot(provision, property=conflict),
    )

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": "property_conflict"}
    assert store.mutations == []


def test_marker_collision_refuses(provision) -> None:
    other_workspace = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    store = MemoryStore(
        provision,
        empty_snapshot(provision, workspace_marker_ids=(other_workspace,)),
    )

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": "acceptance_marker_collision"}
    assert store.mutations == []


def test_conflicting_membership_refuses(provision) -> None:
    membership = replace(
        active_snapshot(provision).memberships[0],
        role="owner",
    )
    store = MemoryStore(
        provision,
        empty_snapshot(provision, memberships=(membership,)),
    )

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": "bundle_drift"}
    assert store.mutations == []


def test_exact_active_bundle_is_idempotent_and_has_one_graph_node(provision) -> None:
    store = MemoryStore(provision, active_snapshot(provision))

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {
        "status": "pass",
        "mode": "provision",
        "bundle_state": "active",
        "action": "none",
    }
    assert store.mutations == []
    assert len(store.current.graph_nodes) == 1
    assert store.current.graph_nodes[0].record_id == PROPERTY_ID


def test_empty_bundle_provisions_once_under_one_locked_transaction(provision) -> None:
    store = MemoryStore(provision, empty_snapshot(provision))

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {
        "status": "pass",
        "mode": "provision",
        "bundle_state": "active",
        "action": "provisioned",
    }
    assert store.transactions == [False]
    assert store.lock_count == 1
    assert store.mutations == ["provision"]
    assert len(store.current.graph_nodes) == 1


def test_archive_changes_only_the_exact_bundle_with_coherent_timestamps(
    provision,
) -> None:
    store = MemoryStore(provision, active_snapshot(provision))

    result = provision.execute(store, config(provision), mode="archive")

    assert result["status"] == "pass"
    assert result["action"] == "archived"
    assert store.mutations == ["archive"]
    assert store.transactions == [False]
    assert store.lock_count == 1
    assert provision.classify_bundle(config(provision), store.current) == "archived"
    assert store.current.memberships[0].revoked_at is not None
    assert store.current.memberships[0].left_at is None
    assert store.current.property.archived_at is not None
    assert store.current.workspace.archived_at is not None


def test_exact_archived_bundle_reactivates_without_second_graph_node(provision) -> None:
    store = MemoryStore(provision, archived_snapshot(provision))

    result = provision.execute(store, config(provision), mode="provision")

    assert result["status"] == "pass"
    assert result["action"] == "reactivated"
    assert store.mutations == ["reactivate"]
    assert store.transactions == [False]
    assert store.lock_count == 1
    assert provision.classify_bundle(config(provision), store.current) == "active"
    assert len(store.current.graph_nodes) == 1
    assert store.current.graph_nodes[0].property_graph_node_id == NODE_ID


def test_exact_archived_bundle_is_idempotent_for_archive(provision) -> None:
    store = MemoryStore(provision, archived_snapshot(provision))

    result = provision.execute(store, config(provision), mode="archive")

    assert result == {
        "status": "pass",
        "mode": "archive",
        "bundle_state": "archived",
        "action": "none",
    }
    assert store.transactions == [False]
    assert store.lock_count == 1
    assert store.mutations == []


def test_reactivation_refuses_any_attached_row_or_identity_drift(provision) -> None:
    drifted_counts = dict(archived_snapshot(provision).attached_counts)
    drifted_counts["vnext_core.cases"] = 1
    drifted = archived_snapshot(provision, attached_counts=drifted_counts)
    store = MemoryStore(provision, drifted)

    result = provision.execute(store, config(provision), mode="provision")

    assert result == {"status": "refused", "reason": "unexpected_attached_rows"}
    assert store.mutations == []


@pytest.mark.parametrize(
    "drift",
    [
        lambda p, s: replace(
            s, workspace=replace(s.workspace, workspace_type="personal")
        ),
        lambda p, s: replace(
            s, workspace=replace(s.workspace, created_by_user_id=UUID(int=9))
        ),
        lambda p, s: replace(
            s, memberships=(replace(s.memberships[0], role="member"),)
        ),
        lambda p, s: replace(
            s, property=replace(s.property, created_by_user_id=UUID(int=8))
        ),
        lambda p, s: replace(
            s, graph_nodes=(replace(s.graph_nodes[0], record_id=UUID(int=7)),)
        ),
    ],
)
def test_reactivation_refuses_exact_bundle_drift(provision, drift) -> None:
    store = MemoryStore(provision, drift(provision, archived_snapshot(provision)))

    result = provision.execute(store, config(provision), mode="provision")

    assert result["status"] == "refused"
    assert store.mutations == []


def test_mutation_failure_rolls_back_the_whole_operation(provision) -> None:
    original = active_snapshot(provision)
    store = MemoryStore(provision, original)
    store.raise_after_mutation = True

    result = provision.execute(store, config(provision), mode="archive")

    assert result == {
        "status": "unavailable",
        "reason": "database_operation_unavailable",
    }
    assert provision.classify_bundle(config(provision), store.current) == "active"


def test_database_credential_is_environment_only_and_never_rendered(
    provision, capsys
) -> None:
    secret = (
        "postgresql://operator:super-secret@example.invalid/postgres"
        "?sslmode=verify-full"
    )

    def failing_connection_factory(value: str):
        raise RuntimeError(f"could not connect to {value}")

    code = provision.main(
        [
            "--auth-user-id",
            str(USER_ID),
            "--workspace-id",
            str(WORKSPACE_ID),
            "--property-id",
            str(PROPERTY_ID),
        ],
        environ={provision.DATABASE_URL_ENV: secret},
        connection_factory=failing_connection_factory,
    )

    output = capsys.readouterr()
    assert code == 1
    assert secret not in output.out + output.err
    assert "super-secret" not in output.out + output.err
    assert "database_operation_unavailable" in output.out


@pytest.mark.parametrize(
    "credential",
    [
        "eyJhbGciOiJIUzI1NiJ9.payload.signature",
        "sb_publishable_example",
        "sb_secret_example",
        "anon-key",
        "https://project.supabase.co",
        "postgresql://service_role:secret@db.example.test/postgres",
        "postgresql://operator:secret@db.example.test/postgres",
        "postgresql://operator:secret@db.example.test/postgres?sslmode=disable",
    ],
)
def test_non_operator_database_credentials_are_refused(provision, credential) -> None:
    with pytest.raises(provision.SafeProvisioningFailure) as error:
        provision.validate_operator_database_url(credential)
    assert error.value.reason == "operator_database_url_invalid"


@pytest.mark.parametrize(
    "credential",
    [
        "postgresql://operator:secret@db.example.test/postgres?sslmode=verify-full",
        "postgresql://operator:secret@localhost/postgres",
        "postgresql://operator:secret@127.0.0.1/postgres",
    ],
)
def test_operator_database_credentials_require_verified_remote_tls(
    provision, credential
) -> None:
    assert provision.validate_operator_database_url(credential) == credential


def test_effective_remote_host_override_requires_verified_tls(provision) -> None:
    credential = (
        "postgresql://operator:secret@localhost/postgres?host=db.example.test"
    )

    with pytest.raises(provision.SafeProvisioningFailure) as error:
        provision.validate_operator_database_url(credential)

    assert error.value.reason == "operator_database_url_invalid"


def test_run_pins_verified_tls_against_ambient_override(
    provision, monkeypatch
) -> None:
    credential = (
        "postgresql://operator:secret@db.example.test/postgres?sslmode=verify-full"
    )
    calls = []

    @contextmanager
    def recording_connect(value, **kwargs):
        calls.append((value, kwargs))
        raise RuntimeError("stop before network")
        yield

    monkeypatch.setattr(provision, "connect", recording_connect)
    monkeypatch.setenv("POSTGRES_SSLMODE", "disable")

    assert provision.run(credential, config(provision), mode="dry_run") == {
        "status": "unavailable",
        "reason": "database_operation_unavailable",
    }
    assert calls == [
        (
            credential,
            {"connection_factory": None, "sslmode": "verify-full"},
        )
    ]


def test_provisioning_implementation_contains_no_destructive_sql(provision) -> None:
    source = (
        (ROOT / "scripts" / "provision_stage1_acceptance.py")
        .read_text(encoding="utf-8")
        .upper()
    )
    assert "DELETE" not in source
    assert "TRUNCATE" not in source
    assert "CASCADE" not in source


def test_cli_has_explicit_modes_and_no_generic_force(provision) -> None:
    parser = provision.build_parser()
    option_strings = {
        option for action in parser._actions for option in action.option_strings
    }
    assert {"--apply-provision", "--apply-archive"} <= option_strings
    assert "--force" not in option_strings
