from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app
from services.vnext.auth import get_supabase_jwt_verifier
from services.vnext.accounts import get_account_authorizer
from services.vnext.durable_cases import CaseService, get_case_service
from tests.account_fixtures import active_account_authorizer
from tests.durable_case_fixtures import MemoryCaseRepository, snapshot
from tests.test_vnext_auth_api import _token, verifier  # noqa: F401


@pytest.fixture
def client(verifier):
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_account_authorizer] = active_account_authorizer
    app.dependency_overrides[get_case_service] = lambda: service
    service = CaseService(MemoryCaseRepository())
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def auth(user=None):
    return {"Authorization": f"Bearer {_token(**({'subject': str(user)} if user else {}))}"}


def test_api_import_read_acl_conflict_and_no_cache(client):
    payload = {"snapshot": snapshot(), "import_key": "local-case", "explicit_consent": True}
    response = client.post("/v1/saved-cases", headers=auth(), json=payload)
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    value = response.json(); case_id = value["id"]
    assert value["snapshot"] == payload["snapshot"]
    assert client.get(f"/v1/saved-cases/{case_id}", headers=auth(UUID(int=2))).status_code == 404
    assert client.get("/v1/saved-cases", headers=auth(UUID(int=2))).json() == []
    assert client.get(f"/v1/saved-cases/{case_id}").status_code == 401
    assert client.patch(f"/v1/saved-cases/{case_id}/metadata", headers=auth(), json={"expected_revision": 1, "notes": "authored"}).status_code == 200
    assert client.patch(f"/v1/saved-cases/{case_id}/metadata", headers=auth(), json={"expected_revision": 1, "notes": "stale"}).status_code == 409
    assert client.put(f"/v1/saved-cases/{case_id}/membership", headers=auth(), json={"expected_revision": 2, "member_id": str(UUID(int=2)), "role": "viewer"}).status_code == 200
    assert client.get(f"/v1/saved-cases/{case_id}", headers=auth(UUID(int=2))).status_code == 200
    assert client.patch(f"/v1/saved-cases/{case_id}/metadata", headers=auth(UUID(int=2)), json={"expected_revision": 3, "notes": "deny"}).status_code == 403


@pytest.mark.parametrize("path", ["", "/00000000-0000-0000-0000-000000000001", "/00000000-0000-0000-0000-000000000001/activity"])
def test_identity_and_pagination_are_not_authority(client, path):
    assert client.get(f"/v1/saved-cases{path}?user_id=forged", headers=auth()).status_code == 422
    assert client.get(f"/v1/saved-cases{path}", headers={**auth(), "X-Workspace-Role": "owner"}).status_code == 422
    assert client.get("/v1/saved-cases?limit=1000", headers=auth()).status_code == 422


def test_default_api_unavailable_and_suspension_fail_closed(client):
    app.dependency_overrides.pop(get_case_service)
    response = client.get("/v1/saved-cases", headers=auth())
    assert response.status_code == 503
    assert response.json()["error"]["details"]["reason_code"] == "persistence_pending"
    from tests.test_consumer_account import AccountAuthorizer, Repository, account
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repository(account("suspended")))
    assert client.get("/v1/saved-cases", headers=auth()).status_code == 403


def test_validation_does_not_echo_secrets(client):
    response = client.post("/v1/saved-cases", headers=auth(), json={"snapshot": snapshot(), "import_key": "key", "explicit_consent": True, "password": "SECRET"})
    assert response.status_code == 422 and "SECRET" not in response.text
