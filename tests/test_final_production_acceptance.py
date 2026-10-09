"""Final acceptance fails closed before traffic or readiness claims."""

import importlib
import json
import socket

import pytest

from scripts import generate_release_evidence as evidence, production_smoke

SHA = "a" * 40


def test_hosted_requires_pinned_identity_before_requests(monkeypatch):
    monkeypatch.setattr(production_smoke, "_hosted_json", lambda *a, **k: pytest.fail("unexpected request"))
    result = production_smoke.run_hosted(frontend_url="https://front.example", backend_url="https://api.example")
    assert result["status"] == "configuration_required"
    assert result["classification"] == "CONFIGURATION REQUIRED"
    assert result["network_requests"] == 0


def test_live_budget_and_environment_required_before_transmission(monkeypatch):
    from scripts.provider_acceptance import run
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("unexpected request"))
    result = run(capability="geocoding", mode="bounded-live", allow_live=True, environ={"GOOGLE_MAPS_API_KEY": "private"})
    assert result["result"] == "configuration_required"
    assert result["network_requests"] == 0


def test_legacy_certification_import_is_provider_free(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("unexpected request"))
    importlib.import_module("scripts.certify_real_provider")


def test_missing_gates_never_produce_go():
    result = evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=[])
    assert result["verdict"] == "NO-GO"
    assert all(row["classification"] == "NOT VERIFIED" for row in result["gates"])
    assert result["expected_main_sha"] == SHA


def test_false_hosted_identity_pass_is_rejected():
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=[{
            "capability": "deployed_identity", "classification": "PASS", "mode": "hosted", "test_result": "pass",
            "frontend_sha": SHA, "backend_sha": "b" * 40,
        }])


def test_local_provider_fixture_cannot_pass_production_gate():
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=[{
            "capability": "geocoding", "classification": "PASS", "mode": "local", "test_result": "pass",
        }])


def test_duplicate_or_unsafe_evidence_rejected():
    row = {"capability": "local_software", "classification": "PASS", "mode": "local", "test_result": "pass"}
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=[row, row])
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=[{**row, "reason_code": "https://private:secret@example"}])


def test_bounded_evidence_preserves_restrictions():
    result = evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=[{
        "capability": "local_software", "classification": "PASS", "mode": "local", "test_result": "pass",
        "reason_code": "local_regression_passed", "owner_action": "none",
    }])
    assert result["verdict"] == "NO-GO"
    assert result["gates"][0]["acceptance_timestamp"]
    assert "secret" not in json.dumps(result).replace("secrets_included", "")


@pytest.mark.parametrize("origin", ["https://front.example:invalid", "https://front.example:8443", "http://front.example"])
def test_unsafe_target_is_configuration_required(origin):
    assert production_smoke.run_hosted(frontend_url=origin, backend_url="https://api.example")["classification"] == "CONFIGURATION REQUIRED"


def test_redirects_never_forward_smoke_credentials():
    from urllib.request import Request
    request = Request("https://api.example/release-version", headers={"X-Production-Smoke-Token": "private"})
    assert production_smoke._NoRedirect().redirect_request(request, None, 302, "", {}, "https://other.example") is None


def test_valid_identity_with_empty_health_payloads_cannot_pass(monkeypatch):
    headers = {"content-security-policy": "default-src 'none'", "referrer-policy": "strict-origin", "x-content-type-options": "nosniff", "x-frame-options": "DENY", "cache-control": "no-store"}
    def response(url, **kwargs):
        if kwargs.get("method") == "OPTIONS":
            return 204, {"access-control-allow-origin": "https://front.example"}, None
        if url.endswith("release-version"):
            return 200, headers, {"commit_sha": SHA, "environment": "production", "release_version": "r1"}
        return 200, headers, {}
    monkeypatch.setattr(production_smoke, "_hosted_json", response)
    monkeypatch.setattr(production_smoke, "_hosted_text", lambda *a, **k: (200, headers, "offline"))
    result = production_smoke.run_hosted(frontend_url="https://front.example", backend_url="https://api.example", expected_environment="production", expected_release="r1", expected_frontend_sha=SHA, expected_backend_sha=SHA)
    assert result["classification"] == "BLOCKED"
    for key in ("health", "liveness", "readiness", "source_status", "compatibility"):
        assert result["checks"][key] == "fail"


@pytest.mark.parametrize("environment", [None, "preview", "production"])
def test_complete_scorecard_without_versions_and_owner_evidence_cannot_be_go(environment):
    rows = []
    for capability in evidence.REQUIRED_GATES:
        row = {"capability": capability, "classification": "PASS", "mode": "local" if capability in evidence.LOCAL_GATES else "hosted", "test_result": "pass", "frontend_sha": SHA, "backend_sha": SHA}
        row.update({key: True for key in ("code_implemented", "configuration_valid", "accepted_artifact_present", "deployed_release_verified", "bounded_live_verified")})
        if environment:
            row["confirmed_environment"] = environment
        rows.append(row)
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="release-1", gates=rows)


def test_json_transport_preserves_supported_demo_array(monkeypatch):
    class Response:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return b'[{"case_id":"fixture"}]'
    monkeypatch.setattr(production_smoke, "urlopen", lambda *a, **k: Response())
    assert production_smoke._hosted_json("https://api.example/demo-cases", timeout=1)[2] == [{"case_id": "fixture"}]


def test_reason_codes_cannot_echo_api_keys():
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="r1", gates=[{
            "capability": "local_software", "classification": "NOT VERIFIED", "reason_code": "AIzaSyCustomerPrivateKey1234567890",
        }])


def artifact_observation():
    return {"capability": "wra", "classification": "PASS", "test_result": "pass", "mode": "hosted", "confirmed_environment": "production", "frontend_sha": SHA, "backend_sha": SHA, "frontend_release_version": "r1", "backend_release_version": "r1", "data_version": "v1", "artifact_version": "v1", "source_release_date": "2026-01-01", "import_timestamp": "2026-10-09T00:00:00Z", "geographic_coverage": "Taipei", "scenario": "24h-350mm", "manifest_sha256": "c" * 64, "artifact_sha256": "d" * 64, **{key: True for key in ("code_implemented", "configuration_valid", "accepted_artifact_present", "deployed_release_verified", "bounded_live_verified", "positive_fixture_verified", "negative_fixture_verified", "unknown_semantics_verified")}}


@pytest.mark.parametrize("field", ["artifact_version", "source_release_date", "import_timestamp", "geographic_coverage", "scenario"])
@pytest.mark.parametrize("value", ["unknown", "pending", "unconfigured", "not_checked"])
def test_missing_metadata_aliases_cannot_pass(field, value):
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="r1", gates=[{**artifact_observation(), field: value}])


@pytest.mark.parametrize(("field", "value"), [("source_release_date", "2026-02-30"), ("import_timestamp", "2026-13-01T00:00:00Z"), ("scenario", "arbitrary"), ("scenario", "48h-350mm")])
def test_invalid_metadata_cannot_pass(field, value):
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="r1", gates=[{**artifact_observation(), field: value}])


def test_exact_artifact_observation_preserved_but_missing_other_gates_still_block_go():
    result = evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="r1", gates=[artifact_observation()])
    assert result["verdict"] == "NO-GO"
    assert next(row for row in result["gates"] if row["capability"] == "wra")["classification"] == "PASS"


@pytest.mark.parametrize("field", ["frontend_release_version", "backend_release_version"])
def test_deployed_release_version_must_match_expected(field):
    with pytest.raises(ValueError):
        evidence.build_acceptance_evidence(expected_main_sha=SHA, release_version="r1", gates=[{**artifact_observation(), field: "old-release"}])
