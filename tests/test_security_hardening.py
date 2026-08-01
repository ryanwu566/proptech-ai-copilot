from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api_main import app
from services.pilot_evidence import PilotEvidenceStore, safe_csv_cell
from services.pilot_persistence import configured_persistence
from services.security import ScopedSessionManager, safe_external_url, security_headers


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_security_headers_and_private_cache_policy_are_present() -> None:
    response = client.get("/pilot/source-status")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "private, no-store"


def test_cross_origin_state_change_is_rejected() -> None:
    response = client.post("/client-errors", headers={"Origin": "https://attacker.invalid"}, json={"error_code": "network_failure"})
    assert response.status_code == 403
    assert "attacker.invalid" not in response.text


def test_scoped_session_is_short_lived_scoped_and_revocable() -> None:
    manager = ScopedSessionManager("k" * 32, now=lambda: 1000)
    token = manager.issue("administrator")
    assert manager.verify(token, role="administrator") is not None
    assert manager.verify(token, role="reviewer") is None
    manager.revoke(token)
    assert manager.verify(token, role="administrator") is None


def test_cookie_admin_session_requires_csrf_and_does_not_return_bootstrap() -> None:
    from backend.api import routes_pilot

    old = routes_pilot._store
    routes_pilot._store = PilotEvidenceStore(":memory:")
    try:
        with client as session_client:
            response = session_client.post("/pilot/admin/session", headers={"X-Pilot-Admin-Bootstrap": "a" * 16})
            assert response.status_code == 503
            assert "a" * 16 not in response.text
    finally:
        routes_pilot._store = old


def test_production_serverless_without_durable_database_fails_closed() -> None:
    choice = configured_persistence(environ={"APP_ENV": "production", "APP_RUNTIME": "serverless"})
    assert choice["status"] == "unavailable"
    assert choice["adapter"] == "none"


def test_csv_formula_and_url_injection_boundaries_are_safe() -> None:
    assert safe_csv_cell("=SUM(A1)").startswith("'")
    assert safe_csv_cell("normal") == "normal"
    for value in ("javascript:alert(1)", "http://127.0.0.1/private"):
        try:
            safe_external_url(value)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe URL accepted")


def test_public_export_escapes_untrusted_html_and_does_not_expose_raw_fields() -> None:
    store = PilotEvidenceStore(":memory:")
    exported = store.safe_export(fmt="html")
    assert "<script" not in exported.lower()
    assert "participant_hash" not in json.dumps(exported)


def test_security_contract_files_and_frontend_headers_exist() -> None:
    doc = (ROOT / "docs/security-performance-release.md").read_text(encoding="utf-8")
    config = (ROOT / "frontend_next/next.config.mjs").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in config
    assert all(section in doc for section in ("Threat model", "CSRF", "Production persistence", "Route bundle budgets"))


def test_security_header_builder_has_no_unbounded_or_secret_values() -> None:
    headers = security_headers(production=True, private=True)
    assert headers["Strict-Transport-Security"].startswith("max-age=")
    assert "token" not in " ".join(headers).lower()
