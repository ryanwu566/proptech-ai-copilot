"""Regression tests for Phase 2B-1.5 lineage and collision evidence rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.plvr_lineage_collision_resolution import (
    BaselineBinding,
    BatchClassification,
    CohortCandidate,
    CollisionResolution,
    DedupeEvidence,
    DedupeLineage,
    DuplicateEvidence,
    DuplicateIdentityTier,
    EvidenceLevel,
    FutureLineageClassification,
    LineageEvidence,
    LineageStatus,
    RepairCohort,
    RowSnapshot,
    ScopedSimulationInput,
    baseline_hash,
    build_scoped_manifest,
    classify_batch,
    classify_dedupe_lineage,
    classify_duplicate_identity,
    classify_future_lineage,
    classify_lineage,
    classify_repair_cohort,
    duplicate_preconditions_match,
    manifest_matches_baseline,
    resolve_collision,
    row_precondition_matches,
    simulate_scoped_cohort,
)


ROOT = Path(__file__).resolve().parents[1]


def authoritative_artifact(**overrides: object) -> LineageEvidence:
    values: dict[str, object] = {
        "proposed_city": "桃園市",
        "source_filename": "official-city-file.csv",
        "source_artifact_hash": "artifact-sha256",
        "source_artifact_city": "桃園市",
        "raw_row_identity": "raw-row-7",
        "deterministic_artifact_join": True,
        "immutable_artifact": True,
    }
    values.update(overrides)
    return LineageEvidence(**values)


def baseline(**overrides: object) -> BaselineBinding:
    values: dict[str, object] = {
        "production_snapshot_at": "2026-08-11T15:00:00+08:00",
        "main_commit_sha": "8511576e2de1e4a17433056f5323793e22b5767d",
        "official_row_count": 451_672,
        "invalid_row_count": 126_087,
    }
    values.update(overrides)
    return BaselineBinding(**values)


def candidate(**overrides: object) -> CohortCandidate:
    values: dict[str, object] = {
        "row_id": 7,
        "source": "official_plvr_opendata",
        "before_hash": "a" * 64,
        "current_city": "台南市",
        "current_district": "中壢區",
        "target_city": "桃園市",
        "target_district": "中壢區",
        "lineage_evidence_code": "artifact_hash_and_raw_row_identity",
        "source_artifact_identifier": "private-artifact-id",
        "collision_type": "NO_COLLISION",
        "counterpart_id": None,
        "counterpart_before_hash": "",
        "dedupe_disposition": "DEDUPE_REBUILD_AUTHORITATIVE",
        "proposed_action": "update_geography",
        "batch_identifier": "private-batch-id",
        "classification": RepairCohort.AUTHORITATIVE_UPDATE_READY,
        "affected_scope": "桃園市/中壢區/2025-02",
    }
    values.update(overrides)
    return CohortCandidate(**values)


def test_artifact_hash_file_scope_and_raw_row_identity_are_authoritative() -> None:
    decision = classify_lineage(authoritative_artifact())

    assert decision.status == LineageStatus.COMPLETE
    assert decision.evidence_level == EvidenceLevel.LEVEL_A
    assert decision.authoritative_city == "桃園市"


def test_filename_without_immutable_artifact_context_is_partial() -> None:
    decision = classify_lineage(
        LineageEvidence(proposed_city="桃園市", source_filename="a_lvr_land_a.csv")
    )

    assert decision.status == LineageStatus.PARTIAL
    assert decision.evidence_level == EvidenceLevel.LEVEL_D


def test_district_uniqueness_is_supporting_only() -> None:
    decision = classify_lineage(
        LineageEvidence(proposed_city="桃園市", supporting_signals=("canonical_district_unique",))
    )

    assert decision.status == LineageStatus.PARTIAL
    assert decision.evidence_level == EvidenceLevel.LEVEL_D


def test_artifact_city_conflicting_with_proposed_city_is_conflicting() -> None:
    decision = classify_lineage(authoritative_artifact(proposed_city="高雄市"))

    assert decision.status == LineageStatus.CONFLICTING
    assert decision.reason_code == "authoritative_city_conflicts_with_proposed_target"


def test_missing_lineage_is_not_ready() -> None:
    decision = classify_lineage(LineageEvidence(proposed_city="桃園市"))

    assert decision.status == LineageStatus.MISSING


def test_immutable_row_linked_import_run_is_level_b() -> None:
    decision = classify_lineage(
        LineageEvidence(
            proposed_city="桃園市",
            import_run_id="run-1",
            import_artifact_hash="artifact-hash",
            import_run_city="桃園市",
            deterministic_run_join=True,
            immutable_artifact=True,
        )
    )

    assert decision == decision.__class__(
        LineageStatus.COMPLETE,
        EvidenceLevel.LEVEL_B,
        "桃園市",
        "authoritative_lineage_complete",
    )


def test_verified_official_row_identity_is_level_c() -> None:
    decision = classify_lineage(
        LineageEvidence(
            proposed_city="桃園市",
            official_transaction_id="official-7",
            official_identity_city="桃園市",
            official_identity_verified=True,
        )
    )

    assert decision.status == LineageStatus.COMPLETE
    assert decision.evidence_level == EvidenceLevel.LEVEL_C


def test_two_authoritative_sources_that_disagree_are_conflicting() -> None:
    decision = classify_lineage(
        authoritative_artifact(
            import_run_id="run-1",
            import_artifact_hash="artifact-sha256",
            import_run_city="高雄市",
            deterministic_run_join=True,
        )
    )

    assert decision.status == LineageStatus.CONFLICTING
    assert decision.authoritative_city == ""


def test_same_official_id_and_artifact_is_duplicate_identity_a() -> None:
    tier = classify_duplicate_identity(
        DuplicateEvidence(
            left_official_transaction_id="official-1",
            right_official_transaction_id="official-1",
            left_artifact_hash="artifact",
            right_artifact_hash="artifact",
        )
    )

    assert tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_A


def test_same_raw_row_hash_and_artifact_is_duplicate_identity_b() -> None:
    tier = classify_duplicate_identity(
        DuplicateEvidence(
            left_artifact_hash="artifact",
            right_artifact_hash="artifact",
            left_raw_row_hash="raw-row",
            right_raw_row_hash="raw-row",
        )
    )

    assert tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_B


def test_same_normalized_facts_without_row_identity_is_probable_only() -> None:
    tier = classify_duplicate_identity(DuplicateEvidence(normalized_facts_match=True))

    assert tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_C
    assert resolve_collision(tier, counterpart_verified=True) == CollisionResolution.AMBIGUOUS_COLLISION


def test_conflicting_official_ids_can_never_authorize_deletion() -> None:
    tier = classify_duplicate_identity(
        DuplicateEvidence(
            left_official_transaction_id="official-1",
            right_official_transaction_id="official-2",
            normalized_facts_match=True,
        )
    )

    assert tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_CONFLICT
    assert resolve_collision(tier, counterpart_verified=True) == CollisionResolution.UNRESOLVED_COLLISION


def test_same_dedupe_key_with_conflicting_facts_stays_unresolved() -> None:
    tier = classify_duplicate_identity(DuplicateEvidence(critical_facts_conflict=True))

    assert tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_CONFLICT


def test_provable_duplicate_requires_counterpart_precondition() -> None:
    assert (
        resolve_collision(DuplicateIdentityTier.DUPLICATE_IDENTITY_A, counterpart_verified=False)
        == CollisionResolution.UNRESOLVED_COLLISION
    )
    assert (
        resolve_collision(DuplicateIdentityTier.DUPLICATE_IDENTITY_A, counterpart_verified=True)
        == CollisionResolution.PROVABLE_DUPLICATE_READY
    )


def test_authoritatively_distinct_collision_can_be_repair_ready() -> None:
    result = resolve_collision(
        DuplicateIdentityTier.DUPLICATE_IDENTITY_CONFLICT,
        counterpart_verified=True,
        authoritative_distinct_rows=True,
    )

    assert result == CollisionResolution.REPAIR_WITH_COLLISION_READY


def test_historical_unknown_key_version_is_not_repair_ready() -> None:
    result = classify_dedupe_lineage(DedupeEvidence(geography_changes=True))

    assert result == DedupeLineage.DEDUPE_LEGACY_UNKNOWN


def test_authoritative_dedupe_rebuild_requires_original_identity() -> None:
    result = classify_dedupe_lineage(
        DedupeEvidence(
            geography_changes=True,
            algorithm_version="v2",
            algorithm_version_verified=True,
            original_transaction_id="official-1",
            immutable_rebuild_inputs=True,
        )
    )

    assert result == DedupeLineage.DEDUPE_REBUILD_AUTHORITATIVE


def test_verified_derivable_algorithm_can_be_rebuilt_without_official_id() -> None:
    result = classify_dedupe_lineage(
        DedupeEvidence(
            geography_changes=True,
            algorithm_version="facts-v1",
            algorithm_version_verified=True,
            persisted_facts_sufficient=True,
        )
    )

    assert result == DedupeLineage.DEDUPE_REBUILD_DERIVABLE


def test_new_dedupe_collision_blocks_rebuild() -> None:
    result = classify_dedupe_lineage(
        DedupeEvidence(geography_changes=True, proposed_key_collision=True)
    )

    assert result == DedupeLineage.DEDUPE_COLLISION


def test_unchanged_geography_does_not_require_key_rebuild() -> None:
    result = classify_dedupe_lineage(DedupeEvidence(geography_changes=False))

    assert result == DedupeLineage.DEDUPE_NOT_REQUIRED


def test_complete_no_collision_candidate_enters_update_cohort() -> None:
    result = classify_repair_cohort(
        action="update",
        lineage=classify_lineage(authoritative_artifact()),
        target_is_canonical=True,
        stable_identity_known=True,
        collision=CollisionResolution.NO_COLLISION,
        dedupe=DedupeLineage.DEDUPE_REBUILD_AUTHORITATIVE,
    )

    assert result == RepairCohort.AUTHORITATIVE_UPDATE_READY


def test_supporting_lineage_never_enters_update_cohort() -> None:
    result = classify_repair_cohort(
        action="update",
        lineage=classify_lineage(
            LineageEvidence(proposed_city="桃園市", supporting_signals=("address_city",))
        ),
        target_is_canonical=True,
        stable_identity_known=True,
        collision=CollisionResolution.NO_COLLISION,
        dedupe=DedupeLineage.DEDUPE_REBUILD_DERIVABLE,
    )

    assert result == RepairCohort.NOT_READY


def test_provable_duplicate_enters_duplicate_cohort() -> None:
    result = classify_repair_cohort(
        action="duplicate",
        lineage=classify_lineage(authoritative_artifact()),
        target_is_canonical=True,
        stable_identity_known=True,
        collision=CollisionResolution.PROVABLE_DUPLICATE_READY,
        dedupe=DedupeLineage.DEDUPE_NOT_REQUIRED,
    )

    assert result == RepairCohort.PROVABLE_DUPLICATE_READY


def test_reimport_requires_verified_batch_artifact() -> None:
    common = {
        "action": "reimport",
        "lineage": classify_lineage(authoritative_artifact()),
        "target_is_canonical": True,
        "stable_identity_known": True,
        "collision": CollisionResolution.NO_COLLISION,
        "dedupe": DedupeLineage.DEDUPE_NOT_REQUIRED,
    }

    assert classify_repair_cohort(**common, batch_artifact_verified=False) == RepairCohort.NOT_READY
    assert (
        classify_repair_cohort(**common, batch_artifact_verified=True)
        == RepairCohort.AUTHORITATIVE_REIMPORT_READY
    )


def test_manifest_baseline_hash_mismatch_invalidates_manifest() -> None:
    manifest = build_scoped_manifest(baseline(), ())

    assert manifest_matches_baseline(manifest, baseline())
    assert not manifest_matches_baseline(manifest, baseline(official_row_count=451_673))


def test_changed_production_row_fails_optimistic_precondition() -> None:
    expected = RowSnapshot(7, "台南市", "中壢區", "key", "before")
    changed = RowSnapshot(7, "桃園市", "中壢區", "key", "before")

    assert row_precondition_matches(expected, expected)
    assert not row_precondition_matches(expected, changed)


def test_duplicate_requires_both_rows_to_match_snapshot() -> None:
    bad = RowSnapshot(7, "台南市", "中壢區", "key-a", "hash-a")
    counterpart = RowSnapshot(8, "桃園市", "中壢區", "key-b", "hash-b")
    changed_counterpart = RowSnapshot(8, "桃園市", "中壢區", "key-b", "changed")

    assert duplicate_preconditions_match(bad, bad, counterpart, counterpart)
    assert not duplicate_preconditions_match(bad, bad, counterpart, changed_counterpart)


def test_manifest_is_deterministic_across_identical_snapshots() -> None:
    first = build_scoped_manifest(baseline(), (candidate(row_id=2), candidate(row_id=1)))
    second = build_scoped_manifest(baseline(), (candidate(row_id=1), candidate(row_id=2)))

    assert first == second
    assert first["manifest_sha256"] == second["manifest_sha256"]


def test_manifest_uses_opaque_identifiers_and_has_no_raw_address_field() -> None:
    manifest = build_scoped_manifest(baseline(), (candidate(),))
    encoded = json.dumps(manifest, ensure_ascii=False).lower()

    assert "private-artifact-id" not in encoded
    assert "private-batch-id" not in encoded
    assert "address_text" not in encoded
    assert manifest["entries"][0]["stable_row_reference"] != "7"


def test_duplicate_manifest_requires_counterpart_hash() -> None:
    duplicate = candidate(
        classification=RepairCohort.PROVABLE_DUPLICATE_READY,
        counterpart_id=8,
        counterpart_before_hash="",
    )

    with pytest.raises(ValueError, match="verified counterpart"):
        build_scoped_manifest(baseline(), (duplicate,))


def test_empty_ready_cohort_has_stable_empty_manifest() -> None:
    not_ready = candidate(classification=RepairCohort.NOT_READY)
    manifest = build_scoped_manifest(baseline(), (not_ready,))

    assert manifest["row_count"] == 0
    assert manifest["entries"] == []
    assert len(manifest["manifest_sha256"]) == 64
    assert manifest["baseline_hash"] == baseline_hash(baseline())


def test_unresolved_future_artifact_stays_unresolved() -> None:
    assert (
        classify_future_lineage(
            artifact_verified=False,
            raw_period="",
            normalized_period="2026-10",
        )
        == FutureLineageClassification.UNRESOLVED
    )


def test_authoritative_raw_period_proves_future_source_semantic() -> None:
    assert (
        classify_future_lineage(
            artifact_verified=True,
            raw_period="2026-10",
            normalized_period="2026-10",
        )
        == FutureLineageClassification.VALID_SOURCE_FUTURE_SEMANTIC_ANOMALY
    )


def test_authoritative_parse_mismatch_is_import_error() -> None:
    assert (
        classify_future_lineage(
            artifact_verified=True,
            raw_period="2025-10",
            normalized_period="2026-10",
            parse_mismatch=True,
        )
        == FutureLineageClassification.PARSE_OR_IMPORT_ERROR
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "deterministic_artifact_lineage": True,
                "all_rows_share_one_proven_corruption": True,
                "mixed_outcomes": False,
                "partial_metadata": True,
            },
            BatchClassification.AUTHORITATIVE_BAD_IMPORT_BATCH,
        ),
        (
            {
                "deterministic_artifact_lineage": False,
                "all_rows_share_one_proven_corruption": False,
                "mixed_outcomes": True,
                "partial_metadata": True,
            },
            BatchClassification.MIXED_BAD_BATCH,
        ),
        (
            {
                "deterministic_artifact_lineage": False,
                "all_rows_share_one_proven_corruption": False,
                "mixed_outcomes": False,
                "partial_metadata": True,
            },
            BatchClassification.PARTIAL_LINEAGE_BATCH,
        ),
    ],
)
def test_batch_classification(kwargs: dict[str, bool], expected: BatchClassification) -> None:
    assert classify_batch(**kwargs) == expected


def test_empty_scoped_simulation_does_not_apply_supporting_rows() -> None:
    result = simulate_scoped_cohort(
        ScopedSimulationInput(451_672, 126_087, 57_547, 1, ())
    )

    assert result == {
        "baseline_transactions": 451_672,
        "repair_ready_rows": 0,
        "update_candidates": 0,
        "duplicate_removal_candidates": 0,
        "reimport_candidates": 0,
        "projected_transaction_rows": 451_672,
        "projected_invalid_rows": 126_087,
        "remaining_collisions": 57_547,
        "future_rows_remaining": 1,
        "affected_aggregate_scopes": 0,
    }


def test_scoped_simulation_counts_only_admitted_rows() -> None:
    values = ScopedSimulationInput(
        100,
        20,
        5,
        1,
        (
            candidate(row_id=1),
            candidate(
                row_id=2,
                classification=RepairCohort.PROVABLE_DUPLICATE_READY,
                counterpart_id=3,
                counterpart_before_hash="b" * 64,
            ),
            candidate(row_id=4, classification=RepairCohort.NOT_READY),
        ),
    )

    result = simulate_scoped_cohort(values)

    assert result["repair_ready_rows"] == 2
    assert result["projected_transaction_rows"] == 99
    assert result["projected_invalid_rows"] == 18


def test_phase_2b_15_module_has_no_database_or_write_execution_path() -> None:
    source = (ROOT / "services" / "plvr_lineage_collision_resolution.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "psycopg" not in source
    assert "database_url" not in source
    assert "update real_price_transactions" not in source
    assert "delete from real_price_transactions" not in source
    assert "apply_migration" not in source


def test_committed_summary_is_aggregate_only_and_fail_closed() -> None:
    payload = json.loads(
        (ROOT / "docs" / "plvr-lineage-collision-summary-v1.json").read_text(encoding="utf-8")
    )
    encoded = json.dumps(payload, ensure_ascii=False).lower()
    committed_manifest = payload["scoped_manifest"]
    committed_baseline = BaselineBinding(**committed_manifest["baseline"])

    assert payload["repair_ready_cohorts"]["total_scoped_ready"] == 0
    assert payload["gate"] == "NOT_READY_FOR_ANY_PHASE_2B2"
    assert payload["production_safety"]["rows_changed"] == 0
    assert committed_manifest == build_scoped_manifest(committed_baseline, ())
    assert "address_text" not in encoded
    assert "database_url" not in encoded


def test_document_rejects_mass_update_and_defines_all_repair_options() -> None:
    document = (ROOT / "docs" / "plvr-lineage-collision-resolution.md").read_text(
        encoding="utf-8"
    )

    assert "AUTHORITATIVE_ARTIFACT_UNAVAILABLE" in document
    assert "Option A" in document
    assert "Option B" in document
    assert "Option C" in document
    assert "Option D" in document
    assert "NOT_READY_FOR_ANY_PHASE_2B2" in document
    assert "SELECT only" in document
