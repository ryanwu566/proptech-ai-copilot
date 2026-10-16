"""Auth/account protected personal cloud-case API; persistence is not enabled."""
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Query, Response

from backend.api.v1.router import reject_client_identity_overrides
from backend.api.v1.errors import vnext_error_responses
from services.vnext.accounts import require_active_account
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal
from services.vnext.durable_cases import (
    Activity, CaseService, CaseSummary, CaseView, CreateCase, MembershipUpdate,
    IDEMPOTENCY_PATTERN, MetadataUpdate, MonitoringUpdate, Scope, get_case_service,
)

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128, pattern=IDEMPOTENCY_PATTERN)]


def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/v1/saved-cases", tags=["personal-saved-cases"], responses=vnext_error_responses(401, 403, 404, 409, 422, 503), dependencies=[
    Depends(require_authenticated_principal), Depends(require_active_account),
    Depends(reject_client_identity_overrides), Depends(no_store),
])


@router.post("", response_model=CaseView, status_code=201)
def create_case(body: CreateCase, idempotency_key: IdempotencyKey, principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.create(principal, body, idempotency_key=idempotency_key)


@router.get("", response_model=list[CaseSummary])
def list_cases(scope: Scope = "owned", offset: int = Query(0, ge=0, le=10000), limit: int = Query(20, ge=1, le=100),
               principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.list(principal, scope=scope, offset=offset, limit=limit)


@router.get("/{case_id}", response_model=CaseView)
def open_case(case_id: UUID, principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.open(principal, case_id)


@router.patch("/{case_id}/metadata", response_model=CaseView)
def update_metadata(case_id: UUID, body: MetadataUpdate, idempotency_key: IdempotencyKey, principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.metadata(principal, case_id, body, idempotency_key=idempotency_key)


@router.put("/{case_id}/membership", response_model=CaseView)
def update_membership(case_id: UUID, body: MembershipUpdate, idempotency_key: IdempotencyKey, principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.membership(principal, case_id, body, idempotency_key=idempotency_key)


@router.put("/{case_id}/monitoring", response_model=CaseView)
def update_monitoring(case_id: UUID, body: MonitoringUpdate, idempotency_key: IdempotencyKey, principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.monitoring(principal, case_id, body, idempotency_key=idempotency_key)


@router.get("/{case_id}/activity", response_model=list[Activity])
def read_activity(case_id: UUID, offset: int = Query(0, ge=0, le=10000), limit: int = Query(20, ge=1, le=100),
                  principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), service: CaseService = Depends(get_case_service)):
    return service.activity(principal, case_id, offset=offset, limit=limit)
