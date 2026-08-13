"""Pure-data validation for the Phase 2D PLVR cutover design.

This module validates committed JSON design artifacts only. It has no database
client, environment lookup, SQL execution, deployment call, or mutation path.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


PLAN_SCHEMA_VERSION = "plvr-shadow-cutover-plan-v1"
GATES_SCHEMA_VERSION = "plvr-cutover-validation-gates-v1"
FAILURES_SCHEMA_VERSION = "plvr-cutover-failure-matrix-v1"
APPROVALS_SCHEMA_VERSION = "plvr-cutover-approval-matrix-v1"
SELECTED_SWITCH_MECHANISM = "metadata_backed_active_generation_id"

REQUIRED_APPROVALS = {
    "A_CREATE_PRODUCTION_SCHEMA_OBJECTS",
    "B_WRITE_AUTHORITATIVE_ROWS",
    "C_BUILD_CANDIDATE_AGGREGATES",
    "D_SWITCH_PRODUCTION_READERS",
    "E_RETIRE_OR_DELETE_LEGACY_GENERATIONS",
}
REQUIRED_GATES = {
    "transaction_row_count",
    "canonical_geography_invalid_count",
    "future_publishable_row_count",
    "lineage_missing_count",
    "source_conflict_count",
    "duplicate_authoritative_identity_count",
    "period_range",
    "city_coverage",
    "geographic_unit_coverage",
    "aggregate_scope_count",
    "aggregate_unexplained_scope_count",
    "golden_region_validation",
    "valuation_smoke",
    "market_insight_smoke",
    "read_model_status",
}
REQUIRED_FAILURES = {
    "candidate_table_creation_failure",
    "partial_load",
    "duplicate_load",
    "manifest_mismatch",
    "row_count_mismatch",
    "schema_mismatch",
    "aggregate_rebuild_failure",
    "green_read_failure",
    "blue_green_disagreement",
    "vercel_frontend_deployment_mismatch",
    "render_backend_deployment_mismatch",
    "connection_pool_stale_state",
    "active_generation_switch_failure",
    "post_switch_acceptance_failure",
    "rollback_failure",
}
SECRET_MARKERS = (
    "database_url",
    "postgresql://",
    "postgres://",
    "password",
    "credential",
    "api_key",
    "secret_value",
    "access_token",
)


def validate_cutover_design(
    plan: Mapping[str, Any],
    gates: Mapping[str, Any],
    failure_matrix: Mapping[str, Any],
    approval_matrix: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a deterministic validation report for four design artifacts."""

    errors: list[str] = []
    _expect(plan.get("schema_version") == PLAN_SCHEMA_VERSION, "plan_schema", errors)
    _expect(gates.get("schema_version") == GATES_SCHEMA_VERSION, "gates_schema", errors)
    _expect(
        failure_matrix.get("schema_version") == FAILURES_SCHEMA_VERSION,
        "failure_matrix_schema",
        errors,
    )
    _expect(
        approval_matrix.get("schema_version") == APPROVALS_SCHEMA_VERSION,
        "approval_matrix_schema",
        errors,
    )
    _validate_safety(plan, errors)
    _validate_generation_model(plan, errors)
    _validate_steps(plan, errors)
    _validate_gates(gates, errors)
    _validate_approvals(approval_matrix, errors)
    _validate_failures(failure_matrix, errors)
    _validate_no_secrets(
        {
            "plan": plan,
            "gates": gates,
            "failure_matrix": failure_matrix,
            "approval_matrix": approval_matrix,
        },
        errors,
    )
    return {
        "schema_version": "plvr-cutover-plan-validation-result-v1",
        "status": "pass" if not errors else "fail",
        "error_codes": sorted(set(errors)),
        "production_connection_attempted": False,
        "production_mutation_capability": False,
        "execution_authorized": False,
    }


def _validate_safety(plan: Mapping[str, Any], errors: list[str]) -> None:
    _expect(plan.get("mode") == "DESIGN_ONLY", "mode_not_design_only", errors)
    safety = _mapping(plan.get("safety"))
    for key in (
        "production_writes",
        "production_ddl",
        "production_dml",
        "migrations_executed",
        "candidate_rows_loaded",
        "aggregate_rebuilds",
        "read_path_switches",
        "legacy_rows_deleted",
    ):
        _expect(safety.get(key) == 0, f"safety_{key}_not_zero", errors)
    _expect(safety.get("execution_authorized") is False, "execution_authorized", errors)
    _expect(
        plan.get("production_cutover_performed") is False,
        "production_cutover_performed",
        errors,
    )


def _validate_generation_model(plan: Mapping[str, Any], errors: list[str]) -> None:
    target = _mapping(plan.get("target_generation_model"))
    _expect(
        plan.get("selected_switch_mechanism") == SELECTED_SWITCH_MECHANISM,
        "unsupported_switch_mechanism",
        errors,
    )
    pointer = _mapping(target.get("active_pointer"))
    _expect(
        pointer.get("transaction_binding") == "generation_id",
        "transaction_generation_not_bound",
        errors,
    )
    _expect(
        pointer.get("aggregate_binding") == "same_generation_id",
        "aggregate_generation_not_atomic",
        errors,
    )
    _expect(
        pointer.get("single_row_atomic_switch") is True,
        "active_pointer_not_atomic",
        errors,
    )
    invariants = set(target.get("invariants") or ())
    for invariant in (
        "transaction_and_aggregate_generation_match",
        "candidate_cannot_be_active_before_validation",
        "failed_candidate_remains_inactive",
        "legacy_generation_is_preserved",
    ):
        _expect(invariant in invariants, f"missing_invariant_{invariant}", errors)


def _validate_steps(plan: Mapping[str, Any], errors: list[str]) -> None:
    runbook = _mapping(plan.get("runbook"))
    steps = [item for item in runbook.get("steps") or () if isinstance(item, Mapping)]
    sequences = [item.get("sequence") for item in steps]
    _expect(
        sequences == sorted(sequences) and len(sequences) == len(set(sequences)),
        "runbook_order_invalid",
        errors,
    )
    by_id = {str(item.get("id")): item for item in steps}
    required = {
        "validate_candidate_transactions",
        "validate_candidate_aggregates",
        "run_shadow_comparison",
        "define_and_verify_rollback",
        "capture_rollback_pointer",
        "approve_read_switch",
        "atomic_active_generation_switch",
        "post_switch_acceptance",
    }
    _expect(required <= set(by_id), "runbook_steps_missing", errors)
    if required <= set(by_id):
        switch_order = by_id["atomic_active_generation_switch"]["sequence"]
        for prerequisite in required - {
            "atomic_active_generation_switch",
            "post_switch_acceptance",
        }:
            _expect(
                by_id[prerequisite]["sequence"] < switch_order,
                f"{prerequisite}_after_switch",
                errors,
            )
        _expect(
            by_id["post_switch_acceptance"]["sequence"] > switch_order,
            "acceptance_before_switch",
            errors,
        )
    _expect(
        runbook.get("point_of_no_user_visible_change")
        == "approve_read_switch:completed",
        "no_change_point_missing",
        errors,
    )
    _expect(
        runbook.get("first_user_visible_change")
        == "atomic_active_generation_switch:transaction_commit",
        "first_visible_change_invalid",
        errors,
    )
    _expect(
        runbook.get("cutover_commit_point")
        == "atomic_active_generation_switch:transaction_commit",
        "cutover_commit_point_invalid",
        errors,
    )
    _expect(
        "delete" not in " ".join(by_id).lower(),
        "legacy_deletion_step_present",
        errors,
    )


def _validate_gates(gates: Mapping[str, Any], errors: list[str]) -> None:
    items = [item for item in gates.get("gates") or () if isinstance(item, Mapping)]
    by_id = {str(item.get("id")): item for item in items}
    _expect(REQUIRED_GATES <= set(by_id), "validation_gates_missing", errors)
    for gate_id in REQUIRED_GATES & set(by_id):
        gate = by_id[gate_id]
        _expect(bool(gate.get("expected_baseline")), f"{gate_id}_baseline_missing", errors)
        _expect(bool(gate.get("allowed_delta")), f"{gate_id}_delta_missing", errors)
        _expect(bool(gate.get("fail_closed_rule")), f"{gate_id}_fail_closed_missing", errors)
    _expect(
        _mapping(by_id.get("future_publishable_row_count")).get("expected_baseline")
        == "0",
        "future_publishable_gate_not_zero",
        errors,
    )
    _expect(
        _mapping(by_id.get("canonical_geography_invalid_count")).get(
            "expected_baseline"
        )
        == "0",
        "canonical_invalid_gate_not_zero",
        errors,
    )
    _expect(
        _mapping(by_id.get("lineage_missing_count")).get("expected_baseline") == "0",
        "lineage_gate_not_zero",
        errors,
    )
    _expect(
        _mapping(by_id.get("golden_region_validation")).get("expected_baseline")
        == "7/7",
        "golden_region_gate_invalid",
        errors,
    )


def _validate_approvals(approvals: Mapping[str, Any], errors: list[str]) -> None:
    items = [item for item in approvals.get("approvals") or () if isinstance(item, Mapping)]
    by_id = {str(item.get("id")): item for item in items}
    _expect(REQUIRED_APPROVALS == set(by_id), "approval_boundaries_incomplete", errors)
    for approval_id, approval in by_id.items():
        _expect(
            approval.get("authorized") is False,
            f"{approval_id}_unexpectedly_authorized",
            errors,
        )
        _expect(
            approval.get("independent") is True,
            f"{approval_id}_not_independent",
            errors,
        )
        _expect(bool(approval.get("stop_point")), f"{approval_id}_stop_missing", errors)
    deletion = _mapping(by_id.get("E_RETIRE_OR_DELETE_LEGACY_GENERATIONS"))
    _expect(
        deletion.get("phase_2d_policy") == "PROHIBITED",
        "legacy_deletion_not_prohibited",
        errors,
    )


def _validate_failures(failures: Mapping[str, Any], errors: list[str]) -> None:
    items = [item for item in failures.get("failure_modes") or () if isinstance(item, Mapping)]
    by_id = {str(item.get("id")): item for item in items}
    _expect(REQUIRED_FAILURES <= set(by_id), "failure_modes_missing", errors)
    fields = {
        "detection",
        "impact",
        "automatic_response",
        "manual_response",
        "user_visible",
        "rollback_required",
    }
    for failure_id in REQUIRED_FAILURES & set(by_id):
        _expect(fields <= set(by_id[failure_id]), f"{failure_id}_fields_missing", errors)


def _validate_no_secrets(value: Any, errors: list[str]) -> None:
    serialized = json.dumps(value, ensure_ascii=True, sort_keys=True).lower()
    for marker in SECRET_MARKERS:
        _expect(marker not in serialized, f"secret_marker_{marker}", errors)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _expect(condition: bool, error: str, errors: list[str]) -> None:
    if not condition:
        errors.append(error)
