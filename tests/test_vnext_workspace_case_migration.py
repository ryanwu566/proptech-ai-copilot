from __future__ import annotations

import json
from pathlib import Path

from scripts.migration_registry import checksum, load_registry, next_safe_sequence


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/013_vnext_workspace_case_foundation.sql"
REGISTRY = ROOT / "database/migration_registry.json"
SQL = MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_013_is_registered_once_and_advances_sequence() -> None:
    registrations = load_registry()
    selected = [item for item in registrations if item.sequence == 13]

    assert len(selected) == 1
    assert selected[0].filename == MIGRATION.name
    assert selected[0].execution_policy == "production_runner"
    assert selected[0].sha256 == checksum(MIGRATION)
    assert next_safe_sequence(registrations) == 15


def test_historical_registry_entries_and_migration_012_are_untouched() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    frozen = {entry["filename"]: entry["sha256"] for entry in payload["migrations"]}

    assert frozen["001_add_dedupe_key_to_real_price_transactions.sql"] == (
        "2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223"
    )
    assert frozen["011_add_plvr_compact_green_schema.sql"] == (
        "107ba18c7db124a40183dc048581f821c853499feca203f874152c5b0dab2af2"
    )
    assert frozen["012_security_rls_deny_by_default.sql"] == (
        "bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056"
    )


def test_private_schema_model_has_only_slice_2_records() -> None:
    for table in (
        "vnext_core.workspaces",
        "vnext_core.workspace_members",
        "vnext_core.cases",
        "vnext_private.idempotency_records",
        "vnext_private.audit_events",
    ):
        assert SQL.count(f"create table {table}") == 1

    assert "create table vnext_core.property" not in SQL
    assert "create table vnext_core.evidence" not in SQL
    assert "property_entity_id" not in SQL
    assert "security definer" not in SQL
    assert "auth.role()" not in SQL
    assert "user_metadata" not in SQL


def test_workspace_membership_and_case_constraints_are_explicit() -> None:
    assert "workspace_type in ('personal', 'team')" in SQL
    assert "role in ('owner', 'admin', 'manager', 'member', 'viewer')" in SQL
    assert "status in ('invited', 'active', 'suspended', 'left', 'removed')" in SQL
    assert "identity_status in (" in SQL
    for status in ("unverified", "legacy_unverified", "resolving", "confirmed"):
        assert f"'{status}'" in SQL
    assert "vnext_case_identity_is_immutable" in SQL
    assert "vnext_case_identity_command_required" in SQL
    assert "vnext_case_assignment_command_required" in SQL
    assert "vnext_case_version_increment_required" in SQL
    assert "vnext_case_archive_is_terminal" in SQL


def test_vnext_api_role_has_no_secret_owner_or_bypass_privilege() -> None:
    assert "create role vnext_api" in SQL
    assert "nosuperuser" in SQL
    assert "nobypassrls" in SQL
    assert "nocreaterole" in SQL
    assert "noinherit" in SQL
    assert "password '" not in SQL
    assert "authorization" not in "\n".join(
        line for line in SQL.splitlines() if line.lstrip().startswith("grant ")
    )
    assert "grant select, insert, update on vnext_core.cases to vnext_api" in SQL
    assert "grant insert on vnext_private.audit_events to vnext_api" in SQL
    assert "grant update on vnext_private.audit_events" not in SQL
    assert "grant delete" not in SQL


def test_every_tenant_table_has_enabled_and_forced_rls() -> None:
    for table in (
        "vnext_core.workspaces",
        "vnext_core.workspace_members",
        "vnext_core.cases",
        "vnext_private.idempotency_records",
        "vnext_private.audit_events",
    ):
        assert f"alter table {table} enable row level security" in SQL
        assert f"alter table {table} force row level security" in SQL


def test_membership_self_read_is_non_recursive_and_case_rls_is_role_aware() -> None:
    self_policy = SQL.split("create policy workspace_members_self_select", 1)[1].split(
        "create policy workspaces_active_member_select", 1
    )[0]
    assert "user_id = (select auth.uid())" in self_policy
    assert "from vnext_core.workspace_members" not in self_policy

    update_policy = SQL.split("create policy cases_active_writer_update", 1)[1].split(
        "create policy idempotency_actor_select", 1
    )[0]
    assert "using (" in update_policy
    assert "with check (" in update_policy
    assert "'viewer'" not in update_policy
    assert "member.status = 'active'" in update_policy
    assert "trg_vnext_cases_guard_update" in SQL


def test_idempotency_is_bounded_and_audit_is_append_only() -> None:
    assert "uq_vnext_idempotency_scope" in SQL
    assert "request_fingerprint ~ '^[0-9a-f]{64}$'" in SQL
    assert "expires_at > created_at" in SQL
    assert "octet_length(metadata::text) <= 16384" in SQL
    assert "trg_vnext_audit_append_only" in SQL
    assert "vnext_audit_event_is_append_only" in SQL
