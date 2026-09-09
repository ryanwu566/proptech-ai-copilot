from __future__ import annotations

import json
from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts import validate_postgres_migration as migration_validator
from scripts.migration_registry import checksum, load_registry, next_safe_sequence


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/018_add_vnext_spatial_foundation.sql"
REGISTRY = ROOT / "database/migration_registry.json"
FROZEN_STAGE_1 = {
    "013_vnext_workspace_case_foundation.sql": (
        "322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952"
    ),
    "014_vnext_property_graph_evidence_foundation.sql": (
        "0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd"
    ),
    "015_vnext_identity_resolution_candidates.sql": (
        "b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f"
    ),
    "016_vnext_identity_confirmation_case_links.sql": (
        "b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636"
    ),
    "017_vnext_legacy_saved_case_import.sql": (
        "0753b222597d7e0d6cbc618a17bc1d07d047a0d499318936c29880a119182efa"
    ),
}


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_018_is_registered_once_and_advances_sequence() -> None:
    registrations = load_registry()
    matching = [item for item in registrations if item.filename == MIGRATION.name]

    assert len(matching) == 1
    assert matching[0].sequence == 18
    assert matching[0].sha256 == checksum(MIGRATION)
    assert MIGRATION in migration_runner.MIGRATIONS
    assert MIGRATION in migration_validator.MIGRATIONS
    assert next_safe_sequence(registrations) == 19


def test_migrations_013_through_017_remain_frozen() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registered = {item["filename"]: item["sha256"] for item in payload["migrations"]}

    assert {name: registered[name] for name in FROZEN_STAGE_1} == FROZEN_STAGE_1
    assert {
        name: checksum(ROOT / "database/migrations" / name) for name in FROZEN_STAGE_1
    } == FROZEN_STAGE_1


def test_geometry_storage_is_append_only_versioned_and_evidence_linked() -> None:
    sql = _sql()

    assert "create table vnext_core.parcel_geometry_versions" in sql
    assert "source_geometry_wkb bytea not null" in sql
    assert "source_geometry_sha256" in sql
    assert "normalized_geometry jsonb not null" in sql
    assert "normalized_crs = 'epsg:4326'" in sql
    assert "fk_vnext_parcel_geometry_reference" in sql
    assert "fk_vnext_parcel_geometry_evidence" in sql
    assert "uq_vnext_parcel_geometry_parcel_version" in sql
    assert "uq_vnext_parcel_geometry_superseded_once" in sql
    assert "trg_vnext_parcel_geometry_append_only" in sql
    assert "vnext_spatial_geometry_supersession_invalid" in sql


def test_global_layer_registry_is_immutable_and_application_read_only() -> None:
    sql = _sql()
    layer_lines = "\n".join(
        line for line in sql.splitlines() if "spatial_layers" in line
    )

    assert "create table vnext_core.spatial_layers" in sql
    assert "uq_vnext_spatial_layers_key_version" in sql
    assert "trg_vnext_spatial_layers_append_only" in sql
    assert "grant select on vnext_core.spatial_layers to vnext_api" in sql
    assert "grant insert on vnext_core.spatial_layers" not in sql
    assert "grant update on vnext_core.spatial_layers" not in sql
    assert "workspace_id" not in layer_lines


def test_observation_states_and_unknown_safe_constraints_remain_distinct() -> None:
    sql = _sql()

    for status in (
        "present",
        "absent",
        "no_match",
        "unavailable",
        "unknown",
        "partial_coverage",
        "provider_error",
        "stale",
        "not_assessed",
    ):
        assert f"'{status}'" in sql
    assert "observation_status <> 'absent'" in sql
    assert "coverage_status = 'complete'" in sql
    assert "coverage -> 'gaps' = '[]'::jsonb" in sql
    assert "observation_status <> 'partial_coverage'" in sql
    assert "or coverage_status = 'partial'" in sql
    assert "when 'provider_error' then 'unavailable'" in sql
    assert "when 'no_match' then 'unknown'" in sql


def test_authority_constraints_cannot_upgrade_synthetic_or_test_sources() -> None:
    sql = _sql()

    assert "authority_class = 'official' and source_type = 'official'" in sql
    assert "authority_class = 'synthetic'" in sql
    assert "source_type in ('demo', 'test')" in sql
    assert "source_environment in ('demo', 'test')" in sql
    assert "government_verified" not in sql


def test_tenant_tables_use_stage_1_rls_and_global_registry_has_no_write_policy() -> (
    None
):
    sql = _sql()

    for table in ("parcel_geometry_versions", "spatial_observations"):
        assert f"alter table vnext_core.{table} enable row level security" in sql
        assert f"alter table vnext_core.{table} force row level security" in sql
    assert "parcel_geometry_active_member_select" in sql
    assert "parcel_geometry_active_writer_insert" in sql
    assert "spatial_observations_active_member_select" in sql
    assert "spatial_observations_active_writer_insert" in sql
    assert "to anon" not in sql
    assert "to authenticated" not in sql
    assert "service_role" not in sql
    assert "security definer" not in sql


def test_no_postgis_provider_or_confirmation_surface_is_introduced() -> None:
    sql = _sql()

    assert "create extension" not in sql
    assert "nlsc" not in sql
    assert "insert into vnext_core.property_entities" not in sql
    assert "insert into vnext_core.case_property_links" not in sql
    assert "identity_confirmation" not in sql
