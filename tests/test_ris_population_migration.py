from __future__ import annotations

from pathlib import Path

from scripts import apply_production_migrations as migration_runner
from scripts import validate_postgres_migration as migration_validator
from scripts.migration_registry import checksum, load_registry


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/019_add_ris_village_demographics.sql"


def _sql() -> str:
    return " ".join(MIGRATION.read_text(encoding="utf-8").lower().split())


def test_migration_registry_freezes_phase3a_migration() -> None:
    registration = load_registry()[-1]

    assert registration.registry_order == 20
    assert registration.logical_id == "production-019-ris-village-demographics"
    assert registration.sequence == 19
    assert registration.filename == MIGRATION.name
    assert registration.execution_policy == "production_runner"
    assert registration.sha256 == checksum(MIGRATION)


def test_production_runner_includes_phase3a_migration_from_registry() -> None:
    assert migration_runner.MIGRATIONS[-1] == MIGRATION
    assert migration_validator.MIGRATIONS[-1] == MIGRATION


def test_migration_defines_monthly_observation_schema_and_business_key() -> None:
    sql = _sql()

    for token in (
        "create table public.ris_village_demographics",
        "id bigint generated always as identity primary key",
        "statistic_yyymm text not null",
        "statistic_month date not null",
        "district_code text not null",
        "site_id text not null",
        "village text not null",
        "audit_reasons jsonb not null default '[]'::jsonb",
        "source_provider text not null default 'ris'",
        "source_dataset text not null default 'odrp014'",
        "unique (statistic_yyymm, district_code)",
    ):
        assert token in sql

    assert "unique (district_code)" not in sql


def test_migration_enforces_numeric_checks_without_rejecting_audit_mismatches() -> None:
    sql = _sql()

    for column in (
        "household_count",
        "total_population",
        "male_population",
        "female_population",
        "age_0_14",
        "age_15_64",
        "age_65_plus",
    ):
        assert f"check ({column} >= 0)" in sql
    for column in ("child_ratio", "working_age_ratio", "elderly_ratio"):
        assert f"check ({column} is null or ({column} >= 0 and {column} <= 1))" in sql
    assert "check (average_household_size is null or average_household_size >= 0)" in sql
    assert "male_population + female_population" not in sql
    assert "age_0_14 + age_15_64 + age_65_plus" not in sql


def test_migration_defines_required_indexes_and_validator_contract() -> None:
    sql = _sql()
    required = {
        "idx_ris_village_demographics_district_month",
        "idx_ris_village_demographics_site_month",
        "idx_ris_village_demographics_month",
    }

    assert "(district_code, statistic_month desc)" in sql
    assert "(site_id, statistic_month desc)" in sql
    assert "(statistic_month)" in sql
    assert "ris_village_demographics" in migration_validator.REQUIRED_TABLES
    assert required.issubset(migration_validator.REQUIRED_INDEXES)


def test_migration_enables_rls_without_browser_policies_or_grants() -> None:
    sql = _sql()

    assert "alter table public.ris_village_demographics enable row level security" in sql
    assert "force row level security" not in sql
    assert "create policy" not in sql
    assert "grant " not in sql
    assert "revoke all on table public.ris_village_demographics from public" in sql
    assert "has_table_privilege('anon', 'public.ris_village_demographics'" in sql
    assert "has_table_privilege('authenticated', 'public.ris_village_demographics'" in sql
