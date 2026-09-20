from __future__ import annotations

import ast
import json
import socket
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

import backend.db
from backend.api_main import app
from services.adapters.nlsc_cad_gateway_adapter import NlscCadGatewayAdapter
from services.adapters.nlsc_gateway_adapter import NlscGatewayAdapter
from services.adapters.nlsc_tile_gateway_adapter import NlscTileGatewayAdapter
from services.vnext import db_principal
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags


ROOT = Path(__file__).resolve().parents[1]
PATH = "/v1/planning/taipei/observe"
ISSUER = "https://fixture-project.supabase.co/auth/v1"
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()
VALID_CERTIFICATE: dict[str, object] = {
    "jurisdiction": "Taipei City",
    "scope": "urban_plan_non_national_park",
    "document_kind": "issued_zoning_certificate",
    "reported_document_reference": "都規證字第115-001號",
    "reported_zone_label": "第三種住宅區",
}


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


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


@contextmanager
def _client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool = True,
    mode: str | None = "manual_evidence",
):
    verifier = SupabaseJWTVerifier(
        issuer=ISSUER,
        signing_key_resolver=lambda _token: PUBLIC_KEY,
    )
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags(
        taipei_planning_read_v1=enabled
    )
    if mode is None:
        monkeypatch.delenv("TAIPEI_PLANNING_SOURCE_MODE", raising=False)
    else:
        monkeypatch.setenv("TAIPEI_PLANNING_SOURCE_MODE", mode)
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_manual_certificate_returns_only_fixed_unverified_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _client(monkeypatch) as client:
        response = client.post(PATH, headers=_headers(), json=VALID_CERTIFICATE)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "LIMITED"
    assert payload["authority_class"] == "USER_PROVIDED"
    assert payload["coverage_status"] == "LIMITED"
    assert payload["verification_required"] is True
    assert payload["verification_status"] == "unverified"
    assert payload["document_kind"] == "issued_zoning_certificate"
    assert payload["source_portal"] == "https://zone.udd.gov.taipei/new_index1.aspx"
    assert set(payload) == {
        "status",
        "jurisdiction",
        "scope",
        "authority_class",
        "document_kind",
        "issuing_authority",
        "source_portal",
        "reported_document_reference",
        "reported_plan_identifier",
        "reported_zone_code",
        "reported_zone_label",
        "reported_effective_date",
        "coverage_status",
        "verification_required",
        "verification_status",
        "limitations",
        "normalized_at",
        "disclaimer",
    }


def test_reported_effective_date_and_punctuation_do_not_upgrade_announcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = {
        **VALID_CERTIFICATE,
        "document_kind": "official_urban_plan_announcement",
        "reported_document_reference": "府都規字第1150001號/附件A\\B",
        "reported_effective_date": "2026-09-19",
    }
    with _client(monkeypatch) as client:
        response = client.post(PATH, headers=_headers(), json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["reported_document_reference"] == "府都規字第1150001號/附件A\\B"
    assert payload["reported_effective_date"] == "2026-09-19"
    assert (
        payload["status"],
        payload["authority_class"],
        payload["coverage_status"],
        payload["verification_status"],
    ) == ("LIMITED", "USER_PROVIDED", "LIMITED", "unverified")
    assert any("later amendments" in item for item in payload["limitations"])


def test_feature_off_is_bounded_404(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch, enabled=False) as client:
        response = client.post(PATH, headers=_headers(), json=VALID_CERTIFICATE)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "manual_evidence" not in response.text


def test_vnext_context_reports_planning_flag_without_source_mode_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/v1", headers=_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["features"]["taipei_planning_read_v1"] is True
    assert "manual_evidence" not in json.dumps(payload)


@pytest.mark.parametrize("mode", [None, "", "live_api", "manual_authoritative_evidence"])
def test_unavailable_source_mode_is_bounded_503_without_value_echo(
    monkeypatch: pytest.MonkeyPatch,
    mode: str | None,
) -> None:
    with _client(monkeypatch, mode=mode) as client:
        response = client.post(PATH, headers=_headers(), json=VALID_CERTIFICATE)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "coverage_unavailable"
    if mode:
        assert mode not in response.text


def test_route_requires_global_vnext_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        response = client.post(PATH, json=VALID_CERTIFICATE)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_route_rejects_all_query_parameters_without_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted = "https://evil.invalid/reference"
    with _client(monkeypatch) as client:
        response = client.post(
            PATH,
            params={"source_url": submitted},
            headers=_headers(),
            json=VALID_CERTIFICATE,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert submitted not in response.text


@pytest.mark.parametrize(
    "changes",
    [
        {"jurisdiction": "New Taipei City"},
        {"jurisdiction": "Taipei"},
        {"scope": "national_park"},
        {"document_kind": "LUI_002"},
        {"coordinates": {"lat": 25.0, "lng": 121.5}},
        {"address": "臺北市信義區"},
        {"parcel_id": "001"},
        {"source_url": "https://evil.invalid"},
        {"reported_document_reference": "https://evil.invalid/reference"},
        {"reported_document_reference": "https:evil.invalid/reference"},
        {"reported_document_reference": r"http:\\evil.invalid\reference"},
        {"reported_document_reference": r"file:\\server\share"},
        {"reported_document_reference": "www.evil.invalid"},
        {"reported_document_reference": "C:\\secret"},
        {"reported_document_reference": "/etc/passwd"},
        {"reported_document_reference": ".."},
        {"reported_document_reference": "safe/../secret"},
        {"reported_document_reference": "<b>reference</b>"},
        {"reported_document_reference": "bad\x00reference"},
        {"reported_document_reference": "bad\u0085reference"},
        {"reported_document_reference": "bad\u009freference"},
        {"reported_document_reference": "\ttrimmed-control"},
        {"reported_document_reference": "trimmed-control\n"},
        {"reported_document_reference": "x" * 201},
        {"reported_effective_date": "2026-02-30"},
        {"reported_effective_date": 0},
        {"reported_effective_date": 1728000000},
        {"reported_effective_date": "2026-09-19T00:00:00Z"},
    ],
)
def test_invalid_or_unsupported_input_is_bounded_422_without_echo(
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
) -> None:
    body = {**VALID_CERTIFICATE, **changes}
    with _client(monkeypatch) as client:
        response = client.post(PATH, headers=_headers(), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"validation_failed", "unsupported_input"}
    serialized_input = json.dumps(changes, ensure_ascii=False)
    assert serialized_input not in response.text


def test_success_crosses_no_transport_nlsc_database_persistence_or_job_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("planning manual seam crossed a forbidden boundary")

    original_connect = socket.socket.connect

    def forbid_external_socket(sock, address):
        host = address[0] if isinstance(address, tuple) and address else None
        if host in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("planning manual seam attempted external transport")

    monkeypatch.setattr(socket.socket, "connect", forbid_external_socket)
    monkeypatch.setattr(backend.db, "get_connection", forbidden)
    monkeypatch.setattr(db_principal, "get_vnext_database_principal_context", forbidden)
    monkeypatch.setattr(NlscGatewayAdapter, "terrain_point", forbidden)
    monkeypatch.setattr(NlscCadGatewayAdapter, "cad_009_address_query_land", forbidden)
    monkeypatch.setattr(NlscTileGatewayAdapter, "fetch_tile", forbidden)
    monkeypatch.setattr(BackgroundTasks, "add_task", forbidden)

    with _client(monkeypatch) as client:
        response = client.post(PATH, headers=_headers(), json=VALID_CERTIFICATE)

    assert response.status_code == 200


def test_planning_modules_import_no_transport_database_or_persistence_packages() -> None:
    prohibited = (
        "httpx",
        "requests",
        "playwright",
        "selenium",
        "backend.db",
        "services.adapters",
        "services.vnext.persistence",
        "services.vnext.db_principal",
    )
    for relative in ("services/vnext/taipei_planning.py", "backend/api/v1/taipei_planning.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any(name.startswith(prohibited) for name in imported), (relative, imported)
