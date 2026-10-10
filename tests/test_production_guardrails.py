from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI


def test_production_requires_exact_hosts_and_no_unavailable_distributed_driver():
    from services.production_guardrails import assert_guardrail_configuration

    with pytest.raises(RuntimeError, match="guardrail"):
        assert_guardrail_configuration({"APP_ENV": "production"})
    for invalid in ("*", "*.example.com", "https://api.example.com", "api.example.com:443", ""):
        with pytest.raises(RuntimeError):
            assert_guardrail_configuration({"APP_ENV": "production", "API_ALLOWED_HOSTS": invalid})
    with pytest.raises(RuntimeError):
        assert_guardrail_configuration({"APP_ENV": "production", "API_ALLOWED_HOSTS": "api.example.com", "ANTI_ABUSE_ENFORCEMENT_MODE": "postgres"})
    assert_guardrail_configuration({"APP_ENV": "production", "API_ALLOWED_HOSTS": "api.example.com"})


@pytest.mark.parametrize("key,value", [("OPERATIONS", "301"), ("CONCURRENCY", "5"), ("REQUESTS", "31"), ("WINDOW_SECONDS", "1"), ("OPERATIONS", "NaN"), ("OPERATION_WINDOW_SECONDS", "60")])
def test_production_cost_overrides_cannot_weaken_current_limits(key, value):
    from services.production_guardrails import assert_guardrail_configuration
    with pytest.raises(RuntimeError):
        assert_guardrail_configuration({"APP_ENV": "production", "API_ALLOWED_HOSTS": "api.example.com", f"ANTI_ABUSE_GEOCODING_{key}": value})


def test_ingress_rejects_bad_host_and_malformed_or_unapproved_origin_before_route(monkeypatch):
    from backend.api.ingress_middleware import IngressMiddleware
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://frontend.example.com")
    app = FastAPI()
    calls = []
    @app.get("/probe")
    def probe():
        calls.append(1)
        return {"ok": True}
    app.add_middleware(IngressMiddleware)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://api.example.com") as client:
            for headers in ({"host": "evil.example.com"}, {"origin": "null"}, {"origin": "https://evil.example.com"}, {"origin": "garbage"}):
                response = await client.get("/probe", headers=headers)
                assert response.status_code in {400, 403}
            assert not calls
            assert (await client.get("/docs")).status_code == 404
            assert (await client.get("/probe", headers={"origin": "https://frontend.example.com", "x-forwarded-for": "192.0.2.99"})).status_code == 200
            assert (await client.get("/probe")).status_code == 200
    asyncio.run(exercise())
    assert len(calls) == 2


def test_no_owner_evidence_cannot_pass():
    from services.guardrail_evidence import evaluate_controls
    result = evaluate_controls(commit="a" * 40)
    assert result["production_decision"] == "NO_GO"
    assert result["controls"]["trusted_ingress"]["state"] == "BLOCKED"
    assert all(row["state"] == "BLOCKED" for row in result["controls"].values())


def test_malformed_owner_state_is_a_failure_and_nonstandard_json_is_rejected(tmp_path):
    from services.guardrail_evidence import evaluate_controls, read_bounded_json
    assert evaluate_controls(commit="a" * 40, records={"trusted_ingress": {"state": []}})["controls"]["trusted_ingress"]["state"] == "FAIL"
    path = tmp_path / "invalid.json"
    path.write_text('{"amount": NaN}')
    with pytest.raises(ValueError):
        read_bounded_json(path)


def owner_record(tmp_path, *, commit="a" * 40, age=0, facts=None):
    source = tmp_path / "source.json"
    source.write_text('{"synthetic_test_receipt": true}')
    proof = tmp_path / "proof.json"
    proof.write_text(json.dumps({"control": "trusted_ingress", "release_commit": commit,
        "facts": facts or {"proxy_headers": "disabled", "direct_backend_bypass": "denied", "all_ingress_paths_reviewed": True},
        "evidence_files": [{"file": "source.json", "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "kind": "cloud_export"}]}))
    return {"state": "PASS", "owner_role": "ingress_owner", "verified_at": (datetime.now(UTC) - timedelta(days=age)).isoformat(),
        "release_commit": commit, "proof_file": "proof.json", "proof_sha256": hashlib.sha256(proof.read_bytes()).hexdigest()}


def test_owner_pass_requires_hashed_facts_freshness_and_exact_release(tmp_path):
    from services.guardrail_evidence import evaluate_controls
    row = owner_record(tmp_path)
    result = evaluate_controls(commit="a" * 40, records={"trusted_ingress": row}, proof_root=tmp_path)
    assert result["controls"]["trusted_ingress"]["state"] == "PASS"
    assert result["production_decision"] == "NO_GO"
    (tmp_path / "source.json").write_text('{}')
    assert evaluate_controls(commit="a" * 40, records={"trusted_ingress": row}, proof_root=tmp_path)["controls"]["trusted_ingress"]["state"] == "FAIL"
    row = owner_record(tmp_path)
    for mutation in ({"proof_sha256": "0" * 64}, {"release_commit": "b" * 40}, {"proof_file": "../proof.json"}, {"owner_role": "nobody"}, {"verified_at": "tomorrow"}):
        invalid = dict(row, **mutation)
        assert evaluate_controls(commit="a" * 40, records={"trusted_ingress": invalid}, proof_root=tmp_path)["controls"]["trusted_ingress"]["state"] == "FAIL"
    stale = owner_record(tmp_path, age=8)
    assert evaluate_controls(commit="a" * 40, records={"trusted_ingress": stale}, proof_root=tmp_path)["controls"]["trusted_ingress"]["state"] == "FAIL"
    bad_facts = owner_record(tmp_path, facts={"proxy_headers": "disabled", "direct_backend_bypass": "allowed", "all_ingress_paths_reviewed": True})
    assert evaluate_controls(commit="a" * 40, records={"trusted_ingress": bad_facts}, proof_root=tmp_path)["controls"]["trusted_ingress"]["state"] == "FAIL"


def test_release_evidence_includes_blocked_external_controls_by_default():
    from scripts.generate_release_evidence import build_evidence
    result = build_evidence(release_id="test", commit="a" * 40, schema_version="schema-007")
    assert result["production_guardrails"]["controls"]["global_cost_ceiling"]["state"] == "BLOCKED"
    assert result["production_guardrails"]["production_decision"] == "NO_GO"


def test_invalid_ipv6_origin_is_rejected_without_an_exception():
    from services.security import safe_origin
    assert safe_origin("https://[") is None


def test_monitoring_distinguishes_503_from_other_5xx_without_extra_labels():
    from services.metrics import BoundedMetricsRegistry
    metrics = BoundedMetricsRegistry({"/health"})
    for status in (503, 500, 503, 429):
        metrics.observe_http_request(method="GET", route_template="/health", status_code=status, duration_seconds=.01)
    rendered = metrics.render_prometheus()
    assert "proptech_http_responses_503_total 2\n" in rendered
    assert "proptech_http_responses_5xx_total 3\n" in rendered


def test_production_ingress_rejections_are_observed_and_allow_cors(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.api_main import app, http_metrics
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_ALLOWED_HOSTS", "api.example.com")
    # CORS allowlist was frozen at import; use its existing local test origin.
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    before = http_metrics.render_prometheus()
    response = TestClient(app).get("/health", headers={"origin": "http://localhost:3000"})
    assert response.status_code == 400
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert before != http_metrics.render_prometheus()
    assert response.headers["x-content-type-options"] == "nosniff"
