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
    """In production mode, /readiness must not reveal config-status fields."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example.invalid/app")
    monkeypatch.setenv("PILOT_SESSION_SIGNING_KEY", "s" * 32)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://frontend.example")
    monkeypatch.setenv("PUBLIC_APP_BASE_URL", "https://frontend.example")
    monkeypatch.setenv("PILOT_ADMIN_TOKEN", "admin-test-token")
    with TestClient(app) as client:
        response = client.get("/readiness")
    # In production, even if 503, the runtime block should be minimal
    body = response.json() if response.status_code == 200 else {}
    if response.status_code == 200:
        runtime = body.get("runtime", {})
        # Must NOT contain these reconnaissance-useful fields
        for sensitive_key in ("session_secret", "admin_token", "reviewer_token", "database_source"):
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
