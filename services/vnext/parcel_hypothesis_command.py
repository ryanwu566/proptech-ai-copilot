"""Manual parcel hypotheses on existing PropertyEntity records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_command_repository import _translate_database_error
from services.vnext.parcel_hypothesis import NormalizedParcelHypothesis, normalize_parcel_hypothesis
from services.vnext.persistence import (
    CASE_WRITE_ROLES, IdempotencyDecision, IdempotencyReservation, _append_audit,
)
from services.vnext.property_graph import (
    DATA_SOURCE_REGISTRY, SourceEnvironment, SourceType,
)

PARCEL_HYPOTHESIS_SOURCE_ID = "user-upload"
PARCEL_HYPOTHESIS_RESPONSE_TYPE = "parcel_hypothesis_relation"


@dataclass(frozen=True)
class ParcelHypothesisRecord:
    property_entity_id: UUID
    identity_reference_id: UUID
    relation_id: UUID
    normalized_key: str
    display_value: str
    created_at: datetime


@dataclass(frozen=True)
class ParcelHypothesisOutcome:
    record: ParcelHypothesisRecord
    normalized: NormalizedParcelHypothesis
    replayed: bool


class ParcelHypothesisWriter(Protocol):
    def require_property(self, **kwargs: object) -> None: ...
    def append(self, **kwargs: object) -> ParcelHypothesisRecord: ...
    def get_by_relation_id(self, **kwargs: object) -> ParcelHypothesisRecord: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...
    def mark_failed(self, **kwargs: object) -> None: ...


class PostgresParcelHypothesisRepository:
    """One principal-bound transaction for reference, graph edge and replay marker."""

    def __init__(self, principal_context: DatabasePrincipalContext, authorizer: WorkspaceAuthorizer) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def require_property(self, *, principal: AuthenticatedPrincipal, workspace_id: UUID, property_entity_id: UUID) -> None:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT 1 FROM vnext_core.property_entities WHERE workspace_id = %s "
                "AND property_entity_id = %s AND entity_status <> 'archived'",
                (workspace_id, property_entity_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()

    def get_by_relation_id(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, relation_id: UUID,
    ) -> ParcelHypothesisRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT reference.identity_reference_id, relation.property_relation_id, "
                "reference.normalized_key, reference.display_value, reference.created_at "
                "FROM vnext_core.property_relations relation "
                "JOIN vnext_core.property_graph_nodes property_node ON "
                "property_node.workspace_id = relation.workspace_id AND property_node.property_graph_node_id = relation.from_node_id "
                "JOIN vnext_core.property_graph_nodes parcel_node ON "
                "parcel_node.workspace_id = relation.workspace_id AND parcel_node.property_graph_node_id = relation.to_node_id "
                "JOIN vnext_core.property_identity_references reference ON "
                "reference.workspace_id = parcel_node.workspace_id AND reference.identity_reference_id = parcel_node.record_id "
                "WHERE relation.workspace_id = %s AND relation.property_relation_id = %s "
                "AND property_node.node_type = 'property' AND property_node.record_id = %s "
                "AND parcel_node.node_type = 'parcel' AND reference.reference_type = 'parcel' "
                "AND relation.relation_type = 'property_parcel' AND relation.relation_status = 'proposed' "
                "AND relation.identity_confirmation_id IS NULL "
                "AND relation.source_id = %s AND relation.source_type = 'user' "
                "AND relation.source_environment = 'production' "
                "AND reference.source_id = %s AND reference.source_type = 'user' "
                "AND reference.source_environment = 'production' AND reference.reference_status = 'unverified'",
                (workspace_id, relation_id, property_entity_id, PARCEL_HYPOTHESIS_SOURCE_ID, PARCEL_HYPOTHESIS_SOURCE_ID),
            ).fetchone()
        if row is None:
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        return ParcelHypothesisRecord(property_entity_id, UUID(str(row[0])), UUID(str(row[1])), str(row[2]), str(row[3]), row[4])

    def append(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, normalized: NormalizedParcelHypothesis,
        idempotency_record_id: UUID, request_id: str,
    ) -> ParcelHypothesisRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        source = DATA_SOURCE_REGISTRY[PARCEL_HYPOTHESIS_SOURCE_ID]
        if (source.source_type is not SourceType.USER
            or SourceEnvironment.PRODUCTION not in source.environments
            or not source.request_appendable):
            raise VNextError.permission_denied()
        try:
            with self._principal_context.transaction(principal) as connection:
                # Serialize this command's duplicate check for a workspace/key.
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"parcel-hypothesis:{workspace_id}:{normalized.normalized_key}",),
                )
                property_node = connection.execute(
                    "SELECT node.property_graph_node_id FROM vnext_core.property_entities property "
                    "JOIN vnext_core.property_graph_nodes node ON node.workspace_id = property.workspace_id "
                    "AND node.node_type = 'property' AND node.record_id = property.property_entity_id "
                    "WHERE property.workspace_id = %s AND property.property_entity_id = %s "
                    "AND property.entity_status <> 'archived'",
                    (workspace_id, property_entity_id),
                ).fetchone()
                if property_node is None:
                    raise VNextError.not_found()
                duplicate = connection.execute(
                    "SELECT 1 FROM vnext_core.property_identity_references "
                    "WHERE workspace_id = %s AND reference_type = 'parcel' AND normalized_key = %s LIMIT 1",
                    (workspace_id, normalized.normalized_key),
                ).fetchone()
                if duplicate is not None:
                    raise VNextError.conflicting_evidence()
                reference = connection.execute(
                    "INSERT INTO vnext_core.property_identity_references ("
                    "workspace_id, reference_type, normalized_key, display_value, source_id, "
                    "source_type, source_environment, reference_status, created_by_user_id"
                    ") VALUES (%s, 'parcel', %s, %s, %s, 'user', 'production', 'unverified', %s) "
                    "RETURNING identity_reference_id, created_at",
                    (workspace_id, normalized.normalized_key, normalized.display_value,
                     PARCEL_HYPOTHESIS_SOURCE_ID, principal.user_id),
                ).fetchone()
                if reference is None:
                    raise VNextError.permission_denied()
                parcel_node = connection.execute(
                    "SELECT property_graph_node_id FROM vnext_core.property_graph_nodes "
                    "WHERE workspace_id = %s AND node_type = 'parcel' AND record_id = %s",
                    (workspace_id, reference[0]),
                ).fetchone()
                if parcel_node is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                relation = connection.execute(
                    "INSERT INTO vnext_core.property_relations ("
                    "workspace_id, from_node_id, to_node_id, relation_type, direction, "
                    "source_id, source_type, source_environment, relation_status, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'property_parcel', 'directed', %s, 'user', "
                    "'production', 'proposed', %s) RETURNING property_relation_id",
                    (workspace_id, property_node[0], parcel_node[0], PARCEL_HYPOTHESIS_SOURCE_ID, principal.user_id),
                ).fetchone()
                if relation is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                completed = connection.execute(
                    "UPDATE vnext_private.idempotency_records SET operation_status = 'succeeded', "
                    "response_status_code = 201, response_reference_type = %s, response_reference_id = %s, "
                    "updated_at = clock_timestamp() WHERE idempotency_record_id = %s AND workspace_id = %s "
                    "AND actor_user_id = %s AND operation_status = 'pending' RETURNING idempotency_key_hash",
                    (PARCEL_HYPOTHESIS_RESPONSE_TYPE, relation[0], idempotency_record_id, workspace_id, principal.user_id),
                ).fetchone()
                if completed is None:
                    raise VNextError.idempotency_conflict()
                _append_audit(
                    connection, principal=principal, workspace_id=workspace_id,
                    event_type="parcel_hypothesis.created", resource_type="property_relation",
                    resource_id=UUID(str(relation[0])), request_id=request_id,
                    outcome="succeeded", idempotency_key_hash=str(completed[0]),
                    metadata={"property_entity_id": str(property_entity_id), "parcel_identity_reference_id": str(reference[0])},
                )
                return ParcelHypothesisRecord(
                    property_entity_id, UUID(str(reference[0])), UUID(str(relation[0])),
                    normalized.normalized_key, normalized.display_value, reference[1],
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None


class ParcelHypothesisApplicationService:
    def __init__(self, *, authorizer: WorkspaceAuthorizer, writer: ParcelHypothesisWriter, idempotency_repository: IdempotencyWriter) -> None:
        self._authorizer = authorizer
        self._writer = writer
        self._idempotency_repository = idempotency_repository

    def create(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, components: dict[str, str | None],
        idempotency_key: str, request_id: str,
    ) -> ParcelHypothesisOutcome:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        normalized = normalize_parcel_hypothesis(components)
        self._writer.require_property(principal=principal, workspace_id=workspace_id, property_entity_id=property_entity_id)
        route = f"/v1/properties/{property_entity_id}/parcel-hypotheses"
        canonical_request = json.dumps(
            {"workspace_id": str(workspace_id), "normalized_key": normalized.normalized_key},
            ensure_ascii=True, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
        reservation = self._idempotency_repository.reserve(
            principal=principal, workspace_id=workspace_id, method="POST",
            canonical_route=route, idempotency_key=idempotency_key,
            canonical_request=canonical_request,
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
                or reservation.response_reference_type != PARCEL_HYPOTHESIS_RESPONSE_TYPE
                or reservation.response_reference_id is None):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            record = self._writer.get_by_relation_id(
                principal=principal, workspace_id=workspace_id,
                property_entity_id=property_entity_id,
                relation_id=reservation.response_reference_id,
            )
            if record.normalized_key != normalized.normalized_key:
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return ParcelHypothesisOutcome(record, normalized, True)
        try:
            record = self._writer.append(
                principal=principal, workspace_id=workspace_id, property_entity_id=property_entity_id,
                normalized=normalized, idempotency_record_id=reservation.idempotency_record_id,
                request_id=request_id,
            )
        except VNextError as error:
            try:
                self._idempotency_repository.mark_failed(
                    principal=principal, workspace_id=workspace_id,
                    idempotency_record_id=reservation.idempotency_record_id,
                    response_status_code=error.status_code, response_error_code=error.code.value,
                )
            except Exception:
                pass
            raise
        except Exception:
            error = VNextError(ErrorCode.INTERNAL_ERROR)
            try:
                self._idempotency_repository.mark_failed(
                    principal=principal, workspace_id=workspace_id,
                    idempotency_record_id=reservation.idempotency_record_id,
                    response_status_code=error.status_code, response_error_code=error.code.value,
                )
            except Exception:
                pass
            raise error from None
        return ParcelHypothesisOutcome(record, normalized, False)
