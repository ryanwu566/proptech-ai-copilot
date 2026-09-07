"""Atomic persistence for reviewed identity and Case attachment commands."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer, WorkspaceRole
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_resolution import (IdentityCandidateStatus,
                                                IdentityCandidateType,
                                                ResolutionStatus)
from services.vnext.identity_resolution_repository import (
    _CANDIDATE_COLUMNS, _DECISION_COLUMNS, IdentityCandidateRecord,
    IdentityDecisionRecord, _candidate_record, _decision_record)
from services.vnext.persistence import (_CASE_COLUMNS, CaseRecord,
                                        _append_audit, _bounded_text,
                                        _case_record)
from services.vnext.property_graph import (CoverageStatus, SourceEnvironment,
                                           SourceType)

IDENTITY_DECISION_ROLES = frozenset({WorkspaceRole.OWNER, WorkspaceRole.ADMIN})
_REASON_CODE = re.compile(r"^[a-z][a-z0-9._-]{2,79}$")
_CONFIRMABLE_STATES = frozenset(
    {
        ResolutionStatus.CANDIDATES_FOUND.value,
        ResolutionStatus.AMBIGUOUS.value,
        ResolutionStatus.PARTIALLY_RESOLVED.value,
    }
)
_UNCONFIRMABLE_CANDIDATE_STATES = frozenset(
    {
        IdentityCandidateStatus.INSUFFICIENT,
        IdentityCandidateStatus.REJECTED,
        IdentityCandidateStatus.SUPERSEDED,
    }
)
_REFERENCE_TYPES = {
    IdentityCandidateType.ADDRESS: "property_address",
    IdentityCandidateType.GEO_REFERENCE: "property_geo_reference",
    IdentityCandidateType.PARCEL: "property_parcel",
    IdentityCandidateType.BUILDING: "property_building",
}


@dataclass(frozen=True)
class ConfirmationWriteResult:
    decision: IdentityDecisionRecord
    property_entity_id: UUID
    identity_reference_id: UUID
    property_relation_id: UUID


@dataclass(frozen=True)
class CasePropertyLinkRecord:
    case_property_link_id: UUID
    workspace_id: UUID
    case_id: UUID
    property_entity_id: UUID
    identity_resolution_id: UUID
    identity_confirmation_id: UUID
    actor_user_id: UUID
    case_version_before: int
    case_version_after: int
    supersedes_case_property_link_id: UUID | None
    request_id: str
    idempotency_record_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class AttachmentWriteResult:
    case: CaseRecord
    link: CasePropertyLinkRecord


_CASE_LINK_COLUMNS = (
    "case_property_link_id, workspace_id, case_id, property_entity_id, "
    "identity_resolution_id, identity_confirmation_id, actor_user_id, "
    "case_version_before, case_version_after, supersedes_case_property_link_id, "
    "request_id, idempotency_record_id, created_at"
)


def _decoded(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        selected = json.loads(value)
        if isinstance(selected, dict):
            return selected
    raise VNextError.validation_failed()


def _encoded(value: Mapping[str, object]) -> str:
    try:
        encoded = json.dumps(
            dict(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None
    if len(encoded.encode("utf-8")) > 16_384:
        raise VNextError.validation_failed()
    return encoded


def _case_link_record(row: tuple[Any, ...]) -> CasePropertyLinkRecord:
    return CasePropertyLinkRecord(
        case_property_link_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        case_id=UUID(str(row[2])),
        property_entity_id=UUID(str(row[3])),
        identity_resolution_id=UUID(str(row[4])),
        identity_confirmation_id=UUID(str(row[5])),
        actor_user_id=UUID(str(row[6])),
        case_version_before=int(row[7]),
        case_version_after=int(row[8]),
        supersedes_case_property_link_id=(
            None if row[9] is None else UUID(str(row[9]))
        ),
        request_id=str(row[10]),
        idempotency_record_id=UUID(str(row[11])),
        created_at=row[12],
    )


def _translate_database_error(error: Exception) -> VNextError:
    sqlstate = str(getattr(error, "sqlstate", ""))
    if sqlstate in {"40001", "40P01", "23505"}:
        return VNextError.version_conflict()
    if sqlstate == "42501":
        return VNextError.permission_denied()
    if sqlstate == "23503":
        return VNextError.not_found()
    if sqlstate == "23514":
        return VNextError.validation_failed()
    return VNextError(ErrorCode.INTERNAL_ERROR)


class PostgresIdentityCommandRepository:
    """Apply each reviewed identity command in one principal-bound transaction."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    @staticmethod
    def _resolution_state(connection: Any, workspace_id: UUID, resolution_id: UUID):
        return connection.execute(
            "SELECT version, resolution_status, needs_human_confirmation, "
            "coverage_status, coverage FROM vnext_core.identity_resolutions "
            "WHERE workspace_id = %s AND identity_resolution_id = %s",
            (workspace_id, resolution_id),
        ).fetchone()

    @staticmethod
    def _current_version(connection: Any, workspace_id: UUID, resolution_id: UUID, base: int):
        row = connection.execute(
            "SELECT count(*), bool_or(decision_type IN ('confirmed', 'resolution_rejected')) "
            "FROM vnext_core.identity_decisions WHERE workspace_id = %s "
            "AND identity_resolution_id = %s",
            (workspace_id, resolution_id),
        ).fetchone()
        return base + int(row[0]), bool(row[1]) if row[1] is not None else False

    @staticmethod
    def _candidate(
        connection: Any,
        workspace_id: UUID,
        resolution_id: UUID,
        candidate_id: UUID,
    ) -> IdentityCandidateRecord:
        row = connection.execute(
            "SELECT " + _CANDIDATE_COLUMNS + " FROM vnext_core.identity_candidates "
            "WHERE workspace_id = %s AND identity_resolution_id = %s "
            "AND identity_candidate_id = %s",
            (workspace_id, resolution_id, candidate_id),
        ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _candidate_record(row)

    @staticmethod
    def _complete_idempotency(
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        idempotency_record_id: UUID,
        reference_type: str,
        reference_id: UUID,
        status_code: int,
    ) -> str:
        row = connection.execute(
            "UPDATE vnext_private.idempotency_records SET operation_status = 'succeeded', "
            "response_status_code = %s, response_reference_type = %s, "
            "response_reference_id = %s, updated_at = clock_timestamp() "
            "WHERE idempotency_record_id = %s AND workspace_id = %s "
            "AND actor_user_id = %s AND operation_status = 'pending' "
            "RETURNING idempotency_key_hash",
            (
                status_code,
                reference_type,
                reference_id,
                idempotency_record_id,
                workspace_id,
                principal.user_id,
            ),
        ).fetchone()
        if row is None:
            raise VNextError.idempotency_conflict()
        return str(row[0])

    @staticmethod
    def _validate_evidence(
        connection: Any,
        *,
        workspace_id: UUID,
        candidate: IdentityCandidateRecord,
    ) -> UUID:
        if candidate.coverage_status is not CoverageStatus.KNOWN:
            raise VNextError(ErrorCode.COVERAGE_UNAVAILABLE)
        if not candidate.supporting_evidence_ids:
            raise VNextError(ErrorCode.COVERAGE_UNAVAILABLE)
        rows = connection.execute(
            "SELECT evidence_id, coverage_status, evidence_status, quality_status, "
            "license_status, expires_at FROM vnext_core.evidence_items "
            "WHERE workspace_id = %s AND evidence_id = ANY(%s)",
            (workspace_id, list(candidate.supporting_evidence_ids)),
        ).fetchall()
        if len(rows) != len(candidate.supporting_evidence_ids):
            raise VNextError.not_found()
        for row in rows:
            coverage, status, quality, license_status, expires_at = (
                str(row[1]),
                str(row[2]),
                str(row[3]),
                str(row[4]),
                row[5],
            )
            if status == "stale" or expires_at is not None and expires_at <= datetime.now(
                timezone.utc
            ):
                raise VNextError.stale_evidence()
            if status == "conflicting":
                raise VNextError.conflicting_evidence()
            if coverage != "known" or status not in {"available", "user_provided"}:
                raise VNextError(ErrorCode.COVERAGE_UNAVAILABLE)
            if quality != "passed" or license_status not in {"approved", "not_applicable"}:
                raise VNextError.validation_failed()
        return min(candidate.supporting_evidence_ids, key=lambda value: value.int)

    @staticmethod
    def _validate_conflicts(
        connection: Any,
        *,
        workspace_id: UUID,
        resolution_id: UUID,
        candidate_id: UUID,
    ) -> None:
        blocking = connection.execute(
            "SELECT 1 FROM vnext_core.identity_conflicts WHERE workspace_id = %s "
            "AND identity_resolution_id = %s AND severity = 'blocking' "
            "AND resolution_state IN ('open', 'requires_review') "
            "AND (left_candidate_id = %s OR right_candidate_id = %s) LIMIT 1",
            (workspace_id, resolution_id, candidate_id, candidate_id),
        ).fetchone()
        if blocking is not None:
            raise VNextError.conflicting_evidence()

    @staticmethod
    def _materialize_property(
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        candidate: IdentityCandidateRecord,
    ) -> tuple[UUID, bool]:
        if candidate.possible_existing_property_entity_id is not None:
            row = connection.execute(
                "SELECT property_entity_id FROM vnext_core.property_entities "
                "WHERE workspace_id = %s AND property_entity_id = %s",
                (workspace_id, candidate.possible_existing_property_entity_id),
            ).fetchone()
            if row is None:
                raise VNextError.not_found()
            return UUID(str(row[0])), False
        row = connection.execute(
            "INSERT INTO vnext_core.property_entities ("
            "workspace_id, entity_status, display_label, created_by_user_id"
            ") VALUES (%s, 'unverified', %s, %s) RETURNING property_entity_id",
            (workspace_id, candidate.display_identity, principal.user_id),
        ).fetchone()
        if row is None:
            raise VNextError.permission_denied()
        return UUID(str(row[0])), True

    @staticmethod
    def _materialize_reference(
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        candidate: IdentityCandidateRecord,
    ) -> tuple[UUID, bool]:
        if candidate.supporting_reference_ids:
            rows = connection.execute(
                "SELECT identity_reference_id, reference_type, normalized_key, "
                "display_value, source_id, source_type, source_environment, "
                "source_record_id, confidence, confidence_method, reference_status, "
                "valid_from, valid_to FROM vnext_core.property_identity_references "
                "WHERE workspace_id = %s AND identity_reference_id = ANY(%s)",
                (workspace_id, list(candidate.supporting_reference_ids)),
            ).fetchall()
            if len(rows) != len(candidate.supporting_reference_ids):
                raise VNextError.not_found()
            exact: list[UUID] = []
            now = datetime.now(timezone.utc)
            for row in rows:
                if str(row[10]) in {"disputed", "superseded", "rejected", "limited"}:
                    raise VNextError.conflicting_evidence()
                if row[11] is not None and row[11] > now:
                    raise VNextError.stale_evidence()
                if row[12] is not None and row[12] <= now:
                    raise VNextError.stale_evidence()
                if (
                    str(row[1]) == candidate.candidate_type.value
                    and str(row[2]) == candidate.normalized_key
                    and str(row[3]) == candidate.display_identity
                    and str(row[4]) == candidate.source_id
                    and str(row[5]) == candidate.source_type.value
                    and str(row[6]) == candidate.source_environment.value
                    and (None if row[7] is None else str(row[7]))
                    == candidate.source_record_id
                    and float(row[8]) == candidate.confidence
                    and str(row[9]) == candidate.confidence_method
                ):
                    exact.append(UUID(str(row[0])))
            if len(exact) != 1:
                raise VNextError.conflicting_evidence()
            return exact[0], False
        row = connection.execute(
            "INSERT INTO vnext_core.property_identity_references ("
            "workspace_id, reference_type, normalized_key, display_value, source_id, "
            "source_type, source_environment, source_record_id, confidence, "
            "confidence_method, reference_status, created_by_user_id"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'observed', %s) "
            "RETURNING identity_reference_id",
            (
                workspace_id,
                candidate.candidate_type.value,
                candidate.normalized_key,
                candidate.display_identity,
                candidate.source_id,
                candidate.source_type.value,
                candidate.source_environment.value,
                candidate.source_record_id,
                candidate.confidence,
                candidate.confidence_method,
                principal.user_id,
            ),
        ).fetchone()
        if row is None:
            raise VNextError.permission_denied()
        return UUID(str(row[0])), True

    def confirm(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        identity_resolution_id: UUID,
        identity_candidate_id: UUID,
        expected_version: int,
        confirmation_reason: str,
        request_id: str,
        idempotency_record_id: UUID,
    ) -> ConfirmationWriteResult:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=IDENTITY_DECISION_ROLES
        )
        reason = _bounded_text(confirmation_reason, maximum=1000)
        if len(reason) < 8 or expected_version < 1:
            raise VNextError.validation_failed()
        selected_request_id = _bounded_text(request_id, maximum=128)
        try:
            with self._principal_context.transaction(principal) as connection:
                resolution = self._resolution_state(
                    connection, workspace_id, identity_resolution_id
                )
                if resolution is None:
                    raise VNextError.not_found()
                current_version, terminal = self._current_version(
                    connection, workspace_id, identity_resolution_id, int(resolution[0])
                )
                if current_version != expected_version or terminal:
                    raise VNextError.version_conflict()
                if str(resolution[1]) not in _CONFIRMABLE_STATES or not bool(resolution[2]):
                    raise VNextError(ErrorCode.AMBIGUOUS_IDENTITY)
                candidate = self._candidate(
                    connection,
                    workspace_id,
                    identity_resolution_id,
                    identity_candidate_id,
                )
                if (
                    candidate.candidate_status in _UNCONFIRMABLE_CANDIDATE_STATES
                    or not candidate.needs_human_confirmation
                    or candidate.candidate_type is IdentityCandidateType.COMPOSITE_PROPERTY
                ):
                    raise VNextError(ErrorCode.AMBIGUOUS_IDENTITY)
                if (
                    candidate.source_type in {SourceType.DEMO, SourceType.TEST}
                    or candidate.source_environment is not SourceEnvironment.PRODUCTION
                ):
                    raise VNextError.permission_denied()
                already_rejected = connection.execute(
                    "SELECT 1 FROM vnext_core.identity_decisions WHERE workspace_id = %s "
                    "AND identity_resolution_id = %s AND identity_candidate_id = %s "
                    "AND decision_type = 'candidate_rejected' LIMIT 1",
                    (workspace_id, identity_resolution_id, identity_candidate_id),
                ).fetchone()
                if already_rejected is not None:
                    raise VNextError.version_conflict()
                primary_evidence_id = self._validate_evidence(
                    connection, workspace_id=workspace_id, candidate=candidate
                )
                self._validate_conflicts(
                    connection,
                    workspace_id=workspace_id,
                    resolution_id=identity_resolution_id,
                    candidate_id=identity_candidate_id,
                )
                property_entity_id, created_property = self._materialize_property(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    candidate=candidate,
                )
                reference_id, created_reference = self._materialize_reference(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    candidate=candidate,
                )
                decision_id = uuid4()
                decision_row = connection.execute(
                    "INSERT INTO vnext_core.identity_decisions ("
                    "identity_decision_id, workspace_id, identity_resolution_id, "
                    "identity_candidate_id, property_entity_id, "
                    "materialized_identity_reference_id, primary_evidence_id, "
                    "decision_type, decision_reason, resolution_version_observed, "
                    "decision_version, candidate_type_snapshot, candidate_status_snapshot, "
                    "confidence_snapshot, confidence_method_snapshot, "
                    "coverage_status_snapshot, coverage_snapshot, "
                    "supporting_evidence_ids_snapshot, supporting_reference_ids_snapshot, "
                    "source_id_snapshot, source_type_snapshot, source_environment_snapshot, "
                    "source_record_id_snapshot, created_new_property, created_new_reference, "
                    "actor_user_id, request_id, idempotency_record_id"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, 'confirmed', %s, %s, %s, "
                    "%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s, %s, %s) RETURNING " + _DECISION_COLUMNS,
                    (
                        decision_id,
                        workspace_id,
                        identity_resolution_id,
                        identity_candidate_id,
                        property_entity_id,
                        reference_id,
                        primary_evidence_id,
                        reason,
                        expected_version,
                        expected_version + 1,
                        candidate.candidate_type.value,
                        candidate.candidate_status.value,
                        candidate.confidence,
                        candidate.confidence_method,
                        candidate.coverage_status.value,
                        _encoded(candidate.coverage),
                        list(candidate.supporting_evidence_ids),
                        list(candidate.supporting_reference_ids),
                        candidate.source_id,
                        candidate.source_type.value,
                        candidate.source_environment.value,
                        candidate.source_record_id,
                        created_property,
                        created_reference,
                        principal.user_id,
                        selected_request_id,
                        idempotency_record_id,
                    ),
                ).fetchone()
                if decision_row is None:
                    raise VNextError.permission_denied()
                decision = _decision_record(decision_row)
                nodes = connection.execute(
                    "SELECT node_type, record_id, property_graph_node_id "
                    "FROM vnext_core.property_graph_nodes WHERE workspace_id = %s "
                    "AND ((node_type = 'property' AND record_id = %s) "
                    "OR (node_type = %s AND record_id = %s))",
                    (
                        workspace_id,
                        property_entity_id,
                        candidate.candidate_type.value,
                        reference_id,
                    ),
                ).fetchall()
                node_map = {str(row[0]): UUID(str(row[2])) for row in nodes}
                if "property" not in node_map or candidate.candidate_type.value not in node_map:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                relation_id = uuid4()
                relation = connection.execute(
                    "INSERT INTO vnext_core.property_relations ("
                    "property_relation_id, workspace_id, from_node_id, to_node_id, "
                    "relation_type, direction, confidence, confidence_method, source_id, "
                    "source_type, source_environment, evidence_id, relation_status, "
                    "confirmed_by_user_id, confirmed_at, created_by_user_id, "
                    "identity_confirmation_id"
                    ") VALUES (%s, %s, %s, %s, %s, 'directed', %s, %s, %s, %s, %s, %s, "
                    "'confirmed', %s, %s, %s, %s) RETURNING property_relation_id",
                    (
                        relation_id,
                        workspace_id,
                        node_map["property"],
                        node_map[candidate.candidate_type.value],
                        _REFERENCE_TYPES[candidate.candidate_type],
                        candidate.confidence,
                        candidate.confidence_method,
                        candidate.source_id,
                        candidate.source_type.value,
                        candidate.source_environment.value,
                        primary_evidence_id,
                        principal.user_id,
                        decision.created_at,
                        principal.user_id,
                        decision.identity_decision_id,
                    ),
                ).fetchone()
                if relation is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                key_hash = self._complete_idempotency(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    reference_type="identity_decision",
                    reference_id=decision.identity_decision_id,
                    status_code=200,
                )
                _append_audit(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    event_type="identity.confirmed",
                    resource_type="identity_decision",
                    resource_id=decision.identity_decision_id,
                    request_id=selected_request_id,
                    outcome="succeeded",
                    idempotency_key_hash=key_hash,
                    metadata={
                        "resolution_id": str(identity_resolution_id),
                        "candidate_id": str(identity_candidate_id),
                        "property_entity_id": str(property_entity_id),
                        "confirmation_id": str(decision.identity_decision_id),
                        "previous_version": expected_version,
                        "new_version": expected_version + 1,
                    },
                )
                return ConfirmationWriteResult(
                    decision=decision,
                    property_entity_id=property_entity_id,
                    identity_reference_id=reference_id,
                    property_relation_id=UUID(str(relation[0])),
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def reject(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        identity_resolution_id: UUID,
        identity_candidate_id: UUID | None,
        expected_version: int,
        reason_code: str,
        request_id: str,
        idempotency_record_id: UUID,
    ) -> IdentityDecisionRecord:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=IDENTITY_DECISION_ROLES
        )
        selected_reason = reason_code.strip()
        if expected_version < 1 or not _REASON_CODE.fullmatch(selected_reason):
            raise VNextError.validation_failed()
        selected_request_id = _bounded_text(request_id, maximum=128)
        try:
            with self._principal_context.transaction(principal) as connection:
                resolution = self._resolution_state(
                    connection, workspace_id, identity_resolution_id
                )
                if resolution is None:
                    raise VNextError.not_found()
                current_version, terminal = self._current_version(
                    connection, workspace_id, identity_resolution_id, int(resolution[0])
                )
                if current_version != expected_version or terminal:
                    raise VNextError.version_conflict()
                candidate = None
                if identity_candidate_id is not None:
                    candidate = self._candidate(
                        connection,
                        workspace_id,
                        identity_resolution_id,
                        identity_candidate_id,
                    )
                    prior = connection.execute(
                        "SELECT 1 FROM vnext_core.identity_decisions "
                        "WHERE workspace_id = %s AND identity_resolution_id = %s "
                        "AND identity_candidate_id = %s "
                        "AND decision_type = 'candidate_rejected' LIMIT 1",
                        (workspace_id, identity_resolution_id, identity_candidate_id),
                    ).fetchone()
                    if prior is not None:
                        raise VNextError.version_conflict()
                decision_id = uuid4()
                if candidate is None:
                    values = (
                        decision_id,
                        workspace_id,
                        identity_resolution_id,
                        selected_reason,
                        expected_version,
                        expected_version + 1,
                        str(resolution[3]),
                        _encoded(_decoded(resolution[4])),
                        principal.user_id,
                        selected_request_id,
                        idempotency_record_id,
                    )
                    statement = (
                        "INSERT INTO vnext_core.identity_decisions ("
                        "identity_decision_id, workspace_id, identity_resolution_id, "
                        "decision_type, reason_code, resolution_version_observed, "
                        "decision_version, coverage_status_snapshot, coverage_snapshot, "
                        "actor_user_id, request_id, idempotency_record_id"
                        ") VALUES (%s, %s, %s, 'resolution_rejected', %s, %s, %s, %s, "
                        "%s::jsonb, %s, %s, %s) RETURNING "
                        + _DECISION_COLUMNS
                    )
                else:
                    values = (
                        decision_id,
                        workspace_id,
                        identity_resolution_id,
                        candidate.identity_candidate_id,
                        selected_reason,
                        expected_version,
                        expected_version + 1,
                        candidate.candidate_type.value,
                        candidate.candidate_status.value,
                        candidate.confidence,
                        candidate.confidence_method,
                        candidate.coverage_status.value,
                        _encoded(candidate.coverage),
                        list(candidate.supporting_evidence_ids),
                        list(candidate.supporting_reference_ids),
                        candidate.source_id,
                        candidate.source_type.value,
                        candidate.source_environment.value,
                        candidate.source_record_id,
                        principal.user_id,
                        selected_request_id,
                        idempotency_record_id,
                    )
                    statement = (
                        "INSERT INTO vnext_core.identity_decisions ("
                        "identity_decision_id, workspace_id, identity_resolution_id, "
                        "identity_candidate_id, decision_type, reason_code, "
                        "resolution_version_observed, decision_version, "
                        "candidate_type_snapshot, candidate_status_snapshot, "
                        "confidence_snapshot, confidence_method_snapshot, "
                        "coverage_status_snapshot, coverage_snapshot, "
                        "supporting_evidence_ids_snapshot, supporting_reference_ids_snapshot, "
                        "source_id_snapshot, source_type_snapshot, source_environment_snapshot, "
                        "source_record_id_snapshot, actor_user_id, request_id, "
                        "idempotency_record_id"
                        ") VALUES (%s, %s, %s, %s, 'candidate_rejected', %s, %s, %s, %s, "
                        "%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                        "RETURNING "
                        + _DECISION_COLUMNS
                    )
                row = connection.execute(statement, values).fetchone()
                if row is None:
                    raise VNextError.permission_denied()
                decision = _decision_record(row)
                key_hash = self._complete_idempotency(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    reference_type="identity_decision",
                    reference_id=decision.identity_decision_id,
                    status_code=200,
                )
                metadata = {
                    "resolution_id": str(identity_resolution_id),
                    "reason_code": selected_reason,
                    "previous_version": expected_version,
                    "new_version": expected_version + 1,
                }
                if identity_candidate_id is not None:
                    metadata["candidate_id"] = str(identity_candidate_id)
                _append_audit(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    event_type="identity.rejected",
                    resource_type="identity_decision",
                    resource_id=decision.identity_decision_id,
                    request_id=selected_request_id,
                    outcome="succeeded",
                    idempotency_key_hash=key_hash,
                    metadata=metadata,
                )
                return decision
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def get_case_property_link_by_id(
        self,
        *,
        principal: AuthenticatedPrincipal,
        case_property_link_id: UUID,
    ) -> CasePropertyLinkRecord:
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _CASE_LINK_COLUMNS + " FROM vnext_core.case_property_links "
                "WHERE case_property_link_id = %s",
                (case_property_link_id,),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _case_link_record(row)

    def attach_resolution(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        identity_resolution_id: UUID,
        identity_confirmation_id: UUID,
        property_entity_id: UUID,
        expected_case_version: int,
        request_id: str,
        idempotency_record_id: UUID,
    ) -> AttachmentWriteResult:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=IDENTITY_DECISION_ROLES
        )
        if expected_case_version < 1:
            raise VNextError.validation_failed()
        selected_request_id = _bounded_text(request_id, maximum=128)
        try:
            with self._principal_context.transaction(principal) as connection:
                case_row = connection.execute(
                    "SELECT " + _CASE_COLUMNS + " FROM vnext_core.cases "
                    "WHERE workspace_id = %s AND case_id = %s",
                    (workspace_id, case_id),
                ).fetchone()
                if case_row is None:
                    raise VNextError.not_found()
                if int(case_row[7]) != expected_case_version:
                    raise VNextError.version_conflict()
                confirmation = connection.execute(
                    "SELECT identity_decision_id FROM vnext_core.identity_decisions "
                    "WHERE workspace_id = %s AND identity_decision_id = %s "
                    "AND identity_resolution_id = %s AND property_entity_id = %s "
                    "AND decision_type = 'confirmed'",
                    (
                        workspace_id,
                        identity_confirmation_id,
                        identity_resolution_id,
                        property_entity_id,
                    ),
                ).fetchone()
                if confirmation is None:
                    raise VNextError.not_found()
                current = connection.execute(
                    "SELECT link.case_property_link_id FROM vnext_core.case_property_links link "
                    "WHERE link.workspace_id = %s AND link.case_id = %s AND NOT EXISTS ("
                    "SELECT 1 FROM vnext_core.case_property_links later "
                    "WHERE later.workspace_id = link.workspace_id "
                    "AND later.case_id = link.case_id "
                    "AND later.supersedes_case_property_link_id = link.case_property_link_id"
                    ") ORDER BY link.case_version_after DESC LIMIT 1",
                    (workspace_id, case_id),
                ).fetchone()
                supersedes_id = None if current is None else UUID(str(current[0]))
                link_id = uuid4()
                link_row = connection.execute(
                    "INSERT INTO vnext_core.case_property_links ("
                    "case_property_link_id, workspace_id, case_id, property_entity_id, "
                    "identity_resolution_id, identity_confirmation_id, actor_user_id, "
                    "case_version_before, case_version_after, "
                    "supersedes_case_property_link_id, request_id, idempotency_record_id"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING " + _CASE_LINK_COLUMNS,
                    (
                        link_id,
                        workspace_id,
                        case_id,
                        property_entity_id,
                        identity_resolution_id,
                        identity_confirmation_id,
                        principal.user_id,
                        expected_case_version,
                        expected_case_version + 1,
                        supersedes_id,
                        selected_request_id,
                        idempotency_record_id,
                    ),
                ).fetchone()
                if link_row is None:
                    raise VNextError.permission_denied()
                updated_case = connection.execute(
                    "UPDATE vnext_core.cases SET identity_status = 'confirmed', "
                    "version = version + 1, updated_at = clock_timestamp() "
                    "WHERE workspace_id = %s AND case_id = %s AND version = %s "
                    "RETURNING " + _CASE_COLUMNS,
                    (workspace_id, case_id, expected_case_version),
                ).fetchone()
                if updated_case is None:
                    raise VNextError.version_conflict()
                link = _case_link_record(link_row)
                case = _case_record(updated_case)
                key_hash = self._complete_idempotency(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    reference_type="case_property_link",
                    reference_id=link.case_property_link_id,
                    status_code=200,
                )
                _append_audit(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    event_type="case.identity_attached",
                    resource_type="case_property_link",
                    resource_id=link.case_property_link_id,
                    request_id=selected_request_id,
                    outcome="succeeded",
                    idempotency_key_hash=key_hash,
                    metadata={
                        "case_id": str(case_id),
                        "resolution_id": str(identity_resolution_id),
                        "property_entity_id": str(property_entity_id),
                        "confirmation_id": str(identity_confirmation_id),
                        "case_property_link_id": str(link.case_property_link_id),
                        "previous_version": expected_case_version,
                        "new_version": expected_case_version + 1,
                    },
                )
                return AttachmentWriteResult(case=case, link=link)
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None
