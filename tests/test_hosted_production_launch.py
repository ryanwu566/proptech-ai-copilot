from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api_main import app
from scripts import production_smoke
from scripts.generate_release_evidence import build_evidence
from services.postgres_runtime import connect
from services.production_config import load_runtime_configuration


ROOT = Path(__file__).resolve().parents[1]


def test_api_origin_resolver_is_authoritative_and_fail_closed() -> None:
    source = (ROOT / "frontend_next/lib/api-origin.ts").read_text(encoding="utf-8")
    assert "resolveApiOrigin" in source
    assert "localhost" in source
    assert "Production API origin must use HTTPS" in source
    assert "javascript:" not in source


def test_production_config_requires_postgres_and_rejects_sqlite() -> None:
    config = load_runtime_configuration({"APP_ENV": "production", "DATABASE_URL": "sqlite:///unsafe"})
    assert config.production_like is True
    assert config.ready is False
    assert config.database_status == "malformed"


def test_postgres_connection_timeout_and_ssl_are_bounded_without_printing_url(monkeypatch) -> None:
    seen: dict[str, object] = {}

    class FakePsycopg:
        @staticmethod
        def connect(url, **kwargs):
            seen["url"] = url
            seen.update(kwargs)
            return object()

    import sys
    monkeypatch.setitem(sys.modules, "psycopg", FakePsycopg)
    connect("postgresql://db.invalid/app", connect_timeout=120, sslmode="verify-full")
    assert seen["connect_timeout"] == 30
    assert seen["sslmode"] == "verify-full"


def test_release_and_compatibility_endpoints_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("RELEASE_VERSION", "release-1")
    monkeypatch.setenv("RELEASE_COMMIT_SHA", "abc123")
    with TestClient(app) as client:
        release = client.get("/release-version")
        compatibility = client.get("/compatibility")
    assert release.status_code == 200
    payload = release.json()
    assert payload["release_version"] == "release-1"
    assert payload["commit_sha"] == "abc123"
    assert "DATABASE_URL" not in json.dumps(payload)
    assert compatibility.status_code == 200
    assert compatibility.json()["status"] == "compatible"


def test_local_smoke_is_provider_free_and_checks_compatibility(monkeypatch) -> None:
    result = production_smoke.run()
    assert result["mode"] == "local"
    assert result["external_provider_called"] is False
    assert "compatibility" in result["checks"]


def test_hosted_smoke_uses_only_safe_categories(monkeypatch) -> None:
    def fake_json(url, *, timeout, method="GET", headers=None):
        if method == "OPTIONS":
            return 204, {"access-control-allow-origin": "https://front.example"}, None
        if url.endswith("/"):
            return 200, {}, {}
        if url.endswith("/release-version"):
            return 200, {"content-security-policy": "default-src 'none'", "referrer-policy": "strict-origin", "x-content-type-options": "nosniff", "x-frame-options": "DENY", "cache-control": "no-store"}, {"environment": "preview", "release_version": "r1"}
        return 200, {}, {"status": "ok"}

    monkeypatch.setattr(production_smoke, "_hosted_json", fake_json)
    monkeypatch.setattr(production_smoke, "_hosted_text", lambda url, *, timeout: (200, {"content-security-policy": "default-src 'none'", "referrer-policy": "strict-origin", "x-content-type-options": "nosniff"}, "Explicit offline competition example"))
    result = production_smoke.run_hosted(frontend_url="https://front.example", backend_url="https://api.example", expected_environment="preview", expected_release="r1")
    assert result["status"] == "pass"
    assert all(value in {"pass", "fail"} for value in result["checks"].values())


def test_migration_ledger_and_safe_workflow_contract_exist() -> None:
    migration = (ROOT / "database/migrations/007_add_schema_migration_ledger.sql").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/hosted-production-smoke.yml").read_text(encoding="utf-8")
    assert "schema_migration_ledger" in migration
    assert "schedule:" in workflow and "workflow_dispatch:" in workflow
    assert "permissions: {}" in workflow
    assert "response body" not in workflow.lower()
    assert "set -x" not in workflow


def test_permissions_policy_omits_unsupported_bluetooth_directive() -> None:
    config = (ROOT / "frontend_next/next.config.mjs").read_text(encoding="utf-8")
    assert "Permissions-Policy" in config
    assert "bluetooth" not in config.lower()
    assert "camera=()" in config
    assert "geolocation=()" in config


def test_docs_define_owner_action_and_truthful_pending_state() -> None:
    launch = (ROOT / "docs/hosted-production-launch.md").read_text(encoding="utf-8")
    rollback = (ROOT / "docs/hosted-rollback-runbook.md").read_text(encoding="utf-8")
    evidence = (ROOT / "docs/production-release-evidence.md").read_text(encoding="utf-8")
    assert "COMPLETE_REQUIRES_OWNER_ACTION" in launch
    assert "managed PostgreSQL" in rollback
    assert "pending" in evidence


def test_release_evidence_generator_is_non_secret_and_allowlisted() -> None:
    payload = build_evidence(release_id="release-1", commit="abc123", schema_version="schema-007", local_status="ci_verified", owner_actions=["configure-preview"])
    assert payload["privacy"] == {"secrets_included": False, "raw_payloads_included": False, "customer_data_included": False}
    assert payload["validation"]["preview"] == "pending"
    assert "hosted-owner-launch-checklist.md" in (ROOT / "docs/hosted-production-launch.md").read_text(encoding="utf-8")
