"""Workspace membership and role authorization contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Collection, Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.errors import VNextError


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


ALL_WORKSPACE_ROLES = frozenset(WorkspaceRole)


@dataclass(frozen=True)
class WorkspaceMembership:
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole


class WorkspaceMembershipRepository(Protocol):
    """Persistence seam for the future Stage 1A membership repository."""

    def get_active_membership(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None: ...


class UnavailableWorkspaceMembershipRepository:
    """Default until membership persistence is present; always fail closed."""

    def get_active_membership(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None:
        return None


class WorkspaceAuthorizer:
    def __init__(self, repository: WorkspaceMembershipRepository) -> None:
        self._repository = repository

    def require_workspace_access(
        self,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership:
        membership = self._repository.get_active_membership(
            workspace_id=workspace_id,
            user_id=principal.user_id,
        )
        if (
            membership is None
            or membership.workspace_id != workspace_id
            or membership.user_id != principal.user_id
            or membership.role not in ALL_WORKSPACE_ROLES
        ):
            raise VNextError.permission_denied()
        return membership

    def require_workspace_role(
        self,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        *,
        allowed_roles: Collection[WorkspaceRole],
    ) -> WorkspaceMembership:
        membership = self.require_workspace_access(principal, workspace_id)
        allowed = frozenset(allowed_roles)
        if not allowed or membership.role not in allowed:
            raise VNextError.permission_denied()
        return membership


_DEFAULT_AUTHORIZER = WorkspaceAuthorizer(UnavailableWorkspaceMembershipRepository())


def get_workspace_authorizer() -> WorkspaceAuthorizer:
    return _DEFAULT_AUTHORIZER
