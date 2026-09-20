from __future__ import annotations

import json
from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts import validate_postgres_migration as migration_validator
from scripts.migration_registry import checksum, load_registry, next_safe_sequence


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/018_vnext_case_parcel_set_v1.sql"
REGISTRY = ROOT / "database/migration_registry.json"
FROZEN_001_017 = {
    "001_add_dedupe_key_to_real_price_transactions.sql": "2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223",
    "002_add_market_direct_query_indexes.sql": "2cb6da19a01415ffee34845aa294843257cce7f9991803e0ca470e3405cfc310",
    "002_expand_valuation_import_runs.sql": "0108c13fad4d0310e291c0d2e041868c7d59b8fb2f47739831139fa3039b2d64",
    "003_add_market_region_coverage.sql": "267db5dcba4c12646b78f480b289cbd289a323bc205a0a8fe5ba507290efb16b",
    "004_add_pilot_evidence.sql": "ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516",
    "005_add_pilot_security_indexes.sql": "7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c",
    "006_add_tax_analysis_history.sql": "cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0",
    "007_add_schema_migration_ledger.sql": "1d1d20edf40b9d2782dd9e314d7e4a2d35ac0aaac5d1570494e58f3e3d982996",
    "008_add_official_market_pipeline.sql": "22e0a282a40692e05054388fe2e4aa5f25c253e733b2aedd50f4d30446b788d9",
    "009_separate_official_market_region_coverage.sql": "c14084726fa101f3a93e700525abe90f1caee46f542f5a37a13d5d545b3526f7",
    "010_add_plvr_generation_schema.sql": "fcf69fc2d3b5e6419e2d94a6d92abc03c9b4424204e9bd129b85ea749ebed4a5",
    "011_add_plvr_compact_green_schema.sql": "107ba18c7db124a40183dc048581f821c853499feca203f874152c5b0dab2af2",
    "012_security_rls_deny_by_default.sql": "bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056",
    "013_vnext_workspace_case_foundation.sql": "322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952",
    "014_vnext_property_graph_evidence_foundation.sql": "0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd",
    "015_vnext_identity_resolution_candidates.sql": "b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f",
    "016_vnext_identity_confirmation_case_links.sql": "b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636",
    "017_vnext_legacy_saved_case_import.sql": "0753b222597d7e0d6cbc618a17bc1d07d047a0d499318936c29880a119182efa",
}


def _sql() -> str:
    assert MIGRATION.is_file(), "migration 018 must exist"
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_018_is_registered_last_without_historical_checksum_drift() -> None:
    registrations = load_registry()
    frozen = {item.filename: item.sha256 for item in registrations}

    assert {name: frozen[name] for name in FROZEN_001_017} == FROZEN_001_017
    assert registrations[-1].filename == MIGRATION.name
    assert registrations[-1].sequence == 18
    assert registrations[-1].execution_policy == "production_runner"
    assert registrations[-1].sha256 == checksum(MIGRATION)
    assert migration_runner.MIGRATIONS[-1] == MIGRATION
    assert migration_validator.MIGRATIONS[-1] == MIGRATION
    assert next_safe_sequence(registrations) == 19
    assert not list(MIGRATION.parent.glob("019_*.sql"))


def test_registry_contains_exactly_one_new_018_entry() -> None:
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["migrations"]

    assert len(entries) == 19
    assert [item["registry_order"] for item in entries] == list(range(1, 20))
    assert len([item for item in entries if item["sequence"] == 18]) == 1
    assert entries[-1]["logical_id"] == "production-018-vnext-case-parcel-set-v1"


def test_production_verifier_requires_the_new_schema_objects() -> None:
    assert {
        "vnext_core.case_parcel_sets",
        "vnext_core.case_parcel_set_members",
    } <= migration_validator.REQUIRED_VNEXT_TABLES
    assert {
        "vnext_core.idx_vnext_case_parcel_sets_active_member",
        "vnext_core.idx_vnext_case_parcel_set_members_order",
        "vnext_core.idx_vnext_case_parcel_set_members_reference",
    } <= migration_validator.REQUIRED_VNEXT_INDEXES
    assert {
        "fk_vnext_case_parcel_sets_case",
        "fk_vnext_case_parcel_sets_active_member",
        "fk_vnext_case_parcel_set_members_set",
        "fk_vnext_case_parcel_set_members_reference",
    } <= migration_validator.REQUIRED_VNEXT_FOREIGN_KEYS


def test_schema_enforces_one_bounded_case_local_parcel_set() -> None:
    sql = _sql()

    assert "create table vnext_core.case_parcel_sets" in sql
    assert "create table vnext_core.case_parcel_set_members" in sql
    assert "unique (workspace_id, case_id)" in sql
    assert "unique (workspace_id, parcel_set_id, parcel_identity_reference_id)" in sql
    assert "unique (workspace_id, parcel_set_id, parcel_set_member_id)" in sql
    assert "check (position between 1 and 100)" in sql
    assert "check (status in ('draft', 'case_reviewed'))" in sql
    assert "check (review_status in ('candidate', 'case_selected', 'case_rejected'))" in sql
    assert "check (version >= 1)" in sql
    assert "selected_reference_type <> 'parcel'" in sql
    assert "vnext_case_parcel_member_reference_must_be_parcel" in sql
    assert "foreign key (workspace_id, parcel_set_id, active_member_id)" in sql


def test_schema_enforces_versioned_updates_and_case_review_wording() -> None:
    sql = _sql()

    assert "new.version <> old.version + 1" in sql
    assert "vnext_case_parcel_set_version_increment_required" in sql
    assert "new.updated_at <= old.updated_at" in sql
    assert "status = 'case_reviewed'" in sql
    assert "reviewed_at is not null" in sql
    assert "not official or canonical parcel confirmation" in sql
    assert "does not change property identity" in sql


def test_schema_allows_member_reads_but_only_writer_mutations() -> None:
    sql = _sql()

    for table in ("case_parcel_sets", "case_parcel_set_members"):
        assert f"alter table vnext_core.{table} enable row level security" in sql
        assert f"alter table vnext_core.{table} force row level security" in sql
        assert f"grant select, insert, update on vnext_core.{table} to vnext_api" in sql
    assert sql.count("member.role in ('owner', 'admin', 'manager', 'member', 'viewer')") == 2
    assert sql.count("member.role in ('owner', 'admin', 'manager', 'member')") == 6
    assert "grant delete" not in sql
    assert "for delete" not in sql
    assert "security definer" not in sql
    assert "bypassrls" not in sql


def test_trigger_functions_pin_search_path_and_scope_excludes_geometry_and_events() -> None:
    sql = _sql()

    assert sql.count("set search_path = pg_catalog, public, auth, vnext_core, vnext_private") == 2
    assert "create table vnext_private" not in sql
    assert "create table vnext_core.case_parcel_set_events" not in sql
    assert "geometry" not in sql
    assert "postgis" not in sql
    assert "nlsc" not in sql
    assert "insert into vnext_core.property_identity_references" not in sql
    assert "update vnext_core.property_identity_references" not in sql
    assert "insert into vnext_core.identity_decisions" not in sql
    assert "insert into vnext_core.property_relations" not in sql
    assert "insert into vnext_core.case_property_links" not in sql
