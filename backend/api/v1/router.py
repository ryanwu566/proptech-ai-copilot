"""Authenticated infrastructure-only VNext routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal
from services.vnext.authorization import (
    WorkspaceAuthorizer,
    get_workspace_authorizer,
)
from services.vnext.errors import VNextError
from services.vnext.feature_flags import (
    VNextFeatureFlags,
    get_vnext_feature_flags,
)


router = APIRouter(
    prefix="/v1",
    tags=["vnext-infrastructure"],
    dependencies=[Depends(require_authenticated_principal)],
)

_FORGED_IDENTITY_HEADERS = frozenset({"x-user-id", "x-role", "x-workspace-role"})
_FORGED_IDENTITY_QUERY_FIELDS = frozenset({"user_id", "role", "workspace_role"})


def reject_client_identity_overrides(request: Request) -> None:
    header_names = {name.lower() for name in request.headers.keys()}
    query_names = set(request.query_params.keys())
    if header_names & _FORGED_IDENTITY_HEADERS or query_names & _FORGED_IDENTITY_QUERY_FIELDS:
        raise VNextError.validation_failed()


@router.get("")
def vnext_context(
    _identity_boundary: None = Depends(reject_client_identity_overrides),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    flags: VNextFeatureFlags = Depends(get_vnext_feature_flags),
) -> dict[str, object]:
    """Return a bounded authenticated context without domain/resource data."""

    return {
        "status": "ok",
        "principal": {"user_id": str(principal.user_id)},
        "features": {"identity_v1": flags.identity_v1},
    }


@router.get("/workspaces/{workspace_id}/context")
def workspace_context(
    workspace_id: UUID,
    _identity_boundary: None = Depends(reject_client_identity_overrides),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    authorizer: WorkspaceAuthorizer = Depends(get_workspace_authorizer),
) -> dict[str, str]:
    """Exercise server-side membership resolution without domain endpoints."""

    membership = authorizer.require_workspace_access(principal, workspace_id)
    return {
        "status": "ok",
        "workspace_id": str(membership.workspace_id),
        "user_id": str(membership.user_id),
        "role": membership.role.value,
    }
