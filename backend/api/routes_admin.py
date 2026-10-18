"""Every admin read authorizes independently before touching its source."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from backend.api.v1.errors import vnext_error_responses

from services.admin.authorization import require_platform_admin
from services.admin.contracts import AdminSnapshot, Section, UserRow
from services.admin.commands import AccountCommand, QuotaCommand, QuotaPolicy
from services.admin.store import AdminStore, get_admin_store
from services.vnext.auth import AuthenticatedPrincipal
from backend.api.v1.router import reject_client_identity_overrides
from services.admin.summaries import AdminSummarySource, get_admin_summary_source
from services.vnext.errors import VNextError

router = APIRouter(prefix="/v1/admin", tags=["admin"],
    responses=vnext_error_responses(401, 403, 404, 409, 422, 503),
    dependencies=[Depends(require_platform_admin), Depends(reject_client_identity_overrides)])


@router.get('/accounts/{target}', response_model=UserRow)
def exact_account(target: UUID, response: Response,
    principal: AuthenticatedPrincipal = Depends(require_platform_admin), store: AdminStore = Depends(get_admin_store)):
    response.headers['Cache-Control'] = 'private, no-store'
    return store.account(principal, target)


@router.post('/accounts/{target}/commands')
def account_command(target: UUID, command: AccountCommand, response: Response,
    principal: AuthenticatedPrincipal = Depends(require_platform_admin), store: AdminStore = Depends(get_admin_store)):
    response.headers['Cache-Control'] = 'private, no-store'
    return store.command(principal, command, target)


@router.get('/quota-policy', response_model=list[QuotaPolicy])
def quota_policy(response: Response, principal: AuthenticatedPrincipal = Depends(require_platform_admin),
    store: AdminStore = Depends(get_admin_store)):
    response.headers['Cache-Control'] = 'private, no-store'
    return store.policies(principal)


@router.post('/quota-policy/commands')
def quota_command(command: QuotaCommand, response: Response,
    principal: AuthenticatedPrincipal = Depends(require_platform_admin), store: AdminStore = Depends(get_admin_store)):
    response.headers['Cache-Control'] = 'private, no-store'
    return store.command(principal, command)


@router.get("/{section}", response_model=AdminSnapshot, responses=vnext_error_responses(401, 403, 422, 503))
def read_admin_section(
    section: Section,
    response: Response,
    cursor: Annotated[str | None, Query(max_length=128, pattern=r"^[A-Za-z0-9_-]{1,128}$")] = None,
    source: AdminSummarySource = Depends(get_admin_summary_source),
) -> AdminSnapshot:
    response.headers["Cache-Control"] = "private, no-store"
    try:
        snapshot = AdminSnapshot.model_validate(source.read(section, cursor))
        if snapshot.section != section:
            raise ValueError("wrong section")
        return snapshot
    except VNextError:
        raise
    except Exception:
        # No dependency exception/payload reaches logs or clients.
        raise VNextError.provider_unavailable() from None
