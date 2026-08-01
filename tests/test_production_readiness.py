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
