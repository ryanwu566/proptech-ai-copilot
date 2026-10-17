from uuid import UUID, uuid4

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
    return {"Authorization": f"Bearer {_token(**({'subject': str(user)} if user else {}))}", "Idempotency-Key": uuid4().hex}


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


@pytest.mark.parametrize("method,suffix,body", [
    ("POST", "", {"snapshot": snapshot(), "import_key": "local-case", "explicit_consent": True}),
    ("PATCH", "/00000000-0000-0000-0000-000000000001/metadata", {"expected_revision": 1, "title": "new"}),
    ("PUT", "/00000000-0000-0000-0000-000000000001/membership", {"expected_revision": 1, "member_id": str(UUID(int=2)), "role": "viewer"}),
    ("PUT", "/00000000-0000-0000-0000-000000000001/monitoring", {"expected_revision": 1, "cadence": "off"}),
])
@pytest.mark.parametrize("key", [None, "short", "x" * 129, "key with spaces invalid"])
def test_every_command_requires_a_bounded_idempotency_header(client, method, suffix, body, key):
    headers = auth()
    headers.pop("Idempotency-Key")
    if key is not None:
        headers["Idempotency-Key"] = key
    response = client.request(method, f"/v1/saved-cases{suffix}", headers=headers, json=body)
    assert response.status_code == 422
    assert "no-store" in response.headers["cache-control"]


def test_all_seven_routes_keep_auth_account_identity_and_no_store_dependencies():
    from backend.api.durable_cases import router, no_store
    from backend.api.v1.router import reject_client_identity_overrides
    from services.vnext.auth import require_authenticated_principal
    from services.vnext.accounts import require_active_account
    assert len(router.routes) == 7
    for route in router.routes:
        assert {require_authenticated_principal, require_active_account, reject_client_identity_overrides, no_store} <= {dependency.call for dependency in route.dependant.dependencies}


@pytest.mark.parametrize("method,suffix,body", [
    ("GET", "", None), ("GET", "/{id}", None), ("GET", "/{id}/activity", None),
    ("POST", "", {"snapshot": snapshot(), "import_key": "copy", "explicit_consent": True}),
    ("PATCH", "/{id}/metadata", {"expected_revision": 1, "notes": "Note"}),
    ("PUT", "/{id}/membership", {"expected_revision": 1, "member_id": str(UUID(int=2)), "role": "viewer"}),
    ("PUT", "/{id}/monitoring", {"expected_revision": 1, "cadence": "daily"}),
])
def test_every_route_rejects_anonymous_forged_and_suspended_requests(client, method, suffix, body):
    from tests.test_consumer_account import AccountAuthorizer, Repository, account
    path = "/v1/saved-cases" + suffix.format(id=UUID(int=1))
    for headers, expected in [({}, 401), ({**auth(), "X-User-ID": str(UUID(int=2))}, 422)]:
        response = client.request(method, path, headers=headers, json=body)
        assert response.status_code == expected
        assert "no-store" in response.headers["cache-control"]
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repository(account("suspended")))
    response = client.request(method, path, headers=auth(), json=body)
    assert response.status_code == 403 and "no-store" in response.headers["cache-control"]


def test_http_command_retries_preserve_status_resource_revision_and_activity(client):
    create_headers = auth()
    payload = {"snapshot": snapshot(), "import_key": "local", "explicit_consent": True}
    created = client.post("/v1/saved-cases", headers=create_headers, json=payload)
    replay = client.post("/v1/saved-cases", headers=create_headers, json=payload)
    assert created.status_code == replay.status_code == 201 and created.json() == replay.json()
    case_id = created.json()["id"]
    for revision, method, suffix, body in [
        (1, "PATCH", "metadata", {"notes": "Authored note"}),
        (2, "PUT", "membership", {"member_id": str(UUID(int=2)), "role": "viewer"}),
        (3, "PUT", "monitoring", {"cadence": "daily"}),
    ]:
        headers = auth(); body = {"expected_revision": revision, **body}
        path = f"/v1/saved-cases/{case_id}/{suffix}"
        first = client.request(method, path, headers=headers, json=body)
        replay = client.request(method, path, headers=headers, json=body)
        assert first.status_code == replay.status_code == 200 and first.json() == replay.json()
        assert replay.json()["revision"] == revision + 1
        changed = client.request(method, path, headers=headers, json={**body, "expected_revision": revision + 1})
        assert changed.status_code == 409 and changed.json()["error"]["code"] == "idempotency_conflict"
    assert len(client.get(f"/v1/saved-cases/{case_id}/activity", headers=auth()).json()) == 4
