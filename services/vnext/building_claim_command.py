"""Atomic manual cadastral building-number claims on existing properties."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.building_claim import (
    BUILDING_CLAIM_KIND, BUILDING_CLAIM_VERSION, NormalizedBuildingClaim,
    normalize_building_claim,
)
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


BUILDING_CLAIM_SOURCE_ID = "user-upload"
BUILDING_CLAIM_FACT_TYPE = "building.manual_cadastral_claim.v1"
BUILDING_CLAIM_RESPONSE_TYPE = "building_claim_relation"


@dataclass(frozen=True)
class BuildingClaimRecord:
    property_entity_id: UUID
    identity_reference_id: UUID
    building_node_id: UUID
    evidence_id: UUID
    evidence_link_id: UUID
    relation_id: UUID
    normalized_key: str
    display_value: str
    created_at: datetime


@dataclass(frozen=True)
class BuildingClaimOutcome:
    record: BuildingClaimRecord
    normalized: NormalizedBuildingClaim
    replayed: bool


class BuildingClaimWriter(Protocol):
    def require_property(self, **kwargs: object) -> None: ...
    def append(self, **kwargs: object) -> BuildingClaimRecord: ...
    def get_by_relation_id(self, **kwargs: object) -> BuildingClaimRecord: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...
    def mark_failed(self, **kwargs: object) -> None: ...


def _claim_evidence(
    *, normalized: NormalizedBuildingClaim, property_entity_id: UUID,
    principal: AuthenticatedPrincipal, request_id: str,
) -> EvidenceDraft:
    return EvidenceDraft(
        fact_type=BUILDING_CLAIM_FACT_TYPE,
        source_id=BUILDING_CLAIM_SOURCE_ID,
        source_environment=SourceEnvironment.PRODUCTION,
        retrieved_at=datetime.now(timezone.utc),
        coverage_status=CoverageStatus.UNKNOWN,
        coverage={"scope": "manual_claim", "status": "unknown"},
        evidence_status=EvidenceStatus.USER_PROVIDED,
        quality_status=QualityStatus.NOT_CHECKED,
        quality={"verification": "unverified"},
        license_status=LicenseStatus.NOT_APPLICABLE,
        license={"basis": "user_provided"},
        value={
            "identifier_kind": BUILDING_CLAIM_KIND,
            "property_entity_id": str(property_entity_id),
            "actor_user_id": str(principal.user_id),
            "request_id": request_id,
            "raw_input": dict(normalized.raw_input),
            "normalized_components": dict(normalized.normalized_components),
            "normalized_key": normalized.normalized_key,
        },
        value_schema=BUILDING_CLAIM_VERSION,
        lineage={"normalization_version": BUILDING_CLAIM_VERSION, "identity_scope": "building"},
    )


class PostgresBuildingClaimRepository:
    """Reference, node, raw evidence, proposed edge, idempotency and audit in one transaction."""

    def __init__(self, principal_context: DatabasePrincipalContext, authorizer: WorkspaceAuthorizer) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def require_property(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID,
    ) -> None:
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
    ) -> BuildingClaimRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT reference.identity_reference_id, building_node.property_graph_node_id, "
                "evidence.evidence_id, link.evidence_link_id, relation.property_relation_id, "
                "reference.normalized_key, reference.display_value, relation.created_at "
                "FROM vnext_core.property_relations relation "
                "JOIN vnext_core.property_graph_nodes property_node ON "
                "property_node.workspace_id = relation.workspace_id "
                "AND property_node.property_graph_node_id = relation.from_node_id "
                "JOIN vnext_core.property_graph_nodes building_node ON "
                "building_node.workspace_id = relation.workspace_id "
                "AND building_node.property_graph_node_id = relation.to_node_id "
                "JOIN vnext_core.property_identity_references reference ON "
                "reference.workspace_id = building_node.workspace_id "
                "AND reference.identity_reference_id = building_node.record_id "
                "JOIN vnext_core.evidence_items evidence ON "
                "evidence.workspace_id = relation.workspace_id AND evidence.evidence_id = relation.evidence_id "
                "JOIN vnext_core.evidence_links link ON link.workspace_id = evidence.workspace_id "
                "AND link.evidence_id = evidence.evidence_id AND link.subject_node_id = building_node.property_graph_node_id "
                "WHERE relation.workspace_id = %s AND relation.property_relation_id = %s "
                "AND property_node.node_type = 'property' AND property_node.record_id = %s "
                "AND building_node.node_type = 'building' AND reference.reference_type = 'building' "
                "AND relation.relation_type = 'property_building' AND relation.direction = 'directed' "
                "AND relation.relation_status = 'proposed' AND relation.identity_confirmation_id IS NULL "
                "AND relation.source_id = %s AND relation.source_type = 'user' "
                "AND relation.source_environment = 'production' "
                "AND reference.source_id = %s AND reference.source_type = 'user' "
                "AND reference.source_environment = 'production' AND reference.reference_status = 'unverified' "
                "AND evidence.fact_type = %s AND evidence.value_schema = %s "
                "AND evidence.evidence_status = 'user_provided' "
                "AND link.link_type = 'describes' AND link.fact_scope = %s",
                (workspace_id, relation_id, property_entity_id, BUILDING_CLAIM_SOURCE_ID,
                 BUILDING_CLAIM_SOURCE_ID, BUILDING_CLAIM_FACT_TYPE,
                 BUILDING_CLAIM_VERSION, BUILDING_CLAIM_FACT_TYPE),
            ).fetchone()
        if row is None:
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        return BuildingClaimRecord(
            property_entity_id, UUID(str(row[0])), UUID(str(row[1])), UUID(str(row[2])),
            UUID(str(row[3])), UUID(str(row[4])), str(row[5]), str(row[6]), row[7],
        )

    def append(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, normalized: NormalizedBuildingClaim,
        idempotency_record_id: UUID, request_id: str,
    ) -> BuildingClaimRecord:
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        source = DATA_SOURCE_REGISTRY[BUILDING_CLAIM_SOURCE_ID]
        if (source.source_type is not SourceType.USER
            or SourceEnvironment.PRODUCTION not in source.environments
            or not source.request_appendable):
            raise VNextError.permission_denied()
        draft = _claim_evidence(
            normalized=normalized, property_entity_id=property_entity_id,
            principal=principal, request_id=request_id,
        )
        evidence_source, selected = _validated_evidence_draft(draft)
        content_hash = _evidence_hash(draft, evidence_source, selected)
        try:
            with self._principal_context.transaction(principal) as connection:
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"building-claim:{workspace_id}:{normalized.normalized_key}",),
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
                existing_relation = connection.execute(
                    "SELECT 1 FROM vnext_core.property_relations relation "
                    "JOIN vnext_core.property_graph_nodes building_node ON "
                    "building_node.workspace_id = relation.workspace_id "
                    "AND building_node.property_graph_node_id = relation.to_node_id "
                    "JOIN vnext_core.property_identity_references reference ON "
                    "reference.workspace_id = building_node.workspace_id "
                    "AND reference.identity_reference_id = building_node.record_id "
                    "WHERE relation.workspace_id = %s AND relation.from_node_id = %s "
                    "AND relation.relation_type = 'property_building' "
                    "AND building_node.node_type = 'building' AND reference.reference_type = 'building' "
                    "AND reference.normalized_key = %s LIMIT 1",
                    (workspace_id, property_node[0], normalized.normalized_key),
                ).fetchone()
                if existing_relation is not None:
                    raise VNextError.conflicting_evidence()
                reusable = connection.execute(
                    "SELECT reference.identity_reference_id, node.property_graph_node_id "
                    "FROM vnext_core.property_identity_references reference "
                    "JOIN vnext_core.property_graph_nodes node ON node.workspace_id = reference.workspace_id "
                    "AND node.node_type = 'building' AND node.record_id = reference.identity_reference_id "
                    "WHERE reference.workspace_id = %s AND reference.reference_type = 'building' "
                    "AND reference.normalized_key = %s AND reference.display_value = %s "
                    "AND reference.source_id = %s AND reference.source_type = 'user' "
                    "AND reference.source_environment = 'production' AND reference.reference_status = 'unverified' "
                    "AND reference.created_by_user_id = %s AND reference.source_record_id IS NULL "
                    "AND reference.confidence IS NULL AND reference.valid_from IS NULL "
                    "AND reference.valid_to IS NULL AND reference.supersedes_reference_id IS NULL "
                    "AND NOT EXISTS (SELECT 1 FROM vnext_core.property_relations edge "
                    "WHERE edge.workspace_id = reference.workspace_id "
                    "AND (edge.from_node_id = node.property_graph_node_id OR edge.to_node_id = node.property_graph_node_id)) "
                    "AND NOT EXISTS (SELECT 1 FROM vnext_core.evidence_links link "
                    "WHERE link.workspace_id = reference.workspace_id "
                    "AND link.subject_node_id = node.property_graph_node_id) "
                    "ORDER BY reference.created_at, reference.identity_reference_id LIMIT 1",
                    (workspace_id, normalized.normalized_key, normalized.display_value,
                     BUILDING_CLAIM_SOURCE_ID, principal.user_id),
                ).fetchone()
                if reusable is None:
                    reference = connection.execute(
                        "INSERT INTO vnext_core.property_identity_references ("
                        "workspace_id, reference_type, normalized_key, display_value, source_id, "
                        "source_type, source_environment, reference_status, created_by_user_id"
                        ") VALUES (%s, 'building', %s, %s, %s, 'user', 'production', "
                        "'unverified', %s) RETURNING identity_reference_id",
                        (workspace_id, normalized.normalized_key, normalized.display_value,
                         BUILDING_CLAIM_SOURCE_ID, principal.user_id),
                    ).fetchone()
                    if reference is None:
                        raise VNextError.permission_denied()
                    reference_id = UUID(str(reference[0]))
                    node = connection.execute(
                        "SELECT property_graph_node_id FROM vnext_core.property_graph_nodes "
                        "WHERE workspace_id = %s AND node_type = 'building' AND record_id = %s",
                        (workspace_id, reference_id),
                    ).fetchone()
                    if node is None:
                        raise VNextError(ErrorCode.INTERNAL_ERROR)
                    building_node_id = UUID(str(node[0]))
                else:
                    reference_id = UUID(str(reusable[0]))
                    building_node_id = UUID(str(reusable[1]))
                evidence = connection.execute(
                    "INSERT INTO vnext_core.evidence_items ("
                    "workspace_id, fact_type, value, value_schema, source_id, source_type, "
                    "source_environment, retrieved_at, coverage_status, coverage, evidence_status, "
                    "quality_status, quality, license_status, license, lineage, content_hash, created_by_user_id"
                    ") VALUES (%s, %s, %s::jsonb, %s, %s, 'user', 'production', %s, %s, "
                    "%s::jsonb, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s) "
                    "RETURNING evidence_id",
                    (workspace_id, BUILDING_CLAIM_FACT_TYPE, selected["value"], BUILDING_CLAIM_VERSION,
                     BUILDING_CLAIM_SOURCE_ID, draft.retrieved_at, draft.coverage_status.value,
                     selected["coverage"], draft.evidence_status.value, draft.quality_status.value,
                     selected["quality"], draft.license_status.value, selected["license"],
                     selected["lineage"], content_hash, principal.user_id),
                ).fetchone()
                if evidence is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                evidence_id = UUID(str(evidence[0]))
                link = connection.execute(
                    "INSERT INTO vnext_core.evidence_links ("
                    "workspace_id, evidence_id, subject_node_id, link_type, fact_scope, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'describes', %s, %s) RETURNING evidence_link_id",
                    (workspace_id, evidence_id, building_node_id, BUILDING_CLAIM_FACT_TYPE, principal.user_id),
                ).fetchone()
                if link is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                relation = connection.execute(
                    "INSERT INTO vnext_core.property_relations ("
                    "workspace_id, from_node_id, to_node_id, relation_type, direction, "
                    "source_id, source_type, source_environment, evidence_id, relation_status, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'property_building', 'directed', %s, 'user', "
                    "'production', %s, 'proposed', %s) RETURNING property_relation_id, created_at",
                    (workspace_id, property_node[0], building_node_id,
                     BUILDING_CLAIM_SOURCE_ID, evidence_id, principal.user_id),
                ).fetchone()
                if relation is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                relation_id = UUID(str(relation[0]))
                completed = connection.execute(
                    "UPDATE vnext_private.idempotency_records SET operation_status = 'succeeded', "
                    "response_status_code = 201, response_reference_type = %s, response_reference_id = %s, "
                    "updated_at = clock_timestamp() WHERE idempotency_record_id = %s AND workspace_id = %s "
                    "AND actor_user_id = %s AND operation_status = 'pending' RETURNING idempotency_key_hash",
                    (BUILDING_CLAIM_RESPONSE_TYPE, relation_id, idempotency_record_id,
                     workspace_id, principal.user_id),
                ).fetchone()
                if completed is None:
                    raise VNextError.idempotency_conflict()
                _append_audit(
                    connection, principal=principal, workspace_id=workspace_id,
                    event_type="building_claim.created", resource_type="property_relation",
                    resource_id=relation_id, request_id=request_id,
                    outcome="succeeded", idempotency_key_hash=str(completed[0]),
                    metadata={
                        "property_entity_id": str(property_entity_id),
                        "building_identity_reference_id": str(reference_id),
                    },
                )
                return BuildingClaimRecord(
                    property_entity_id, reference_id, building_node_id, evidence_id,
                    UUID(str(link[0])), relation_id, normalized.normalized_key,
                    normalized.display_value, relation[1],
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None


class BuildingClaimApplicationService:
    def __init__(
        self, *, authorizer: WorkspaceAuthorizer, writer: BuildingClaimWriter,
        idempotency_repository: IdempotencyWriter,
    ) -> None:
        self._authorizer = authorizer
        self._writer = writer
        self._idempotency_repository = idempotency_repository

    def create(
        self, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
        property_entity_id: UUID, components: dict[str, str | None],
        idempotency_key: str, request_id: str,
    ) -> BuildingClaimOutcome:
        if not isinstance(principal, AuthenticatedPrincipal):
            raise VNextError.authentication_required()
        self._authorizer.require_workspace_role(principal, workspace_id, allowed_roles=CASE_WRITE_ROLES)
        normalized = normalize_building_claim(components)
        self._writer.require_property(
            principal=principal, workspace_id=workspace_id, property_entity_id=property_entity_id,
        )
        route = f"/v1/properties/{property_entity_id}/building-hypotheses"
        canonical_request = json.dumps(
            {"workspace_id": str(workspace_id), "identifier_kind": BUILDING_CLAIM_KIND,
             "raw_input": dict(normalized.raw_input), "normalized_key": normalized.normalized_key},
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
                or reservation.response_reference_type != BUILDING_CLAIM_RESPONSE_TYPE
                or reservation.response_reference_id is None):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            record = self._writer.get_by_relation_id(
                principal=principal, workspace_id=workspace_id,
                property_entity_id=property_entity_id,
                relation_id=reservation.response_reference_id,
            )
            if record.normalized_key != normalized.normalized_key:
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return BuildingClaimOutcome(record, normalized, True)
        try:
            record = self._writer.append(
                principal=principal, workspace_id=workspace_id,
                property_entity_id=property_entity_id, normalized=normalized,
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
        return BuildingClaimOutcome(record, normalized, False)
