from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.api.v1.legacy_case_import import get_legacy_import_service
from backend.api_main import app
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
from services.vnext.errors import VNextError
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags


ISSUER = "https://fixture-project.supabase.co/auth/v1"
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
IMPORT_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
CASE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
EVIDENCE_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()


def _token(*, private_key=PRIVATE_KEY) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(USER_ID),
            "iss": ISSUER,
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "fixture-key"},
    )


def _body(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "workspace_id": str(WORKSPACE_ID),
        "legacy_format": "saved_case_v1",
        "legacy_client_id": "browser-saved-case-1",
        "payload": {
            "version": 1,
            "title": "Explicitly imported case",
            "workflowMode": "buying_wizard",
            "data": {"inputs": {"city": "Synthetic City"}},
        },
        "import_mode": "copy",
        "consent": True,
    }
    body.update(changes)
    return body


class _Service:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, object]] = []

    def import_case(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        imported_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        return SimpleNamespace(
            replayed=False,
            result=SimpleNamespace(
                case=SimpleNamespace(case_id=CASE_ID),
                import_record=SimpleNamespace(
                    legacy_case_import_id=IMPORT_ID,
                    workspace_id=WORKSPACE_ID,
                    accepted_field_classes=("case_metadata", "property_inputs"),
                    dropped_field_classes=("provider_payloads",),
                    warnings=("terrain_reference_only",),
                    imported_at=imported_at,
                ),
                evidence_ids=(EVIDENCE_ID,),
            ),
        )


@contextmanager
def _client(*, enabled: bool = True, service: _Service | None = None):
    verifier = SupabaseJWTVerifier(
        issuer=ISSUER,
        signing_key_resolver=lambda _token: PUBLIC_KEY,
    )
    selected = service or _Service()
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags(
        legacy_case_import_v1=enabled
    )
    app.dependency_overrides[get_legacy_import_service] = lambda: selected
    client = TestClient(app)
    try:
        yield client, selected
    finally:
        client.close()
        app.dependency_overrides.clear()


def _headers(token: str | None = None, key: str = "slice7-import-key-0001") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token or _token()}",
        "Idempotency-Key": key,
    }


def test_explicit_copy_import_returns_only_unverified_identity_projection() -> None:
    with _client() as (client, service):
        response = client.post(
            "/v1/cases/import-legacy", headers=_headers(), json=_body()
        )

    assert response.status_code == 201
    assert response.json() == {
        "legacy_case_import_id": str(IMPORT_ID),
        "case_id": str(CASE_ID),
        "workspace_id": str(WORKSPACE_ID),
        "import_status": "imported_unverified",
        "identity_status": "legacy_unverified",
        "property_entity_id": None,
        "resolution_id": None,
        "accepted_field_classes": ["case_metadata", "property_inputs"],
        "dropped_field_classes": ["provider_payloads"],
        "warnings": ["terrain_reference_only"],
        "evidence_ids": [str(EVIDENCE_ID)],
        "imported_at": "2026-09-01T00:00:00Z",
    }
    assert service.calls[0]["consent"] is True
    assert service.calls[0]["import_mode"] == "copy"
    assert response.headers["Cache-Control"] == "private, no-store"


def test_import_requires_authentication_and_valid_signature() -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with _client() as (client, service):
        missing = client.post(
            "/v1/cases/import-legacy",
            headers={"Idempotency-Key": "slice7-import-key-0001"},
            json=_body(),
        )
        invalid = client.post(
            "/v1/cases/import-legacy",
            headers=_headers(_token(private_key=other_key)),
            json=_body(),
        )

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert invalid.json()["error"]["code"] == "authentication_required"
    assert service.calls == []


def test_import_feature_is_default_deny_and_independent_of_identity_v1() -> None:
    with _client(enabled=False) as (client, service):
        response = client.post(
            "/v1/cases/import-legacy", headers=_headers(), json=_body()
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert service.calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"legacy_format": "saved_case_v2"},
        {"import_mode": "merge"},
        {"consent": False},
        {"legacy_client_id": "contains spaces"},
        {"unexpected": "field"},
    ],
)
def test_import_contract_rejects_non_allowlisted_modes_and_fields(changes) -> None:
    with _client() as (client, service):
        response = client.post(
            "/v1/cases/import-legacy", headers=_headers(), json=_body(**changes)
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert service.calls == []


@pytest.mark.parametrize("header", ["X-User-ID", "X-Role", "X-Workspace-Role"])
def test_import_rejects_client_forged_identity(header: str) -> None:
    with _client() as (client, service):
        response = client.post(
            "/v1/cases/import-legacy",
            headers={**_headers(), header: "owner"},
            json=_body(),
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert service.calls == []


def test_import_requires_a_bounded_idempotency_key() -> None:
    with _client() as (client, service):
        missing = client.post(
            "/v1/cases/import-legacy",
            headers={"Authorization": f"Bearer {_token()}"},
            json=_body(),
        )
        short = client.post(
            "/v1/cases/import-legacy",
            headers=_headers(key="short"),
            json=_body(),
        )

    assert missing.status_code == short.status_code == 422
    assert service.calls == []


def test_import_errors_never_expose_raw_exception_or_database_url() -> None:
    service = _Service(
        RuntimeError("postgresql://user:secret@host.invalid/private raw payload")
    )
    with _client(service=service) as (client, _service):
        response = client.post(
            "/v1/cases/import-legacy", headers=_headers(), json=_body()
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret" not in response.text
    assert "raw payload" not in response.text


def test_duplicate_import_error_is_structured_without_source_content() -> None:
    service = _Service(
        VNextError.duplicate_legacy_import(
            details={"import_status": "duplicate_requires_explicit_choice"}
        )
    )
    with _client(service=service) as (client, _service):
        response = client.post(
            "/v1/cases/import-legacy", headers=_headers(), json=_body()
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_legacy_import"
    assert response.json()["error"]["details"] == {
        "import_status": "duplicate_requires_explicit_choice"
    }


def test_openapi_adds_only_the_explicit_legacy_import_command() -> None:
    with _client() as (client, _service):
        schema = client.get("/openapi.json").json()

    operation = schema["paths"]["/v1/cases/import-legacy"]["post"]
    assert {"SupabaseBearer": []} in operation["security"]
    assert "Idempotency-Key" in [item["name"] for item in operation["parameters"]]
    assert not any(
        marker in path
        for path in schema["paths"]
        for marker in ("legacy/merge", "legacy/upload", "property-entities/import")
    )
