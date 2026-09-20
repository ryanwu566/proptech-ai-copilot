"""Feature-gated API for durable Case-local parcel-set review."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.v1.errors import request_id as correlation_request_id
from backend.api.v1.errors import vnext_error_responses
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal
from services.vnext.authorization import WorkspaceAuthorizer, get_workspace_authorizer
from services.vnext.case_parcel_set import (
    CaseParcelSetMemberRecord,
    CaseParcelSetRecord,
    ParcelMemberReviewStatus,
    ParcelSetStatus,
)
from services.vnext.case_parcel_set_repository import PostgresCaseParcelSetRepository
from services.vnext.case_parcel_set_service import CaseParcelSetApplicationService
from services.vnext.db_principal import get_vnext_database_principal_context
from services.vnext.errors import VNextError
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags
from services.vnext.persistence import PostgresIdempotencyRepository


router = APIRouter(tags=["vnext-case-parcel-set"])

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]{16,128}$",
    ),
]
ExistingVersion = Annotated[int, Field(ge=1)]
_FORGED_HEADERS = frozenset({"x-user-id", "x-role", "x-workspace-role"})
_FORGED_QUERY = frozenset({"user_id", "role", "workspace_role"})


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InitializeParcelSetRequest(_StrictModel):
    workspace_id: UUID
    expected_version: Literal[0]


class AddParcelMemberRequest(_StrictModel):
    workspace_id: UUID
    parcel_identity_reference_id: UUID
    expected_version: ExistingVersion


class ReviewParcelMemberRequest(_StrictModel):
    workspace_id: UUID
    review_status: ParcelMemberReviewStatus
    expected_version: ExistingVersion


class SetActiveParcelMemberRequest(_StrictModel):
    workspace_id: UUID
    active_member_id: UUID | None
    expected_version: ExistingVersion


class ReorderParcelMembersRequest(_StrictModel):
    workspace_id: UUID
    ordered_member_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]
    expected_version: ExistingVersion

    @field_validator("ordered_member_ids")
    @classmethod
    def require_distinct_members(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate parcel-set member")
        return value


class MarkParcelSetCaseReviewedRequest(_StrictModel):
    workspace_id: UUID
    expected_version: ExistingVersion


class CaseParcelSetMemberDTO(_StrictModel):
    parcel_set_member_id: UUID
    parcel_identity_reference_id: UUID
    position: Annotated[int, Field(ge=1, le=100)]
    review_status: ParcelMemberReviewStatus
    created_at: datetime
    updated_at: datetime


class CaseParcelSetDTO(_StrictModel):
    parcel_set_id: UUID
    workspace_id: UUID
    case_id: UUID
    status: ParcelSetStatus
    version: Annotated[int, Field(ge=1)]
    active_member_id: UUID | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    members: Annotated[list[CaseParcelSetMemberDTO], Field(max_length=100)]


def reject_client_identity_overrides(request: Request) -> None:
    if {name.lower() for name in request.headers} & _FORGED_HEADERS or set(
        request.query_params
    ) & _FORGED_QUERY:
        raise VNextError.validation_failed()


def require_case_parcel_set_feature(
    flags: VNextFeatureFlags = Depends(get_vnext_feature_flags),
) -> None:
    if not flags.case_parcel_set_v1:
        raise VNextError.not_found()


def get_case_parcel_set_repository() -> PostgresCaseParcelSetRepository:
    return PostgresCaseParcelSetRepository(
        get_vnext_database_principal_context(), get_workspace_authorizer()
    )


def get_case_parcel_set_idempotency_repository() -> PostgresIdempotencyRepository:
    return PostgresIdempotencyRepository(
        get_vnext_database_principal_context(), get_workspace_authorizer()
    )


def get_case_parcel_set_service(
    repository: PostgresCaseParcelSetRepository = Depends(
        get_case_parcel_set_repository
    ),
    idempotency_repository: PostgresIdempotencyRepository = Depends(
        get_case_parcel_set_idempotency_repository
    ),
    authorizer: WorkspaceAuthorizer = Depends(get_workspace_authorizer),
) -> CaseParcelSetApplicationService:
    return CaseParcelSetApplicationService(
        authorizer=authorizer,
        writer=repository,
        idempotency_repository=idempotency_repository,
    )


def _member_dto(record: CaseParcelSetMemberRecord) -> CaseParcelSetMemberDTO:
    return CaseParcelSetMemberDTO(
        parcel_set_member_id=record.parcel_set_member_id,
        parcel_identity_reference_id=record.parcel_identity_reference_id,
        position=record.position,
        review_status=record.review_status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _dto(record: CaseParcelSetRecord) -> CaseParcelSetDTO:
    return CaseParcelSetDTO(
        parcel_set_id=record.parcel_set_id,
        workspace_id=record.workspace_id,
        case_id=record.case_id,
        status=record.status,
        version=record.version,
        active_member_id=record.active_member_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        reviewed_at=record.reviewed_at,
        members=[_member_dto(member) for member in record.members],
    )


_ROUTE_DEPENDENCIES = [
    Depends(reject_client_identity_overrides),
    Depends(require_case_parcel_set_feature),
]
_ERRORS = vnext_error_responses(401, 403, 404, 409, 422, 500, 503)


@router.get(
    "/cases/{case_id}/parcel-set",
    response_model=CaseParcelSetDTO,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def get_case_parcel_set(
    case_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    return _dto(service.get(principal=principal, case_id=case_id))


@router.post(
    "/cases/{case_id}/parcel-set",
    response_model=CaseParcelSetDTO,
    status_code=201,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def initialize_case_parcel_set(
    case_id: UUID,
    body: InitializeParcelSetRequest,
    request: Request,
    response: Response,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    outcome = service.initialize(
        principal=principal,
        workspace_id=body.workspace_id,
        case_id=case_id,
        expected_version=body.expected_version,
        idempotency_key=idempotency_key,
        request_id=correlation_request_id(request),
    )
    if outcome.replayed:
        response.status_code = 200
    return _dto(outcome.record)


@router.post(
    "/cases/{case_id}/parcel-set/members",
    response_model=CaseParcelSetDTO,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def add_case_parcel_set_member(
    case_id: UUID,
    body: AddParcelMemberRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    return _dto(
        service.add_member(
            principal=principal,
            workspace_id=body.workspace_id,
            case_id=case_id,
            parcel_identity_reference_id=body.parcel_identity_reference_id,
            expected_version=body.expected_version,
            idempotency_key=idempotency_key,
            request_id=correlation_request_id(request),
        ).record
    )


@router.post(
    "/cases/{case_id}/parcel-set/members/{member_id}/review",
    response_model=CaseParcelSetDTO,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def review_case_parcel_set_member(
    case_id: UUID,
    member_id: UUID,
    body: ReviewParcelMemberRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    return _dto(
        service.review_member(
            principal=principal,
            workspace_id=body.workspace_id,
            case_id=case_id,
            member_id=member_id,
            review_status=body.review_status,
            expected_version=body.expected_version,
            idempotency_key=idempotency_key,
            request_id=correlation_request_id(request),
        ).record
    )


@router.post(
    "/cases/{case_id}/parcel-set/active-member",
    response_model=CaseParcelSetDTO,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def set_case_parcel_set_active_member(
    case_id: UUID,
    body: SetActiveParcelMemberRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    return _dto(
        service.set_active_member(
            principal=principal,
            workspace_id=body.workspace_id,
            case_id=case_id,
            active_member_id=body.active_member_id,
            expected_version=body.expected_version,
            idempotency_key=idempotency_key,
            request_id=correlation_request_id(request),
        ).record
    )


@router.post(
    "/cases/{case_id}/parcel-set/reorder",
    response_model=CaseParcelSetDTO,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def reorder_case_parcel_set_members(
    case_id: UUID,
    body: ReorderParcelMembersRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    return _dto(
        service.reorder(
            principal=principal,
            workspace_id=body.workspace_id,
            case_id=case_id,
            ordered_member_ids=tuple(body.ordered_member_ids),
            expected_version=body.expected_version,
            idempotency_key=idempotency_key,
            request_id=correlation_request_id(request),
        ).record
    )


@router.post(
    "/cases/{case_id}/parcel-set/review",
    response_model=CaseParcelSetDTO,
    dependencies=_ROUTE_DEPENDENCIES,
    responses=_ERRORS,
)
def mark_case_parcel_set_reviewed(
    case_id: UUID,
    body: MarkParcelSetCaseReviewedRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: CaseParcelSetApplicationService = Depends(get_case_parcel_set_service),
) -> CaseParcelSetDTO:
    return _dto(
        service.mark_case_reviewed(
            principal=principal,
            workspace_id=body.workspace_id,
            case_id=case_id,
            expected_version=body.expected_version,
            idempotency_key=idempotency_key,
            request_id=correlation_request_id(request),
        ).record
    )
