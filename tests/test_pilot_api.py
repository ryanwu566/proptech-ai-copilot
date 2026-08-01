from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api_main import app
from backend.api import routes_pilot
from services.pilot_evidence import PilotEvidenceStore


client = TestClient(app)


def test_public_pilot_evidence_is_truthful_empty_and_health_is_distinct(monkeypatch) -> None:
    monkeypatch.setattr(routes_pilot, "_store", PilotEvidenceStore(":memory:"))
    evidence = client.get("/pilot/public-evidence")
    readiness = client.get("/pilot/readiness")
    assert evidence.status_code == 200
    assert evidence.json()["pilot_sessions_completed"] == 0
    assert readiness.status_code == 200
    assert readiness.json()["dependencies"]["pilot_administration"] == "not_configured"


def test_pilot_api_requires_consent_and_keeps_invalid_access_opaque(monkeypatch) -> None:
    store = PilotEvidenceStore(":memory:")
    store.create_campaign("campaign-api", "code-api")
    monkeypatch.setattr(routes_pilot, "_store", store)
    invalid = client.post("/pilot/access", json={"campaign_id": "missing", "pilot_code": "wrong"})
    assert invalid.status_code == 404
    response = client.post("/pilot/access", json={"campaign_id": "campaign-api", "pilot_code": "code-api", "locale": "en", "device_class": "desktop", "viewport_class": "wide"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["mode"] == "closed_pilot"
    session_id, token = payload["session_id"], payload["session_token"]
    denied = client.post(f"/pilot/sessions/{session_id}/events", headers={"X-Pilot-Session-Token": token}, json={"event_type": "pilot_started", "idempotency_key": "one"})
    assert denied.status_code == 403
    consent = client.post(f"/pilot/sessions/{session_id}/consent", headers={"X-Pilot-Session-Token": token}, json={"participation": True, "interaction_metrics": True, "written_feedback": True, "follow_up_contact": False, "publication": False})
    assert consent.status_code == 200
    accepted = client.post(f"/pilot/sessions/{session_id}/events", headers={"X-Pilot-Session-Token": token}, json={"event_type": "pilot_started", "idempotency_key": "one", "metadata": {"address": "private", "price": 1}})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"


def test_professional_review_is_not_public_or_enabled_without_server_configuration(monkeypatch) -> None:
    monkeypatch.delenv("PILOT_REVIEW_TOKEN", raising=False)
    monkeypatch.delenv("PILOT_ADMIN_TOKEN", raising=False)
    response = client.post("/professional-review", json={"reviewer_role": "tax professional", "reviewed_capability": "TaxOracle", "reviewed_rule_version": "v1", "review_scope": "wording", "outcome": "revision_required"})
    assert response.status_code == 503
    status_response = client.get("/professional-review/status")
    assert status_response.json()["public_endorsement"] is False


def test_correlation_header_and_client_error_endpoint_are_bounded() -> None:
    response = client.get("/liveness", headers={"X-Correlation-ID": "pilot-api-123"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "pilot-api-123"
    accepted = client.post("/client-errors", headers={"X-Correlation-ID": "pilot-api-123"}, json={"error_code": "render_failure", "route": "/pilot", "boundary": "error-boundary", "pilot_mode": "closed_pilot"})
    assert accepted.status_code == 202
    assert accepted.json()["support_reference"] == "pilot-api-123"
    rejected = client.post("/client-errors", json={"error_code": "render_failure", "raw_error": "not accepted"})
    assert rejected.status_code == 422
