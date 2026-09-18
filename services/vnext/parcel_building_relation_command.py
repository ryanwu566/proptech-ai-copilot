"""Atomic manual proposed parcel <-> building relation between existing references.

This command asserts an unverified, manual relationship between one existing
parcel identity reference and one existing building identity reference. It does
not create new references, does not confirm anything, does not infer identity
from geometry, and never calls a provider. The single transaction validates the
two references, resolves their existing graph nodes, rejects a duplicate open
relation for the pair, writes one USER_PROVIDED manual-relation evidence, writes
one ``proposed`` ``bidirectional`` ``parcel_building`` relation with
``identity_confirmation_id`` null, completes idempotency, and appends audit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_command_repository import _translate_database_error
from services.vnext.persistence import (
    CASE_WRITE_ROLES, IdempotencyDecision, IdempotencyReservation, _append_audit,
)
from services.vnext.property_graph import (
    CoverageStatus, DATA_SOURCE_REGISTRY, EvidenceDraft, EvidenceStatus,
    LicenseStatus, QualityStatus, SourceEnvironment, SourceType,
    _evidence_hash, _validated_evidence_draft,
)


PARCEL_BUILDING_RELATION_SOURCE_ID = "user-upload"
PARCEL_BUILDING_RELATION_FACT_TYPE = "parcel_building.manual_relation.v1"
PARCEL_BUILDING_RELATION_VERSION = "parcel-building-manual-relation-v1"
PARCEL_BUILDING_RELATION_RESPONSE_TYPE = "parcel_building_relation"


@dataclass(frozen=True)
class ParcelBuildingRelationRecord:
    workspace_id: UUID
    parcel_identity_reference_id: UUID
    building_identity_reference_id: UUID
    parcel_node_id: UUID
    building_node_id: UUID
    evidence_id: UUID
    evidence_link_id: UUID
    relation_id: UUID
    pair_key: str
    created_at: datetime


@dataclass(frozen=True)
class ParcelBuildingRelationOutcome:
    record: ParcelBuildingRelationRecord
    replayed: bool


def _pair_key(parcel_reference_id: UUID, building_reference_id: UUID) -> str:
    """A deterministic, order-stable fingerprint for a parcel/building pair.

    The pair is inherently unordered for a bidirectional relation, so the key is
    stable regardless of submission order. It is only used for the advisory lock
    and idempotency fingerprint, never to change any stored fact.
    """

    return (
        f"{PARCEL_BUILDING_RELATION_VERSION}:"
        + json.dumps(
            {"parcel": str(parcel_reference_id), "building": str(building_reference_id)},
            ensure_ascii=True, separators=(",", ":"), sort_keys=True,
        )
    )


def _relation_audit_metadata(
    *, parcel_reference_id: UUID, building_reference_id: UUID,
) -> dict[str, str]:
    """The audit metadata dimensions for a manual parcel<->building relation.

    These are stable, low-cardinality audit dimensions that preserve traceability
    to the parcel reference, the building reference, and the relation shape. They
    must remain compatible with the ``_AUDIT_METADATA_KEYS`` allowlist so the
    single write transaction can persist the audit row instead of rolling back.
    """

    return {
        "parcel_identity_reference_id": str(parcel_reference_id),
        "building_identity_reference_id": str(building_reference_id),
        "relation_type": "parcel_building",
        "direction": "bidirectional",
    }


class ParcelBuildingRelationWriter(Protocol):
    def append(self, **kwargs: object) -> ParcelBuildingRelationRecord: ...
    def get_by_relation_id(self, **kwargs: object) -> ParcelBuildingRelationRecord: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...
    def mark_failed(self, **kwargs: object) -> None: ...


def _relation_evidence(
    *, workspace_id: UUID, parcel_reference_id: UUID, building_reference_id: UUID,
    principal: AuthenticatedPrincipal, request_id: str,
) -> EvidenceDraft:
    return EvidenceDraft(
        fact_type=PARCEL_BUILDING_RELATION_FACT_TYPE,
        source_id=PARCEL_BUILDING_RELATION_SOURCE_ID,
        source_environment=SourceEnvironment.PRODUCTION,
        retrieved_at=datetime.now(timezone.utc),
        coverage_status=CoverageStatus.UNKNOWN,
        coverage={"scope": "manual_relation", "status": "unknown"},
        evidence_status=EvidenceStatus.USER_PROVIDED,
        quality_status=QualityStatus.NOT_CHECKED,
        quality={"verification": "unverified"},
        license_status=LicenseStatus.NOT_APPLICABLE,
        license={"basis": "user_provided"},
        value={
            "relation_kind": "parcel_building",
            "authority": "unverified_manual_relation",
            "workspace_id": str(workspace_id),
            "parcel_identity_reference_id": str(parcel_reference_id),
            "building_identity_reference_id": str(building_reference_id),
            "actor_user_id": str(principal.user_id),
            "request_id": request_id,
        },
        value_schema=PARCEL_BUILDING_RELATION_VERSION,
        lineage={
            "normalization_version": PARCEL_BUILDING_RELATION_VERSION,
            "identity_scope": "parcel_building",
        },
    )


class PostgresParcelBuildingRelationRepository:
    """Reference validation, node reuse, raw evidence, one proposed bidirectional
    edge, idempotency completion and audit in a single principal-bound transaction.

    This repository never inserts into ``property_identity_references`` and never
    inserts an identity decision. It only reads the two existing references and
    their existing graph nodes, then writes one evidence row, one evidence link,
    and one relation row.
    """

    def __init__(self, principal_context: DatabasePrincipalContext, authorizer: WorkspaceAuthorizer) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def get_by_relation_id(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        relation_id: UUID,
    ) -> ParcelBuildingRelationRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT parcel_reference.identity_reference_id, "
                "building_reference.identity_reference_id, "
                "parcel_node.property_graph_node_id, building_node.property_graph_node_id, "
                "evidence.evidence_id, link.evidence_link_id, relation.property_relation_id, "
                "relation.created_at "
                "FROM vnext_core.property_relations relation "
                "JOIN vnext_core.property_graph_nodes parcel_node ON "
                "parcel_node.workspace_id = relation.workspace_id "
                "AND parcel_node.property_graph_node_id = relation.from_node_id "
                "JOIN vnext_core.property_graph_nodes building_node ON "
                "building_node.workspace_id = relation.workspace_id "
                "AND building_node.property_graph_node_id = relation.to_node_id "
                "JOIN vnext_core.property_identity_references parcel_reference ON "
                "parcel_reference.workspace_id = parcel_node.workspace_id "
                "AND parcel_reference.identity_reference_id = parcel_node.record_id "
                "JOIN vnext_core.property_identity_references building_reference ON "
                "building_reference.workspace_id = building_node.workspace_id "
                "AND building_reference.identity_reference_id = building_node.record_id "
                "JOIN vnext_core.evidence_items evidence ON "
                "evidence.workspace_id = relation.workspace_id "
                "AND evidence.evidence_id = relation.evidence_id "
                "JOIN vnext_core.evidence_links link ON link.workspace_id = evidence.workspace_id "
                "AND link.evidence_id = evidence.evidence_id "
                "AND link.subject_node_id = parcel_node.property_graph_node_id "
                "WHERE relation.workspace_id = %s AND relation.property_relation_id = %s "
                "AND parcel_node.node_type = 'parcel' AND parcel_reference.reference_type = 'parcel' "
                "AND building_node.node_type = 'building' AND building_reference.reference_type = 'building' "
                "AND relation.relation_type = 'parcel_building' AND relation.direction = 'bidirectional' "
                "AND relation.relation_status = 'proposed' AND relation.identity_confirmation_id IS NULL "
                "AND relation.source_id = %s AND relation.source_type = 'user' "
                "AND relation.source_environment = 'production' "
                "AND evidence.fact_type = %s AND evidence.value_schema = %s "
                "AND evidence.evidence_status = 'user_provided' "
                "AND link.link_type = 'describes' AND link.fact_scope = %s",
                (workspace_id, relation_id, PARCEL_BUILDING_RELATION_SOURCE_ID,
                 PARCEL_BUILDING_RELATION_FACT_TYPE, PARCEL_BUILDING_RELATION_VERSION,
                 PARCEL_BUILDING_RELATION_FACT_TYPE),
            ).fetchone()
        if row is None:
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        parcel_reference_id = UUID(str(row[0]))
        building_reference_id = UUID(str(row[1]))
        return ParcelBuildingRelationRecord(
            workspace_id, parcel_reference_id, building_reference_id,
            UUID(str(row[2])), UUID(str(row[3])), UUID(str(row[4])),
            UUID(str(row[5])), UUID(str(row[6])),
            _pair_key(parcel_reference_id, building_reference_id), row[7],
        )

    def append(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        parcel_identity_reference_id: UUID, building_identity_reference_id: UUID,
        idempotency_record_id: UUID, request_id: str,
    ) -> ParcelBuildingRelationRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        source = DATA_SOURCE_REGISTRY[PARCEL_BUILDING_RELATION_SOURCE_ID]
        if (source.source_type is not SourceType.USER
            or SourceEnvironment.PRODUCTION not in source.environments
            or not source.request_appendable):
            raise VNextError.permission_denied()
        pair_key = _pair_key(parcel_identity_reference_id, building_identity_reference_id)
        draft = _relation_evidence(
            workspace_id=workspace_id,
            parcel_reference_id=parcel_identity_reference_id,
            building_reference_id=building_identity_reference_id,
            principal=principal, request_id=request_id,
        )
        evidence_source, selected = _validated_evidence_draft(draft)
        content_hash = _evidence_hash(draft, evidence_source, selected)
        try:
            with self._principal_context.transaction(principal) as connection:
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"parcel-building-relation:{workspace_id}:{pair_key}",),
                )
                # Validate the existing parcel reference and resolve its node.
                parcel = connection.execute(
                    "SELECT node.property_graph_node_id FROM vnext_core.property_identity_references reference "
                    "JOIN vnext_core.property_graph_nodes node ON node.workspace_id = reference.workspace_id "
                    "AND node.node_type = 'parcel' AND node.record_id = reference.identity_reference_id "
                    "WHERE reference.workspace_id = %s AND reference.identity_reference_id = %s "
                    "AND reference.reference_type = 'parcel'",
                    (workspace_id, parcel_identity_reference_id),
                ).fetchone()
                if parcel is None:
                    raise VNextError.not_found()
                parcel_node_id = UUID(str(parcel[0]))
                # Validate the existing building reference and resolve its node.
                building = connection.execute(
                    "SELECT node.property_graph_node_id FROM vnext_core.property_identity_references reference "
                    "JOIN vnext_core.property_graph_nodes node ON node.workspace_id = reference.workspace_id "
                    "AND node.node_type = 'building' AND node.record_id = reference.identity_reference_id "
                    "WHERE reference.workspace_id = %s AND reference.identity_reference_id = %s "
                    "AND reference.reference_type = 'building'",
                    (workspace_id, building_identity_reference_id),
                ).fetchone()
                if building is None:
                    raise VNextError.not_found()
                building_node_id = UUID(str(building[0]))
                # Reject a duplicate open relation for the same pair. The relation
                # is bidirectional, so any existing parcel_building edge between the
                # two nodes (either orientation) is a duplicate.
                existing_relation = connection.execute(
                    "SELECT 1 FROM vnext_core.property_relations relation "
                    "WHERE relation.workspace_id = %s AND relation.relation_type = 'parcel_building' "
                    "AND relation.valid_to IS NULL "
                    "AND ((relation.from_node_id = %s AND relation.to_node_id = %s) "
                    "OR (relation.from_node_id = %s AND relation.to_node_id = %s)) LIMIT 1",
                    (workspace_id, parcel_node_id, building_node_id,
                     building_node_id, parcel_node_id),
                ).fetchone()
                if existing_relation is not None:
                    raise VNextError.conflicting_evidence()
                evidence = connection.execute(
                    "INSERT INTO vnext_core.evidence_items ("
                    "workspace_id, fact_type, value, value_schema, source_id, source_type, "
                    "source_environment, retrieved_at, coverage_status, coverage, evidence_status, "
                    "quality_status, quality, license_status, license, lineage, content_hash, created_by_user_id"
                    ") VALUES (%s, %s, %s::jsonb, %s, %s, 'user', 'production', %s, %s, "
                    "%s::jsonb, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s) "
                    "RETURNING evidence_id",
                    (workspace_id, PARCEL_BUILDING_RELATION_FACT_TYPE, selected["value"],
                     PARCEL_BUILDING_RELATION_VERSION, PARCEL_BUILDING_RELATION_SOURCE_ID,
                     draft.retrieved_at, draft.coverage_status.value, selected["coverage"],
                     draft.evidence_status.value, draft.quality_status.value, selected["quality"],
                     draft.license_status.value, selected["license"], selected["lineage"],
                     content_hash, principal.user_id),
                ).fetchone()
                if evidence is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                evidence_id = UUID(str(evidence[0]))
                link = connection.execute(
                    "INSERT INTO vnext_core.evidence_links ("
                    "workspace_id, evidence_id, subject_node_id, link_type, fact_scope, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'describes', %s, %s) RETURNING evidence_link_id",
                    (workspace_id, evidence_id, parcel_node_id,
                     PARCEL_BUILDING_RELATION_FACT_TYPE, principal.user_id),
                ).fetchone()
                if link is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                relation = connection.execute(
                    "INSERT INTO vnext_core.property_relations ("
                    "workspace_id, from_node_id, to_node_id, relation_type, direction, "
                    "source_id, source_type, source_environment, evidence_id, relation_status, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'parcel_building', 'bidirectional', %s, 'user', "
                    "'production', %s, 'proposed', %s) RETURNING property_relation_id, created_at",
                    (workspace_id, parcel_node_id, building_node_id,
                     PARCEL_BUILDING_RELATION_SOURCE_ID, evidence_id, principal.user_id),
                ).fetchone()
                if relation is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                relation_id = UUID(str(relation[0]))
                completed = connection.execute(
                    "UPDATE vnext_private.idempotency_records SET operation_status = 'succeeded', "
                    "response_status_code = 201, response_reference_type = %s, response_reference_id = %s, "
                    "updated_at = clock_timestamp() WHERE idempotency_record_id = %s AND workspace_id = %s "
                    "AND actor_user_id = %s AND operation_status = 'pending' RETURNING idempotency_key_hash",
                    (PARCEL_BUILDING_RELATION_RESPONSE_TYPE, relation_id, idempotency_record_id,
                     workspace_id, principal.user_id),
                ).fetchone()
                if completed is None:
                    raise VNextError.idempotency_conflict()
                _append_audit(
                    connection, principal=principal, workspace_id=workspace_id,
                    event_type="parcel_building_relation.created", resource_type="property_relation",
                    resource_id=relation_id, request_id=request_id,
                    outcome="succeeded", idempotency_key_hash=str(completed[0]),
                    metadata=_relation_audit_metadata(
                        parcel_reference_id=parcel_identity_reference_id,
                        building_reference_id=building_identity_reference_id,
                    ),
                )
                return ParcelBuildingRelationRecord(
                    workspace_id, parcel_identity_reference_id, building_identity_reference_id,
                    parcel_node_id, building_node_id, evidence_id,
                    UUID(str(link[0])), relation_id, pair_key, relation[1],
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None


class ParcelBuildingRelationApplicationService:
    def __init__(
        self, *, authorizer: WorkspaceAuthorizer, writer: ParcelBuildingRelationWriter,
        idempotency_repository: IdempotencyWriter,
    ) -> None:
        self._authorizer = authorizer
        self._writer = writer
        self._idempotency_repository = idempotency_repository

    def create(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        parcel_identity_reference_id: UUID, building_identity_reference_id: UUID,
        idempotency_key: str, request_id: str,
    ) -> ParcelBuildingRelationOutcome:
        if not isinstance(principal, AuthenticatedPrincipal):
            raise VNextError.authentication_required()
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        pair_key = _pair_key(parcel_identity_reference_id, building_identity_reference_id)
        route = "/v1/parcel-building-relations"
        canonical_request = json.dumps(
            {"workspace_id": str(workspace_id), "pair_key": pair_key},
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
                or reservation.response_reference_type != PARCEL_BUILDING_RELATION_RESPONSE_TYPE
                or reservation.response_reference_id is None):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            record = self._writer.get_by_relation_id(
                principal=principal, workspace_id=workspace_id,
                relation_id=reservation.response_reference_id,
            )
            if record.pair_key != pair_key:
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return ParcelBuildingRelationOutcome(record, True)
        try:
            record = self._writer.append(
                principal=principal, workspace_id=workspace_id,
                parcel_identity_reference_id=parcel_identity_reference_id,
                building_identity_reference_id=building_identity_reference_id,
                idempotency_record_id=reservation.idempotency_record_id,
                request_id=request_id,
            )
        except Exception as error:
            selected = error if isinstance(error, VNextError) else VNextError(ErrorCode.INTERNAL_ERROR)
            try:
                self._idempotency_repository.mark_failed(
                    principal=principal, workspace_id=workspace_id,
                    idempotency_record_id=reservation.idempotency_record_id,
                    response_status_code=selected.status_code, response_error_code=selected.code.value,
                )
            except Exception:
                pass
            if isinstance(error, VNextError):
                raise
            raise selected from None
        return ParcelBuildingRelationOutcome(record, False)
