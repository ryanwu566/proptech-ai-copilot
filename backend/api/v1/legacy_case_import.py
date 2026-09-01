"""Explicit, feature-gated SavedCase v1 COPY import API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, StringConstraints

from backend.api.v1.errors import request_id as correlation_request_id
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal
from services.vnext.authorization import WorkspaceAuthorizer, get_workspace_authorizer
from services.vnext.db_principal import get_vnext_database_principal_context
from services.vnext.errors import VNextError
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags
from services.vnext.legacy_case_import_repository import PostgresLegacyCaseImportRepository
from services.vnext.legacy_case_import_service import LegacyCaseImportApplicationService
from services.vnext.persistence import PostgresIdempotencyRepository


router = APIRouter(tags=["vnext-legacy-case-import"])

LegacyClientId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=256,
        pattern=r"^[A-Za-z0-9._:-]+$",
    ),
]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]{16,128}$",
    ),
]
_FORGED_HEADERS = frozenset({"x-user-id", "x-role", "x-workspace-role"})
_FORGED_QUERY = frozenset({"user_id", "role", "workspace_role"})


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LegacyCaseImportRequest(_StrictModel):
    workspace_id: UUID
    legacy_format: Literal["saved_case_v1"]
    legacy_client_id: LegacyClientId
    payload: dict[str, object]
    import_mode: Literal["copy"]
    consent: Literal[True]


class LegacyCaseImportDTO(_StrictModel):
    legacy_case_import_id: UUID
    case_id: UUID
    workspace_id: UUID
    import_status: Literal["imported_unverified"]
    identity_status: Literal["legacy_unverified"]
    property_entity_id: None
    resolution_id: None
    accepted_field_classes: list[str]
    dropped_field_classes: list[str]
    warnings: list[str]
    evidence_ids: list[UUID]
    imported_at: datetime


def reject_client_identity_overrides(request: Request) -> None:
    if {name.lower() for name in request.headers} & _FORGED_HEADERS or set(
        request.query_params
    ) & _FORGED_QUERY:
        raise VNextError.validation_failed()


def require_legacy_import_feature(
    flags: VNextFeatureFlags = Depends(get_vnext_feature_flags),
) -> None:
    if not flags.legacy_case_import_v1:
        raise VNextError.not_found()


def get_legacy_import_repository() -> PostgresLegacyCaseImportRepository:
    return PostgresLegacyCaseImportRepository(
        get_vnext_database_principal_context(), get_workspace_authorizer()
    )


def get_legacy_import_idempotency_repository() -> PostgresIdempotencyRepository:
    return PostgresIdempotencyRepository(
        get_vnext_database_principal_context(), get_workspace_authorizer()
    )


def get_legacy_import_service(
    repository: PostgresLegacyCaseImportRepository = Depends(get_legacy_import_repository),
    idempotency_repository: PostgresIdempotencyRepository = Depends(
        get_legacy_import_idempotency_repository
    ),
    authorizer: WorkspaceAuthorizer = Depends(get_workspace_authorizer),
) -> LegacyCaseImportApplicationService:
    return LegacyCaseImportApplicationService(
        authorizer=authorizer,
        repository=repository,
        idempotency_repository=idempotency_repository,
    )


@router.post(
    "/cases/import-legacy",
    response_model=LegacyCaseImportDTO,
    status_code=201,
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_legacy_import_feature),
    ],
    responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}, 503: {}},
)
def import_legacy_case(
    body: LegacyCaseImportRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    service: LegacyCaseImportApplicationService = Depends(get_legacy_import_service),
) -> LegacyCaseImportDTO:
    outcome = service.import_case(
        principal=principal,
        workspace_id=body.workspace_id,
        legacy_format=body.legacy_format,
        legacy_client_id=body.legacy_client_id,
        payload=body.payload,
        import_mode=body.import_mode,
        consent=body.consent,
        idempotency_key=idempotency_key,
        request_id=correlation_request_id(request),
    )
    record = outcome.result.import_record
    return LegacyCaseImportDTO(
        legacy_case_import_id=record.legacy_case_import_id,
        case_id=outcome.result.case.case_id,
        workspace_id=record.workspace_id,
        import_status="imported_unverified",
        identity_status="legacy_unverified",
        property_entity_id=None,
        resolution_id=None,
        accepted_field_classes=list(record.accepted_field_classes),
        dropped_field_classes=list(record.dropped_field_classes),
        warnings=list(record.warnings),
        evidence_ids=list(outcome.result.evidence_ids),
        imported_at=record.imported_at,
    )
