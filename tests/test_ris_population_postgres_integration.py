from __future__ import annotations

from pathlib import Path

import pytest

from conftest import assert_safe_ris_postgres_test_url
from scripts.validate_postgres_migration import _statements
from services.postgres_runtime import connect
from services.ris_population_ingestion import ingest_prepared_month, prepare_normalized_month


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/019_add_ris_village_demographics.sql"


def _row(yyymm: str, district_code: str, *, village: str) -> dict[str, object]:
    return {
        "statistic_yyymm": yyymm,
        "statistic_month": "2026-07" if yyymm == "11507" else "2026-04",
        "district_code": district_code,
        "site_id": "臺北市大安區",
        "village": village,
        "household_count": 1,
        "total_population": 2,
        "male_population": 2,
        "female_population": 1,
        "age_0_14": 0,
        "age_15_64": 2,
        "age_65_plus": 0,
        "child_ratio": 0.0,
        "working_age_ratio": 1.0,
        "elderly_ratio": 0.0,
        "average_household_size": 2.0,
        "audit_reasons": ["sex_total_mismatch"],
    }


@pytest.mark.external_database
def test_disposable_postgres_migration_rls_constraints_and_upsert(
    ris_postgres_test_url: str,
) -> None:
    expected_database = assert_safe_ris_postgres_test_url(ris_postgres_test_url)

    with connect(ris_postgres_test_url) as connection:
        actual_database = connection.execute("select current_database()").fetchone()[0]
        assert actual_database == expected_database
        assert actual_database.startswith("ris_population_test")

        # The second assertion is intentionally adjacent to destructive setup.
        assert_safe_ris_postgres_test_url(ris_postgres_test_url)
        with connection.transaction():
            connection.execute("drop table if exists public.ris_village_demographics")
            for statement in _statements(MIGRATION):
                connection.execute(statement)

        july = prepare_normalized_month([_row("11507", "same-code", village="甲里")], rows_source=1)
        april = prepare_normalized_month([_row("11504", "same-code", village="乙里")], rows_source=1)
        first = ingest_prepared_month(connection, july)
        second = ingest_prepared_month(connection, july)
        ingest_prepared_month(connection, april)

        assert first["inserted"] == 1 and first["updated"] == 0
        assert second["inserted"] == 0 and second["updated"] == 1
        assert connection.execute(
            "select count(*) from public.ris_village_demographics"
        ).fetchone()[0] == 2
        assert connection.execute(
            "select audit_reasons from public.ris_village_demographics "
            "where statistic_yyymm = '11507' and district_code = 'same-code'"
        ).fetchone()[0] == ["sex_total_mismatch"]

        rls_enabled = connection.execute(
            "select relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relname = 'ris_village_demographics'"
        ).fetchone()[0]
        assert rls_enabled is True
        assert connection.execute(
            "select count(*) from pg_policies "
            "where schemaname = 'public' and tablename = 'ris_village_demographics'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "select count(*) from information_schema.table_privileges "
            "where table_schema = 'public' and table_name = 'ris_village_demographics' "
            "and grantee in ('PUBLIC', 'anon', 'authenticated')"
        ).fetchone()[0] == 0

        with pytest.raises(Exception):
            with connection.transaction():
                connection.execute(
                    "insert into public.ris_village_demographics ("
                    "statistic_yyymm, statistic_month, district_code, site_id, village, "
                    "household_count, total_population, male_population, female_population, "
                    "age_0_14, age_15_64, age_65_plus, child_ratio, audit_reasons"
                    ") values ('11507', date '2026-07-01', 'negative', 'site', 'village', "
                    "-1, 0, 0, 0, 0, 0, 0, 0, '[]'::jsonb)"
                )
