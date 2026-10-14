from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app
from services.vnext.auth import AuthenticatedPrincipal, get_supabase_jwt_verifier
from services.vnext.accounts import Account, AccountAuthorizer, get_account_authorizer
from services.vnext.errors import VNextError
from services.vnext.authorization import WorkspaceAuthorizer, WorkspaceMembership, WorkspaceRole
from tests.test_vnext_auth_api import ISSUER, USER_ID, _token, verifier


class Repository:
    def __init__(self, account):
        self.account = account

    def get_account(self, *, principal):
        return self.account


def account(status="active", role="consumer", user_id=USER_ID):
    now = datetime.now(timezone.utc)
    return Account(user_id, status, role, now, now)


def principal():
    return AuthenticatedPrincipal(USER_ID, str(USER_ID), ISSUER)


@pytest.mark.parametrize("value", [None, account("suspended"), account(role="owner"), account(user_id=UUID(int=2))])
def test_account_authority_fails_closed(value):
    with pytest.raises(VNextError):
        AccountAuthorizer(Repository(value)).require_active(principal())


def test_default_consumer_cannot_be_platform_admin():
    authority = AccountAuthorizer(Repository(account()))
    assert authority.require_active(principal()).platform_role == "consumer"
    with pytest.raises(VNextError):
        authority.require_platform_admin(principal())


def test_active_authoritative_admin_is_allowed():
    assert AccountAuthorizer(Repository(account(role="platform_admin"))).require_platform_admin(principal()).platform_role == "platform_admin"


@pytest.mark.parametrize("role", list(WorkspaceRole))
def test_workspace_role_and_user_metadata_do_not_grant_platform_authority(verifier, role):
    verified = verifier.verify(_token(user_metadata={"platform_role": "platform_admin", "role": "platform_admin"}))
    workspace_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    class Memberships:
        def get_active_membership(self, *, principal, workspace_id):
            return WorkspaceMembership(workspace_id, principal.user_id, role)
    membership = WorkspaceAuthorizer(Memberships()).require_workspace_access(verified, workspace_id)
    assert membership.role == role
    with pytest.raises(VNextError) as error:
        AccountAuthorizer(Repository(account())).require_platform_admin(verified)
    assert str(error.value) == "permission_denied"


@pytest.mark.parametrize("value", [account("unknown"), account(role="admin"), account(role=""), account(role=None), account("suspended", "platform_admin")])
def test_malformed_or_suspended_authority_cannot_authorize_platform_admin(value):
    with pytest.raises(VNextError):
        AccountAuthorizer(Repository(value)).require_platform_admin(principal())


def test_repository_error_denies_without_exception_details():
    class Broken:
        def get_account(self, *, principal):
            raise RuntimeError("secret SQL password JWT")
    with pytest.raises(VNextError) as error:
        AccountAuthorizer(Broken()).require_active(principal())
    assert str(error.value) == "account_unavailable"


@pytest.mark.parametrize("status,expected", [("active", 200), ("suspended", 403), (None, 503)])
def test_direct_protected_api_enforces_account_status(verifier, status, expected):
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repository(account(status) if status else None))
    try:
        with TestClient(app) as client:
            response = client.get("/v1", headers={"Authorization": f"Bearer {_token(user_metadata={'platform_role': 'platform_admin'})}"})
            assert response.status_code == expected
            if status == "suspended":
                assert response.json()["error"]["code"] == "account_suspended"
            if expected != 200:
                assert "secret" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_suspended_user_can_read_own_status_but_cannot_write_or_choose_identity(verifier):
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repository(account("suspended")))
    try:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {_token()}"}
            response = client.get("/v1/account", headers=headers)
            assert response.status_code == 200
            assert response.json()["status"] == "suspended"
            assert response.headers["cache-control"] == "no-store"
            assert client.post("/v1/account", headers=headers, json={"platform_role": "platform_admin"}).status_code in {405, 422}
            assert client.get("/v1/account?user_id=other", headers=headers).status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("method,path", [
    ("GET", "/v1/workspaces/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/context"),
    ("GET", "/v1/properties/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    ("GET", "/v1/cases/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/parcel-set"),
    ("POST", "/v1/cases"),
    ("POST", "/v1/property-resolutions"),
    ("POST", "/v1/cases/import-legacy"),
])
def test_suspended_principal_cannot_bypass_via_domain_routes(verifier, method, path):
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repository(account("suspended")))
    try:
        with TestClient(app) as client:
            response = client.request(method, path, headers={"Authorization": f"Bearer {_token()}"}, **({"json": {}} if method == "POST" else {}))
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "account_suspended"
    finally:
        app.dependency_overrides.clear()
