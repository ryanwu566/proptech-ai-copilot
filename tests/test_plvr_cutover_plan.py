from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

from services.plvr_cutover_plan import (
    REQUIRED_APPROVALS,
    REQUIRED_FAILURES,
    REQUIRED_GATES,
    validate_cutover_design,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def test_committed_phase2d_design_is_valid_and_unexecuted() -> None:
    plan, gates, failures, approvals = _artifacts()
    result = validate_cutover_design(plan, gates, failures, approvals)
    assert result == {
        "schema_version": "plvr-cutover-plan-validation-result-v1",
        "status": "pass",
        "error_codes": [],
        "production_connection_attempted": False,
        "production_mutation_capability": False,
        "execution_authorized": False,
    }
    assert plan["safety"] == {
        "production_writes": 0,
        "production_ddl": 0,
        "production_dml": 0,
        "migrations_executed": 0,
        "candidate_rows_loaded": 0,
        "aggregate_rebuilds": 0,
        "read_path_switches": 0,
        "legacy_rows_deleted": 0,
        "execution_authorized": False,
    }


def test_switch_follows_candidate_validation_shadow_and_rollback() -> None:
    plan, gates, failures, approvals = _artifacts()
    steps = {item["id"]: item for item in plan["runbook"]["steps"]}
    switch = steps["atomic_active_generation_switch"]["sequence"]
    for step in (
        "validate_candidate_transactions",
        "validate_candidate_aggregates",
        "run_shadow_comparison",
        "define_and_verify_rollback",
        "capture_rollback_pointer",
        "approve_read_switch",
    ):
        assert steps[step]["sequence"] < switch

    tampered = copy.deepcopy(plan)
    for item in tampered["runbook"]["steps"]:
        if item["id"] == "run_shadow_comparison":
            item["sequence"] = switch + 1
    result = validate_cutover_design(tampered, gates, failures, approvals)
    assert result["status"] == "fail"
    assert "run_shadow_comparison_after_switch" in result["error_codes"]


def test_transaction_and_aggregate_generation_must_switch_together() -> None:
    plan, gates, failures, approvals = _artifacts()
    pointer = plan["target_generation_model"]["active_pointer"]
    assert pointer == {
        "dataset_key": "official_plvr",
        "transaction_binding": "generation_id",
        "aggregate_binding": "same_generation_id",
        "single_row_atomic_switch": True,
        "rollback_pointer_recorded": True,
    }
    tampered = copy.deepcopy(plan)
    tampered["target_generation_model"]["active_pointer"][
        "aggregate_binding"
    ] = "independent_generation_id"
    result = validate_cutover_design(tampered, gates, failures, approvals)
    assert "aggregate_generation_not_atomic" in result["error_codes"]


def test_hard_gates_are_complete_and_fail_closed() -> None:
    plan, gates, failures, approvals = _artifacts()
    by_id = {item["id"]: item for item in gates["gates"]}
    assert REQUIRED_GATES <= set(by_id)
    assert by_id["transaction_row_count"]["expected_baseline"] == "517195"
    assert by_id["future_publishable_row_count"]["expected_baseline"] == "0"
    assert by_id["canonical_geography_invalid_count"]["expected_baseline"] == "0"
    assert by_id["lineage_missing_count"]["expected_baseline"] == "0"
    assert by_id["aggregate_scope_count"]["expected_baseline"] == "9606"
    assert by_id["golden_region_validation"]["expected_baseline"] == "7/7"
    assert len(gates["golden_regions"]) == 7
    assert all(item["fail_closed_rule"] for item in by_id.values())

    for gate_id in (
        "future_publishable_row_count",
        "canonical_geography_invalid_count",
        "lineage_missing_count",
    ):
        tampered = copy.deepcopy(gates)
        next(item for item in tampered["gates"] if item["id"] == gate_id)[
            "expected_baseline"
        ] = "1"
        result = validate_cutover_design(plan, tampered, failures, approvals)
        assert result["status"] == "fail"


def test_approval_boundaries_are_independent_and_grant_nothing() -> None:
    plan, gates, failures, approvals = _artifacts()
    by_id = {item["id"]: item for item in approvals["approvals"]}
    assert set(by_id) == REQUIRED_APPROVALS
    assert all(item["independent"] is True for item in by_id.values())
    assert all(item["authorized"] is False for item in by_id.values())
    assert (
        by_id["E_RETIRE_OR_DELETE_LEGACY_GENERATIONS"]["phase_2d_policy"]
        == "PROHIBITED"
    )

    tampered = copy.deepcopy(approvals)
    tampered["approvals"][3]["authorized"] = True
    result = validate_cutover_design(plan, gates, failures, tampered)
    assert result["status"] == "fail"
    assert any(code.endswith("unexpectedly_authorized") for code in result["error_codes"])


def test_failure_matrix_covers_required_fail_closed_operations() -> None:
    plan, gates, failures, approvals = _artifacts()
    by_id = {item["id"]: item for item in failures["failure_modes"]}
    assert REQUIRED_FAILURES <= set(by_id)
    for item in by_id.values():
        assert {
            "detection",
            "impact",
            "automatic_response",
            "manual_response",
            "user_visible",
            "rollback_required",
        } <= set(item)
    assert by_id["post_switch_acceptance_failure"]["rollback_required"] is True
    assert by_id["rollback_failure"]["user_visible"] is True

    tampered = copy.deepcopy(failures)
    tampered["failure_modes"] = [
        item
        for item in tampered["failure_modes"]
        if item["id"] != "connection_pool_stale_state"
    ]
    result = validate_cutover_design(plan, gates, tampered, approvals)
    assert "failure_modes_missing" in result["error_codes"]


def test_safe_artifacts_and_tools_have_no_secret_or_mutation_surface() -> None:
    artifact_paths = (
        ARTIFACTS / "plvr_cutover_plan.json",
        ARTIFACTS / "plvr_cutover_validation_gates.json",
        ARTIFACTS / "plvr_cutover_failure_matrix.json",
        ARTIFACTS / "plvr_cutover_approval_matrix.json",
    )
    serialized = " ".join(
        path.read_text(encoding="utf-8").lower() for path in artifact_paths
    )
    for marker in (
        "database_url",
        "postgresql://",
        "postgres://",
        "password",
        "secret_value",
        "access_token",
    ):
        assert marker not in serialized

    tool_source = " ".join(
        path.read_text(encoding="utf-8").lower()
        for path in (
            ROOT / "services" / "plvr_cutover_plan.py",
            ROOT / "scripts" / "validate_plvr_cutover_plan.py",
        )
    )
    for forbidden in (
        "import psycopg",
        "import os",
        "subprocess",
        ".execute(",
        "requests.",
        "httpx.",
    ):
        assert forbidden not in tool_source


def test_cli_validation_is_local_and_deterministic() -> None:
    result = subprocess.run(
        ["python", "scripts/validate_plvr_cutover_plan.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "PLVR_CUTOVER_DESIGN_VALIDATION=pass" in result.stdout
    assert "PRODUCTION_CONNECTION_ATTEMPTED=no" in result.stdout
    assert "PRODUCTION_MUTATION_CAPABILITY=no" in result.stdout


def _artifacts() -> tuple[dict, dict, dict, dict]:
    return (
        _read("plvr_cutover_plan.json"),
        _read("plvr_cutover_validation_gates.json"),
        _read("plvr_cutover_failure_matrix.json"),
        _read("plvr_cutover_approval_matrix.json"),
    )


def _read(filename: str) -> dict:
    return json.loads((ARTIFACTS / filename).read_text(encoding="utf-8"))
