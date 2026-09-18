"""Internal-only, append-only parcel evidence linkage under existing RLS."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol
from uuid import UUID

from pydantic import ValidationError

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.feature_flags import VNextFeatureFlags
from services.vnext.identity_command_repository import _translate_database_error
from services.vnext.parcel_evidence import (
    PARCEL_EVIDENCE_FACT_TYPE, ParcelEvidenceEnvelope, canonical_parcel_evidence,
    parcel_evidence_draft,
)
from services.vnext.persistence import (
    CASE_WRITE_ROLES, IdempotencyDecision, IdempotencyReservation, _append_audit,
)
from services.vnext.property_graph import _validated_evidence_draft

PARCEL_EVIDENCE_RESPONSE_TYPE = "parcel_evidence"


@dataclass(frozen=True)
class ParcelEvidenceRecord:
    evidence_id: UUID
    evidence_link_id: UUID
    content_hash: str
    created_at: datetime


@dataclass(frozen=True)
class ParcelEvidenceOutcome:
    record: ParcelEvidenceRecord
    envelope: ParcelEvidenceEnvelope
    replayed: bool
    duplicate: bool


class ParcelEvidenceWriter(Protocol):
    def require_target(self, **kwargs: object) -> None: ...
    def append(self, **kwargs: object) -> tuple[ParcelEvidenceRecord, bool]: ...
    def get_by_evidence_id(self, **kwargs: object) -> ParcelEvidenceRecord: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...
    def mark_failed(self, **kwargs: object) -> None: ...


class PostgresParcelEvidenceRepository:
    def __init__(self, principal_context: DatabasePrincipalContext, authorizer: WorkspaceAuthorizer) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    @staticmethod
    def _target_node(connection, workspace_id: UUID, property_entity_id: UUID, parcel_identity_reference_id: UUID):
        return connection.execute(
            "SELECT parcel_node.property_graph_node_id FROM vnext_core.property_entities property "
            "JOIN vnext_core.property_graph_nodes property_node ON "
            "property_node.workspace_id = property.workspace_id AND property_node.node_type = 'property' "
            "AND property_node.record_id = property.property_entity_id "
            "JOIN vnext_core.property_relations relation ON relation.workspace_id = property.workspace_id "
            "AND relation.from_node_id = property_node.property_graph_node_id "
            "JOIN vnext_core.property_graph_nodes parcel_node ON "
            "parcel_node.workspace_id = relation.workspace_id AND parcel_node.property_graph_node_id = relation.to_node_id "
            "JOIN vnext_core.property_identity_references reference ON "
            "reference.workspace_id = parcel_node.workspace_id AND reference.identity_reference_id = parcel_node.record_id "
            "WHERE property.workspace_id = %s AND property.property_entity_id = %s "
            "AND property.entity_status <> 'archived' AND relation.relation_type = 'property_parcel' "
            "AND relation.relation_status = 'proposed' AND relation.identity_confirmation_id IS NULL "
            "AND relation.source_id = 'user-upload' AND relation.source_type = 'user' "
            "AND relation.source_environment = 'production' "
            "AND parcel_node.node_type = 'parcel' AND reference.identity_reference_id = %s "
            "AND reference.reference_type = 'parcel' AND reference.reference_status = 'unverified' "
            "AND reference.source_id = 'user-upload' AND reference.source_type = 'user' "
            "AND reference.source_environment = 'production' LIMIT 1",
            (workspace_id, property_entity_id, parcel_identity_reference_id),
        ).fetchone()

    def require_target(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, parcel_identity_reference_id: UUID,
    ) -> None:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        with self._principal_context.transaction(principal) as connection:
            node = self._target_node(connection, workspace_id, property_entity_id, parcel_identity_reference_id)
        if node is None:
            raise VNextError.not_found()

    def get_by_evidence_id(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, parcel_identity_reference_id: UUID,
        evidence_id: UUID,
    ) -> ParcelEvidenceRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        with self._principal_context.transaction(principal) as connection:
            node = self._target_node(connection, workspace_id, property_entity_id, parcel_identity_reference_id)
            if node is None:
                raise VNextError.not_found()
            row = connection.execute(
                "SELECT evidence.evidence_id, link.evidence_link_id, evidence.content_hash, evidence.created_at "
                "FROM vnext_core.evidence_items evidence JOIN vnext_core.evidence_links link "
                "ON link.workspace_id = evidence.workspace_id AND link.evidence_id = evidence.evidence_id "
                "WHERE evidence.workspace_id = %s AND evidence.evidence_id = %s "
                "AND link.subject_node_id = %s AND link.link_type = 'describes' "
                "AND link.fact_scope = %s AND evidence.fact_type = %s "
                "AND evidence.value_schema = 'parcel-evidence-v1'",
                (workspace_id, evidence_id, node[0], PARCEL_EVIDENCE_FACT_TYPE, PARCEL_EVIDENCE_FACT_TYPE),
            ).fetchone()
        if row is None:
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        return ParcelEvidenceRecord(UUID(str(row[0])), UUID(str(row[1])), str(row[2]), row[3])

    def append(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, parcel_identity_reference_id: UUID,
        envelope: ParcelEvidenceEnvelope, content_hash: str,
        idempotency_record_id: UUID, request_id: str,
    ) -> tuple[ParcelEvidenceRecord, bool]:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        draft = parcel_evidence_draft(envelope)
        source, selected = _validated_evidence_draft(draft)
        try:
            with self._principal_context.transaction(principal) as connection:
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"parcel-evidence:{workspace_id}:{parcel_identity_reference_id}:{content_hash}",),
                )
                node = self._target_node(connection, workspace_id, property_entity_id, parcel_identity_reference_id)
                if node is None:
                    raise VNextError.not_found()
                duplicate = connection.execute(
                    "SELECT evidence.evidence_id, link.evidence_link_id, evidence.created_at "
                    "FROM vnext_core.evidence_items evidence JOIN vnext_core.evidence_links link "
                    "ON link.workspace_id = evidence.workspace_id AND link.evidence_id = evidence.evidence_id "
                    "WHERE evidence.workspace_id = %s AND evidence.fact_type = %s "
                    "AND evidence.content_hash = %s AND link.subject_node_id = %s "
                    "AND link.link_type = 'describes' AND link.fact_scope = %s LIMIT 1",
                    (workspace_id, PARCEL_EVIDENCE_FACT_TYPE, content_hash, node[0], PARCEL_EVIDENCE_FACT_TYPE),
                ).fetchone()
                if duplicate is None:
                    evidence = connection.execute(
                        "INSERT INTO vnext_core.evidence_items ("
                        "workspace_id, fact_type, value, value_schema, source_id, source_type, "
                        "source_environment, provider, source_record_id, retrieved_at, effective_from, "
                        "coverage_status, coverage, evidence_status, quality_confidence, quality_method, "
                        "quality_status, quality, license_status, license, lineage, content_hash, "
                        "raw_artifact_ref, created_by_user_id"
                        ") VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, "
                        "%s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, "
                        "%s::jsonb, %s, %s, %s) RETURNING evidence_id, created_at",
                        (workspace_id, PARCEL_EVIDENCE_FACT_TYPE, selected["value"], selected["value_schema"],
                         source.source_id, source.source_type.value, draft.source_environment.value,
                         selected["provider"], selected["source_record_id"], draft.retrieved_at,
                         draft.effective_from, draft.coverage_status.value, selected["coverage"],
                         draft.evidence_status.value, selected["quality_confidence"], selected["quality_method"],
                         draft.quality_status.value, selected["quality"], draft.license_status.value,
                         selected["license"], selected["lineage"], content_hash,
                         selected["raw_artifact_ref"], principal.user_id),
                    ).fetchone()
                    if evidence is None:
                        raise VNextError.permission_denied()
                    link = connection.execute(
                        "INSERT INTO vnext_core.evidence_links ("
                        "workspace_id, evidence_id, subject_node_id, link_type, fact_scope, created_by_user_id"
                        ") VALUES (%s, %s, %s, 'describes', %s, %s) RETURNING evidence_link_id",
                        (workspace_id, evidence[0], node[0], PARCEL_EVIDENCE_FACT_TYPE, principal.user_id),
                    ).fetchone()
                    if link is None:
                        raise VNextError(ErrorCode.INTERNAL_ERROR)
                    record = ParcelEvidenceRecord(UUID(str(evidence[0])), UUID(str(link[0])), content_hash, evidence[1])
                else:
                    record = ParcelEvidenceRecord(UUID(str(duplicate[0])), UUID(str(duplicate[1])), content_hash, duplicate[2])
                completed = connection.execute(
                    "UPDATE vnext_private.idempotency_records SET operation_status = 'succeeded', "
                    "response_status_code = %s, response_reference_type = %s, response_reference_id = %s, "
                    "updated_at = clock_timestamp() WHERE idempotency_record_id = %s AND workspace_id = %s "
                    "AND actor_user_id = %s AND operation_status = 'pending' RETURNING idempotency_key_hash",
                    (201 if duplicate is None else 200, PARCEL_EVIDENCE_RESPONSE_TYPE, record.evidence_id,
                     idempotency_record_id, workspace_id, principal.user_id),
                ).fetchone()
                if completed is None:
                    raise VNextError.idempotency_conflict()
                if duplicate is None:
                    _append_audit(
                        connection, principal=principal, workspace_id=workspace_id,
                        event_type="parcel_evidence.attached", resource_type="evidence_item",
                        resource_id=record.evidence_id, request_id=request_id,
                        outcome="succeeded", idempotency_key_hash=str(completed[0]),
                        metadata={"property_entity_id": str(property_entity_id),
                                  "parcel_identity_reference_id": str(parcel_identity_reference_id)},
                    )
                return record, duplicate is not None
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None


class ParcelEvidenceApplicationService:
    def __init__(
        self, *, flags: VNextFeatureFlags, authorizer: WorkspaceAuthorizer,
        writer: ParcelEvidenceWriter, idempotency_repository: IdempotencyWriter,
    ) -> None:
        self._flags = flags
        self._authorizer = authorizer
        self._writer = writer
        self._idempotency_repository = idempotency_repository

    def attach(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, parcel_identity_reference_id: UUID,
        envelope: ParcelEvidenceEnvelope | Mapping[str, object],
        idempotency_key: str, request_id: str,
    ) -> ParcelEvidenceOutcome:
        if not isinstance(principal, AuthenticatedPrincipal):
            raise VNextError.authentication_required()
        if not self._flags.identity_v1:
            raise VNextError.not_found()
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        try:
            selected = ParcelEvidenceEnvelope.model_validate(envelope)
        except ValidationError:
            raise VNextError.validation_failed() from None
        canonical, content_hash = canonical_parcel_evidence(selected)
        self._writer.require_target(
            principal=principal, workspace_id=workspace_id,
            property_entity_id=property_entity_id,
            parcel_identity_reference_id=parcel_identity_reference_id,
        )
        route = f"/internal/vnext/properties/{property_entity_id}/parcels/{parcel_identity_reference_id}/evidence"
        request_payload = json.dumps(
            {"workspace_id": str(workspace_id), "envelope": json.loads(canonical)},
            ensure_ascii=True, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
        reservation = self._idempotency_repository.reserve(
            principal=principal, workspace_id=workspace_id, method="POST",
            canonical_route=route, idempotency_key=idempotency_key,
            canonical_request=request_payload,
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            if reservation.operation_status == "pending":
                raise VNextError(ErrorCode.MAINTENANCE)
            if reservation.operation_status == "failed":
                try:
                    code = ErrorCode(str(reservation.response_error_code))
                except ValueError:
                    code = ErrorCode.INTERNAL_ERROR
                raise VNextError(code)
            if (reservation.operation_status != "succeeded"
                or reservation.response_reference_type != PARCEL_EVIDENCE_RESPONSE_TYPE
                or reservation.response_reference_id is None):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            record = self._writer.get_by_evidence_id(
                principal=principal, workspace_id=workspace_id,
                property_entity_id=property_entity_id,
                parcel_identity_reference_id=parcel_identity_reference_id,
                evidence_id=reservation.response_reference_id,
            )
            if record.content_hash != content_hash:
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return ParcelEvidenceOutcome(record, selected, True, False)
        try:
            record, duplicate = self._writer.append(
                principal=principal, workspace_id=workspace_id,
                property_entity_id=property_entity_id,
                parcel_identity_reference_id=parcel_identity_reference_id,
                envelope=selected, content_hash=content_hash,
                idempotency_record_id=reservation.idempotency_record_id,
                request_id=request_id,
            )
        except Exception as error:
            selected_error = error if isinstance(error, VNextError) else VNextError(ErrorCode.INTERNAL_ERROR)
            try:
                self._idempotency_repository.mark_failed(
                    principal=principal, workspace_id=workspace_id,
                    idempotency_record_id=reservation.idempotency_record_id,
                    response_status_code=selected_error.status_code,
                    response_error_code=selected_error.code.value,
                )
            except Exception:
                pass
            if isinstance(error, VNextError):
                raise
            raise selected_error from None
        return ParcelEvidenceOutcome(record, selected, False, duplicate)
