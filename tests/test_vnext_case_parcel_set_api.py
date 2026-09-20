from __future__ import annotations

import importlib.util
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.api_main import app
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
from services.vnext.case_parcel_set import (
    CaseParcelSetMemberRecord,
    CaseParcelSetOutcome,
    CaseParcelSetRecord,
    ParcelMemberReviewStatus,
    ParcelSetStatus,
)
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags


def test_case_parcel_set_api_module_exists() -> None:
    assert importlib.util.find_spec("backend.api.v1.case_parcel_set") is not None


ROOT = Path(__file__).resolve().parents[1]
ISSUER = "https://fixture-project.supabase.co/auth/v1"
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
CASE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SET_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
MEMBER_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
OTHER_MEMBER_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
PARCEL_ID = UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()
NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)


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


def _record() -> CaseParcelSetRecord:
    return CaseParcelSetRecord(
        parcel_set_id=SET_ID,
        workspace_id=WORKSPACE_ID,
        case_id=CASE_ID,
        status=ParcelSetStatus.CASE_REVIEWED,
        version=7,
        active_member_id=MEMBER_ID,
        created_by_user_id=USER_ID,
        created_at=NOW,
        updated_at=NOW,
        reviewed_at=NOW,
        members=(
            CaseParcelSetMemberRecord(
                parcel_set_member_id=MEMBER_ID,
                workspace_id=WORKSPACE_ID,
                parcel_set_id=SET_ID,
                parcel_identity_reference_id=PARCEL_ID,
                position=1,
                review_status=ParcelMemberReviewStatus.CASE_SELECTED,
                created_by_user_id=USER_ID,
                created_at=NOW,
                updated_at=NOW,
            ),
        ),
    )


class _Service:
    def __init__(self, *, replayed: bool = False, error: Exception | None = None) -> None:
        self.replayed = replayed
        self.error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    def _command(self, name: str, kwargs: dict[str, object]) -> CaseParcelSetOutcome:
        self.calls.append((name, kwargs))
        if self.error is not None:
            raise self.error
        return CaseParcelSetOutcome(_record(), self.replayed)

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        if self.error is not None:
            raise self.error
        return _record()

    def initialize(self, **kwargs):
        return self._command("initialize", kwargs)

    def add_member(self, **kwargs):
        return self._command("add_member", kwargs)

    def review_member(self, **kwargs):
        return self._command("review_member", kwargs)

    def set_active_member(self, **kwargs):
        return self._command("set_active_member", kwargs)

    def reorder(self, **kwargs):
        return self._command("reorder", kwargs)

    def mark_case_reviewed(self, **kwargs):
        return self._command("mark_case_reviewed", kwargs)


@contextmanager
def _client(*, enabled: bool = True, service: _Service | None = None):
    from backend.api.v1 import case_parcel_set as api

    verifier = SupabaseJWTVerifier(
        issuer=ISSUER,
        signing_key_resolver=lambda _token: PUBLIC_KEY,
    )
    selected = service or _Service()
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags(
        case_parcel_set_v1=enabled
    )
    app.dependency_overrides[api.get_case_parcel_set_service] = lambda: selected
    client = TestClient(app)
    try:
        yield client, selected
    finally:
        client.close()
        app.dependency_overrides.clear()


def _headers(
    token: str | None = None,
    key: str = "case-parcel-set-key-0001",
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token or _token()}",
        "Idempotency-Key": key,
    }


def _initialize_body(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "workspace_id": str(WORKSPACE_ID),
        "expected_version": 0,
    }
    body.update(changes)
    return body


def test_get_returns_only_ordered_case_scoped_review_state() -> None:
    with _client() as (client, service):
        response = client.get(f"/v1/cases/{CASE_ID}/parcel-set", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "parcel_set_id": str(SET_ID),
        "workspace_id": str(WORKSPACE_ID),
        "case_id": str(CASE_ID),
        "status": "case_reviewed",
        "version": 7,
        "active_member_id": str(MEMBER_ID),
        "created_at": "2026-09-20T00:00:00Z",
        "updated_at": "2026-09-20T00:00:00Z",
        "reviewed_at": "2026-09-20T00:00:00Z",
        "members": [
            {
                "parcel_set_member_id": str(MEMBER_ID),
                "parcel_identity_reference_id": str(PARCEL_ID),
                "position": 1,
                "review_status": "case_selected",
                "created_at": "2026-09-20T00:00:00Z",
                "updated_at": "2026-09-20T00:00:00Z",
            }
        ],
    }
    assert service.calls[0][0] == "get"
    assert response.headers["Cache-Control"] == "private, no-store"
    assert not {
        "property_entity_id", "identity_status", "reference_status",
        "confirmed", "official", "geometry", "address", "provider",
    } & set(response.json())


@pytest.mark.parametrize(
    ("path", "body", "method", "expected_status"),
    [
        (f"/v1/cases/{CASE_ID}/parcel-set", _initialize_body(), "initialize", 201),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/members",
            {
                "workspace_id": str(WORKSPACE_ID),
                "parcel_identity_reference_id": str(PARCEL_ID),
                "expected_version": 1,
            },
            "add_member",
            200,
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/members/{MEMBER_ID}/review",
            {
                "workspace_id": str(WORKSPACE_ID),
                "review_status": "case_selected",
                "expected_version": 2,
            },
            "review_member",
            200,
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/active-member",
            {
                "workspace_id": str(WORKSPACE_ID),
                "active_member_id": str(MEMBER_ID),
                "expected_version": 3,
            },
            "set_active_member",
            200,
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/reorder",
            {
                "workspace_id": str(WORKSPACE_ID),
                "ordered_member_ids": [str(MEMBER_ID), str(OTHER_MEMBER_ID)],
                "expected_version": 4,
            },
            "reorder",
            200,
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/review",
            {"workspace_id": str(WORKSPACE_ID), "expected_version": 5},
            "mark_case_reviewed",
            200,
        ),
    ],
)
def test_commands_have_exact_routes_and_forward_bounded_command_metadata(
    path: str,
    body: dict[str, object],
    method: str,
    expected_status: int,
) -> None:
    with _client() as (client, service):
        response = client.post(path, headers=_headers(), json=body)

    assert response.status_code == expected_status
    assert service.calls[0][0] == method
    call = service.calls[0][1]
    assert call["case_id"] == CASE_ID
    assert call["workspace_id"] == WORKSPACE_ID
    assert call["idempotency_key"] == "case-parcel-set-key-0001"
    assert isinstance(call["request_id"], str)
    assert response.headers["Cache-Control"] == "private, no-store"


def test_initialize_replay_returns_200_instead_of_201() -> None:
    with _client(service=_Service(replayed=True)) as (client, _service):
        response = client.post(
            f"/v1/cases/{CASE_ID}/parcel-set",
            headers=_headers(),
            json=_initialize_body(),
        )

    assert response.status_code == 200


def test_routes_require_authentication_and_valid_signature() -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with _client() as (client, service):
        missing = client.get(f"/v1/cases/{CASE_ID}/parcel-set")
        invalid = client.get(
            f"/v1/cases/{CASE_ID}/parcel-set",
            headers={"Authorization": f"Bearer {_token(private_key=other_key)}"},
        )

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert invalid.json()["error"]["code"] == "authentication_required"
    assert service.calls == []


def test_feature_is_default_deny_for_reads_and_writes() -> None:
    with _client(enabled=False) as (client, service):
        read = client.get(f"/v1/cases/{CASE_ID}/parcel-set", headers=_headers())
        write = client.post(
            f"/v1/cases/{CASE_ID}/parcel-set",
            headers=_headers(),
            json=_initialize_body(),
        )

    assert read.status_code == write.status_code == 404
    assert read.json()["error"]["code"] == "not_found"
    assert service.calls == []


@pytest.mark.parametrize("override", [("header", "X-Role"), ("query", "role")])
def test_routes_reject_forged_identity(override: tuple[str, str]) -> None:
    kind, name = override
    path = f"/v1/cases/{CASE_ID}/parcel-set"
    headers = _headers()
    if kind == "header":
        headers[name] = "owner"
    else:
        path += f"?{name}=owner"
    with _client() as (client, service):
        response = client.get(path, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert service.calls == []


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (f"/v1/cases/{CASE_ID}/parcel-set", _initialize_body(unexpected="value")),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/members",
            {"workspace_id": str(WORKSPACE_ID), "parcel_identity_reference_id": str(PARCEL_ID), "expected_version": 1, "unexpected": True},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/members/{MEMBER_ID}/review",
            {"workspace_id": str(WORKSPACE_ID), "review_status": "case_selected", "expected_version": 1, "unexpected": True},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/active-member",
            {"workspace_id": str(WORKSPACE_ID), "active_member_id": None, "expected_version": 1, "unexpected": True},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/reorder",
            {"workspace_id": str(WORKSPACE_ID), "ordered_member_ids": [str(MEMBER_ID)], "expected_version": 1, "unexpected": True},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/review",
            {"workspace_id": str(WORKSPACE_ID), "expected_version": 1, "unexpected": True},
        ),
    ],
)
def test_every_command_model_forbids_extra_fields(path: str, body: dict[str, object]) -> None:
    with _client() as (client, service):
        response = client.post(path, headers=_headers(), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert service.calls == []


@pytest.mark.parametrize("key", ["short", "!" * 16, "a" * 129])
def test_commands_require_bounded_allowlisted_idempotency_key(key: str) -> None:
    with _client() as (client, service):
        invalid = client.post(
            f"/v1/cases/{CASE_ID}/parcel-set",
            headers=_headers(key=key),
            json=_initialize_body(),
        )
        missing = client.post(
            f"/v1/cases/{CASE_ID}/parcel-set",
            headers={"Authorization": f"Bearer {_token()}"},
            json=_initialize_body(),
        )

    assert invalid.status_code == missing.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (f"/v1/cases/{CASE_ID}/parcel-set", _initialize_body(expected_version=1)),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/members",
            {"workspace_id": str(WORKSPACE_ID), "parcel_identity_reference_id": str(PARCEL_ID), "expected_version": 0},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/reorder",
            {"workspace_id": str(WORKSPACE_ID), "ordered_member_ids": [], "expected_version": 1},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/reorder",
            {"workspace_id": str(WORKSPACE_ID), "ordered_member_ids": [str(MEMBER_ID), str(MEMBER_ID)], "expected_version": 1},
        ),
        (
            f"/v1/cases/{CASE_ID}/parcel-set/reorder",
            {"workspace_id": str(WORKSPACE_ID), "ordered_member_ids": [str(UUID(int=index + 1)) for index in range(101)], "expected_version": 1},
        ),
    ],
)
def test_versions_and_reorder_shape_are_bounded(path: str, body: dict[str, object]) -> None:
    with _client() as (client, service):
        response = client.post(path, headers=_headers(), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert service.calls == []


def test_unhandled_errors_never_expose_database_token_address_or_provider_content() -> None:
    service = _Service(
        error=RuntimeError(
            "postgresql://user:secret@host.invalid token address provider payload"
        )
    )
    with _client(service=service) as (client, _service):
        response = client.get(f"/v1/cases/{CASE_ID}/parcel-set", headers=_headers())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    for secret in ("secret", "postgresql", "token", "address", "provider"):
        assert secret not in response.text.lower()


def test_openapi_has_exact_surface_no_delete_or_canonical_confirmation_fields() -> None:
    with _client() as (client, _service):
        schema = client.get("/openapi.json").json()

    paths = {
        f"/v1/cases/{'{'}case_id{'}'}/parcel-set": {"get", "post"},
        f"/v1/cases/{'{'}case_id{'}'}/parcel-set/members": {"post"},
        f"/v1/cases/{'{'}case_id{'}'}/parcel-set/members/{'{'}member_id{'}'}/review": {"post"},
        f"/v1/cases/{'{'}case_id{'}'}/parcel-set/active-member": {"post"},
        f"/v1/cases/{'{'}case_id{'}'}/parcel-set/reorder": {"post"},
        f"/v1/cases/{'{'}case_id{'}'}/parcel-set/review": {"post"},
    }
    for path, methods in paths.items():
        assert set(schema["paths"][path]) == methods
        assert "delete" not in schema["paths"][path]

    property_names: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                property_names.update(str(name).lower() for name in properties)
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    selected_schemas = {
        name: value
        for name, value in schema["components"]["schemas"].items()
        if name in {"CaseParcelSetDTO", "CaseParcelSetMemberDTO"}
    }
    assert set(selected_schemas) == {"CaseParcelSetDTO", "CaseParcelSetMemberDTO"}
    collect(selected_schemas)
    assert not {
        "property_entity_id", "identity_status", "reference_status", "confirmed",
        "official", "geometry", "address", "provider",
    } & property_names

    source = (ROOT / "backend/api/v1/case_parcel_set.py").read_text(encoding="utf-8").lower()
    service_source = (ROOT / "services/vnext/case_parcel_set_service.py").read_text(encoding="utf-8").lower()
    assert "delete" not in source
    assert not any(marker in source + service_source for marker in ("provider_adapter", "postgis", "nlsc"))
