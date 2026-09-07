from __future__ import annotations

import json
from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts.migration_registry import checksum, load_registry, next_safe_sequence


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/014_vnext_property_graph_evidence_foundation.sql"
REGISTRY = ROOT / "database/migration_registry.json"
SQL = MIGRATION.read_text(encoding="utf-8").lower()

TENANT_TABLES = (
    "vnext_core.property_entities",
    "vnext_core.property_identity_references",
    "vnext_core.property_graph_nodes",
    "vnext_core.property_relations",
    "vnext_core.evidence_items",
    "vnext_core.evidence_lineage",
    "vnext_core.evidence_links",
)


def test_migration_014_is_registered_once_and_advances_sequence() -> None:
    registrations = load_registry()
    selected = [item for item in registrations if item.sequence == 14]

    assert len(selected) == 1
    assert selected[0].filename == MIGRATION.name
    assert selected[0].execution_policy == "production_runner"
    assert selected[0].sha256 == checksum(MIGRATION)
    assert next_safe_sequence(registrations) == 18
    assert MIGRATION in migration_runner.MIGRATIONS


def test_migrations_001_through_013_remain_frozen() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    frozen = {entry["filename"]: entry["sha256"] for entry in payload["migrations"]}

    assert frozen["001_add_dedupe_key_to_real_price_transactions.sql"] == (
        "2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223"
    )
    assert frozen["012_security_rls_deny_by_default.sql"] == (
        "bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056"
    )
    assert frozen["013_vnext_workspace_case_foundation.sql"] == (
        "322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952"
    )


def test_slice_3_creates_only_the_reviewed_graph_and_evidence_tables() -> None:
    assert SQL.count("create table ") == len(TENANT_TABLES)
    for table in TENANT_TABLES:
        assert SQL.count(f"create table {table}") == 1

    for deferred_table in (
        "property_candidates",
        "property_resolutions",
        "property_confirmations",
        "property_case_links",
        "listings",
        "titles",
        "provider_calls",
    ):
        assert f"create table vnext_core.{deferred_table}" not in SQL


def test_graph_model_preserves_real_typed_nodes_and_many_to_many_history() -> None:
    assert "unique (workspace_id, node_type, record_id)" in SQL
    assert "'property', 'address', 'geo_reference', 'parcel'" in SQL
    assert "'building', 'listing', 'case'" in SQL
    assert "guard_property_graph_node_target" in SQL
    assert "vnext_graph_listing_target_unavailable" in SQL
    assert "property_address" in SQL
    assert "property_geo_reference" in SQL
    assert "property_parcel" in SQL
    assert "property_building" in SQL
    assert "parcel_building" in SQL
    assert "unique (workspace_id, from_node_id, to_node_id" not in SQL
    assert "valid_from timestamptz" in SQL
    assert "valid_to timestamptz" in SQL
    assert "supersedes_relation_id uuid" in SQL
    assert "selected_from_type <> 'parcel'" in SQL
    assert "selected_to_type <> 'building'" in SQL


def test_evidence_contract_is_immutable_versioned_and_provenance_complete() -> None:
    for field in (
        "source_id text not null",
        "source_type text not null",
        "source_environment text not null",
        "retrieved_at timestamptz not null",
        "coverage_status text not null",
        "quality_status text not null",
        "license_status text not null",
        "content_hash text not null",
        "evidence_version bigint not null",
        "supersedes_evidence_id uuid",
    ):
        assert field in SQL
    for status in (
        "available",
        "limited",
        "unavailable",
        "unknown",
        "stale",
        "conflicting",
        "user_provided",
        "unverified",
    ):
        assert f"'{status}'" in SQL
    assert "evidence_status in ('unavailable', 'unknown')" in SQL
    assert "value is null and value_ref is null" in SQL
    assert "child_evidence_id uuid not null" in SQL
    assert "parent_evidence_id uuid not null" in SQL
    assert "uq_vnext_evidence_lineage_edge" in SQL
    assert "trg_vnext_evidence_items_append_only" in SQL


def test_cross_workspace_edges_are_prevented_by_composite_foreign_keys() -> None:
    for target in (
        "property_graph_nodes(workspace_id, property_graph_node_id)",
        "evidence_items(workspace_id, evidence_id)",
        "property_relations(workspace_id, property_relation_id)",
        "property_identity_references(workspace_id, identity_reference_id)",
    ):
        assert f"references vnext_core.{target}" in SQL


def test_every_slice_3_table_has_forced_rls_and_append_only_grants() -> None:
    for table in TENANT_TABLES:
        assert f"alter table {table} enable row level security" in SQL
        assert f"alter table {table} force row level security" in SQL
        assert f"revoke all on table {table} from public" in SQL
        assert f"grant select, insert on {table} to vnext_api" in SQL
        assert f"grant update on {table}" not in SQL
        assert f"grant delete on {table}" not in SQL

    assert "member.role in ('owner', 'admin', 'manager', 'member')" in SQL
    assert "source_type in ('user', 'deterministic', 'demo', 'test')" in SQL
    assert "relation_status <> 'confirmed'" in SQL
    assert "security definer" not in SQL
    assert "auth.role()" not in SQL
    assert "user_metadata" not in SQL
