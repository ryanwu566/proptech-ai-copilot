"""Executable non-confirming identity resolution and Property read APIs."""

from __future__ import annotations

import os
import re
import secrets
from datetime import datetime
from functools import lru_cache
from typing import Annotated, Literal, Mapping, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.api.v1.errors import request_id as correlation_request_id
from services.vnext.auth import (AuthenticatedPrincipal,
                                 require_authenticated_principal)
from services.vnext.authorization import (WorkspaceAuthorizer,
                                          get_workspace_authorizer)
from services.vnext.db_principal import get_vnext_database_principal_context
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.feature_flags import (VNextFeatureFlags,
                                          get_vnext_feature_flags)
from services.vnext.identity_command_repository import (
    CasePropertyLinkRecord, PostgresIdentityCommandRepository)
from services.vnext.identity_command_service import \
    IdentityCommandApplicationService
from services.vnext.identity_resolution import (IdentityResolutionEngine,
                                                ResolutionInputType)
from services.vnext.identity_resolution_repository import (
    IDENTITY_WRITE_ROLES, IdentityCandidateRecord, IdentityConflictRecord,
    IdentityDecisionRecord, IdentityResolutionRecord,
    PostgresIdentityResolutionRepository, ResolutionAttemptRecord)
from services.vnext.identity_resolution_service import \
    IdentityResolutionApplicationService
from services.vnext.pagination import (CURSOR_SIGNING_KEY_ENV, CursorCodec,
                                       cursor_datetime, cursor_uuid)
from services.vnext.persistence import (CasePurpose, CaseRecord,
                                        PostgresCaseRepository,
                                        PostgresIdempotencyRepository)
from services.vnext.property_graph import (EvidenceRecord, EvidenceStatus,
                                           PropertyEntityRecord,
                                           PropertyRelationRecord,
                                           PropertyRelationStatus,
                                           PropertyRelationType)
from services.vnext.property_read_repository import (
    EvidencePosition, GraphPosition, PostgresPropertyReadRepository,
    PropertyEvidencePage, PropertyGraphNodeRecord, PropertyGraphPage)

router = APIRouter(tags=["vnext-property-identity"])

BoundedText512 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=512),
]
BoundedText160 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
BoundedText120 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
BoundedConfirmationReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=1000),
]
BoundedCaseTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=240),
]
ReasonCode = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9._-]{2,79}$"),
]
Coordinate = Annotated[float, Field(strict=True)]
_IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9._:-]{16,128}$"
_FACT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{2,119}$")
_FORGED_IDENTITY_HEADERS = frozenset({"x-user-id", "x-role", "x-workspace-role"})
_FORGED_IDENTITY_QUERY_FIELDS = frozenset({"user_id", "role", "workspace_role"})
_PROCESS_CURSOR_KEY = secrets.token_bytes(32)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddressValue(_StrictModel):
    text: BoundedText512


class AddressInput(_StrictModel):
    kind: Literal["address"]
    value: AddressValue


class LotNumberValue(_StrictModel):
    jurisdiction: BoundedText160
    section: BoundedText160
    subsection: BoundedText160 | None = None
    lot_number: BoundedText120


class LotNumberInput(_StrictModel):
    kind: Literal["lot_number"]
    value: LotNumberValue


class BuildingNumberValue(_StrictModel):
    jurisdiction: BoundedText160 | None = None
    building_number: BoundedText160


class BuildingNumberInput(_StrictModel):
    kind: Literal["building_number"]
    value: BuildingNumberValue


class CoordinatesValue(_StrictModel):
    latitude: Annotated[Coordinate, Field(ge=-90, le=90)]
    longitude: Annotated[Coordinate, Field(ge=-180, le=180)]
    crs: Literal["EPSG:4326"]


class CoordinatesInput(_StrictModel):
    kind: Literal["coordinates"]
    value: CoordinatesValue


class MapClickValue(CoordinatesValue):
    map_context: BoundedText160 | None = None


class MapClickInput(_StrictModel):
    kind: Literal["map_click"]
    value: MapClickValue


ResolutionInputRequest = Annotated[
    Union[
        AddressInput,
        LotNumberInput,
        BuildingNumberInput,
        CoordinatesInput,
        MapClickInput,
    ],
    Field(discriminator="kind"),
]


class ResolutionCreateRequest(_StrictModel):
    workspace_id: UUID
    input: ResolutionInputRequest
    case_id: UUID | None = None


class ResolutionConfirmRequest(_StrictModel):
    candidate_id: UUID
    version: Annotated[int, Field(ge=1)]
    confirmation_reason: BoundedConfirmationReason


class ResolutionRejectRequest(_StrictModel):
    candidate_id: UUID | None = None
    version: Annotated[int, Field(ge=1)]
    reason_code: ReasonCode


class CaseCreateRequest(_StrictModel):
    workspace_id: UUID
    purpose: CasePurpose
    title: BoundedCaseTitle


class CaseAttachResolutionRequest(_StrictModel):
    resolution_id: UUID
    case_version: Annotated[int, Field(ge=1)]


class SourceDTO(_StrictModel):
    source_id: str
    source_type: str
    environment: str
    provider_id: str | None = None
    source_record_id: str | None = None
    retrieved_at: datetime | None = None


class ResolutionInputDTO(_StrictModel):
    kind: str
    value: dict[str, object]


class ResolutionAttemptDTO(_StrictModel):
    attempt_id: UUID
    order: int
    strategy_id: str
    source: SourceDTO
    status: str
    coverage_status: str
    coverage: dict[str, object]
    result_count: int
    error_category: str | None
    error_code: str | None
    retryable: bool | None
    started_at: datetime
    completed_at: datetime


class IdentityCandidateDTO(_StrictModel):
    candidate_id: UUID
    candidate_type: str
    normalized_identity: dict[str, object]
    display_identity: str
    source: SourceDTO
    confidence: float
    confidence_method: str
    ranking_trace: dict[str, object]
    rank: int
    status: str
    coverage_status: str
    coverage: dict[str, object]
    supporting_evidence_ids: list[UUID]
    supporting_identity_reference_ids: list[UUID]
    possible_existing_property_entity_id: UUID | None
    needs_human_confirmation: Literal[True]


class IdentityConflictDTO(_StrictModel):
    conflict_id: UUID
    left_candidate_id: UUID
    right_candidate_id: UUID | None
    related_identity_reference_id: UUID | None
    related_evidence_id: UUID | None
    related_property_entity_id: UUID | None
    category: str
    severity: str
    state: str


class IdentityDecisionDTO(_StrictModel):
    decision_id: UUID
    decision_type: str
    candidate_id: UUID | None
    property_entity_id: UUID | None
    reason_code: str | None
    resolution_version_observed: int
    decision_version: int
    actor_user_id: UUID
    decided_at: datetime


class PropertyResolutionDTO(_StrictModel):
    resolution_id: UUID
    workspace_id: UUID
    case_id: UUID | None
    state: str
    input: ResolutionInputDTO
    normalized_input: dict[str, object]
    normalization_version: str
    coverage_status: str
    coverage: dict[str, object]
    ambiguity: str
    needs_human_confirmation: bool
    candidates: list[IdentityCandidateDTO]
    conflicts: list[IdentityConflictDTO]
    provider_attempts: list[ResolutionAttemptDTO]
    decisions: list[IdentityDecisionDTO]
    selected_candidate_id: UUID | None = None
    confirmed_property_entity_id: UUID | None = None
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class ConfirmationSummaryDTO(_StrictModel):
    available: bool
    human_confirmed: bool
    confirmation_id: UUID | None = None
    confirmed_at: datetime | None = None
    confirmed_by: UUID | None = None
    resolution_id: UUID | None = None


class PropertyDTO(_StrictModel):
    property_entity_id: UUID
    workspace_id: UUID
    lifecycle_state: str
    display_label: str
    confirmation_summary: ConfirmationSummaryDTO
    version: int
    created_at: datetime
    updated_at: datetime


class GraphNodeDTO(_StrictModel):
    node_id: UUID
    node_type: str
    record_id: UUID
    display_label: str
    status: str | None
    source: SourceDTO | None
    valid_from: datetime | None
    valid_to: datetime | None


class PropertyRelationDTO(_StrictModel):
    relation_id: UUID
    from_node_id: UUID
    to_node_id: UUID
    relation_type: str
    direction: str
    confidence: float | None
    confidence_method: str | None
    source: SourceDTO
    evidence_id: UUID | None
    status: str
    valid_from: datetime | None
    valid_to: datetime | None
    supersedes_relation_id: UUID | None
    created_at: datetime
    confirmation_id: UUID | None


class CaseDTO(_StrictModel):
    case_id: UUID
    workspace_id: UUID
    purpose: str
    status: str
    title: str
    identity_status: str
    assigned_member_id: UUID | None
    version: int
    opened_at: datetime
    updated_at: datetime


class CasePropertyLinkDTO(_StrictModel):
    case_property_link_id: UUID
    case_id: UUID
    property_entity_id: UUID
    resolution_id: UUID
    confirmation_id: UUID
    supersedes_case_property_link_id: UUID | None
    attached_by: UUID
    attached_at: datetime


class CaseAttachmentDTO(_StrictModel):
    case: CaseDTO
    link: CasePropertyLinkDTO


class PropertyGraphDTO(_StrictModel):
    property: PropertyDTO
    nodes: list[GraphNodeDTO]
    relations: list[PropertyRelationDTO]
    as_of: datetime | None
    next_cursor: str | None


class EvidenceDTO(_StrictModel):
    evidence_id: UUID
    workspace_id: UUID
    fact_type: str
    value: dict[str, object] | None
    has_private_value_reference: bool
    value_schema: str | None
    source: SourceDTO
    effective_from: datetime | None
    effective_to: datetime | None
    expires_at: datetime | None
    coverage_status: str
    coverage: dict[str, object]
    status: str
    quality_confidence: float | None
    quality_method: str | None
    quality_status: str
    quality: dict[str, object]
    license_status: str
    license_reference: str | None
    license: dict[str, object]
    lineage: dict[str, object]
    content_hash: str
    version: int
    supersedes_evidence_id: UUID | None
    created_at: datetime


class PropertyEvidenceDTO(_StrictModel):
    property: PropertyDTO
    evidence: list[EvidenceDTO]
    next_cursor: str | None


def reject_client_identity_overrides(request: Request) -> None:
    if {name.lower() for name in request.headers} & _FORGED_IDENTITY_HEADERS or set(
        request.query_params
    ) & _FORGED_IDENTITY_QUERY_FIELDS:
        raise VNextError.validation_failed()


def require_identity_feature(
    flags: VNextFeatureFlags = Depends(get_vnext_feature_flags),
) -> None:
    if not flags.identity_v1:
        raise VNextError.not_found()


@lru_cache(maxsize=1)
def get_identity_resolution_engine() -> IdentityResolutionEngine:
    # No current source is production_accepted for identity resolution.
    return IdentityResolutionEngine(())


def get_identity_resolution_repository() -> PostgresIdentityResolutionRepository:
    return PostgresIdentityResolutionRepository(
        get_vnext_database_principal_context(),
        get_workspace_authorizer(),
    )


def get_idempotency_repository() -> PostgresIdempotencyRepository:
    return PostgresIdempotencyRepository(
        get_vnext_database_principal_context(),
        get_workspace_authorizer(),
    )


def get_case_repository() -> PostgresCaseRepository:
    return PostgresCaseRepository(
        get_vnext_database_principal_context(),
        get_workspace_authorizer(),
    )


def get_identity_command_repository() -> PostgresIdentityCommandRepository:
    return PostgresIdentityCommandRepository(
        get_vnext_database_principal_context(),
        get_workspace_authorizer(),
    )


def get_resolution_application_service(
    engine: IdentityResolutionEngine = Depends(get_identity_resolution_engine),
    resolution_repository: PostgresIdentityResolutionRepository = Depends(
        get_identity_resolution_repository
    ),
    idempotency_repository: PostgresIdempotencyRepository = Depends(
        get_idempotency_repository
    ),
    case_repository: PostgresCaseRepository = Depends(get_case_repository),
    authorizer: WorkspaceAuthorizer = Depends(get_workspace_authorizer),
) -> IdentityResolutionApplicationService:
    return IdentityResolutionApplicationService(
        authorizer=authorizer,
        engine=engine,
        resolution_repository=resolution_repository,
        idempotency_repository=idempotency_repository,
        case_repository=case_repository,
    )


def get_identity_command_service(
    resolution_repository: PostgresIdentityResolutionRepository = Depends(
        get_identity_resolution_repository
    ),
    command_repository: PostgresIdentityCommandRepository = Depends(
        get_identity_command_repository
    ),
    idempotency_repository: PostgresIdempotencyRepository = Depends(
        get_idempotency_repository
    ),
    case_repository: PostgresCaseRepository = Depends(get_case_repository),
    authorizer: WorkspaceAuthorizer = Depends(get_workspace_authorizer),
) -> IdentityCommandApplicationService:
    return IdentityCommandApplicationService(
        authorizer=authorizer,
        resolution_repository=resolution_repository,
        command_repository=command_repository,
        idempotency_repository=idempotency_repository,
        case_repository=case_repository,
    )


def get_property_read_repository() -> PostgresPropertyReadRepository:
    return PostgresPropertyReadRepository(
        get_vnext_database_principal_context(),
        get_workspace_authorizer(),
    )


@lru_cache(maxsize=1)
def get_cursor_codec() -> CursorCodec:
    configured = os.getenv(CURSOR_SIGNING_KEY_ENV, "")
    if configured:
        return CursorCodec(configured.encode("utf-8"))
    if os.getenv("APP_ENV", "development").strip().lower() in {"production", "preview"}:
        raise VNextError(ErrorCode.MAINTENANCE)
    return CursorCodec(_PROCESS_CURSOR_KEY)


def _raw_input(
    value: ResolutionInputRequest,
) -> tuple[ResolutionInputType, dict[str, object]]:
    if isinstance(value, AddressInput):
        return ResolutionInputType.ADDRESS, {"address": value.value.text}
    if isinstance(value, LotNumberInput):
        return ResolutionInputType.LOT_NUMBER, value.value.model_dump(exclude_none=True)
    if isinstance(value, BuildingNumberInput):
        return ResolutionInputType.BUILDING_NUMBER, value.value.model_dump(
            exclude_none=True
        )
    if isinstance(value, CoordinatesInput):
        return ResolutionInputType.COORDINATES, value.value.model_dump()
    if isinstance(value, MapClickInput):
        return ResolutionInputType.MAP_CLICK, value.value.model_dump(exclude_none=True)
    raise VNextError.unsupported_input()


def _attempt_dto(record: ResolutionAttemptRecord) -> ResolutionAttemptDTO:
    return ResolutionAttemptDTO(
        attempt_id=record.resolution_attempt_id,
        order=record.attempt_order,
        strategy_id=record.strategy_id,
        source=SourceDTO(
            source_id=record.source_id,
            source_type=record.source_type.value,
            environment=record.source_environment.value,
            provider_id=record.provider_id,
            retrieved_at=record.retrieved_at,
        ),
        status=record.status.value,
        coverage_status=record.coverage_status.value,
        coverage=dict(record.coverage),
        result_count=record.result_count,
        error_category=(
            None if record.error_category is None else record.error_category.value
        ),
        error_code=record.error_code,
        retryable=record.error_retryable,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


def _candidate_dto(record: IdentityCandidateRecord) -> IdentityCandidateDTO:
    return IdentityCandidateDTO(
        candidate_id=record.identity_candidate_id,
        candidate_type=record.candidate_type.value,
        normalized_identity=dict(record.normalized_identity),
        display_identity=record.display_identity,
        source=SourceDTO(
            source_id=record.source_id,
            source_type=record.source_type.value,
            environment=record.source_environment.value,
            source_record_id=record.source_record_id,
            retrieved_at=record.retrieved_at,
        ),
        confidence=record.confidence,
        confidence_method=record.confidence_method,
        ranking_trace=dict(record.ranking_factors),
        rank=record.rank,
        status=record.candidate_status.value,
        coverage_status=record.coverage_status.value,
        coverage=dict(record.coverage),
        supporting_evidence_ids=list(record.supporting_evidence_ids),
        supporting_identity_reference_ids=list(record.supporting_reference_ids),
        possible_existing_property_entity_id=record.possible_existing_property_entity_id,
        needs_human_confirmation=True,
    )


def _conflict_dto(record: IdentityConflictRecord) -> IdentityConflictDTO:
    return IdentityConflictDTO(
        conflict_id=record.identity_conflict_id,
        left_candidate_id=record.left_candidate_id,
        right_candidate_id=record.right_candidate_id,
        related_identity_reference_id=record.related_identity_reference_id,
        related_evidence_id=record.related_evidence_id,
        related_property_entity_id=record.related_property_entity_id,
        category=record.conflict_type.value,
        severity=record.severity.value,
        state=record.resolution_state.value,
    )


def _decision_dto(record: IdentityDecisionRecord) -> IdentityDecisionDTO:
    return IdentityDecisionDTO(
        decision_id=record.identity_decision_id,
        decision_type=record.decision_type,
        candidate_id=record.identity_candidate_id,
        property_entity_id=record.property_entity_id,
        reason_code=record.reason_code,
        resolution_version_observed=record.resolution_version_observed,
        decision_version=record.decision_version,
        actor_user_id=record.actor_user_id,
        decided_at=record.created_at,
    )


def resolution_dto(record: IdentityResolutionRecord) -> PropertyResolutionDTO:
    raw_value = dict(record.resolution_input.raw_input)
    if record.resolution_input.input_type is ResolutionInputType.ADDRESS:
        raw_value = {"text": raw_value.get("address")}
    confirmation = next(
        (item for item in reversed(record.decisions) if item.decision_type == "confirmed"),
        None,
    )
    resolution_rejection = next(
        (
            item
            for item in reversed(record.decisions)
            if item.decision_type == "resolution_rejected"
        ),
        None,
    )
    terminal = confirmation is not None or resolution_rejection is not None
    state = (
        "confirmed"
        if confirmation is not None
        else "rejected"
        if resolution_rejection is not None
        else record.status.value
    )
    projected_version = max(
        [record.version, *(item.decision_version for item in record.decisions)]
    )
    return PropertyResolutionDTO(
        resolution_id=record.identity_resolution_id,
        workspace_id=record.workspace_id,
        case_id=record.case_id,
        state=state,
        input=ResolutionInputDTO(
            kind=record.resolution_input.input_type.value,
            value=raw_value,
        ),
        normalized_input=dict(record.resolution_input.normalized_input),
        normalization_version=record.resolution_input.normalization_version,
        coverage_status=record.coverage_status.value,
        coverage=dict(record.coverage),
        ambiguity=record.ambiguity_status.value,
        needs_human_confirmation=not terminal,
        candidates=[_candidate_dto(item) for item in record.candidates],
        conflicts=[_conflict_dto(item) for item in record.conflicts],
        provider_attempts=[_attempt_dto(item) for item in record.attempts],
        decisions=[_decision_dto(item) for item in record.decisions],
        selected_candidate_id=(
            None if confirmation is None else confirmation.identity_candidate_id
        ),
        confirmed_property_entity_id=(
            None if confirmation is None else confirmation.property_entity_id
        ),
        version=projected_version,
        created_by=record.requested_by_user_id,
        created_at=record.created_at,
        updated_at=record.created_at,
    )


def property_dto(record: PropertyEntityRecord) -> PropertyDTO:
    return PropertyDTO(
        property_entity_id=record.property_entity_id,
        workspace_id=record.workspace_id,
        lifecycle_state=record.entity_status.value,
        display_label=record.display_label,
        confirmation_summary=ConfirmationSummaryDTO(
            available=record.confirmation_id is not None,
            human_confirmed=record.confirmation_id is not None,
            confirmation_id=record.confirmation_id,
            confirmed_at=record.confirmed_at,
            confirmed_by=record.confirmed_by_user_id,
            resolution_id=record.confirmed_resolution_id,
        ),
        version=record.version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _node_dto(record: PropertyGraphNodeRecord) -> GraphNodeDTO:
    source = None
    if record.source_id is not None:
        if record.source_type is None or record.source_environment is None:
            # Provenance is all-or-nothing in the signed graph contract. Never
            # invent a source type or a production environment for corrupt data.
            raise VNextError(ErrorCode.MAINTENANCE)
        source = SourceDTO(
            source_id=record.source_id,
            source_type=record.source_type.value,
            environment=record.source_environment.value,
        )
    return GraphNodeDTO(
        node_id=record.property_graph_node_id,
        node_type=record.node_type,
        record_id=record.record_id,
        display_label=record.display_label,
        status=(
            None if record.reference_status is None else record.reference_status.value
        ),
        source=source,
        valid_from=record.valid_from,
        valid_to=record.valid_to,
    )


def _relation_dto(record: PropertyRelationRecord) -> PropertyRelationDTO:
    return PropertyRelationDTO(
        relation_id=record.property_relation_id,
        from_node_id=record.from_node_id,
        to_node_id=record.to_node_id,
        relation_type=record.relation_type.value,
        direction=record.direction.value,
        confidence=record.confidence,
        confidence_method=record.confidence_method,
        source=SourceDTO(
            source_id=record.source_id,
            source_type=record.source_type.value,
            environment=record.source_environment.value,
        ),
        evidence_id=record.evidence_id,
        status=record.relation_status.value,
        valid_from=record.valid_from,
        valid_to=record.valid_to,
        supersedes_relation_id=record.supersedes_relation_id,
        created_at=record.created_at,
        confirmation_id=record.identity_confirmation_id,
    )


def case_dto(record: CaseRecord) -> CaseDTO:
    return CaseDTO(
        case_id=record.case_id,
        workspace_id=record.workspace_id,
        purpose=record.purpose.value,
        status=record.status.value,
        title=record.title,
        identity_status=record.identity_status.value,
        assigned_member_id=record.assigned_member_id,
        version=record.version,
        opened_at=record.opened_at,
        updated_at=record.updated_at,
    )


def case_link_dto(record: CasePropertyLinkRecord) -> CasePropertyLinkDTO:
    return CasePropertyLinkDTO(
        case_property_link_id=record.case_property_link_id,
        case_id=record.case_id,
        property_entity_id=record.property_entity_id,
        resolution_id=record.identity_resolution_id,
        confirmation_id=record.identity_confirmation_id,
        supersedes_case_property_link_id=record.supersedes_case_property_link_id,
        attached_by=record.actor_user_id,
        attached_at=record.created_at,
    )


def _graph_dto(page: PropertyGraphPage, codec: CursorCodec) -> PropertyGraphDTO:
    next_cursor = None
    if page.next_position is not None:
        next_cursor = codec.encode(
            kind="property_graph",
            fields={
                "created_at": page.next_position.created_at.isoformat(),
                "relation_id": str(page.next_position.relation_id),
            },
        )
    return PropertyGraphDTO(
        property=property_dto(page.property),
        nodes=[_node_dto(item) for item in page.nodes],
        relations=[_relation_dto(item) for item in page.relations],
        as_of=page.as_of,
        next_cursor=next_cursor,
    )


def _evidence_dto(record: EvidenceRecord) -> EvidenceDTO:
    return EvidenceDTO(
        evidence_id=record.evidence_id,
        workspace_id=record.workspace_id,
        fact_type=record.fact_type,
        value=None if record.value is None else dict(record.value),
        has_private_value_reference=record.value_ref is not None,
        value_schema=record.value_schema,
        source=SourceDTO(
            source_id=record.source_id,
            source_type=record.source_type.value,
            environment=record.source_environment.value,
            provider_id=record.provider,
            source_record_id=record.source_record_id,
            retrieved_at=record.retrieved_at,
        ),
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        expires_at=record.expires_at,
        coverage_status=record.coverage_status.value,
        coverage=dict(record.coverage),
        status=record.evidence_status.value,
        quality_confidence=record.quality_confidence,
        quality_method=record.quality_method,
        quality_status=record.quality_status.value,
        quality=dict(record.quality),
        license_status=record.license_status.value,
        license_reference=record.license_ref,
        license=dict(record.license),
        lineage=dict(record.lineage),
        content_hash=record.content_hash,
        version=record.evidence_version,
        supersedes_evidence_id=record.supersedes_evidence_id,
        created_at=record.created_at,
    )


def _evidence_page_dto(
    page: PropertyEvidencePage,
    codec: CursorCodec,
) -> PropertyEvidenceDTO:
    next_cursor = None
    if page.next_position is not None:
        next_cursor = codec.encode(
            kind="property_evidence",
            fields={
                "fact_type": page.next_position.fact_type,
                "effective_from": (
                    None
                    if page.next_position.effective_from is None
                    else page.next_position.effective_from.isoformat()
                ),
                "retrieved_at": page.next_position.retrieved_at.isoformat(),
                "evidence_id": str(page.next_position.evidence_id),
            },
        )
    return PropertyEvidenceDTO(
        property=property_dto(page.property),
        evidence=[_evidence_dto(item) for item in page.evidence],
        next_cursor=next_cursor,
    )


@router.post(
    "/property-resolutions",
    response_model=PropertyResolutionDTO,
    status_code=201,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 409: {}, 422: {}, 429: {}, 503: {}},
)
def create_property_resolution(
    body: ResolutionCreateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
    ],
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    authorizer: WorkspaceAuthorizer = Depends(get_workspace_authorizer),
    service: IdentityResolutionApplicationService = Depends(
        get_resolution_application_service
    ),
) -> JSONResponse:
    authorizer.require_workspace_role(
        principal,
        body.workspace_id,
        allowed_roles=IDENTITY_WRITE_ROLES,
    )
    input_type, raw_input = _raw_input(body.input)
    outcome = service.create(
        principal=principal,
        workspace_id=body.workspace_id,
        input_type=input_type,
        raw_input=raw_input,
        case_id=body.case_id,
        idempotency_key=idempotency_key,
    )
    payload = resolution_dto(outcome.resolution)
    return JSONResponse(
        status_code=outcome.status_code,
        content=payload.model_dump(mode="json"),
    )


@router.post(
    "/property-resolutions/{identity_resolution_id}/confirm",
    response_model=PropertyResolutionDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}, 503: {}},
)
def confirm_property_resolution(
    identity_resolution_id: UUID,
    body: ResolutionConfirmRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
    ],
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: IdentityCommandApplicationService = Depends(get_identity_command_service),
) -> PropertyResolutionDTO:
    outcome = service.confirm(
        principal=principal,
        identity_resolution_id=identity_resolution_id,
        identity_candidate_id=body.candidate_id,
        expected_version=body.version,
        confirmation_reason=body.confirmation_reason,
        idempotency_key=idempotency_key,
        request_id=correlation_request_id(request),
    )
    return resolution_dto(outcome.resolution)


@router.post(
    "/property-resolutions/{identity_resolution_id}/reject",
    response_model=PropertyResolutionDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}, 503: {}},
)
def reject_property_resolution(
    identity_resolution_id: UUID,
    body: ResolutionRejectRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
    ],
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: IdentityCommandApplicationService = Depends(get_identity_command_service),
) -> PropertyResolutionDTO:
    outcome = service.reject(
        principal=principal,
        identity_resolution_id=identity_resolution_id,
        identity_candidate_id=body.candidate_id,
        expected_version=body.version,
        reason_code=body.reason_code,
        idempotency_key=idempotency_key,
        request_id=correlation_request_id(request),
    )
    return resolution_dto(outcome.resolution)


@router.post(
    "/cases",
    response_model=CaseDTO,
    status_code=201,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 409: {}, 422: {}, 503: {}},
)
def create_case(
    body: CaseCreateRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
    ],
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: IdentityCommandApplicationService = Depends(get_identity_command_service),
) -> CaseDTO:
    outcome = service.create_case(
        principal=principal,
        workspace_id=body.workspace_id,
        purpose=body.purpose,
        title=body.title,
        idempotency_key=idempotency_key,
        request_id=correlation_request_id(request),
    )
    return case_dto(outcome.case)


@router.post(
    "/cases/{case_id}/attach-resolution",
    response_model=CaseAttachmentDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}, 503: {}},
)
def attach_case_resolution(
    case_id: UUID,
    body: CaseAttachResolutionRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
    ],
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: IdentityCommandApplicationService = Depends(get_identity_command_service),
) -> CaseAttachmentDTO:
    outcome = service.attach_resolution(
        principal=principal,
        case_id=case_id,
        identity_resolution_id=body.resolution_id,
        expected_case_version=body.case_version,
        idempotency_key=idempotency_key,
        request_id=correlation_request_id(request),
    )
    return CaseAttachmentDTO(case=case_dto(outcome.case), link=case_link_dto(outcome.link))


@router.get(
    "/property-resolutions/{identity_resolution_id}",
    response_model=PropertyResolutionDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}},
)
def get_property_resolution(
    identity_resolution_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: IdentityResolutionApplicationService = Depends(
        get_resolution_application_service
    ),
) -> PropertyResolutionDTO:
    return resolution_dto(
        service.get(
            principal=principal,
            identity_resolution_id=identity_resolution_id,
        )
    )


@router.get(
    "/properties/{property_entity_id}",
    response_model=PropertyDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}},
)
def get_property(
    property_entity_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    repository: PostgresPropertyReadRepository = Depends(get_property_read_repository),
) -> PropertyDTO:
    return property_dto(
        repository.get_property(
            principal=principal,
            property_entity_id=property_entity_id,
        )
    )


@router.get(
    "/properties/{property_entity_id}/graph",
    response_model=PropertyGraphDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
def get_property_graph(
    property_entity_id: UUID,
    as_of: datetime | None = Query(default=None),
    relation_type: PropertyRelationType | None = Query(default=None),
    status: PropertyRelationStatus | None = Query(default=None),
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    repository: PostgresPropertyReadRepository = Depends(get_property_read_repository),
    codec: CursorCodec = Depends(get_cursor_codec),
) -> PropertyGraphDTO:
    position = None
    if cursor is not None:
        decoded = codec.decode(
            cursor,
            kind="property_graph",
            expected_fields=frozenset({"created_at", "relation_id"}),
        )
        created_at = cursor_datetime(decoded.fields["created_at"])
        if created_at is None:
            raise VNextError.validation_failed()
        position = GraphPosition(
            created_at=created_at,
            relation_id=cursor_uuid(decoded.fields["relation_id"]),
        )
    page = repository.get_graph(
        principal=principal,
        property_entity_id=property_entity_id,
        as_of=as_of,
        relation_type=relation_type,
        status=status,
        position=position,
        limit=limit,
    )
    return _graph_dto(page, codec)


@router.get(
    "/properties/{property_entity_id}/evidence",
    response_model=PropertyEvidenceDTO,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_identity_feature),
    ],
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
def get_property_evidence(
    property_entity_id: UUID,
    fact_type: Annotated[str | None, Query(min_length=3, max_length=120)] = None,
    status: EvidenceStatus | None = Query(default=None),
    effective_at: datetime | None = Query(default=None),
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    repository: PostgresPropertyReadRepository = Depends(get_property_read_repository),
    codec: CursorCodec = Depends(get_cursor_codec),
) -> PropertyEvidenceDTO:
    if fact_type is not None and not _FACT_TYPE.fullmatch(fact_type):
        raise VNextError.validation_failed()
    position = None
    if cursor is not None:
        decoded = codec.decode(
            cursor,
            kind="property_evidence",
            expected_fields=frozenset(
                {"fact_type", "effective_from", "retrieved_at", "evidence_id"}
            ),
        )
        retrieved_at = cursor_datetime(decoded.fields["retrieved_at"])
        if retrieved_at is None or not decoded.fields["fact_type"]:
            raise VNextError.validation_failed()
        position = EvidencePosition(
            fact_type=str(decoded.fields["fact_type"]),
            effective_from=cursor_datetime(decoded.fields["effective_from"]),
            retrieved_at=retrieved_at,
            evidence_id=cursor_uuid(decoded.fields["evidence_id"]),
        )
    page = repository.get_evidence(
        principal=principal,
        property_entity_id=property_entity_id,
        fact_type=fact_type,
        status=status,
        effective_at=effective_at,
        position=position,
        limit=limit,
    )
    return _evidence_page_dto(page, codec)
