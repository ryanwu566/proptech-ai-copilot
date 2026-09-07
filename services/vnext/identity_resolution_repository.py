"""Principal-bound append/read persistence for identity-resolution history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping
from uuid import UUID, uuid4

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer, WorkspaceRole
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import VNextError
from services.vnext.identity_resolution import (
    AmbiguityStatus,
    IdentityCandidateStatus,
    IdentityCandidateType,
    IdentityConflictSeverity,
    IdentityConflictState,
    IdentityConflictType,
    IdentityResolutionDraft,
    NormalizedResolutionInput,
    ResolutionAttemptStatus,
    ResolutionErrorCategory,
    ResolutionInputType,
    ResolutionStatus,
)
from services.vnext.property_graph import CoverageStatus, SourceEnvironment, SourceType


IDENTITY_WRITE_ROLES = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.MANAGER,
        WorkspaceRole.MEMBER,
    }
)


@dataclass(frozen=True)
class ResolutionAttemptRecord:
    resolution_attempt_id: UUID
    workspace_id: UUID
    identity_resolution_id: UUID
    attempt_order: int
    strategy_id: str
    provider_id: str
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    status: ResolutionAttemptStatus
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    result_count: int
    error_category: ResolutionErrorCategory | None
    error_code: str | None
    error_retryable: bool | None
    started_at: datetime
    completed_at: datetime
    retrieved_at: datetime | None
    created_by_user_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class IdentityCandidateRecord:
    identity_candidate_id: UUID
    workspace_id: UUID
    identity_resolution_id: UUID
    candidate_type: IdentityCandidateType
    normalized_key: str
    normalized_identity: Mapping[str, object]
    display_identity: str
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    source_record_id: str | None
    retrieved_at: datetime
    confidence: float
    confidence_method: str
    ranking_factors: Mapping[str, object]
    rank: int
    candidate_status: IdentityCandidateStatus
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    supporting_evidence_ids: tuple[UUID, ...]
    supporting_reference_ids: tuple[UUID, ...]
    possible_existing_property_entity_id: UUID | None
    supersedes_candidate_id: UUID | None
    needs_human_confirmation: bool
    created_by_user_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class IdentityConflictRecord:
    identity_conflict_id: UUID
    workspace_id: UUID
    identity_resolution_id: UUID
    left_candidate_id: UUID
    right_candidate_id: UUID | None
    related_identity_reference_id: UUID | None
    related_evidence_id: UUID | None
    related_property_entity_id: UUID | None
    conflict_type: IdentityConflictType
    severity: IdentityConflictSeverity
    source_basis: Mapping[str, object]
    conflict_basis: Mapping[str, object]
    resolution_state: IdentityConflictState
    created_by_user_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class IdentityDecisionRecord:
    identity_decision_id: UUID
    workspace_id: UUID
    identity_resolution_id: UUID
    identity_candidate_id: UUID | None
    property_entity_id: UUID | None
    materialized_identity_reference_id: UUID | None
    primary_evidence_id: UUID | None
    decision_type: str
    decision_reason: str | None
    reason_code: str | None
    resolution_version_observed: int
    decision_version: int
    candidate_type_snapshot: str | None
    candidate_status_snapshot: str | None
    confidence_snapshot: float | None
    confidence_method_snapshot: str | None
    coverage_status_snapshot: CoverageStatus
    coverage_snapshot: Mapping[str, object]
    supporting_evidence_ids_snapshot: tuple[UUID, ...]
    supporting_reference_ids_snapshot: tuple[UUID, ...]
    source_id_snapshot: str | None
    source_type_snapshot: SourceType | None
    source_environment_snapshot: SourceEnvironment | None
    source_record_id_snapshot: str | None
    created_new_property: bool | None
    created_new_reference: bool | None
    actor_user_id: UUID
    request_id: str
    idempotency_record_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class IdentityResolutionRecord:
    identity_resolution_id: UUID
    workspace_id: UUID
    case_id: UUID | None
    resolution_input: NormalizedResolutionInput
    status: ResolutionStatus
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    ambiguity_status: AmbiguityStatus
    needs_human_confirmation: bool
    supersedes_resolution_id: UUID | None
    version: int
    requested_by_user_id: UUID
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    attempts: tuple[ResolutionAttemptRecord, ...]
    candidates: tuple[IdentityCandidateRecord, ...]
    conflicts: tuple[IdentityConflictRecord, ...]
    decisions: tuple[IdentityDecisionRecord, ...] = ()


_RESOLUTION_COLUMNS = (
    "identity_resolution_id, workspace_id, case_id, input_type, raw_input, "
    "normalized_input, normalized_key, normalization_version, resolution_status, coverage_status, "
    "coverage, ambiguity_status, needs_human_confirmation, supersedes_resolution_id, "
    "version, requested_by_user_id, started_at, completed_at, created_at"
)
_ATTEMPT_COLUMNS = (
    "resolution_attempt_id, workspace_id, identity_resolution_id, attempt_order, "
    "strategy_id, provider_id, source_id, source_type, source_environment, "
    "attempt_status, coverage_status, coverage, result_count, error_category, "
    "error_code, error_retryable, started_at, completed_at, retrieved_at, "
    "created_by_user_id, created_at"
)
_CANDIDATE_COLUMNS = (
    "identity_candidate_id, workspace_id, identity_resolution_id, candidate_type, "
    "normalized_key, normalized_identity, display_identity, source_id, source_type, "
    "source_environment, source_record_id, retrieved_at, confidence, confidence_method, "
    "ranking_factors, rank, candidate_status, coverage_status, coverage, "
    "supporting_evidence_ids, supporting_reference_ids, "
    "possible_existing_property_entity_id, supersedes_candidate_id, "
    "needs_human_confirmation, created_by_user_id, created_at"
)
_CONFLICT_COLUMNS = (
    "identity_conflict_id, workspace_id, identity_resolution_id, left_candidate_id, "
    "right_candidate_id, related_identity_reference_id, related_evidence_id, "
    "related_property_entity_id, conflict_type, severity, source_basis, conflict_basis, "
    "resolution_state, created_by_user_id, created_at"
)
_DECISION_COLUMNS = (
    "identity_decision_id, workspace_id, identity_resolution_id, "
    "identity_candidate_id, property_entity_id, materialized_identity_reference_id, "
    "primary_evidence_id, decision_type, decision_reason, reason_code, "
    "resolution_version_observed, decision_version, candidate_type_snapshot, "
    "candidate_status_snapshot, confidence_snapshot, confidence_method_snapshot, "
    "coverage_status_snapshot, coverage_snapshot, supporting_evidence_ids_snapshot, "
    "supporting_reference_ids_snapshot, source_id_snapshot, source_type_snapshot, "
    "source_environment_snapshot, source_record_id_snapshot, created_new_property, "
    "created_new_reference, actor_user_id, request_id, idempotency_record_id, created_at"
)


def _encoded(value: Mapping[str, object]) -> str:
    try:
        result = json.dumps(
            dict(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None
    if len(result.encode("utf-8")) > 16_384:
        raise VNextError.validation_failed()
    return result


def _decoded(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        selected = json.loads(value)
        if isinstance(selected, dict):
            return selected
    raise VNextError.validation_failed()


def _attempt_record(row: tuple[Any, ...]) -> ResolutionAttemptRecord:
    return ResolutionAttemptRecord(
        resolution_attempt_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        identity_resolution_id=UUID(str(row[2])),
        attempt_order=int(row[3]),
        strategy_id=str(row[4]),
        provider_id=str(row[5]),
        source_id=str(row[6]),
        source_type=SourceType(str(row[7])),
        source_environment=SourceEnvironment(str(row[8])),
        status=ResolutionAttemptStatus(str(row[9])),
        coverage_status=CoverageStatus(str(row[10])),
        coverage=_decoded(row[11]),
        result_count=int(row[12]),
        error_category=None if row[13] is None else ResolutionErrorCategory(str(row[13])),
        error_code=None if row[14] is None else str(row[14]),
        error_retryable=None if row[15] is None else bool(row[15]),
        started_at=row[16],
        completed_at=row[17],
        retrieved_at=row[18],
        created_by_user_id=UUID(str(row[19])),
        created_at=row[20],
    )


def _candidate_record(row: tuple[Any, ...]) -> IdentityCandidateRecord:
    return IdentityCandidateRecord(
        identity_candidate_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        identity_resolution_id=UUID(str(row[2])),
        candidate_type=IdentityCandidateType(str(row[3])),
        normalized_key=str(row[4]),
        normalized_identity=_decoded(row[5]),
        display_identity=str(row[6]),
        source_id=str(row[7]),
        source_type=SourceType(str(row[8])),
        source_environment=SourceEnvironment(str(row[9])),
        source_record_id=None if row[10] is None else str(row[10]),
        retrieved_at=row[11],
        confidence=float(row[12]),
        confidence_method=str(row[13]),
        ranking_factors=_decoded(row[14]),
        rank=int(row[15]),
        candidate_status=IdentityCandidateStatus(str(row[16])),
        coverage_status=CoverageStatus(str(row[17])),
        coverage=_decoded(row[18]),
        supporting_evidence_ids=tuple(UUID(str(value)) for value in row[19]),
        supporting_reference_ids=tuple(UUID(str(value)) for value in row[20]),
        possible_existing_property_entity_id=(
            None if row[21] is None else UUID(str(row[21]))
        ),
        supersedes_candidate_id=None if row[22] is None else UUID(str(row[22])),
        needs_human_confirmation=bool(row[23]),
        created_by_user_id=UUID(str(row[24])),
        created_at=row[25],
    )


def _conflict_record(row: tuple[Any, ...]) -> IdentityConflictRecord:
    return IdentityConflictRecord(
        identity_conflict_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        identity_resolution_id=UUID(str(row[2])),
        left_candidate_id=UUID(str(row[3])),
        right_candidate_id=None if row[4] is None else UUID(str(row[4])),
        related_identity_reference_id=None if row[5] is None else UUID(str(row[5])),
        related_evidence_id=None if row[6] is None else UUID(str(row[6])),
        related_property_entity_id=None if row[7] is None else UUID(str(row[7])),
        conflict_type=IdentityConflictType(str(row[8])),
        severity=IdentityConflictSeverity(str(row[9])),
        source_basis=_decoded(row[10]),
        conflict_basis=_decoded(row[11]),
        resolution_state=IdentityConflictState(str(row[12])),
        created_by_user_id=UUID(str(row[13])),
        created_at=row[14],
    )


def _decision_record(row: tuple[Any, ...]) -> IdentityDecisionRecord:
    return IdentityDecisionRecord(
        identity_decision_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        identity_resolution_id=UUID(str(row[2])),
        identity_candidate_id=None if row[3] is None else UUID(str(row[3])),
        property_entity_id=None if row[4] is None else UUID(str(row[4])),
        materialized_identity_reference_id=(
            None if row[5] is None else UUID(str(row[5]))
        ),
        primary_evidence_id=None if row[6] is None else UUID(str(row[6])),
        decision_type=str(row[7]),
        decision_reason=None if row[8] is None else str(row[8]),
        reason_code=None if row[9] is None else str(row[9]),
        resolution_version_observed=int(row[10]),
        decision_version=int(row[11]),
        candidate_type_snapshot=None if row[12] is None else str(row[12]),
        candidate_status_snapshot=None if row[13] is None else str(row[13]),
        confidence_snapshot=None if row[14] is None else float(row[14]),
        confidence_method_snapshot=None if row[15] is None else str(row[15]),
        coverage_status_snapshot=CoverageStatus(str(row[16])),
        coverage_snapshot=_decoded(row[17]),
        supporting_evidence_ids_snapshot=tuple(UUID(str(value)) for value in row[18]),
        supporting_reference_ids_snapshot=tuple(UUID(str(value)) for value in row[19]),
        source_id_snapshot=None if row[20] is None else str(row[20]),
        source_type_snapshot=None if row[21] is None else SourceType(str(row[21])),
        source_environment_snapshot=(
            None if row[22] is None else SourceEnvironment(str(row[22]))
        ),
        source_record_id_snapshot=None if row[23] is None else str(row[23]),
        created_new_property=None if row[24] is None else bool(row[24]),
        created_new_reference=None if row[25] is None else bool(row[25]),
        actor_user_id=UUID(str(row[26])),
        request_id=str(row[27]),
        idempotency_record_id=UUID(str(row[28])),
        created_at=row[29],
    )


def _resolution_record(
    row: tuple[Any, ...],
    *,
    attempts: tuple[ResolutionAttemptRecord, ...],
    candidates: tuple[IdentityCandidateRecord, ...],
    conflicts: tuple[IdentityConflictRecord, ...],
    decisions: tuple[IdentityDecisionRecord, ...] = (),
) -> IdentityResolutionRecord:
    input_type = ResolutionInputType(str(row[3]))
    raw_input = _decoded(row[4])
    normalized_input = _decoded(row[5])
    return IdentityResolutionRecord(
        identity_resolution_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        case_id=None if row[2] is None else UUID(str(row[2])),
        resolution_input=NormalizedResolutionInput(
            input_type=input_type,
            raw_input=raw_input,
            normalized_input=normalized_input,
            normalized_key=str(row[6]),
            normalization_version=str(row[7]),
        ),
        status=ResolutionStatus(str(row[8])),
        coverage_status=CoverageStatus(str(row[9])),
        coverage=_decoded(row[10]),
        ambiguity_status=AmbiguityStatus(str(row[11])),
        needs_human_confirmation=bool(row[12]),
        supersedes_resolution_id=None if row[13] is None else UUID(str(row[13])),
        version=int(row[14]),
        requested_by_user_id=UUID(str(row[15])),
        started_at=row[16],
        completed_at=row[17],
        created_at=row[18],
        attempts=attempts,
        candidates=candidates,
        conflicts=conflicts,
        decisions=decisions,
    )


class PostgresIdentityResolutionRepository:
    """Atomically append one complete run and read its immutable aggregate."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
        *,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer
        self._id_factory = id_factory

    def append_resolution(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        draft: IdentityResolutionDraft,
        case_id: UUID | None = None,
        supersedes_resolution_id: UUID | None = None,
        idempotency_record_id: UUID | None = None,
        idempotency_response_status_code: int | None = None,
        idempotency_operation_status: str | None = None,
    ) -> IdentityResolutionRecord:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=IDENTITY_WRITE_ROLES,
        )
        if (
            not draft.needs_human_confirmation
            or draft.status in {
                ResolutionStatus.RECEIVED,
                ResolutionStatus.NORMALIZING,
                ResolutionStatus.SUPERSEDED,
            }
            or draft.completed_at is None
        ):
            raise VNextError.validation_failed()
        completion_values = (
            idempotency_record_id,
            idempotency_response_status_code,
            idempotency_operation_status,
        )
        if (
            idempotency_record_id is None
            and any(value is not None for value in completion_values[1:])
            or idempotency_record_id is not None
            and (
                idempotency_response_status_code is None
                or not 100 <= idempotency_response_status_code <= 599
                or idempotency_operation_status not in {"succeeded", "failed"}
            )
        ):
            raise VNextError.validation_failed()

        resolution_id = self._id_factory()
        created_at = draft.completed_at
        attempt_ids = [self._id_factory() for _ in draft.attempts]
        candidate_ids = {
            candidate.observation_id: self._id_factory() for candidate in draft.candidates
        }
        conflict_ids = [self._id_factory() for _ in draft.conflicts]
        attempts: list[ResolutionAttemptRecord] = []
        candidates: list[IdentityCandidateRecord] = []
        conflicts: list[IdentityConflictRecord] = []

        with self._principal_context.transaction(principal) as connection:
            connection.execute(
                "INSERT INTO vnext_core.identity_resolutions ("
                "identity_resolution_id, workspace_id, case_id, input_type, raw_input, "
                "normalized_input, normalized_key, normalization_version, resolution_status, "
                "coverage_status, coverage, ambiguity_status, needs_human_confirmation, "
                "supersedes_resolution_id, version, requested_by_user_id, started_at, "
                "completed_at, created_at"
                ") VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, "
                "%s::jsonb, %s, true, %s, 1, %s, %s, %s, %s)",
                (
                    resolution_id,
                    workspace_id,
                    case_id,
                    draft.resolution_input.input_type.value,
                    _encoded(draft.resolution_input.raw_input),
                    _encoded(draft.resolution_input.normalized_input),
                    draft.resolution_input.normalized_key,
                    draft.resolution_input.normalization_version,
                    draft.status.value,
                    draft.coverage_status.value,
                    _encoded(draft.coverage),
                    draft.ambiguity_status.value,
                    supersedes_resolution_id,
                    principal.user_id,
                    draft.started_at,
                    draft.completed_at,
                    created_at,
                ),
            )

            for attempt_id, attempt in zip(attempt_ids, draft.attempts):
                connection.execute(
                    "INSERT INTO vnext_core.resolution_attempts ("
                    "resolution_attempt_id, workspace_id, identity_resolution_id, "
                    "attempt_order, strategy_id, provider_id, source_id, source_type, "
                    "source_environment, attempt_status, coverage_status, coverage, "
                    "result_count, error_category, error_code, error_retryable, started_at, "
                    "completed_at, retrieved_at, created_by_user_id, created_at"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        attempt_id,
                        workspace_id,
                        resolution_id,
                        attempt.attempt_order,
                        attempt.strategy_id,
                        attempt.provider_id,
                        attempt.source_id,
                        attempt.source_type.value,
                        attempt.source_environment.value,
                        attempt.status.value,
                        attempt.coverage_status.value,
                        _encoded(attempt.coverage),
                        attempt.result_count,
                        None if attempt.error_category is None else attempt.error_category.value,
                        attempt.error_code,
                        attempt.error_retryable,
                        attempt.started_at,
                        attempt.completed_at,
                        attempt.retrieved_at,
                        principal.user_id,
                        created_at,
                    ),
                )
                attempts.append(
                    ResolutionAttemptRecord(
                        resolution_attempt_id=attempt_id,
                        workspace_id=workspace_id,
                        identity_resolution_id=resolution_id,
                        attempt_order=attempt.attempt_order,
                        strategy_id=attempt.strategy_id,
                        provider_id=attempt.provider_id,
                        source_id=attempt.source_id,
                        source_type=attempt.source_type,
                        source_environment=attempt.source_environment,
                        status=attempt.status,
                        coverage_status=attempt.coverage_status,
                        coverage=attempt.coverage,
                        result_count=attempt.result_count,
                        error_category=attempt.error_category,
                        error_code=attempt.error_code,
                        error_retryable=attempt.error_retryable,
                        started_at=attempt.started_at,
                        completed_at=attempt.completed_at,
                        retrieved_at=attempt.retrieved_at,
                        created_by_user_id=principal.user_id,
                        created_at=created_at,
                    )
                )

            for candidate in draft.candidates:
                candidate_id = candidate_ids[candidate.observation_id]
                connection.execute(
                    "INSERT INTO vnext_core.identity_candidates ("
                    "identity_candidate_id, workspace_id, identity_resolution_id, "
                    "candidate_type, normalized_key, normalized_identity, display_identity, "
                    "source_id, source_type, source_environment, source_record_id, "
                    "retrieved_at, confidence, confidence_method, ranking_factors, rank, "
                    "candidate_status, coverage_status, coverage, supporting_evidence_ids, "
                    "supporting_reference_ids, possible_existing_property_entity_id, "
                    "supersedes_candidate_id, needs_human_confirmation, created_by_user_id, "
                    "created_at"
                    ") VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, "
                    "%s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, "
                    "true, %s, %s)",
                    (
                        candidate_id,
                        workspace_id,
                        resolution_id,
                        candidate.candidate_type.value,
                        candidate.normalized_key,
                        _encoded(candidate.normalized_identity),
                        candidate.display_identity,
                        candidate.source_id,
                        candidate.source_type.value,
                        candidate.source_environment.value,
                        candidate.source_record_id,
                        candidate.retrieved_at,
                        candidate.confidence,
                        candidate.confidence_method,
                        _encoded(candidate.ranking_factors),
                        candidate.rank,
                        candidate.candidate_status.value,
                        candidate.coverage_status.value,
                        _encoded(candidate.coverage),
                        list(candidate.supporting_evidence_ids),
                        list(candidate.supporting_reference_ids),
                        candidate.possible_existing_property_entity_id,
                        candidate.supersedes_candidate_id,
                        principal.user_id,
                        created_at,
                    ),
                )
                candidates.append(
                    IdentityCandidateRecord(
                        identity_candidate_id=candidate_id,
                        workspace_id=workspace_id,
                        identity_resolution_id=resolution_id,
                        candidate_type=candidate.candidate_type,
                        normalized_key=candidate.normalized_key,
                        normalized_identity=candidate.normalized_identity,
                        display_identity=candidate.display_identity,
                        source_id=candidate.source_id,
                        source_type=candidate.source_type,
                        source_environment=candidate.source_environment,
                        source_record_id=candidate.source_record_id,
                        retrieved_at=candidate.retrieved_at,
                        confidence=candidate.confidence,
                        confidence_method=candidate.confidence_method,
                        ranking_factors=candidate.ranking_factors,
                        rank=candidate.rank,
                        candidate_status=candidate.candidate_status,
                        coverage_status=candidate.coverage_status,
                        coverage=candidate.coverage,
                        supporting_evidence_ids=candidate.supporting_evidence_ids,
                        supporting_reference_ids=candidate.supporting_reference_ids,
                        possible_existing_property_entity_id=(
                            candidate.possible_existing_property_entity_id
                        ),
                        supersedes_candidate_id=candidate.supersedes_candidate_id,
                        needs_human_confirmation=True,
                        created_by_user_id=principal.user_id,
                        created_at=created_at,
                    )
                )

            for conflict_id, conflict in zip(conflict_ids, draft.conflicts):
                left_candidate_id = candidate_ids[conflict.left_observation_id]
                right_candidate_id = (
                    None
                    if conflict.right_observation_id is None
                    else candidate_ids[conflict.right_observation_id]
                )
                connection.execute(
                    "INSERT INTO vnext_core.identity_conflicts ("
                    "identity_conflict_id, workspace_id, identity_resolution_id, "
                    "left_candidate_id, right_candidate_id, related_identity_reference_id, "
                    "related_evidence_id, related_property_entity_id, conflict_type, "
                    "severity, source_basis, conflict_basis, resolution_state, "
                    "created_by_user_id, created_at"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s::jsonb, %s::jsonb, %s, %s, %s)",
                    (
                        conflict_id,
                        workspace_id,
                        resolution_id,
                        left_candidate_id,
                        right_candidate_id,
                        conflict.related_identity_reference_id,
                        conflict.related_evidence_id,
                        conflict.related_property_entity_id,
                        conflict.conflict_type.value,
                        conflict.severity.value,
                        _encoded(conflict.source_basis),
                        _encoded(conflict.conflict_basis),
                        conflict.resolution_state.value,
                        principal.user_id,
                        created_at,
                    ),
                )
                conflicts.append(
                    IdentityConflictRecord(
                        identity_conflict_id=conflict_id,
                        workspace_id=workspace_id,
                        identity_resolution_id=resolution_id,
                        left_candidate_id=left_candidate_id,
                        right_candidate_id=right_candidate_id,
                        related_identity_reference_id=conflict.related_identity_reference_id,
                        related_evidence_id=conflict.related_evidence_id,
                        related_property_entity_id=conflict.related_property_entity_id,
                        conflict_type=conflict.conflict_type,
                        severity=conflict.severity,
                        source_basis=conflict.source_basis,
                        conflict_basis=conflict.conflict_basis,
                        resolution_state=conflict.resolution_state,
                        created_by_user_id=principal.user_id,
                        created_at=created_at,
                    )
                )

            if idempotency_record_id is not None:
                completed = connection.execute(
                    "UPDATE vnext_private.idempotency_records SET "
                    "operation_status = %s, response_status_code = %s, "
                    "response_reference_type = 'identity_resolution', "
                    "response_reference_id = %s, updated_at = clock_timestamp() "
                    "WHERE idempotency_record_id = %s AND workspace_id = %s "
                    "AND actor_user_id = %s AND operation_status = 'pending' "
                    "RETURNING idempotency_record_id",
                    (
                        idempotency_operation_status,
                        idempotency_response_status_code,
                        resolution_id,
                        idempotency_record_id,
                        workspace_id,
                        principal.user_id,
                    ),
                ).fetchone()
                if completed is None:
                    raise VNextError.idempotency_conflict()

        return IdentityResolutionRecord(
            identity_resolution_id=resolution_id,
            workspace_id=workspace_id,
            case_id=case_id,
            resolution_input=draft.resolution_input,
            status=draft.status,
            coverage_status=draft.coverage_status,
            coverage=draft.coverage,
            ambiguity_status=draft.ambiguity_status,
            needs_human_confirmation=True,
            supersedes_resolution_id=supersedes_resolution_id,
            version=1,
            requested_by_user_id=principal.user_id,
            started_at=draft.started_at,
            completed_at=draft.completed_at,
            created_at=created_at,
            attempts=tuple(attempts),
            candidates=tuple(candidates),
            conflicts=tuple(conflicts),
        )

    def get_resolution_by_id(
        self,
        *,
        principal: AuthenticatedPrincipal,
        identity_resolution_id: UUID,
    ) -> IdentityResolutionRecord:
        """Discover a resolution workspace through RLS without tenant enumeration."""

        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT workspace_id FROM vnext_core.identity_resolutions "
                "WHERE identity_resolution_id = %s",
                (identity_resolution_id,),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return self.get_resolution(
            principal=principal,
            workspace_id=UUID(str(row[0])),
            identity_resolution_id=identity_resolution_id,
        )

    def get_decision_by_id(
        self,
        *,
        principal: AuthenticatedPrincipal,
        identity_decision_id: UUID,
    ) -> IdentityDecisionRecord:
        """Read one decision through RLS without disclosing its workspace."""

        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _DECISION_COLUMNS + " FROM vnext_core.identity_decisions "
                "WHERE identity_decision_id = %s",
                (identity_decision_id,),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _decision_record(row)

    def get_resolution(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        identity_resolution_id: UUID,
    ) -> IdentityResolutionRecord:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            resolution = connection.execute(
                "SELECT " + _RESOLUTION_COLUMNS + " FROM vnext_core.identity_resolutions "
                "WHERE workspace_id = %s AND identity_resolution_id = %s",
                (workspace_id, identity_resolution_id),
            ).fetchone()
            if resolution is None:
                raise VNextError.not_found()
            attempts = tuple(
                _attempt_record(row)
                for row in connection.execute(
                    "SELECT " + _ATTEMPT_COLUMNS + " FROM vnext_core.resolution_attempts "
                    "WHERE workspace_id = %s AND identity_resolution_id = %s "
                    "ORDER BY attempt_order",
                    (workspace_id, identity_resolution_id),
                ).fetchall()
            )
            candidates = tuple(
                _candidate_record(row)
                for row in connection.execute(
                    "SELECT " + _CANDIDATE_COLUMNS + " FROM vnext_core.identity_candidates "
                    "WHERE workspace_id = %s AND identity_resolution_id = %s ORDER BY rank",
                    (workspace_id, identity_resolution_id),
                ).fetchall()
            )
            conflicts = tuple(
                _conflict_record(row)
                for row in connection.execute(
                    "SELECT " + _CONFLICT_COLUMNS + " FROM vnext_core.identity_conflicts "
                    "WHERE workspace_id = %s AND identity_resolution_id = %s "
                    "ORDER BY created_at, identity_conflict_id",
                    (workspace_id, identity_resolution_id),
                ).fetchall()
            )
            decisions = tuple(
                _decision_record(row)
                for row in connection.execute(
                    "SELECT " + _DECISION_COLUMNS + " FROM vnext_core.identity_decisions "
                    "WHERE workspace_id = %s AND identity_resolution_id = %s "
                    "ORDER BY decision_version, identity_decision_id",
                    (workspace_id, identity_resolution_id),
                ).fetchall()
            )
        return _resolution_record(
            resolution,
            attempts=attempts,
            candidates=candidates,
            conflicts=conflicts,
            decisions=decisions,
        )
