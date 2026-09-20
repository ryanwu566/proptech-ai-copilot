"""Provision or archive one tightly bounded Stage 1 acceptance bundle.

The default mode is a database read-only inspection. Mutating modes require
explicit command-line switches and an operator PostgreSQL URL supplied through
one server-only environment variable. Output is deliberately allowlisted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid5


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_runtime import connect


DATABASE_URL_ENV = "STAGE1_ACCEPTANCE_DATABASE_URL"
MARKER = "[PROD ACCEPTANCE TEST]"
WORKSPACE_LABEL = f"{MARKER} Stage 1 Workspace"
PROPERTY_LABEL = f"{MARKER} Stage 1 Unverified Property"
MEMBERSHIP_NAMESPACE = UUID("e0448837-69ab-4c77-8931-f750fc27d48a")
ADVISORY_LOCK_KEY = 7_613_370_104_100_001

REQUIRED_MIGRATIONS = (
    (
        "013_vnext_workspace_case_foundation",
        "322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952",
    ),
    (
        "014_vnext_property_graph_evidence_foundation",
        "0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd",
    ),
    (
        "015_vnext_identity_resolution_candidates",
        "b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f",
    ),
    (
        "016_vnext_identity_confirmation_case_links",
        "b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636",
    ),
    (
        "017_vnext_legacy_saved_case_import",
        "0753b222597d7e0d6cbc618a17bc1d07d047a0d499318936c29880a119182efa",
    ),
)
POLICY_MIGRATION_PATHS = tuple(
    ROOT / "database" / "migrations" / f"{migration_id}.sql"
    for migration_id, _checksum in REQUIRED_MIGRATIONS
)

REQUIRED_TABLES = frozenset(
    {
        "vnext_core.workspaces",
        "vnext_core.workspace_members",
        "vnext_core.cases",
        "vnext_core.property_entities",
        "vnext_core.property_identity_references",
        "vnext_core.property_graph_nodes",
        "vnext_core.property_relations",
        "vnext_core.evidence_items",
        "vnext_core.evidence_lineage",
        "vnext_core.evidence_links",
        "vnext_core.identity_resolutions",
        "vnext_core.resolution_attempts",
        "vnext_core.identity_candidates",
        "vnext_core.identity_conflicts",
        "vnext_core.identity_decisions",
        "vnext_core.case_property_links",
        "vnext_private.idempotency_records",
        "vnext_private.audit_events",
        "vnext_private.legacy_case_imports",
    }
)
ATTACHED_TABLES = tuple(sorted(REQUIRED_TABLES - {"vnext_core.workspaces"}))
EXPECTED_ATTACHED_COUNTS = {
    table: (
        1
        if table
        in {
            "vnext_core.workspace_members",
            "vnext_core.property_entities",
            "vnext_core.property_graph_nodes",
        }
        else 0
    )
    for table in ATTACHED_TABLES
}

_SELECT_POLICIES = frozenset(
    {
        "workspace_members_self_select",
        "workspaces_active_member_select",
        "cases_active_member_select",
        "idempotency_actor_select",
        "property_entities_active_member_select",
        "identity_references_active_member_select",
        "property_graph_nodes_active_member_select",
        "property_relations_active_member_select",
        "evidence_items_active_member_select",
        "evidence_lineage_active_member_select",
        "evidence_links_active_member_select",
        "identity_resolutions_active_member_select",
        "resolution_attempts_active_member_select",
        "identity_candidates_active_member_select",
        "identity_conflicts_active_member_select",
        "identity_decisions_active_member_select",
        "case_property_links_active_member_select",
        "legacy_case_imports_actor_select",
    }
)
_INSERT_POLICIES = frozenset(
    {
        "cases_active_writer_insert",
        "idempotency_actor_insert",
        "audit_actor_insert",
        "property_entities_active_writer_insert",
        "identity_references_active_writer_insert",
        "property_graph_nodes_active_writer_insert",
        "property_relations_active_writer_insert",
        "evidence_items_active_writer_insert",
        "evidence_lineage_active_writer_insert",
        "evidence_links_active_writer_insert",
        "identity_resolutions_active_writer_insert",
        "resolution_attempts_active_writer_insert",
        "identity_candidates_active_writer_insert",
        "identity_conflicts_active_writer_insert",
        "identity_decisions_owner_admin_insert",
        "property_relations_human_confirmation_insert",
        "case_property_links_owner_admin_insert",
        "legacy_case_imports_actor_insert",
    }
)
_UPDATE_POLICIES = frozenset(
    {
        "cases_active_writer_update",
        "idempotency_actor_update",
    }
)
EXPECTED_POLICY_COMMANDS = {
    **{name: "SELECT" for name in _SELECT_POLICIES},
    **{name: "INSERT" for name in _INSERT_POLICIES},
    **{name: "UPDATE" for name in _UPDATE_POLICIES},
}

_POLICY_STATEMENT = re.compile(
    r"\bcreate\s+policy\s+(?P<name>[a-z0-9_]+)\s+"
    r"on\s+(?P<schema>[a-z0-9_]+)\.(?P<table>[a-z0-9_]+)\s+"
    r"for\s+(?P<command>select|insert|update)\s+to\s+vnext_api\s+"
    r"(?P<body>.*?);",
    re.IGNORECASE | re.DOTALL,
)
_POLICY_TOKEN = re.compile(
    r"'(?:''|[^'])*'|<>|<=|>=|=|[a-z_][a-z0-9_$.]*|\d+(?:\.\d+)?",
    re.IGNORECASE,
)


class SafeProvisioningFailure(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ExpectedPolicy:
    schema: str
    table: str
    name: str
    command: str
    qual: str | None
    with_check: str | None


def _parenthesized_clause(body: str, keyword: str) -> str | None:
    match = re.search(rf"\b{keyword}\s*\(", body, re.IGNORECASE)
    if match is None:
        return None
    opening = body.find("(", match.start())
    depth = 0
    quoted = False
    index = opening
    while index < len(body):
        character = body[index]
        if character == "'":
            if quoted and index + 1 < len(body) and body[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
        elif not quoted:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    return body[opening + 1 : index]
        index += 1
    raise RuntimeError("trusted_policy_contract_invalid")


def _policy_predicate_signature(expression: str | None) -> tuple[str, ...] | None:
    if expression is None:
        return None
    normalized = expression
    normalized = re.sub(
        r"auth\.uid\(\)\s+as\s+uid(?:_\d+)?",
        "auth.uid()",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"::\s*(?:pg_catalog\.)?[a-z_][a-z0-9_.]*(?:\[\])?",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    tokens = [
        token if token.startswith("'") else token.lower()
        for token in _POLICY_TOKEN.findall(normalized)
    ]
    canonical: list[str] = []
    index = 0
    while index < len(tokens):
        window = tokens[index : index + 3]
        if window == ["=", "any", "array"]:
            canonical.append("in")
            index += 3
            continue
        if window == ["<>", "all", "array"]:
            canonical.extend(("not", "in"))
            index += 3
            continue
        canonical.append(tokens[index])
        index += 1
    return tuple(canonical)


@lru_cache(maxsize=1)
def _expected_policy_specs() -> Mapping[tuple[str, str, str], ExpectedPolicy]:
    expected: dict[tuple[str, str, str], ExpectedPolicy] = {}
    for path in POLICY_MIGRATION_PATHS:
        source = path.read_text(encoding="utf-8")
        for match in _POLICY_STATEMENT.finditer(source):
            name = match.group("name").lower()
            policy = ExpectedPolicy(
                schema=match.group("schema").lower(),
                table=match.group("table").lower(),
                name=name,
                command=match.group("command").upper(),
                qual=_parenthesized_clause(match.group("body"), "using"),
                with_check=_parenthesized_clause(match.group("body"), r"with\s+check"),
            )
            key = (policy.schema, policy.table, policy.name)
            if key in expected:
                raise RuntimeError("trusted_policy_contract_invalid")
            expected[key] = policy

    if {
        policy.name: policy.command for policy in expected.values()
    } != EXPECTED_POLICY_COMMANDS or any(
        (policy.command == "SELECT" and policy.qual is None)
        or (policy.command == "INSERT" and policy.with_check is None)
        or (
            policy.command == "UPDATE"
            and (policy.qual is None or policy.with_check is None)
        )
        for policy in expected.values()
    ):
        raise RuntimeError("trusted_policy_contract_invalid")
    return expected


def _policy_catalog_is_safe(
    policy_rows: list[tuple[object, ...]],
    relation_rows: list[tuple[object, ...]],
) -> bool:
    relations = {
        str(row[0]): (bool(row[1]), bool(row[2]), str(row[3])) for row in relation_rows
    }
    if set(relations) != REQUIRED_TABLES or any(
        not rls_enabled or not rls_forced or owner == "vnext_api"
        for rls_enabled, rls_forced, owner in relations.values()
    ):
        return False

    expected = _expected_policy_specs()
    actual = {(str(row[0]), str(row[1]), str(row[2])): row for row in policy_rows}
    if len(actual) != len(policy_rows) or set(actual) != set(expected):
        return False

    for key, policy in expected.items():
        row = actual[key]
        if (
            str(row[3]).upper() != "PERMISSIVE"
            or {str(role) for role in row[4]} != {"vnext_api"}
            or str(row[5]).upper() != policy.command
            or _policy_predicate_signature(row[6])
            != _policy_predicate_signature(policy.qual)
            or _policy_predicate_signature(row[7])
            != _policy_predicate_signature(policy.with_check)
        ):
            return False
    return True


@dataclass(frozen=True)
class AcceptanceConfig:
    auth_user_id: UUID
    workspace_id: UUID
    property_id: UUID

    def __post_init__(self) -> None:
        if len({self.auth_user_id, self.workspace_id, self.property_id}) != 3:
            raise SafeProvisioningFailure("acceptance_uuid_conflict")

    @property
    def membership_id(self) -> UUID:
        value = f"{self.workspace_id}:{self.auth_user_id}:viewer"
        return uuid5(MEMBERSHIP_NAMESPACE, value)


@dataclass(frozen=True)
class PrerequisiteSnapshot:
    migrations: Mapping[str, str]
    terminal_migration_id: str | None
    tables: frozenset[str]
    graph_trigger_enabled: bool
    operator_role: str
    operator_bypasses_rls: bool
    operator_privileges: bool
    request_role_safe: bool
    request_rls_safe: bool


@dataclass(frozen=True)
class WorkspaceRow:
    workspace_id: UUID
    workspace_type: str
    display_name: str
    status: str
    version: int
    created_by_user_id: UUID
    personal_owner_user_id: UUID | None
    archived_at: datetime | None


@dataclass(frozen=True)
class MembershipRow:
    workspace_member_id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    status: str
    joined_at: datetime | None
    left_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class PropertyRow:
    property_entity_id: UUID
    workspace_id: UUID
    entity_status: str
    display_label: str
    version: int
    created_by_user_id: UUID
    archived_at: datetime | None


@dataclass(frozen=True)
class GraphNodeRow:
    property_graph_node_id: UUID
    workspace_id: UUID
    node_type: str
    record_id: UUID
    created_by_user_id: UUID


@dataclass(frozen=True)
class BundleSnapshot:
    auth_user_exists: bool
    workspace: WorkspaceRow | None
    workspace_marker_ids: tuple[UUID, ...]
    memberships: tuple[MembershipRow, ...]
    property: PropertyRow | None
    workspace_properties: tuple[PropertyRow, ...]
    property_marker_ids: tuple[UUID, ...]
    graph_nodes: tuple[GraphNodeRow, ...]
    attached_counts: Mapping[str, int]


def validate_prerequisites(snapshot: PrerequisiteSnapshot) -> None:
    expected_migrations = dict(REQUIRED_MIGRATIONS)
    if snapshot.terminal_migration_id != REQUIRED_MIGRATIONS[-1][0] or any(
        snapshot.migrations.get(key) != value
        for key, value in expected_migrations.items()
    ):
        raise SafeProvisioningFailure("migration_state_invalid")
    if not REQUIRED_TABLES.issubset(snapshot.tables):
        raise SafeProvisioningFailure("schema_objects_missing")
    if not snapshot.graph_trigger_enabled:
        raise SafeProvisioningFailure("graph_trigger_missing")
    if snapshot.operator_role in {"vnext_api", "anon", "authenticated", "service_role"}:
        raise SafeProvisioningFailure("operator_role_invalid")
    if not snapshot.operator_bypasses_rls:
        raise SafeProvisioningFailure("operator_rls_bypass_required")
    if not snapshot.operator_privileges:
        raise SafeProvisioningFailure("operator_privileges_missing")
    if not snapshot.request_role_safe:
        raise SafeProvisioningFailure("request_role_unsafe")
    if not snapshot.request_rls_safe:
        raise SafeProvisioningFailure("request_rls_unsafe")


def _workspace_identity_matches(config: AcceptanceConfig, row: WorkspaceRow) -> bool:
    return (
        row.workspace_id == config.workspace_id
        and row.workspace_type == "team"
        and row.display_name == WORKSPACE_LABEL
        and row.version == 1
        and row.created_by_user_id == config.auth_user_id
        and row.personal_owner_user_id is None
    )


def _property_identity_matches(config: AcceptanceConfig, row: PropertyRow) -> bool:
    return (
        row.property_entity_id == config.property_id
        and row.workspace_id == config.workspace_id
        and row.display_label == PROPERTY_LABEL
        and row.version == 1
        and row.created_by_user_id == config.auth_user_id
    )


def _all_counts_are_zero(snapshot: BundleSnapshot) -> bool:
    return all(snapshot.attached_counts.get(table, 0) == 0 for table in ATTACHED_TABLES)


def classify_bundle(config: AcceptanceConfig, snapshot: BundleSnapshot) -> str:
    if not snapshot.auth_user_exists:
        raise SafeProvisioningFailure("auth_user_missing")

    if (
        set(snapshot.workspace_marker_ids) - {config.workspace_id}
        or set(snapshot.property_marker_ids) - {config.property_id}
        or len(snapshot.workspace_marker_ids) > 1
        or len(snapshot.property_marker_ids) > 1
    ):
        raise SafeProvisioningFailure("acceptance_marker_collision")

    if snapshot.workspace is not None and not _workspace_identity_matches(
        config, snapshot.workspace
    ):
        raise SafeProvisioningFailure("workspace_conflict")
    if snapshot.property is not None and not _property_identity_matches(
        config, snapshot.property
    ):
        raise SafeProvisioningFailure("property_conflict")

    if snapshot.workspace is None:
        if (
            snapshot.property is not None
            or snapshot.memberships
            or snapshot.workspace_properties
            or snapshot.graph_nodes
            or not _all_counts_are_zero(snapshot)
            or snapshot.workspace_marker_ids
            or snapshot.property_marker_ids
        ):
            raise SafeProvisioningFailure("bundle_drift")
        return "empty"

    if snapshot.property is None:
        raise SafeProvisioningFailure("bundle_drift")
    if snapshot.workspace_marker_ids != (config.workspace_id,):
        raise SafeProvisioningFailure("bundle_drift")
    if snapshot.property_marker_ids != (config.property_id,):
        raise SafeProvisioningFailure("bundle_drift")
    if len(snapshot.memberships) != 1:
        raise SafeProvisioningFailure("bundle_drift")
    membership = snapshot.memberships[0]
    if (
        membership.workspace_member_id != config.membership_id
        or membership.workspace_id != config.workspace_id
        or membership.user_id != config.auth_user_id
        or membership.role != "viewer"
    ):
        raise SafeProvisioningFailure("bundle_drift")
    if snapshot.workspace_properties != (snapshot.property,):
        raise SafeProvisioningFailure("bundle_drift")
    if dict(snapshot.attached_counts) != EXPECTED_ATTACHED_COUNTS:
        raise SafeProvisioningFailure("unexpected_attached_rows")
    if len(snapshot.graph_nodes) != 1:
        raise SafeProvisioningFailure("graph_node_count_invalid")
    node = snapshot.graph_nodes[0]
    if (
        node.workspace_id != config.workspace_id
        or node.node_type != "property"
        or node.record_id != config.property_id
        or node.created_by_user_id != config.auth_user_id
    ):
        raise SafeProvisioningFailure("bundle_drift")

    active = (
        snapshot.workspace.status == "active"
        and snapshot.workspace.archived_at is None
        and membership.status == "active"
        and membership.joined_at is not None
        and membership.left_at is None
        and membership.revoked_at is None
        and snapshot.property.entity_status == "unverified"
        and snapshot.property.archived_at is None
    )
    if active:
        return "active"

    archived = (
        snapshot.workspace.status == "archived"
        and snapshot.workspace.archived_at is not None
        and membership.status == "removed"
        and membership.joined_at is not None
        and membership.left_at is None
        and membership.revoked_at is not None
        and snapshot.property.entity_status == "archived"
        and snapshot.property.archived_at is not None
    )
    if archived:
        return "archived"
    raise SafeProvisioningFailure("bundle_drift")


def _dry_run_result(state: str) -> dict[str, str]:
    return {
        "status": "ready",
        "mode": "dry_run",
        "bundle_state": state,
        "next_action": {
            "empty": "provision",
            "active": "none",
            "archived": "reactivate",
        }[state],
    }


def execute(store: Any, config: AcceptanceConfig, *, mode: str) -> dict[str, str]:
    if mode not in {"dry_run", "provision", "archive"}:
        return {"status": "refused", "reason": "operation_invalid"}
    try:
        with store.transaction(read_only=mode == "dry_run"):
            if mode != "dry_run":
                store.acquire_lock()
            validate_prerequisites(store.inspect_prerequisites())
            before = store.inspect_bundle(config, lock_rows=mode != "dry_run")
            state = classify_bundle(config, before)
            if mode == "dry_run":
                return _dry_run_result(state)

            action = "none"
            expected_state = state
            if mode == "provision":
                expected_state = "active"
                if state == "empty":
                    store.provision(config)
                    action = "provisioned"
                elif state == "archived":
                    store.reactivate(config)
                    action = "reactivated"
            else:
                if state == "empty":
                    raise SafeProvisioningFailure("bundle_missing")
                expected_state = "archived"
                if state == "active":
                    store.archive(config)
                    action = "archived"

            after = store.inspect_bundle(config, lock_rows=True)
            actual_state = classify_bundle(config, after)
            if actual_state != expected_state:
                raise SafeProvisioningFailure("postcondition_failed")
            return {
                "status": "pass",
                "mode": mode,
                "bundle_state": actual_state,
                "action": action,
            }
    except SafeProvisioningFailure as error:
        return {"status": "refused", "reason": error.reason}
    except Exception:
        return {"status": "unavailable", "reason": "database_operation_unavailable"}


def _uuid(value: object) -> UUID:
    return UUID(str(value))


class PostgresAcceptanceStore:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, *, read_only: bool):
        with self.connection.transaction():
            if read_only:
                self.connection.execute("SET TRANSACTION READ ONLY")
            yield

    def acquire_lock(self) -> None:
        self.connection.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (ADVISORY_LOCK_KEY,),
        )

    def inspect_prerequisites(self) -> PrerequisiteSnapshot:
        migration_rows = self.connection.execute(
            "SELECT migration_id, checksum FROM public.schema_migration_ledger "
            "WHERE migration_id = ANY(%s)",
            ([name for name, _checksum in REQUIRED_MIGRATIONS],),
        ).fetchall()
        migrations = {str(row[0]): str(row[1]) for row in migration_rows}
        terminal_migration = self.connection.execute(
            "SELECT migration_id FROM public.schema_migration_ledger "
            "WHERE migration_id ~ '^[0-9]{3}_' "
            "ORDER BY substring(migration_id FROM 1 FOR 3)::integer DESC, "
            "applied_at DESC LIMIT 1"
        ).fetchone()
        table_rows = self.connection.execute(
            "SELECT name, to_regclass(name) FROM unnest(%s::text[]) AS item(name)",
            (list(REQUIRED_TABLES),),
        ).fetchall()
        tables = frozenset(str(row[0]) for row in table_rows if row[1] is not None)
        trigger = self.connection.execute(
            "SELECT trigger.tgenabled, pg_get_triggerdef(trigger.oid) "
            "FROM pg_trigger trigger "
            "JOIN pg_class relation ON relation.oid = trigger.tgrelid "
            "JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace "
            "WHERE namespace.nspname = 'vnext_core' "
            "AND relation.relname = 'property_entities' "
            "AND trigger.tgname = 'trg_vnext_property_entities_graph_node' "
            "AND NOT trigger.tgisinternal"
        ).fetchone()
        trigger_definition = "" if trigger is None else str(trigger[1]).upper()
        graph_trigger_enabled = bool(
            trigger
            and str(trigger[0]) in {"O", "A"}
            and "AFTER INSERT" in trigger_definition
            and "FOR EACH ROW" in trigger_definition
            and "EXECUTE FUNCTION VNEXT_PRIVATE.APPEND_PROPERTY_GRAPH_NODE()"
            in trigger_definition
        )
        operator = self.connection.execute(
            "SELECT role.rolname, role.rolsuper, role.rolbypassrls "
            "FROM pg_roles role WHERE role.rolname = current_user"
        ).fetchone()
        if operator is None:
            operator_role, operator_bypasses = "", False
        else:
            operator_role = str(operator[0])
            operator_bypasses = bool(operator[1]) or bool(operator[2])
        privilege_checks = [
            "has_schema_privilege(current_user, 'auth', 'USAGE')",
            "has_schema_privilege(current_user, 'vnext_core', 'USAGE')",
            "has_schema_privilege(current_user, 'vnext_private', 'USAGE')",
            "has_table_privilege(current_user, 'auth.users', 'SELECT')",
            "has_table_privilege(current_user, 'vnext_core.workspaces', 'SELECT')",
            "has_table_privilege(current_user, 'vnext_core.workspaces', 'INSERT')",
            "has_table_privilege(current_user, 'vnext_core.workspaces', 'UPDATE')",
            "has_table_privilege(current_user, 'vnext_core.workspace_members', 'SELECT')",
            "has_table_privilege(current_user, 'vnext_core.workspace_members', 'INSERT')",
            "has_table_privilege(current_user, 'vnext_core.workspace_members', 'UPDATE')",
            "has_table_privilege(current_user, 'vnext_core.property_entities', 'SELECT')",
            "has_table_privilege(current_user, 'vnext_core.property_entities', 'INSERT')",
            "has_table_privilege(current_user, 'vnext_core.property_entities', 'UPDATE')",
            "has_table_privilege(current_user, 'vnext_core.property_graph_nodes', 'INSERT')",
            *[
                f"has_table_privilege(current_user, '{table}', 'SELECT')"
                for table in ATTACHED_TABLES
            ],
        ]
        privilege_row = self.connection.execute(
            "SELECT " + " AND ".join(privilege_checks)
        ).fetchone()
        request_role = self.connection.execute(
            "SELECT role.rolsuper, role.rolinherit, role.rolcreaterole, "
            "role.rolcreatedb, role.rolcanlogin, role.rolreplication, "
            "role.rolbypassrls, NOT EXISTS ("
            "SELECT 1 FROM pg_auth_members membership WHERE membership.member = role.oid"
            ") FROM pg_roles role WHERE role.rolname = 'vnext_api'"
        ).fetchone()
        rls_rows = self.connection.execute(
            "SELECT namespace.nspname || '.' || relation.relname, "
            "relation.relrowsecurity, relation.relforcerowsecurity, owner.rolname "
            "FROM pg_class relation "
            "JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace "
            "JOIN pg_roles owner ON owner.oid = relation.relowner "
            "WHERE namespace.nspname || '.' || relation.relname = ANY(%s) "
            "AND relation.relkind = 'r'",
            (list(REQUIRED_TABLES),),
        ).fetchall()
        policy_rows = self.connection.execute(
            "SELECT schemaname, tablename, policyname, permissive, roles, cmd, "
            "qual, with_check FROM pg_policies "
            "WHERE schemaname IN ('vnext_core', 'vnext_private')"
        ).fetchall()
        return PrerequisiteSnapshot(
            migrations=migrations,
            terminal_migration_id=(
                None if terminal_migration is None else str(terminal_migration[0])
            ),
            tables=tables,
            graph_trigger_enabled=graph_trigger_enabled,
            operator_role=operator_role,
            operator_bypasses_rls=operator_bypasses,
            operator_privileges=bool(privilege_row and privilege_row[0]),
            request_role_safe=bool(
                request_role
                and tuple(bool(value) for value in request_role)
                == (False, False, False, False, True, False, False, True)
            ),
            request_rls_safe=_policy_catalog_is_safe(policy_rows, rls_rows),
        )

    def inspect_bundle(
        self,
        config: AcceptanceConfig,
        *,
        lock_rows: bool,
    ) -> BundleSnapshot:
        suffix = " FOR UPDATE" if lock_rows else ""
        auth_user_exists = self.connection.execute(
            "SELECT EXISTS (SELECT 1 FROM auth.users WHERE id = %s)",
            (config.auth_user_id,),
        ).fetchone()[0]
        workspace_row = self.connection.execute(
            "SELECT workspace_id, workspace_type, display_name, status, version, "
            "created_by_user_id, personal_owner_user_id, archived_at "
            "FROM vnext_core.workspaces WHERE workspace_id = %s" + suffix,
            (config.workspace_id,),
        ).fetchone()
        workspace = (
            None
            if workspace_row is None
            else WorkspaceRow(
                _uuid(workspace_row[0]),
                str(workspace_row[1]),
                str(workspace_row[2]),
                str(workspace_row[3]),
                int(workspace_row[4]),
                _uuid(workspace_row[5]),
                None if workspace_row[6] is None else _uuid(workspace_row[6]),
                workspace_row[7],
            )
        )
        workspace_marker_rows = self.connection.execute(
            "SELECT workspace_id FROM vnext_core.workspaces "
            "WHERE display_name LIKE %s ORDER BY workspace_id" + suffix,
            (f"{MARKER}%",),
        ).fetchall()
        membership_rows = self.connection.execute(
            "SELECT workspace_member_id, workspace_id, user_id, role, status, "
            "joined_at, left_at, revoked_at FROM vnext_core.workspace_members "
            "WHERE workspace_id = %s ORDER BY workspace_member_id" + suffix,
            (config.workspace_id,),
        ).fetchall()
        memberships = tuple(
            MembershipRow(
                _uuid(row[0]),
                _uuid(row[1]),
                _uuid(row[2]),
                str(row[3]),
                str(row[4]),
                row[5],
                row[6],
                row[7],
            )
            for row in membership_rows
        )
        property_row = self.connection.execute(
            "SELECT property_entity_id, workspace_id, entity_status, display_label, "
            "version, created_by_user_id, archived_at "
            "FROM vnext_core.property_entities WHERE property_entity_id = %s" + suffix,
            (config.property_id,),
        ).fetchone()
        property_record = (
            None
            if property_row is None
            else PropertyRow(
                _uuid(property_row[0]),
                _uuid(property_row[1]),
                str(property_row[2]),
                str(property_row[3]),
                int(property_row[4]),
                _uuid(property_row[5]),
                property_row[6],
            )
        )
        workspace_property_rows = self.connection.execute(
            "SELECT property_entity_id, workspace_id, entity_status, display_label, "
            "version, created_by_user_id, archived_at "
            "FROM vnext_core.property_entities WHERE workspace_id = %s "
            "ORDER BY property_entity_id" + suffix,
            (config.workspace_id,),
        ).fetchall()
        workspace_properties = tuple(
            PropertyRow(
                _uuid(row[0]),
                _uuid(row[1]),
                str(row[2]),
                str(row[3]),
                int(row[4]),
                _uuid(row[5]),
                row[6],
            )
            for row in workspace_property_rows
        )
        property_marker_rows = self.connection.execute(
            "SELECT property_entity_id FROM vnext_core.property_entities "
            "WHERE display_label LIKE %s ORDER BY property_entity_id" + suffix,
            (f"{MARKER}%",),
        ).fetchall()
        graph_rows = self.connection.execute(
            "SELECT property_graph_node_id, workspace_id, node_type, record_id, "
            "created_by_user_id FROM vnext_core.property_graph_nodes "
            "WHERE workspace_id = %s ORDER BY property_graph_node_id" + suffix,
            (config.workspace_id,),
        ).fetchall()
        graph_nodes = tuple(
            GraphNodeRow(
                _uuid(row[0]),
                _uuid(row[1]),
                str(row[2]),
                _uuid(row[3]),
                _uuid(row[4]),
            )
            for row in graph_rows
        )
        counts = {
            table: int(
                self.connection.execute(
                    f"SELECT count(*) FROM {table} WHERE workspace_id = %s",
                    (config.workspace_id,),
                ).fetchone()[0]
            )
            for table in ATTACHED_TABLES
        }
        return BundleSnapshot(
            auth_user_exists=bool(auth_user_exists),
            workspace=workspace,
            workspace_marker_ids=tuple(_uuid(row[0]) for row in workspace_marker_rows),
            memberships=memberships,
            property=property_record,
            workspace_properties=workspace_properties,
            property_marker_ids=tuple(_uuid(row[0]) for row in property_marker_rows),
            graph_nodes=graph_nodes,
            attached_counts=counts,
        )

    @staticmethod
    def _require_one(cursor: Any) -> None:
        if cursor.rowcount != 1:
            raise SafeProvisioningFailure("concurrent_bundle_drift")

    def provision(self, config: AcceptanceConfig) -> None:
        self._require_one(
            self.connection.execute(
                "INSERT INTO vnext_core.workspaces ("
                "workspace_id, workspace_type, display_name, status, version, "
                "created_by_user_id, personal_owner_user_id"
                ") VALUES (%s, 'team', %s, 'active', 1, %s, NULL)",
                (config.workspace_id, WORKSPACE_LABEL, config.auth_user_id),
            )
        )
        self._require_one(
            self.connection.execute(
                "INSERT INTO vnext_core.workspace_members ("
                "workspace_member_id, workspace_id, user_id, role, status, joined_at, "
                "left_at, revoked_at"
                ") VALUES (%s, %s, %s, 'viewer', 'active', clock_timestamp(), NULL, NULL)",
                (config.membership_id, config.workspace_id, config.auth_user_id),
            )
        )
        self._require_one(
            self.connection.execute(
                "INSERT INTO vnext_core.property_entities ("
                "property_entity_id, workspace_id, entity_status, display_label, version, "
                "created_by_user_id, archived_at"
                ") VALUES (%s, %s, 'unverified', %s, 1, %s, NULL)",
                (
                    config.property_id,
                    config.workspace_id,
                    PROPERTY_LABEL,
                    config.auth_user_id,
                ),
            )
        )

    def archive(self, config: AcceptanceConfig) -> None:
        self._require_one(
            self.connection.execute(
                "UPDATE vnext_core.workspace_members SET status = 'removed', "
                "revoked_at = clock_timestamp(), left_at = NULL, updated_at = clock_timestamp() "
                "WHERE workspace_member_id = %s AND workspace_id = %s AND user_id = %s "
                "AND role = 'viewer' AND status = 'active' AND joined_at IS NOT NULL "
                "AND left_at IS NULL AND revoked_at IS NULL",
                (config.membership_id, config.workspace_id, config.auth_user_id),
            )
        )
        self._require_one(
            self.connection.execute(
                "UPDATE vnext_core.property_entities SET entity_status = 'archived', "
                "archived_at = clock_timestamp(), updated_at = clock_timestamp() "
                "WHERE property_entity_id = %s AND workspace_id = %s "
                "AND entity_status = 'unverified' AND display_label = %s "
                "AND created_by_user_id = %s AND archived_at IS NULL",
                (
                    config.property_id,
                    config.workspace_id,
                    PROPERTY_LABEL,
                    config.auth_user_id,
                ),
            )
        )
        self._require_one(
            self.connection.execute(
                "UPDATE vnext_core.workspaces SET status = 'archived', "
                "archived_at = clock_timestamp(), updated_at = clock_timestamp() "
                "WHERE workspace_id = %s AND workspace_type = 'team' "
                "AND display_name = %s AND status = 'active' "
                "AND created_by_user_id = %s AND personal_owner_user_id IS NULL "
                "AND archived_at IS NULL",
                (config.workspace_id, WORKSPACE_LABEL, config.auth_user_id),
            )
        )

    def reactivate(self, config: AcceptanceConfig) -> None:
        self._require_one(
            self.connection.execute(
                "UPDATE vnext_core.workspaces SET status = 'active', archived_at = NULL, "
                "updated_at = clock_timestamp() WHERE workspace_id = %s "
                "AND workspace_type = 'team' AND display_name = %s "
                "AND status = 'archived' AND created_by_user_id = %s "
                "AND personal_owner_user_id IS NULL AND archived_at IS NOT NULL",
                (config.workspace_id, WORKSPACE_LABEL, config.auth_user_id),
            )
        )
        self._require_one(
            self.connection.execute(
                "UPDATE vnext_core.property_entities SET entity_status = 'unverified', "
                "archived_at = NULL, updated_at = clock_timestamp() "
                "WHERE property_entity_id = %s AND workspace_id = %s "
                "AND entity_status = 'archived' AND display_label = %s "
                "AND created_by_user_id = %s AND archived_at IS NOT NULL",
                (
                    config.property_id,
                    config.workspace_id,
                    PROPERTY_LABEL,
                    config.auth_user_id,
                ),
            )
        )
        self._require_one(
            self.connection.execute(
                "UPDATE vnext_core.workspace_members SET status = 'active', "
                "revoked_at = NULL, left_at = NULL, updated_at = clock_timestamp() "
                "WHERE workspace_member_id = %s AND workspace_id = %s AND user_id = %s "
                "AND role = 'viewer' AND status = 'removed' AND joined_at IS NOT NULL "
                "AND left_at IS NULL AND revoked_at IS NOT NULL",
                (config.membership_id, config.workspace_id, config.auth_user_id),
            )
        )


def _validated_operator_database_url(value: str) -> tuple[str, str]:
    try:
        if (
            not value
            or any(character.isspace() or character == "\\" for character in value)
            or value.startswith(("eyJ", "sb_"))
        ):
            raise ValueError
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"postgres", "postgresql"}
            or not parsed.hostname
            or not parsed.path
            or parsed.path == "/"
            or parsed.fragment
        ):
            raise ValueError
        from psycopg.conninfo import conninfo_to_dict

        try:
            parameters = conninfo_to_dict(value)
        except Exception as error:
            raise ValueError from error
        operator_name = str(parameters.get("user", "")).lower()
        database_name = str(parameters.get("dbname", ""))
        ssl_modes = [
            mode.lower()
            for mode in parse_qs(parsed.query, keep_blank_values=True).get(
                "sslmode", []
            )
        ]
        effective_sslmode = str(parameters.get("sslmode", "")).lower()
        destinations = [
            host.strip().lower()
            for key in ("host", "hostaddr")
            for host in str(parameters.get(key, "")).split(",")
            if host.strip()
        ]
        local_database = bool(destinations) and all(
            host in {"localhost", "127.0.0.1", "::1"}
            for host in destinations
        )
        if (
            not destinations
            or not operator_name
            or not database_name
            or parameters.get("service")
            or parameters.get("servicefile")
            or operator_name in {"service_role", "anon", "authenticated", "vnext_api"}
            or len(ssl_modes) > 1
            or (effective_sslmode and effective_sslmode != "verify-full")
            or (not local_database and effective_sslmode != "verify-full")
        ):
            raise ValueError
        return value, effective_sslmode or "prefer"
    except (ImportError, TypeError, ValueError):
        raise SafeProvisioningFailure("operator_database_url_invalid") from None


def validate_operator_database_url(value: str) -> str:
    return _validated_operator_database_url(value)[0]


def run(
    database_url: str,
    config: AcceptanceConfig,
    *,
    mode: str,
    connection_factory: Any | None = None,
) -> dict[str, str]:
    try:
        safe_url, sslmode = _validated_operator_database_url(database_url)
        with connect(
            safe_url,
            connection_factory=connection_factory,
            sslmode=sslmode,
        ) as connection:
            return execute(PostgresAcceptanceStore(connection), config, mode=mode)
    except SafeProvisioningFailure as error:
        return {"status": "refused", "reason": error.reason}
    except Exception:
        return {"status": "unavailable", "reason": "database_operation_unavailable"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or explicitly mutate the Stage 1 acceptance bundle."
    )
    parser.add_argument("--auth-user-id", type=UUID, required=True)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--property-id", type=UUID, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply-provision", action="store_true")
    modes.add_argument("--apply-archive", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    connection_factory: Any | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    selected_environ = os.environ if environ is None else environ
    database_url = selected_environ.get(DATABASE_URL_ENV, "")
    try:
        config = AcceptanceConfig(
            auth_user_id=args.auth_user_id,
            workspace_id=args.workspace_id,
            property_id=args.property_id,
        )
        if not database_url:
            result = {"status": "refused", "reason": "operator_database_url_missing"}
        else:
            mode = (
                "provision"
                if args.apply_provision
                else "archive" if args.apply_archive else "dry_run"
            )
            result = run(
                database_url,
                config,
                mode=mode,
                connection_factory=connection_factory,
            )
    except SafeProvisioningFailure as error:
        result = {"status": "refused", "reason": error.reason}
    except Exception:
        result = {"status": "unavailable", "reason": "database_operation_unavailable"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"ready", "pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
