from __future__ import annotations

import json
from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts.migration_registry import checksum, load_registry, next_safe_sequence


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/015_vnext_identity_resolution_candidates.sql"
REGISTRY = ROOT / "database/migration_registry.json"
SQL = MIGRATION.read_text(encoding="utf-8").lower()

TENANT_TABLES = (
    "vnext_core.identity_resolutions",
    "vnext_core.resolution_attempts",
    "vnext_core.identity_candidates",
    "vnext_core.identity_conflicts",
)


def test_migration_015_is_registered_once_and_advances_sequence() -> None:
    registrations = load_registry()
    selected = [item for item in registrations if item.sequence == 15]

    assert len(selected) == 1
    assert selected[0].filename == MIGRATION.name
    assert selected[0].execution_policy == "production_runner"
    assert selected[0].sha256 == checksum(MIGRATION)
    assert next_safe_sequence(registrations) == 18
    assert MIGRATION in migration_runner.MIGRATIONS


def test_migrations_001_through_014_remain_frozen() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    frozen = {entry["filename"]: entry["sha256"] for entry in payload["migrations"]}

    assert frozen["001_add_dedupe_key_to_real_price_transactions.sql"] == (
        "2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223"
    )
    assert frozen["013_vnext_workspace_case_foundation.sql"] == (
        "322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952"
    )
    assert frozen["014_vnext_property_graph_evidence_foundation.sql"] == (
        "0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd"
    )


def test_slice_4_creates_only_the_four_resolution_history_tables() -> None:
    assert SQL.count("create table ") == len(TENANT_TABLES)
    for table in TENANT_TABLES:
        assert SQL.count(f"create table {table}") == 1

    for deferred in (
        "human_confirmations",
        "case_property_links",
        "listings",
        "titles",
        "canonical_properties",
    ):
        assert f"create table vnext_core.{deferred}" not in SQL


def test_candidate_and_resolution_states_never_encode_confirmation() -> None:
    assert "'received', 'normalizing', 'candidates_found', 'ambiguous'" in SQL
    assert "'partially_resolved', 'unresolved', 'failed', 'superseded'" in SQL
    assert "'proposed', 'plausible', 'conflicting'" in SQL
    assert "'insufficient', 'rejected', 'superseded'" in SQL
    assert "needs_human_confirmation boolean not null default true" in SQL
    assert "check (needs_human_confirmation)" in SQL
    assert "candidate_status in ('confirmed'" not in SQL
    assert "resolution_status in ('confirmed'" not in SQL
    assert "create_property_entity" not in SQL
    assert "insert into vnext_core.property_entities" not in SQL
    assert "update vnext_core.cases" not in SQL


def test_attempts_are_bounded_and_keep_safe_failure_categories() -> None:
    for status in (
        "available",
        "limited",
        "unavailable",
        "timeout",
        "unsupported",
        "no_match",
        "error",
    ):
        assert f"'{status}'" in SQL
    for field in (
        "strategy_id text not null",
        "provider_id text not null",
        "coverage_status text not null",
        "result_count integer not null",
        "error_category text",
        "retrieved_at timestamptz",
    ):
        assert field in SQL
    assert "raw_provider" not in SQL
    assert "credential" not in SQL
    assert "token" not in SQL


def test_candidate_provenance_ranking_and_cardinality_are_not_one_to_one() -> None:
    for field in (
        "source_record_id text",
        "source_environment text not null",
        "retrieved_at timestamptz not null",
        "confidence numeric(5, 4) not null",
        "confidence_method text not null",
        "ranking_factors jsonb not null",
        "supporting_evidence_ids uuid[]",
        "supporting_reference_ids uuid[]",
        "possible_existing_property_entity_id uuid",
    ):
        assert field in SQL
    assert "unique (identity_resolution_id, rank)" in SQL
    assert "unique (identity_resolution_id, candidate_type)" not in SQL
    assert "guard_identity_candidate_support" in SQL
    assert "vnext_candidate_evidence_scope_invalid" in SQL
    assert "vnext_candidate_reference_scope_invalid" in SQL


def test_conflicts_retain_both_candidates_and_workspace_scoped_resources() -> None:
    assert "left_candidate_id uuid not null" in SQL
    assert "right_candidate_id uuid" in SQL
    assert "source_basis jsonb not null" in SQL
    assert "conflict_basis jsonb not null" in SQL
    for target in (
        "identity_candidates(\n            workspace_id, identity_resolution_id, identity_candidate_id\n        )",
        "property_identity_references(workspace_id, identity_reference_id)",
        "evidence_items(workspace_id, evidence_id)",
        "property_entities(workspace_id, property_entity_id)",
    ):
        assert f"references vnext_core.{target}" in SQL
    assert "delete from vnext_core.identity_candidates" not in SQL


def test_every_slice_4_table_has_forced_rls_and_append_only_grants() -> None:
    for table in TENANT_TABLES:
        assert f"alter table {table} enable row level security" in SQL
        assert f"alter table {table} force row level security" in SQL
        assert f"revoke all on table {table} from public" in SQL
        assert f"grant select, insert on {table} to vnext_api" in SQL
        assert f"grant update on {table}" not in SQL
        assert f"grant delete on {table}" not in SQL

    assert SQL.count("for select\nto vnext_api") == 4
    assert SQL.count("for insert\nto vnext_api") == 4
    assert "member.role in ('owner', 'admin', 'manager', 'member')" in SQL
    assert "source_type in ('user', 'deterministic', 'demo', 'test')" in SQL
    assert "trg_vnext_identity_resolutions_append_only" in SQL
    assert "trg_vnext_resolution_attempts_append_only" in SQL
    assert "trg_vnext_identity_candidates_append_only" in SQL
    assert "trg_vnext_identity_conflicts_append_only" in SQL
    assert "security definer" not in SQL
    assert "auth.role()" not in SQL
