from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import (
    ALL_WORKSPACE_ROLES,
    WorkspaceAuthorizer,
    WorkspaceMembership,
    WorkspaceMembershipStatus,
    WorkspaceRole,
)
from services.vnext.errors import VNextError


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_WORKSPACE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PRINCIPAL = AuthenticatedPrincipal(
    user_id=USER_ID,
    token_subject=str(USER_ID),
    issuer="https://fixture.supabase.co/auth/v1",
    token_issued_at=datetime.now(timezone.utc),
)


class _Repository:
    def __init__(self, memberships: list[WorkspaceMembership]) -> None:
        self._memberships = {
            (item.workspace_id, item.user_id): item for item in memberships
        }

    def get_active_membership(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ):
        return self._memberships.get((workspace_id, principal.user_id))


def test_no_membership_denies_access() -> None:
    authorizer = WorkspaceAuthorizer(_Repository([]))

    with pytest.raises(VNextError) as error:
        authorizer.require_workspace_access(PRINCIPAL, WORKSPACE_ID)

    assert error.value.code.value == "permission_denied"


@pytest.mark.parametrize("role", list(WorkspaceRole))
def test_every_defined_active_role_has_base_read_access(role: WorkspaceRole) -> None:
    membership = WorkspaceMembership(WORKSPACE_ID, USER_ID, role)
    authorizer = WorkspaceAuthorizer(_Repository([membership]))

    assert authorizer.require_workspace_access(PRINCIPAL, WORKSPACE_ID) == membership
    assert authorizer.require_workspace_role(
        PRINCIPAL,
        WORKSPACE_ID,
        allowed_roles=ALL_WORKSPACE_ROLES,
    ) == membership


def test_role_requirement_is_explicit_and_fails_closed() -> None:
    viewer = WorkspaceMembership(WORKSPACE_ID, USER_ID, WorkspaceRole.VIEWER)
    authorizer = WorkspaceAuthorizer(_Repository([viewer]))

    with pytest.raises(VNextError):
        authorizer.require_workspace_role(
            PRINCIPAL,
            WORKSPACE_ID,
            allowed_roles={WorkspaceRole.MEMBER, WorkspaceRole.MANAGER},
        )


def test_revoked_membership_fails_closed() -> None:
    revoked = WorkspaceMembership(
        WORKSPACE_ID,
        USER_ID,
        WorkspaceRole.OWNER,
        WorkspaceMembershipStatus.REMOVED,
    )
    authorizer = WorkspaceAuthorizer(_Repository([revoked]))

    with pytest.raises(VNextError):
        authorizer.require_workspace_access(PRINCIPAL, WORKSPACE_ID)


def test_cross_workspace_and_cross_user_memberships_do_not_authorize() -> None:
    memberships = [
        WorkspaceMembership(OTHER_WORKSPACE_ID, USER_ID, WorkspaceRole.OWNER),
        WorkspaceMembership(WORKSPACE_ID, OTHER_USER_ID, WorkspaceRole.OWNER),
    ]
    authorizer = WorkspaceAuthorizer(_Repository(memberships))

    with pytest.raises(VNextError):
        authorizer.require_workspace_access(PRINCIPAL, WORKSPACE_ID)
