from __future__ import annotations

import os
import subprocess
from pathlib import Path

from backend.api_main import app
from scripts.migration_registry import load_registry, next_safe_sequence
from services.vnext.errors import ErrorCode
from services.vnext.feature_flags import VNextFeatureFlags


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"

APPROVED_ROUTES = {
    ("GET", "/v1"),
    ("GET", "/v1/workspaces/{workspace_id}/context"),
    ("POST", "/v1/property-resolutions"),
    ("GET", "/v1/property-resolutions/{identity_resolution_id}"),
    ("POST", "/v1/property-resolutions/{identity_resolution_id}/confirm"),
    ("POST", "/v1/property-resolutions/{identity_resolution_id}/reject"),
    ("GET", "/v1/properties/{property_entity_id}"),
    ("GET", "/v1/properties/{property_entity_id}/graph"),
    ("GET", "/v1/properties/{property_entity_id}/evidence"),
    ("POST", "/v1/cases"),
    ("POST", "/v1/cases/{case_id}/attach-resolution"),
    ("POST", "/v1/cases/import-legacy"),
}
COMMAND_ROUTES = {
    "/v1/property-resolutions",
    "/v1/property-resolutions/{identity_resolution_id}/confirm",
    "/v1/property-resolutions/{identity_resolution_id}/reject",
    "/v1/cases",
    "/v1/cases/{case_id}/attach-resolution",
    "/v1/cases/import-legacy",
}


def _schema() -> dict[str, object]:
    app.openapi_schema = None
    return app.openapi()


def test_executable_vnext_route_surface_is_exact_and_has_no_shortcuts() -> None:
    schema = _schema()
    routes = {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        if path.startswith("/v1")
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }

    assert routes == APPROVED_ROUTES
    joined = "\n".join(path for _method, path in routes).lower()
    assert all(
        forbidden not in joined
        for forbidden in (
            "auto-confirm",
            "auto-merge",
            "attach-by-confidence",
            "provider-bypass",
            "admin-shortcut",
            "debug",
        )
    )


def test_openapi_requires_bearer_and_bounded_idempotency_on_every_command() -> None:
    schema = _schema()
    assert schema["components"]["securitySchemes"]["SupabaseBearer"]["scheme"] == "bearer"
    for method, path in APPROVED_ROUTES:
        operation = schema["paths"][path][method.lower()]
        assert {"SupabaseBearer": []} in operation["security"]
    for path in COMMAND_ROUTES:
        operation = schema["paths"][path]["post"]
        parameters = {
            item["name"]: item
            for item in operation.get("parameters", [])
        }
        idempotency = parameters["Idempotency-Key"]
        assert idempotency["in"] == "header" and idempotency["required"] is True
        assert idempotency["schema"]["minLength"] == 16
        assert idempotency["schema"]["maxLength"] == 128
        assert idempotency["schema"]["pattern"] == "^[A-Za-z0-9._:-]{16,128}$"


def test_openapi_errors_are_allowlisted_and_internal_fields_are_absent() -> None:
    schema = _schema()
    error_codes = schema["components"]["schemas"]["ErrorCode"]["enum"]
    assert set(error_codes) == {item.value for item in ErrorCode}
    for method, path in APPROVED_ROUTES:
        operation = schema["paths"][path][method.lower()]
        for status, response in operation["responses"].items():
            if status.startswith(("4", "5")):
                assert response["content"]["application/json"]["schema"] == {
                    "$ref": "#/components/schemas/VNextErrorEnvelopeDTO"
                }
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

    collect(schema["components"]["schemas"])
    for private_field in (
        "value_ref",
        "raw_artifact_ref",
        "idempotency_key_hash",
        "request_fingerprint",
        "database_url",
        "private_payload",
    ):
        assert private_field not in property_names


def test_stage1_feature_flags_and_example_configuration_are_default_off() -> None:
    assert VNextFeatureFlags.from_environment({}) == VNextFeatureFlags(
        identity_v1=False,
        legacy_case_import_v1=False,
    )
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "FEATURE_IDENTITY_V1=false" in example
    assert "FEATURE_LEGACY_CASE_IMPORT_V1=false" in example
    for path in ROOT.glob(".env*"):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "feature_identity_v1=true" not in text
        assert "feature_legacy_case_import_v1=true" not in text


def test_migrations_are_frozen_through_017_and_next_sequence_is_018() -> None:
    registrations = load_registry()
    assert next_safe_sequence(registrations) == 18
    assert max(item.sequence for item in registrations) == 17
    assert not list((ROOT / "database" / "migrations").glob("018_*.sql"))
    assert all(len(item.sha256) == 64 for item in registrations)


def test_frontend_headers_are_bounded_and_supabase_connect_is_exact_origin_only() -> None:
    config = (FRONTEND / "next.config.mjs").read_text(encoding="utf-8")
    for header in (
        "Content-Security-Policy",
        "frame-ancestors 'none'",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Cross-Origin-Opener-Policy",
        "Cross-Origin-Resource-Policy",
    ):
        assert header in config
    assert "connect-src 'self'${apiConnectSource}${supabaseAuthConnectSource}" in config
    assert "https://*.supabase.co" not in config
    assert "url.username || url.password" in config


def test_frontend_session_and_dto_mutation_harness_passes() -> None:
    completed = subprocess.run(
        ["node", "scripts/test-vnext-hardening.mjs"],
        cwd=FRONTEND,
        env={**os.environ, "NODE_ENV": "test"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    assert "VNext frontend hardening: 31 passed" in completed.stdout
