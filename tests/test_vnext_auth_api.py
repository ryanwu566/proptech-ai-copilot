from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.api_main import app
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
from services.vnext.errors import VNextError
from services.vnext.feature_flags import VNextFeatureFlags
from services.vnext.feature_flags import get_vnext_feature_flags


ROOT = Path(__file__).resolve().parents[1]
ISSUER = "https://fixture-project.supabase.co/auth/v1"
AUDIENCE = "authenticated"
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()
OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(
    *,
    subject: str = str(USER_ID),
    expires_at: datetime | None = None,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    private_key=PRIVATE_KEY,
    **extra_claims: object,
) -> str:
    now = datetime.now(timezone.utc)
    claims: dict[str, object] = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": expires_at or now + timedelta(minutes=5),
        **extra_claims,
    }
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "fixture-key"},
    )


@pytest.fixture
def verifier() -> SupabaseJWTVerifier:
    return SupabaseJWTVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        signing_key_resolver=lambda _token: PUBLIC_KEY,
    )


@pytest.fixture
def client(verifier: SupabaseJWTVerifier):
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags()
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


def _auth(token: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token or _token()}"}


def _assert_authentication_required(response) -> None:
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_missing_bearer_is_rejected(client: TestClient) -> None:
    _assert_authentication_required(client.get("/v1"))


@pytest.mark.parametrize(
    "authorization",
    ["", "Bearer", "Bearer ", "Basic abc", "Bearer one two", " Bearer abc"],
)
def test_malformed_bearer_is_rejected(client: TestClient, authorization: str) -> None:
    _assert_authentication_required(
        client.get("/v1", headers={"Authorization": authorization})
    )


def test_invalid_signature_is_rejected(client: TestClient) -> None:
    token = _token(private_key=OTHER_PRIVATE_KEY)

    _assert_authentication_required(client.get("/v1", headers=_auth(token)))


def test_expired_token_is_rejected(client: TestClient) -> None:
    token = _token(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))

    _assert_authentication_required(client.get("/v1", headers=_auth(token)))


def test_wrong_issuer_and_audience_are_rejected(client: TestClient) -> None:
    wrong_issuer = _token(issuer="https://other.supabase.co/auth/v1")
    wrong_audience = _token(audience="other-api")

    _assert_authentication_required(client.get("/v1", headers=_auth(wrong_issuer)))
    _assert_authentication_required(client.get("/v1", headers=_auth(wrong_audience)))


def test_invalid_uuid_subject_is_rejected(client: TestClient) -> None:
    _assert_authentication_required(
        client.get("/v1", headers=_auth(_token(subject="not-a-uuid")))
    )


def test_service_role_jwt_is_never_a_normal_request_principal(client: TestClient) -> None:
    _assert_authentication_required(
        client.get("/v1", headers=_auth(_token(role="service_role")))
    )


def test_valid_token_maps_to_canonical_principal_and_flag_defaults_off(
    client: TestClient,
) -> None:
    response = client.get("/v1", headers=_auth())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "principal": {"user_id": str(USER_ID)},
        "features": {"identity_v1": False},
    }
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Correlation-ID"]


def test_valid_token_builds_minimal_authenticated_principal(
    verifier: SupabaseJWTVerifier,
) -> None:
    principal = verifier.verify(_token())

    assert principal.user_id == USER_ID
    assert principal.token_subject == str(USER_ID)
    assert principal.issuer == ISSUER
    assert principal.token_issued_at is not None


def test_verification_infrastructure_unavailable_fails_closed() -> None:
    verifier = SupabaseJWTVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        signing_key_resolver=lambda _token: (_ for _ in ()).throw(
            RuntimeError("jwks provider unavailable with secret payload")
        ),
    )

    with pytest.raises(VNextError) as error:
        verifier.verify(_token())

    assert error.value.code.value == "authentication_required"


def test_raw_bearer_token_is_not_logged(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    token = _token(private_key=OTHER_PRIVATE_KEY)

    with caplog.at_level(logging.INFO):
        response = client.get("/v1", headers=_auth(token))

    _assert_authentication_required(response)
    assert token not in caplog.text


def test_client_forged_user_and_role_are_rejected(client: TestClient) -> None:
    headers = {
        **_auth(_token(role="owner")),
        "X-User-ID": "22222222-2222-4222-8222-222222222222",
        "X-Workspace-Role": "owner",
    }

    response = client.get("/v1", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert "22222222" not in response.text


def test_missing_workspace_membership_returns_structured_403(client: TestClient) -> None:
    response = client.get(
        f"/v1/workspaces/{WORKSPACE_ID}/context",
        headers=_auth(_token(role="owner")),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "owner" not in response.text


def test_identity_feature_flag_does_not_bypass_membership(client: TestClient) -> None:
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags(
        identity_v1=True
    )

    response = client.get(
        f"/v1/workspaces/{WORKSPACE_ID}/context",
        headers=_auth(),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_vnext_not_found_is_structured_and_contains_no_exception_data(client: TestClient) -> None:
    response = client.get("/v1/not-mounted", headers=_auth())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "sql" not in response.text.lower()
    assert "traceback" not in response.text.lower()


def test_unhandled_vnext_error_is_structured_without_sensitive_data(client: TestClient) -> None:
    app.dependency_overrides[get_vnext_feature_flags] = lambda: (_ for _ in ()).throw(
        RuntimeError("postgresql://user:secret@database.invalid/private")
    )

    response = client.get("/v1", headers=_auth())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret" not in response.text
    assert "postgresql" not in response.text


def test_vnext_cross_origin_rejection_uses_structured_403(client: TestClient) -> None:
    response = client.post(
        "/v1",
        headers={**_auth(), "Origin": "https://attacker.invalid"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert "attacker.invalid" not in response.text


def test_correlation_id_is_normalized(client: TestClient) -> None:
    response = client.get(
        "/v1",
        headers={**_auth(), "X-Correlation-ID": "Bearer secret value"},
    )

    request_id = response.json().get("error", {}).get("request_id") or response.headers[
        "X-Correlation-ID"
    ]
    assert request_id != "Bearer secret value"
    assert " " not in request_id


def test_cors_intentionally_allows_vnext_contract_headers(client: TestClient) -> None:
    response = client.options(
        "/v1",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,idempotency-key,if-match",
        },
    )

    assert response.status_code == 200
    allowed = response.headers["Access-Control-Allow-Headers"].lower()
    assert all(name in allowed for name in ("authorization", "idempotency-key", "if-match"))


def test_openapi_declares_supabase_bearer_security(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["components"]["securitySchemes"]["SupabaseBearer"] == {
        "type": "http",
        "description": "Supabase Auth access token",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert {"SupabaseBearer": []} in schema["paths"]["/v1"]["get"]["security"]


def test_frontend_contains_no_supabase_service_role_reference() -> None:
    forbidden = "SUPABASE_" + "SERVICE_ROLE_KEY"
    files = (
        path
        for path in (ROOT / "frontend_next").rglob("*")
        if path.is_file() and "node_modules" not in path.parts and ".next" not in path.parts
    )

    assert not any(forbidden in path.read_text(encoding="utf-8", errors="ignore") for path in files)


def test_feature_flags_are_default_deny_and_unknown_flags_are_off() -> None:
    flags = VNextFeatureFlags.from_environment({})

    assert flags.identity_v1 is False
    assert flags.enabled("identity_v1") is False
    assert flags.enabled("unregistered_flag") is False
