from __future__ import annotations

import json
from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts import validate_postgres_migration as migration_validator
from scripts.migration_registry import checksum, load_registry, next_safe_sequence


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/017_vnext_legacy_saved_case_import.sql"
REGISTRY = ROOT / "database/migration_registry.json"
FROZEN_016 = "b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636"


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_017_is_registered_once_and_advances_sequence() -> None:
    registrations = load_registry()
    matching = [item for item in registrations if item.filename == MIGRATION.name]

    assert len(matching) == 1
    assert matching[0].sequence == 17
    assert matching[0].execution_policy == "production_runner"
    assert matching[0].sha256 == checksum(MIGRATION)
    assert migration_runner.MIGRATIONS[-1] == MIGRATION
    assert migration_validator.MIGRATIONS[-1] == MIGRATION
    assert next_safe_sequence(registrations) == 18


def test_migrations_001_through_016_remain_frozen() -> None:
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["migrations"]
    migration_016 = next(
        item
        for item in entries
        if item["filename"] == "016_vnext_identity_confirmation_case_links.sql"
    )

    assert migration_016["sha256"] == FROZEN_016
    assert len([item for item in entries if int(item["sequence"]) <= 16]) == 17


def test_import_record_is_bounded_hashed_copy_only_and_contains_no_raw_payload() -> None:
    sql = _sql()
    table = sql.split("create table vnext_private.legacy_case_imports", 1)[1].split(
        ");", 1
    )[0]

    assert "legacy_client_id_hash text not null" in table
    assert "legacy_client_id text" not in table
    assert "raw_payload" not in table
    assert "payload json" not in table
    assert "check (legacy_format = 'saved_case_v1')" in table
    assert "check (schema_version = 1)" in table
    assert "check (import_mode = 'copy')" in table
    assert "legacy_client_id_hash ~ '^[0-9a-f]{64}$'" in table
    assert "accepted_field_classes <@ array[" in table
    assert "dropped_field_classes <@ array[" in table
    assert "warnings <@ array[" in table


def test_import_is_scoped_deduplicated_and_append_only() -> None:
    sql = _sql()

    assert "uq_vnext_legacy_import_scoped_client" in sql
    assert "unique (workspace_id, actor_user_id, legacy_format, legacy_client_id_hash)" in sql
    assert "uq_vnext_legacy_import_case" in sql
    assert "uq_vnext_legacy_import_idempotency" in sql
    assert "create index idx_vnext_legacy_case_imports_actor" in sql
    assert "trg_vnext_legacy_case_import_append_only" in sql
    assert "before update or delete" in sql
    assert "alter table vnext_private.legacy_case_imports enable row level security" in sql
    assert "alter table vnext_private.legacy_case_imports force row level security" in sql
    assert "grant select, insert on vnext_private.legacy_case_imports to vnext_api" in sql
    assert "grant update" not in "\n".join(
        line for line in sql.splitlines() if "legacy_case_imports" in line
    )
    assert "grant delete" not in "\n".join(
        line for line in sql.splitlines() if "legacy_case_imports" in line
    )


def test_import_rls_requires_actor_and_active_writer_membership() -> None:
    sql = _sql()

    assert sql.count("actor_user_id = (select auth.uid())") == 2
    assert sql.count("member.status = 'active'") == 2
    assert sql.count("member.role in ('owner', 'admin', 'manager', 'member')") == 2
    assert "'viewer'" not in "\n".join(
        line for line in sql.splitlines() if "member.role" in line
    )


def test_import_guard_requires_unverified_case_pending_request_and_no_attachment() -> None:
    sql = _sql()

    assert "imported_case.identity_status = 'legacy_unverified'" in sql
    assert "imported_case.version = 1" in sql
    assert "imported_case.created_by_user_id = new.actor_user_id" in sql
    assert "idempotency.http_method = 'post'" in sql
    assert "idempotency.canonical_route = '/v1/cases/import-legacy'" in sql
    assert "idempotency.operation_status = 'pending'" in sql
    assert "vnext_legacy_import_case_attachment_forbidden" in sql


def test_import_adds_no_identity_resolution_confirmation_or_property_creation() -> None:
    sql = _sql()

    assert "insert into vnext_core.property_entities" not in sql
    assert "insert into vnext_core.identity_resolutions" not in sql
    assert "insert into vnext_core.identity_decisions" not in sql
    assert "insert into vnext_core.case_property_links" not in sql
    assert "create_property_entity" not in sql
    assert "security definer" not in sql
    assert "service_role" not in sql
    assert "bypassrls" not in sql
