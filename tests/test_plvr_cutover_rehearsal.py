from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from services.plvr_cutover_rehearsal import (
    BLUE_GENERATION_ID,
    DRY_RUN_DATABASE_NAME,
    GREEN_AGGREGATE_COUNT,
    GREEN_GENERATION_ID,
    GREEN_TRANSACTION_COUNT,
    RehearsalError,
    _aggregate_price_delta,
    _decode_snapshot_metadata,
    inspect_dry_run_target,
    resolve_dry_run_url,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def test_explicit_dry_run_target_is_required_without_production_fallback() -> None:
    with pytest.raises(RehearsalError, match="dry_run_database_not_configured"):
        resolve_dry_run_url({"DATABASE_URL": "postgresql://production.invalid/db"})
    with pytest.raises(RehearsalError, match="dry_run_database_not_configured"):
        resolve_dry_run_url(
            {"PILOT_EVIDENCE_DATABASE_URL": "postgresql://production.invalid/db"}
        )


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@example.invalid/plvr_cutover_dryrun",
        "postgresql://user:password@db.example.invalid/plvr_cutover_dryrun",
    ],
)
def test_nonlocal_dry_run_host_is_rejected(database_url: str) -> None:
    with pytest.raises(RehearsalError, match="dry_run_database_host_not_local"):
        resolve_dry_run_url({"PLVR_DRY_RUN_DATABASE_URL": database_url})


def test_wrong_database_name_is_rejected() -> None:
    with pytest.raises(RehearsalError, match="dry_run_database_name_mismatch"):
        resolve_dry_run_url(
            {"PLVR_DRY_RUN_DATABASE_URL": "postgresql://user:password@localhost/not_dry_run"}
        )


def test_snapshot_metadata_accepts_reviewed_plain_text_schema_version() -> None:
    assert _decode_snapshot_metadata("plvr-production-snapshot-v1") == (
        "plvr-production-snapshot-v1"
    )
    assert _decode_snapshot_metadata('"on"') == "on"


def test_aggregate_price_delta_preserves_exact_one_cent_gate_boundary() -> None:
    assert str(_aggregate_price_delta(90.01, 90.0)) == "0.01"
    assert _aggregate_price_delta(90.02, 90.0) > _aggregate_price_delta(90.01, 90.0)


def test_rehearsal_schema_is_not_a_production_migration() -> None:
    schema = ROOT / "database" / "plvr_phase2e_rehearsal.sql"
    assert schema.is_file()
    text = schema.read_text(encoding="utf-8")
    assert "ISOLATED DATABASE ONLY" in text
    assert "plvr_dataset_generations" in text
    assert schema.parent.name == "database"
    assert "migrations" not in schema.parts


def test_dual_read_region_count_uses_publishable_reader_contract() -> None:
    service = (ROOT / "services" / "plvr_cutover_rehearsal.py").read_text(
        encoding="utf-8"
    )
    start = service.index("def _region_transaction_count")
    end = service.index("def _aggregate_count", start)
    assert "and publishable" in service[start:end]


def test_rehearsal_evidence_is_complete_and_secret_free() -> None:
    summary = _read("plvr_cutover_rehearsal_summary.json")
    gates = _read("plvr_cutover_rehearsal_gates.json")
    switch = _read("plvr_cutover_rehearsal_switch.json")
    rollback = _read("plvr_cutover_rehearsal_rollback.json")
    failure = _read("plvr_cutover_rehearsal_failure_injection.json")

    assert summary["green_metrics"]["transaction_count"] == GREEN_TRANSACTION_COUNT
    assert summary["green_metrics"]["aggregate_count"] == GREEN_AGGREGATE_COUNT
    assert summary["hard_gates_passed"] == 15
    assert summary["golden_regions_passed"] == 7
    assert summary["production_connection_attempts"] == 0
    assert summary["production_ddl"] == 0
    assert summary["production_dml"] == 0
    assert summary["production_writes"] == 0
    assert summary["production_approvals_executed"] == []
    assert len(gates["gates"]) == 15
    assert all(item["result"] == "PASS" for item in gates["gates"])
    assert len(gates["golden_regions"]) == 7
    assert all(item["passed"] for item in gates["golden_regions"])
    assert switch["atomic"] is True
    assert switch["before"] == BLUE_GENERATION_ID
    assert switch["after"] == GREEN_GENERATION_ID
    assert rollback["green_retained"] is True
    assert rollback["under_five_minutes"] is True
    assert all(failure["failure_checks"].values())
    assert all(failure["idempotency_checks"].values())

    encoded = json.dumps(
        [summary, gates, switch, rollback, failure],
        ensure_ascii=False,
    ).lower()
    for marker in (
        "postgresql://",
        "password=",
        "database_url",
        "pilot_evidence_database_url",
        "supabase.co",
        "token=",
    ):
        assert marker not in encoded


@pytest.mark.skipif(
    not os.environ.get("PLVR_DRY_RUN_DATABASE_URL"),
    reason="isolated Phase 2E PostgreSQL target is not configured",
)
def test_isolated_postgres_contains_successful_rehearsal_state() -> None:
    import psycopg

    target = inspect_dry_run_target()
    assert target.database_name == DRY_RUN_DATABASE_NAME
    with psycopg.connect(target.database_url, connect_timeout=10) as connection:
        connection.read_only = True
        pointer = connection.execute(
            "select active_generation_id, previous_generation_id "
            "from plvr_active_dataset where dataset_key = 'official_plvr'"
        ).fetchone()
        transaction_count = connection.execute(
            "select count(*) from plvr_generation_transactions where generation_id = %s",
            (GREEN_GENERATION_ID,),
        ).fetchone()[0]
        aggregate_count = connection.execute(
            "select count(*) from plvr_generation_market_aggregates where generation_id = %s",
            (GREEN_GENERATION_ID,),
        ).fetchone()[0]
        mixed = connection.execute(
            """
            select
                (select count(distinct generation_id) from plvr_active_transactions),
                (select count(distinct generation_id) from plvr_active_market_aggregates),
                (select count(distinct generation_id) from plvr_active_region_coverage)
            """
        ).fetchone()
    assert pointer == (GREEN_GENERATION_ID, BLUE_GENERATION_ID)
    assert transaction_count == GREEN_TRANSACTION_COUNT
    assert aggregate_count == GREEN_AGGREGATE_COUNT
    assert mixed == (1, 1, 1)


def _read(name: str) -> dict[str, object]:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))
