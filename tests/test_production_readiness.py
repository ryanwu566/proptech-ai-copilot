from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app


def test_health_separates_liveness_from_local_sqlite_readiness() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["liveness"] == "ok"
    assert payload["persistence"]["durable"] == "no"
    assert payload["readiness"] == "ready"


def test_production_startup_fails_closed_without_required_database(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PILOT_EVIDENCE_DATABASE_URL", raising=False)
    monkeypatch.delenv("PILOT_SESSION_SIGNING_KEY", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("PUBLIC_APP_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="Required production configuration"):
        with TestClient(app):
            pass


def test_readiness_does_not_expose_config_details_in_production(monkeypatch) -> None:
    """In production mode, /readiness must not reveal config-status reconnaissance fields.

    Uses monkeypatch to force a fully-ready production state so the endpoint
    returns HTTP 200 deterministically — not 503.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example.invalid/app")
    monkeypatch.setenv("PILOT_SESSION_SIGNING_KEY", "s" * 32)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://frontend.example")
    monkeypatch.setenv("PUBLIC_APP_BASE_URL", "https://frontend.example")
    monkeypatch.setenv("PILOT_ADMIN_TOKEN", "admin-test-token")
    # Mock database connectivity so endpoint reaches HTTP 200 path
    monkeypatch.setattr(
        "backend.api.routes_pilot.check_connection", lambda url: "available"
    )
    with TestClient(app) as client:
        response = client.get("/readiness")
    assert response.status_code == 200, (
        f"Expected 200 for fully-ready production config, got {response.status_code}"
    )
    runtime = response.json().get("runtime", {})
    # Production runtime must contain ONLY these minimal public fields
    allowed_keys = {"mode", "ready"}
    assert set(runtime.keys()) == allowed_keys, (
        f"Production runtime should expose only {allowed_keys}, got {set(runtime.keys())}"
    )
    # Explicitly verify no sensitive reconnaissance fields
    for sensitive_key in (
        "session_secret", "admin_token", "reviewer_token",
        "database", "database_source", "cors_origins",
        "public_base_url", "release_version", "api_contract_version",
        "schema_version", "maintenance", "runtime", "production_like", "serverless",
    ):
        assert sensitive_key not in runtime, (
            f"/readiness exposed '{sensitive_key}' in production mode"
        )


def test_readiness_exposes_full_config_in_development() -> None:
    """In development mode, /readiness can show full config for debugging."""
    with TestClient(app) as client:
        response = client.get("/readiness")
    assert response.status_code == 200
    runtime = response.json().get("runtime", {})
    # Development mode should have the full report
    assert "database" in runtime
    assert "mode" in runtime
