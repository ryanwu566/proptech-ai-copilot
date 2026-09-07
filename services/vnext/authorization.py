"""Workspace membership and role authorization contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Collection, Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.db_principal import (
    DatabasePrincipalContext,
    get_vnext_database_principal_context,
)
from services.vnext.errors import VNextError


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


ALL_WORKSPACE_ROLES = frozenset(WorkspaceRole)


class WorkspaceMembershipStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LEFT = "left"
    REMOVED = "removed"


@dataclass(frozen=True)
class WorkspaceMembership:
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    status: WorkspaceMembershipStatus = WorkspaceMembershipStatus.ACTIVE


class WorkspaceMembershipRepository(Protocol):
    """Persistence seam for the future Stage 1A membership repository."""

    def get_active_membership(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership | None: ...


class UnavailableWorkspaceMembershipRepository:
    """Default until membership persistence is present; always fail closed."""

    def get_active_membership(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership | None:
        return None


class PostgresWorkspaceMembershipRepository:
    """Resolve the caller's own membership under its validated DB principal."""

    def __init__(
        self,
        context_provider: Callable[[], DatabasePrincipalContext] = (
            get_vnext_database_principal_context
        ),
    ) -> None:
        self._context_provider = context_provider

    def get_active_membership(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership | None:
        try:
            with self._context_provider().transaction(principal) as connection:
                row = connection.execute(
                    "SELECT workspace_id, user_id, role, status "
                    "FROM vnext_core.workspace_members "
                    "WHERE workspace_id = %s AND user_id = %s AND status = 'active'",
                    (workspace_id, principal.user_id),
                ).fetchone()
        except Exception:
            # Membership infrastructure is an authorization dependency.  Any
            # configuration, role, principal, RLS, or query failure denies.
            return None
        if row is None:
            return None
        try:
            membership = WorkspaceMembership(
                workspace_id=UUID(str(row[0])),
                user_id=UUID(str(row[1])),
                role=WorkspaceRole(str(row[2])),
                status=WorkspaceMembershipStatus(str(row[3])),
            )
        except (TypeError, ValueError):
            return None
        if (
            membership.workspace_id != workspace_id
            or membership.user_id != principal.user_id
            or membership.status != WorkspaceMembershipStatus.ACTIVE
        ):
            return None
        return membership


class WorkspaceAuthorizer:
    def __init__(self, repository: WorkspaceMembershipRepository) -> None:
        self._repository = repository

    def require_workspace_access(
        self,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership:
        membership = self._repository.get_active_membership(
            principal=principal,
            workspace_id=workspace_id,
        )
        if (
            membership is None
            or membership.workspace_id != workspace_id
            or membership.user_id != principal.user_id
            or membership.role not in ALL_WORKSPACE_ROLES
            or membership.status != WorkspaceMembershipStatus.ACTIVE
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


_DEFAULT_AUTHORIZER = WorkspaceAuthorizer(PostgresWorkspaceMembershipRepository())


def get_workspace_authorizer() -> WorkspaceAuthorizer:
    return _DEFAULT_AUTHORIZER
