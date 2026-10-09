from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def test_release_and_compatibility_endpoints_are_bounded(monkeypatch, tmp_path) -> None:
    from services import production_identity
    from scripts.write_backend_build_identity import write_identity
    path = tmp_path / 'build.json'
    write_identity(path, commit='a' * 40)
    original = production_identity.backend_identity
    monkeypatch.setattr(production_identity, 'backend_identity', lambda: original(path))
    monkeypatch.setenv("RELEASE_VERSION", "release-1")
    monkeypatch.setenv("RELEASE_COMMIT_SHA", "a" * 40)
    with TestClient(app) as client:
        release = client.get("/release-version")
        compatibility = client.get("/compatibility")
    assert release.status_code == 200
    payload = release.json()
    assert payload["release_version"] == "release-1"
    assert payload["commit_sha"] == "a" * 40
    assert payload['identity_status'] == 'PASS'
    assert payload['runtime_sha_matches_build'] is True
    assert payload['build_id'].startswith('sha256:')
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
            return 200, {"content-security-policy": "default-src 'none'", "referrer-policy": "strict-origin", "x-content-type-options": "nosniff", "x-frame-options": "DENY", "cache-control": "no-store"}, {"environment": "preview", "release_version": "r1", "commit_sha": "a" * 40,
                'service': 'proptech-api', 'identity_status': 'PASS', 'identity_source': 'ci-build-argument',
                'build_id': 'sha256:' + 'b' * 64, 'build_timestamp': '2026-10-09T00:00:00Z', 'runtime_sha_matches_build': True}
        if url.endswith("/readiness"):
            return 200, {}, {"status": "ready", "runtime": {"ready": True}}
        if url.endswith("/source-status"):
            return 200, {}, {"status": "available", "test_fixtures_excluded": True}
        if url.endswith("/compatibility"):
            return 200, {}, {"status": "compatible"}
        if url.endswith("/demo-cases"):
            return 200, {}, [{"case_id": "fixture"}]
        return 200, {}, {"status": "ok"}

    monkeypatch.setattr(production_smoke, "_hosted_json", fake_json)
    monkeypatch.setattr(production_smoke, "_hosted_text", lambda url, *, timeout: (200, {"content-security-policy": "default-src 'none'", "referrer-policy": "strict-origin", "x-content-type-options": "nosniff"}, "Explicit offline competition example"))
    result = production_smoke.run_hosted(frontend_url="https://front.example", backend_url="https://api.example", expected_environment="preview", expected_release="r1", expected_frontend_sha="a" * 40, expected_backend_sha="a" * 40)
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


def test_release_cli_combines_acceptance_and_closure_without_trusting_go(tmp_path) -> None:
    import subprocess
    import sys

    gates = tmp_path / "gates.json"
    gates.write_text(json.dumps([{
        "capability": "local_software", "classification": "PASS", "mode": "local",
        "test_result": "pass", "reason_code": "local_regression_passed", "owner_action": "none",
    }]), encoding="utf-8")
    closure = tmp_path / "closure.json"
    closure.write_text(json.dumps({
        "schema_version": "production-provider-closure-v1", "sections": {},
        "acceptance": {"lane_status": "PASS", "product_go": True}, "secret": "private-value",
    }), encoding="utf-8")
    output = tmp_path / "release.json"
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/generate_release_evidence.py"),
        "--output", str(output), "--release-id", "release-1", "--commit", "a" * 40,
        "--schema-version", "schema-007", "--acceptance-input", str(gates),
        "--closure-json", str(closure),
    ], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "final-production-acceptance-v1"
    assert payload["gates"][0]["classification"] == "PASS"
    assert payload["verdict"] == "NO-GO"
    assert payload["closure_acceptance"]["lane_status"] == "BLOCKED"
    assert payload["closure_acceptance"]["product_go"] is False
    assert "private-value" not in json.dumps(payload)


def test_blocked_closure_prevents_complete_scorecard_go() -> None:
    from scripts import generate_release_evidence as evidence

    rows = [{
        "capability": capability, "classification": "PASS", "test_result": "pass",
        "mode": "local" if capability in evidence.LOCAL_GATES else "hosted",
        "confirmed_environment": "production", "frontend_sha": "a" * 40, "backend_sha": "a" * 40,
        "frontend_release_version": "r1", "backend_release_version": "r1",
        "data_version": "v1", "artifact_version": "v1", "source_release_date": "2026-01-01",
        "import_timestamp": "2026-10-09T00:00:00Z", "latest_effective_period": "2026-Q3",
        "geographic_coverage": "Taipei", "scenario": "24h-350mm",
        "manifest_sha256": "b" * 64, "artifact_sha256": "c" * 64, "evidence_sha256": "d" * 64,
        **{key: True for key in (
            "code_implemented", "configuration_valid", "accepted_artifact_present",
            "deployed_release_verified", "bounded_live_verified", "owner_evidence_verified",
            "positive_fixture_verified", "negative_fixture_verified", "unknown_semantics_verified",
        )},
    } for capability in evidence.REQUIRED_GATES]
    assert evidence.build_acceptance_evidence(expected_main_sha="a" * 40, release_version="r1", gates=rows)["verdict"] == "GO"
    result = build_evidence(release_id="r1", commit="a" * 40, schema_version="schema-007",
                            acceptance_gates=rows, closure={"schema_version": "production-provider-closure-v1", "sections": {}})
    assert result["verdict"] == "NO-GO"
    assert result["closure_acceptance"]["product_go"] is False


@pytest.mark.parametrize(("extra", "reason"), [
    ({"max_requests": 0}, "live_request_ceiling"),
    ({"max_requests": True}, "live_request_ceiling"),
    ({"disabled": "true"}, "live_acceptance_disabled"),
    ({"disabled": "malformed"}, "live_acceptance_disabled"),
    ({"confirmed_environment": None}, "live_contract_required"),
    ({"request_budget": None}, "live_contract_required"),
    ({"allow_live": False}, "live_contract_required"),
])
def test_combined_provider_safeguards_block_fully_configured_probe(monkeypatch, extra, reason) -> None:
    from scripts import provider_acceptance

    monkeypatch.setattr(provider_acceptance, "_geocoding", lambda **kwargs: pytest.fail("unexpected provider call"))
    options = {"capability": "geocoding", "mode": "bounded-live", "allow_live": True,
               "confirmed_environment": "production", "request_budget": 1, "max_requests": 1}
    values = {"GOOGLE_MAPS_API_KEY": "private-key", "PROVIDER_ACCEPTANCE_DISABLED": extra.get("disabled", "false")}
    options.update({key: value for key, value in extra.items() if key != "disabled"})
    result = provider_acceptance.run(environ=values, **options)
    assert result["reason_code"] == reason
    assert result["result"] == "configuration_required"
    assert result["network_requests"] == 0
    assert result["provider_status"] == "not_checked"
    assert result["production_readiness"] == "unproven"
