"""Pure evidence rules for PLVR lineage recovery and collision resolution.

This module plans future repairs. It has no database connection and exposes no
write operation. Production evidence must be collected through a separate,
read-only boundary before it is passed to these functions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Iterable, Mapping


class EvidenceLevel(StrEnum):
    LEVEL_A = "LEVEL_A_DIRECT_OFFICIAL_ARTIFACT"
    LEVEL_B = "LEVEL_B_IMMUTABLE_IMPORT_ARTIFACT"
    LEVEL_C = "LEVEL_C_EXPLICIT_OFFICIAL_ROW_IDENTITY"
    LEVEL_D = "LEVEL_D_SUPPORTING_ONLY"
    NONE = "NONE"


class LineageStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"


class DuplicateIdentityTier(StrEnum):
    DUPLICATE_IDENTITY_A = "DUPLICATE_IDENTITY_A"
    DUPLICATE_IDENTITY_B = "DUPLICATE_IDENTITY_B"
    DUPLICATE_IDENTITY_C = "DUPLICATE_IDENTITY_C"
    DUPLICATE_IDENTITY_CONFLICT = "DUPLICATE_IDENTITY_CONFLICT"


class CollisionResolution(StrEnum):
    NO_COLLISION = "NO_COLLISION"
    PROVABLE_DUPLICATE_READY = "PROVABLE_DUPLICATE_READY"
    REPAIR_WITH_COLLISION_READY = "REPAIR_WITH_COLLISION_READY"
    AMBIGUOUS_COLLISION = "AMBIGUOUS_COLLISION"
    UNRESOLVED_COLLISION = "UNRESOLVED_COLLISION"


class DedupeLineage(StrEnum):
    DEDUPE_REBUILD_AUTHORITATIVE = "DEDUPE_REBUILD_AUTHORITATIVE"
    DEDUPE_REBUILD_DERIVABLE = "DEDUPE_REBUILD_DERIVABLE"
    DEDUPE_LEGACY_UNKNOWN = "DEDUPE_LEGACY_UNKNOWN"
    DEDUPE_COLLISION = "DEDUPE_COLLISION"
    DEDUPE_NOT_REQUIRED = "DEDUPE_NOT_REQUIRED"


class RepairCohort(StrEnum):
    AUTHORITATIVE_UPDATE_READY = "AUTHORITATIVE_UPDATE_READY"
    PROVABLE_DUPLICATE_READY = "PROVABLE_DUPLICATE_READY"
    AUTHORITATIVE_REIMPORT_READY = "AUTHORITATIVE_REIMPORT_READY"
    NOT_READY = "NOT_READY"


class BatchClassification(StrEnum):
    AUTHORITATIVE_BAD_IMPORT_BATCH = "AUTHORITATIVE_BAD_IMPORT_BATCH"
    MIXED_BAD_BATCH = "MIXED_BAD_BATCH"
    PARTIAL_LINEAGE_BATCH = "PARTIAL_LINEAGE_BATCH"
    UNRESOLVED_BATCH = "UNRESOLVED_BATCH"


class FutureLineageClassification(StrEnum):
    VALID_SOURCE_FUTURE_SEMANTIC_ANOMALY = "VALID_SOURCE_FUTURE_SEMANTIC_ANOMALY"
    PARSE_OR_IMPORT_ERROR = "PARSE_OR_IMPORT_ERROR"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class LineageEvidence:
    proposed_city: str
    source_name: str = ""
    imported_at: str = ""
    dedupe_key: str = ""
    source_filename: str = ""
    source_artifact_hash: str = ""
    source_artifact_city: str = ""
    raw_row_identity: str = ""
    deterministic_artifact_join: bool = False
    import_run_id: str = ""
    import_artifact_hash: str = ""
    import_run_city: str = ""
    deterministic_run_join: bool = False
    official_transaction_id: str = ""
    official_identity_city: str = ""
    official_identity_verified: bool = False
    immutable_artifact: bool = False
    supporting_signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class LineageDecision:
    status: LineageStatus
    evidence_level: EvidenceLevel
    authoritative_city: str
    reason_code: str


@dataclass(frozen=True)
class DuplicateEvidence:
    left_official_transaction_id: str = ""
    right_official_transaction_id: str = ""
    left_artifact_hash: str = ""
    right_artifact_hash: str = ""
    left_raw_row_hash: str = ""
    right_raw_row_hash: str = ""
    normalized_facts_match: bool = False
    critical_facts_conflict: bool = False


@dataclass(frozen=True)
class DedupeEvidence:
    geography_changes: bool
    algorithm_version: str = ""
    algorithm_version_verified: bool = False
    original_transaction_id: str = ""
    immutable_rebuild_inputs: bool = False
    persisted_facts_sufficient: bool = False
    proposed_key_collision: bool = False


@dataclass(frozen=True)
class BaselineBinding:
    production_snapshot_at: str
    main_commit_sha: str
    official_row_count: int
    invalid_row_count: int


@dataclass(frozen=True)
class RowSnapshot:
    row_id: int | str
    city: str
    district: str
    dedupe_key: str
    before_hash: str


@dataclass(frozen=True)
class CohortCandidate:
    row_id: int | str
    source: str
    before_hash: str
    current_city: str
    current_district: str
    target_city: str
    target_district: str
    lineage_evidence_code: str
    source_artifact_identifier: str
    collision_type: str
    counterpart_id: int | str | None
    counterpart_before_hash: str
    dedupe_disposition: str
    proposed_action: str
    batch_identifier: str
    classification: RepairCohort
    affected_scope: str = ""


@dataclass(frozen=True)
class ScopedSimulationInput:
    baseline_transactions: int
    baseline_invalid_rows: int
    baseline_collisions: int
    baseline_future_rows: int
    candidates: tuple[CohortCandidate, ...]


def classify_lineage(evidence: LineageEvidence) -> LineageDecision:
    """Classify lineage without promoting filenames or geography hints alone."""

    authoritative: list[tuple[EvidenceLevel, str]] = []
    if (
        evidence.immutable_artifact
        and evidence.deterministic_artifact_join
        and evidence.source_artifact_hash
        and evidence.source_filename
        and evidence.raw_row_identity
        and evidence.source_artifact_city
    ):
        authoritative.append((EvidenceLevel.LEVEL_A, evidence.source_artifact_city))
    if (
        evidence.immutable_artifact
        and evidence.deterministic_run_join
        and evidence.import_run_id
        and evidence.import_artifact_hash
        and evidence.import_run_city
    ):
        authoritative.append((EvidenceLevel.LEVEL_B, evidence.import_run_city))
    if (
        evidence.official_identity_verified
        and evidence.official_transaction_id
        and evidence.official_identity_city
    ):
        authoritative.append((EvidenceLevel.LEVEL_C, evidence.official_identity_city))

    targets = {_clean(city) for _, city in authoritative if _clean(city)}
    if len(targets) > 1:
        return LineageDecision(
            LineageStatus.CONFLICTING,
            min((level for level, _ in authoritative), default=EvidenceLevel.NONE),
            "",
            "authoritative_sources_disagree",
        )
    if targets:
        target = next(iter(targets))
        strongest = min(level for level, _ in authoritative)
        if _clean(evidence.proposed_city) != target:
            return LineageDecision(
                LineageStatus.CONFLICTING,
                strongest,
                target,
                "authoritative_city_conflicts_with_proposed_target",
            )
        return LineageDecision(
            LineageStatus.COMPLETE,
            strongest,
            target,
            "authoritative_lineage_complete",
        )

    partial_values = (
        evidence.source_name,
        evidence.imported_at,
        evidence.dedupe_key,
        evidence.source_filename,
        evidence.source_artifact_hash,
        evidence.import_run_id,
        evidence.import_artifact_hash,
        evidence.official_transaction_id,
        *evidence.supporting_signals,
    )
    if any(_clean(value) for value in partial_values):
        return LineageDecision(
            LineageStatus.PARTIAL,
            EvidenceLevel.LEVEL_D,
            "",
            "lineage_metadata_is_not_deterministically_row_linked",
        )
    return LineageDecision(
        LineageStatus.MISSING,
        EvidenceLevel.NONE,
        "",
        "authoritative_lineage_missing",
    )


def classify_duplicate_identity(evidence: DuplicateEvidence) -> DuplicateIdentityTier:
    """Require official identity or immutable raw-row identity for proof."""

    left_id = _clean(evidence.left_official_transaction_id)
    right_id = _clean(evidence.right_official_transaction_id)
    left_artifact = _clean(evidence.left_artifact_hash)
    right_artifact = _clean(evidence.right_artifact_hash)
    if evidence.critical_facts_conflict or (left_id and right_id and left_id != right_id):
        return DuplicateIdentityTier.DUPLICATE_IDENTITY_CONFLICT
    if left_id and left_id == right_id and left_artifact and left_artifact == right_artifact:
        return DuplicateIdentityTier.DUPLICATE_IDENTITY_A
    if (
        evidence.left_raw_row_hash
        and evidence.left_raw_row_hash == evidence.right_raw_row_hash
        and left_artifact
        and left_artifact == right_artifact
    ):
        return DuplicateIdentityTier.DUPLICATE_IDENTITY_B
    if evidence.normalized_facts_match:
        return DuplicateIdentityTier.DUPLICATE_IDENTITY_C
    return DuplicateIdentityTier.DUPLICATE_IDENTITY_CONFLICT


def resolve_collision(
    identity_tier: DuplicateIdentityTier,
    *,
    counterpart_verified: bool,
    authoritative_distinct_rows: bool = False,
) -> CollisionResolution:
    """Resolve a collision without treating fact equality as deletion proof."""

    if not counterpart_verified:
        return CollisionResolution.UNRESOLVED_COLLISION
    if identity_tier in {
        DuplicateIdentityTier.DUPLICATE_IDENTITY_A,
        DuplicateIdentityTier.DUPLICATE_IDENTITY_B,
    }:
        return CollisionResolution.PROVABLE_DUPLICATE_READY
    if authoritative_distinct_rows and identity_tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_CONFLICT:
        return CollisionResolution.REPAIR_WITH_COLLISION_READY
    if identity_tier == DuplicateIdentityTier.DUPLICATE_IDENTITY_C:
        return CollisionResolution.AMBIGUOUS_COLLISION
    return CollisionResolution.UNRESOLVED_COLLISION


def classify_dedupe_lineage(evidence: DedupeEvidence) -> DedupeLineage:
    """Classify whether a geography-sensitive key may be rebuilt."""

    if evidence.proposed_key_collision:
        return DedupeLineage.DEDUPE_COLLISION
    if not evidence.geography_changes:
        return DedupeLineage.DEDUPE_NOT_REQUIRED
    if (
        evidence.algorithm_version_verified
        and evidence.algorithm_version
        and evidence.original_transaction_id
        and evidence.immutable_rebuild_inputs
    ):
        return DedupeLineage.DEDUPE_REBUILD_AUTHORITATIVE
    if (
        evidence.algorithm_version_verified
        and evidence.algorithm_version
        and evidence.persisted_facts_sufficient
    ):
        return DedupeLineage.DEDUPE_REBUILD_DERIVABLE
    return DedupeLineage.DEDUPE_LEGACY_UNKNOWN


def classify_repair_cohort(
    *,
    action: str,
    lineage: LineageDecision,
    target_is_canonical: bool,
    stable_identity_known: bool,
    collision: CollisionResolution,
    dedupe: DedupeLineage,
    batch_artifact_verified: bool = False,
) -> RepairCohort:
    """Admit only fully evidenced rows into a future scoped apply cohort."""

    if (
        lineage.status != LineageStatus.COMPLETE
        or not target_is_canonical
        or not stable_identity_known
        or dedupe
        not in {
            DedupeLineage.DEDUPE_REBUILD_AUTHORITATIVE,
            DedupeLineage.DEDUPE_REBUILD_DERIVABLE,
            DedupeLineage.DEDUPE_NOT_REQUIRED,
        }
    ):
        return RepairCohort.NOT_READY
    if action == "update" and collision == CollisionResolution.NO_COLLISION:
        return RepairCohort.AUTHORITATIVE_UPDATE_READY
    if action == "duplicate" and collision == CollisionResolution.PROVABLE_DUPLICATE_READY:
        return RepairCohort.PROVABLE_DUPLICATE_READY
    if action == "reimport" and batch_artifact_verified:
        return RepairCohort.AUTHORITATIVE_REIMPORT_READY
    return RepairCohort.NOT_READY


def classify_batch(
    *,
    deterministic_artifact_lineage: bool,
    all_rows_share_one_proven_corruption: bool,
    mixed_outcomes: bool,
    partial_metadata: bool,
) -> BatchClassification:
    if deterministic_artifact_lineage and all_rows_share_one_proven_corruption and not mixed_outcomes:
        return BatchClassification.AUTHORITATIVE_BAD_IMPORT_BATCH
    if mixed_outcomes:
        return BatchClassification.MIXED_BAD_BATCH
    if partial_metadata:
        return BatchClassification.PARTIAL_LINEAGE_BATCH
    return BatchClassification.UNRESOLVED_BATCH


def classify_future_lineage(
    *,
    artifact_verified: bool,
    raw_period: str,
    normalized_period: str,
    parse_mismatch: bool = False,
) -> FutureLineageClassification:
    if artifact_verified and parse_mismatch:
        return FutureLineageClassification.PARSE_OR_IMPORT_ERROR
    if artifact_verified and raw_period and raw_period == normalized_period:
        return FutureLineageClassification.VALID_SOURCE_FUTURE_SEMANTIC_ANOMALY
    return FutureLineageClassification.UNRESOLVED


def baseline_hash(binding: BaselineBinding) -> str:
    return _hash_payload(asdict(binding))


def build_scoped_manifest(
    binding: BaselineBinding,
    candidates: Iterable[CohortCandidate],
) -> dict[str, Any]:
    """Build a deterministic, privacy-bounded manifest of ready rows only."""

    entries = []
    for candidate in candidates:
        if candidate.classification == RepairCohort.NOT_READY:
            continue
        if not _clean(candidate.before_hash):
            raise ValueError("ready candidate requires a before hash")
        if candidate.classification == RepairCohort.PROVABLE_DUPLICATE_READY and (
            candidate.counterpart_id is None or not candidate.counterpart_before_hash
        ):
            raise ValueError("duplicate candidate requires a verified counterpart")
        entries.append(_manifest_entry(candidate))
    entries.sort(key=lambda item: item["stable_row_reference"])
    payload: dict[str, Any] = {
        "schema_version": "plvr-scoped-repair-cohort-v1",
        "planner_mode": "read_only",
        "baseline": asdict(binding),
        "baseline_hash": baseline_hash(binding),
        "entries": entries,
        "row_count": len(entries),
        "contains_raw_addresses": False,
        "contains_credentials": False,
    }
    payload["manifest_sha256"] = _hash_payload(payload)
    return payload


def manifest_matches_baseline(manifest: Mapping[str, Any], current: BaselineBinding) -> bool:
    return str(manifest.get("baseline_hash") or "") == baseline_hash(current)


def row_precondition_matches(expected: RowSnapshot, current: RowSnapshot) -> bool:
    """Model the future optimistic WHERE predicate for one source row."""

    return expected == current


def duplicate_preconditions_match(
    expected_bad: RowSnapshot,
    current_bad: RowSnapshot,
    expected_counterpart: RowSnapshot,
    current_counterpart: RowSnapshot,
) -> bool:
    return row_precondition_matches(expected_bad, current_bad) and row_precondition_matches(
        expected_counterpart, current_counterpart
    )


def simulate_scoped_cohort(values: ScopedSimulationInput) -> dict[str, int]:
    """Simulate only admitted rows; never include supporting-only candidates."""

    ready = tuple(candidate for candidate in values.candidates if candidate.classification != RepairCohort.NOT_READY)
    updates = sum(candidate.classification == RepairCohort.AUTHORITATIVE_UPDATE_READY for candidate in ready)
    removals = sum(candidate.classification == RepairCohort.PROVABLE_DUPLICATE_READY for candidate in ready)
    reimports = sum(candidate.classification == RepairCohort.AUTHORITATIVE_REIMPORT_READY for candidate in ready)
    affected_scopes = {candidate.affected_scope for candidate in ready if candidate.affected_scope}
    repaired_invalid = updates + removals + reimports
    return {
        "baseline_transactions": values.baseline_transactions,
        "repair_ready_rows": len(ready),
        "update_candidates": updates,
        "duplicate_removal_candidates": removals,
        "reimport_candidates": reimports,
        "projected_transaction_rows": values.baseline_transactions - removals,
        "projected_invalid_rows": max(0, values.baseline_invalid_rows - repaired_invalid),
        "remaining_collisions": max(0, values.baseline_collisions - removals),
        "future_rows_remaining": values.baseline_future_rows,
        "affected_aggregate_scopes": len(affected_scopes),
    }


def _manifest_entry(candidate: CohortCandidate) -> dict[str, Any]:
    counterpart = (
        _opaque_reference(candidate.source, candidate.counterpart_id)
        if candidate.counterpart_id is not None
        else None
    )
    return {
        "stable_row_reference": _opaque_reference(candidate.source, candidate.row_id),
        "before_hash": candidate.before_hash,
        "current_geography": {
            "city": candidate.current_city,
            "district": candidate.current_district,
        },
        "target_geography": {
            "city": candidate.target_city,
            "district": candidate.target_district,
        },
        "lineage_evidence_code": candidate.lineage_evidence_code,
        "source_artifact_reference": (
            _hash_payload({"artifact": candidate.source_artifact_identifier})
            if candidate.source_artifact_identifier
            else None
        ),
        "collision_type": candidate.collision_type,
        "counterpart_reference": counterpart,
        "counterpart_before_hash": candidate.counterpart_before_hash or None,
        "dedupe_disposition": candidate.dedupe_disposition,
        "proposed_action": candidate.proposed_action,
        "batch_reference": (
            _hash_payload({"batch": candidate.batch_identifier}) if candidate.batch_identifier else None
        ),
        "classification": candidate.classification.value,
        "affected_scope": candidate.affected_scope or None,
    }


def _opaque_reference(source: str, identifier: int | str | None) -> str:
    return _hash_payload({"source": source, "row_id": str(identifier or "")})


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hash_payload(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
