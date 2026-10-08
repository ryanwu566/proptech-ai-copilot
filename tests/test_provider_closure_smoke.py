import json

from scripts import production_smoke


def test_explicit_hosted_missing_targets_reports_configuration_required(monkeypatch):
    monkeypatch.setattr(production_smoke, "_hosted_json", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No requests")))
    result = production_smoke.run_hosted(frontend_url="", backend_url="")
    assert result["status"] == "configuration_required"
    assert result["reason_code"] == "configuration_required"


def test_url_with_embedded_credentials_is_rejected_without_leak():
    result = production_smoke.run_hosted(frontend_url="https://user:private-secret@frontend.example", backend_url="https://backend.example")
    assert result["status"] == "configuration_required"
    assert "private-secret" not in json.dumps(result)


def test_release_mismatch_cannot_pass_hosted_smoke(monkeypatch):
    headers = {"content-security-policy": "default-src 'none'", "referrer-policy": "strict-origin", "x-content-type-options": "nosniff", "x-frame-options": "DENY", "cache-control": "no-store"}
    monkeypatch.setattr(production_smoke, "_hosted_text", lambda *args, **kwargs: (200, headers, "offline"))
    def response(url, **kwargs):
        if kwargs.get("method") == "OPTIONS":
            return 204, {"access-control-allow-origin": "https://frontend.example"}, None
        return 200, headers, {"commit_sha": "a" * 40, "environment": "preview", "release_version": "old"}
    monkeypatch.setattr(production_smoke, "_hosted_json", response)
    result = production_smoke.run_hosted(frontend_url="https://frontend.example", backend_url="https://backend.example", expected_environment="production", expected_release="new")
    assert result["status"] == "fail"
    assert result["checks"]["release_identity"] == "fail"


def test_unknown_deployed_shas_cannot_prove_current_main(monkeypatch):
    monkeypatch.setattr(production_smoke, "_hosted_text", lambda *args, **kwargs: (200, {}, "offline"))
    monkeypatch.setattr(production_smoke, "_hosted_json", lambda *args, **kwargs: (200, {}, {}))
    result = production_smoke.run_hosted(frontend_url="https://frontend.example", backend_url="https://backend.example")
    assert result["release_identity"] == {"frontend_sha": "unconfigured", "backend_sha": "unconfigured"}
    assert result["checks"]["deployed_identity"] != "pass"
