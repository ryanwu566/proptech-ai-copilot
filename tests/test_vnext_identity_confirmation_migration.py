from __future__ import annotations

import json
from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts.migration_registry import (checksum, load_registry,
                                        next_safe_sequence)

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/016_vnext_identity_confirmation_case_links.sql"
REGISTRY = ROOT / "database/migration_registry.json"
FROZEN_015 = "b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f"


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_016_is_registered_once_and_advances_sequence() -> None:
    registrations = load_registry()
    matching = [item for item in registrations if item.filename == MIGRATION.name]

    assert len(matching) == 1
    assert matching[0].sequence == 16
    assert matching[0].sha256 == checksum(MIGRATION)
    assert migration_runner.MIGRATIONS[-1] == MIGRATION
    assert next_safe_sequence(registrations) == 17


def test_migrations_001_through_015_remain_frozen() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = payload["migrations"]
    migration_015 = next(
        item for item in entries if item["filename"] == "015_vnext_identity_resolution_candidates.sql"
    )

    assert migration_015["sha256"] == FROZEN_015
    assert len([item for item in entries if int(item["sequence"]) <= 15]) == 16


def test_decision_overlay_is_append_only_scoped_and_versioned() -> None:
    sql = _sql()

    assert "create table vnext_core.identity_decisions" in sql
    assert "resolution_version_observed" in sql
    assert "decision_version = resolution_version_observed + 1" in sql
    assert "supporting_evidence_ids_snapshot" in sql
    assert "supporting_reference_ids_snapshot" in sql
    assert "uq_vnext_identity_decisions_confirmed_resolution" in sql
    assert "trg_vnext_identity_decisions_append_only" in sql
    assert "alter table vnext_core.identity_decisions enable row level security" in sql
    assert "alter table vnext_core.identity_decisions force row level security" in sql
    assert "grant select, insert on vnext_core.identity_decisions to vnext_api" in sql
    assert "grant update" not in "\n".join(
        line for line in sql.splitlines() if "identity_decisions" in line
    )


def test_failed_idempotency_replay_stores_only_an_allowlisted_error_code() -> None:
    sql = _sql()

    assert "add column response_error_code text" in sql
    assert "ck_vnext_idempotency_response_error_code" in sql
    assert "operation_status = 'failed'" in sql


def test_confirmation_is_human_attributed_and_never_rank_driven() -> None:
    sql = _sql()

    assert "identity_decisions_owner_admin_insert" in sql
    assert "member.role in ('owner', 'admin')" in sql
    assert "actor_user_id = (select auth.uid())" in sql
    assert "candidate_status in ('insufficient', 'rejected', 'superseded')" in sql
    assert "candidate_type = 'composite_property'" in sql
    assert "source_type in ('demo', 'test')" in sql
    assert "source_environment <> 'production'" in sql
    assert "severity = 'blocking'" in sql
    assert "rank = 1" not in sql
    assert "order by" not in "\n".join(
        line for line in sql.splitlines() if "confidence" in line
    )


def test_confirmed_relation_retains_generic_guard_and_requires_decision_fk() -> None:
    sql = _sql()

    assert "add column identity_confirmation_id uuid" in sql
    assert "fk_vnext_property_relations_confirmation" in sql
    assert "property_relations_human_confirmation_insert" in sql
    assert "new.confirmed_by_user_id <> confirmation.actor_user_id" in sql
    assert "new.confirmed_at <> confirmation.created_at" in sql
    assert "new.source_type in ('demo', 'test')" in sql
    assert "new.evidence_id is distinct from confirmation.primary_evidence_id" in sql


def test_case_links_are_append_only_historical_and_separate_from_confirmation() -> None:
    sql = _sql()

    assert "create table vnext_core.case_property_links" in sql
    assert "supersedes_case_property_link_id" in sql
    assert "case_version_after = case_version_before + 1" in sql
    assert "trg_vnext_case_property_links_append_only" in sql
    assert "trg_vnext_case_property_links_commit" in sql
    assert "case_property_links_owner_admin_insert" in sql
    assert "vnext_case_property_link_case_update_required" in sql
    assert "new.identity_status <> 'confirmed'" in sql


def test_no_privileged_bypass_or_live_provider_surface_is_added() -> None:
    sql = _sql()

    assert "security definer" not in sql
    assert "service_role" not in sql
    assert "bypassrls" not in sql
    assert "tgos" not in sql
    assert "google" not in sql
    assert "nlsc" not in sql
    assert "plvr" not in sql
