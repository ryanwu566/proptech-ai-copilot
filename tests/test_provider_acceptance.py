"""Operator acceptance must be bounded, explicit and credential-free."""

import json
import socket

import pytest


def test_configuration_missing_is_not_provider_failure():
    from scripts.provider_acceptance import run

    result = run(capability="geocoding", mode="config-only", environ={})
    assert result["result"] == "configuration_required"
    assert result["config_status"]["GOOGLE_MAPS_API_KEY"] == "missing"
    assert result["network_requests"] == 0
    assert result["reason_code"] == "configuration_required"


def test_configured_secret_cannot_become_provider_health_or_output():
    from scripts.provider_acceptance import run

    result = run(capability="geocoding", mode="config-only", environ={"GOOGLE_MAPS_API_KEY": "private-key", "RELEASE_COMMIT_SHA": "a" * 40})
    assert result["result"] == "ready_for_production_acceptance"
    assert result["provider_status"] == "not_checked"
    assert "private-key" not in json.dumps(result)


@pytest.mark.parametrize("version", ["latest", "current", "", "../../artifact"])
def test_gsmma_requires_immutable_exact_version(version):
    from scripts.provider_acceptance import run

    env = {name: "private-value" for name in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT", "R2_BUCKET", "R2_REGION")}
    env["R2_ENDPOINT"] = "https://example.r2.cloudflarestorage.com"
    env["GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION"] = version
    result = run(capability="gsmma", mode="config-only", environ=env)
    assert result["result"] == "configuration_required"
    assert "private-value" not in json.dumps(result)


def test_demo_valuation_configuration_cannot_pass():
    from scripts.provider_acceptance import run

    result = run(capability="valuation", mode="config-only", environ={"VALUATION_DATABASE_URL": "postgresql://private:secret@example/db", "VALUATION_DEMO_MODE": "true", "PLVR_DATA_BACKEND": "blue"})
    assert result["config_status"]["VALUATION_DEMO_MODE"] == "invalid-contract"
    assert result["result"] == "configuration_required"
    assert "secret" not in json.dumps(result)


def test_gateway_url_alone_is_not_numeric_terrain_acceptance():
    from scripts.provider_acceptance import run

    result = run(capability="nlsc", mode="config-only", environ={"NLSC_GATEWAY_BASE_URL": "https://gateway.example"})
    assert result["config_status"]["NLSC_GATEWAY_CLIENT_TOKEN"] == "missing"
    assert result["provider_status"] == "not_checked"


@pytest.mark.parametrize(("url", "token", "expected"), [("https://gateway.gov.tw", "a" * 16, "ready_for_production_acceptance"), ("https://gateway.gov.tw/path", "a" * 40, "configuration_required"), ("https://gateway.gov.tw", "☃" * 40, "configuration_required")])
def test_nlsc_config_uses_actual_runtime_contract(url, token, expected):
    from scripts.provider_acceptance import run
    result = run(capability="nlsc", environ={"NLSC_GATEWAY_BASE_URL": url, "NLSC_GATEWAY_CLIENT_TOKEN": token})
    assert result["result"] == expected


@pytest.mark.parametrize("capability", ["geocoding", "routes"])
def test_offline_fixtures_exercise_real_contract_without_network(monkeypatch, capability):
    from scripts.provider_acceptance import run

    monkeypatch.setattr(socket.socket, "connect", lambda *args: (_ for _ in ()).throw(AssertionError("offline network")))
    result = run(capability=capability, mode="offline-fixture", environ={})
    assert result["result"] == "pass"
    assert result["network_requests"] == 0
    assert result["test_mode"] == "offline-fixture"
    assert result["production_readiness"] == "unproven"


def test_live_failure_is_one_attempt_and_sanitized(monkeypatch):
    import httpx
    from scripts.provider_acceptance import run

    calls = []
    def timeout(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("private-key")
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", timeout)
    result = run(capability="geocoding", mode="bounded-live", environ={"GOOGLE_MAPS_API_KEY": "private-key"}, query="新北市板橋區文化路二段100號", allow_live=True)
    assert calls == [1]
    assert result["network_requests"] == 1
    assert result["reason_code"] == "provider_timeout"
    assert "private-key" not in json.dumps(result)


def test_live_without_explicit_opt_in_never_calls_provider(monkeypatch):
    from scripts.provider_acceptance import run
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no request allowed")))
    result = run(capability="geocoding", mode="bounded-live", environ={"GOOGLE_MAPS_API_KEY": "private-key"}, allow_live=False)
    assert result["result"] == "configuration_required"
    assert result["network_requests"] == 0


@pytest.mark.parametrize(("capability", "inputs"), [("geocoding", {"query": " "}), ("routes", {"origin": (float("nan"), 121), "destination": (25, 121)}), ("routes", {"origin": (25, 181), "destination": (25, 121)})])
def test_invalid_live_inputs_report_zero_requests(monkeypatch, capability, inputs):
    from scripts.provider_acceptance import run
    monkeypatch.setattr(socket.socket, "connect", lambda *args: (_ for _ in ()).throw(AssertionError("no request allowed")))
    result = run(capability=capability, mode="bounded-live", environ={"GOOGLE_MAPS_API_KEY": "private-key"}, allow_live=True, **inputs)
    assert result["result"] == "fail"
    assert result["reason_code"] == "invalid_input"
    assert result["network_requests"] == 0


def test_manual_capabilities_cannot_be_automated():
    from scripts.provider_acceptance import run
    result = run(capability="active-fault", mode="config-only", environ={})
    assert result["result"] == "manual_verification_only"
    assert result["network_requests"] == 0


@pytest.mark.parametrize(("payload", "reason"), [({"status": "REQUEST_DENIED", "results": [], "error_message": "private-key"}, "provider_rejected"), ({"status": "ZERO_RESULTS", "results": []}, "no_match"), ({"status": "OK", "results": [{}]}, "malformed_response"), ({}, "malformed_response"), ({"results": []}, "malformed_response"), ({"status": "OK"}, "malformed_response")])
def test_geocoding_acceptance_distinguishes_rejection_empty_and_malformed(monkeypatch, payload, reason):
    import httpx
    from scripts.provider_acceptance import run
    response = httpx.Response(200, json=payload, request=httpx.Request("GET", "https://fixture.invalid"))
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", lambda *args, **kwargs: response)
    result = run(capability="geocoding", mode="bounded-live", environ={"GOOGLE_MAPS_API_KEY": "private-key"}, allow_live=True)
    assert result["reason_code"] == reason
    assert "private-key" not in json.dumps(result)


@pytest.mark.parametrize(("latitude", "longitude"), [(91, 121.55), (25.025, 181), (float("nan"), 121.55), (25.025, float("inf")), (True, 121.55), ("25.025", 121.55)])
def test_google_invalid_provider_coordinates_cannot_be_accepted(monkeypatch, latitude, longitude):
    import httpx
    from scripts.provider_acceptance import run
    payload = {"status": "OK", "results": [{"formatted_address": "台北市大安區敦化南路二段100號", "types": ["street_address"], "geometry": {"location": {"lat": latitude, "lng": longitude}, "location_type": "ROOFTOP"}, "address_components": [{"long_name": "台北市", "types": ["administrative_area_level_1"]}, {"long_name": "大安區", "types": ["administrative_area_level_2"]}, {"long_name": "敦化南路二段", "types": ["route"]}, {"long_name": "100", "types": ["street_number"]}]}]}
    # Response.json is injected so nonfinite JSON parser behavior cannot hide
    # the adapter's own validation contract.
    response = httpx.Response(200, request=httpx.Request("GET", "https://fixture.invalid"))
    monkeypatch.setattr(response, "json", lambda: payload)
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", lambda *args, **kwargs: response)
    result = run(capability="geocoding", mode="bounded-live", environ={"GOOGLE_MAPS_API_KEY": "private-key"}, allow_live=True)
    assert result["result"] == "fail"
    assert result["reason_code"] == "malformed_response"
