"""Offline contract and security checks for the bounded NLSC gateway client."""

from __future__ import annotations

import json
import math
from pathlib import Path

import httpx
import pytest

from services.adapters.nlsc_gateway_adapter import NlscGatewayAdapter
from services.terrain_risk_providers.nlsc_terrain_provider import NlscTerrainProvider


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "backend-only-client-token-123"
CONFIG = {
    "APP_ENV": "production",
    "NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw",
    "NLSC_GATEWAY_CLIENT_TOKEN": TOKEN,
}
VALID_RESPONSE = {
    "status": "available",
    "slope_value": 12.5,
    "slope_class": "moderate",
    "elevation_m": 42,
    "source": "NLSC",
}
UNAVAILABLE = {
    "status": "unavailable",
    "slope_value": None,
    "slope_class": None,
    "elevation_m": None,
    "source": "NLSC",
}


def client_with(handler, *, follow_redirects: bool = False):
    requests = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(record), follow_redirects=follow_redirects), requests


def test_unconfigured_adapter_never_calls_gateway() -> None:
    client, requests = client_with(lambda request: httpx.Response(200, json=VALID_RESPONSE))
    with client:
        adapter = NlscGatewayAdapter(client=client, environ={"APP_ENV": "production"})
        assert adapter.available is False
        assert adapter.terrain_point(25.03, 121.56, 500) == UNAVAILABLE
    assert requests == []


def test_valid_response_uses_only_fixed_endpoint_and_backend_bearer_credential() -> None:
    payload = {**VALID_RESPONSE, "raw_provider_payload": {"credential": TOKEN}}
    client, requests = client_with(lambda request: httpx.Response(200, json=payload))
    with client:
        adapter = NlscGatewayAdapter(client=client, environ=CONFIG)
        assert adapter.available is True
        result = adapter.terrain_point(25.03, 121.56, 500)
    assert result == VALID_RESPONSE
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://gateway.example.tw/nlsc/terrain/point"
    assert request.method == "POST"
    assert json.loads(request.content) == {"lat": 25.03, "lng": 121.56, "radius_m": 500}
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.extensions["timeout"]["read"] == 4.0
    assert TOKEN not in json.dumps(result)


@pytest.mark.parametrize("failure", ["timeout", "connection", "http_401", "http_503", "redirect", "bad_json", "unexpected"])
def test_gateway_transport_failures_return_unavailable_without_secret(failure: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout(f"timeout {TOKEN}", request=request)
        if failure == "connection":
            raise httpx.ConnectError(f"connection {TOKEN}", request=request)
        if failure == "unexpected":
            raise RuntimeError(f"unexpected transport error {TOKEN}")
        if failure == "bad_json":
            return httpx.Response(200, content=b"{")
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://attacker.example/"})
        return httpx.Response(int(failure.removeprefix("http_")), json={"detail": TOKEN})

    client, requests = client_with(respond, follow_redirects=failure == "redirect")
    with client:
        result = NlscGatewayAdapter(client=client, environ=CONFIG).terrain_point(25.03, 121.56, 500)
    assert result == UNAVAILABLE
    assert len(requests) == 1
    assert TOKEN not in json.dumps(result)


@pytest.mark.parametrize("url", ["http://gateway.example.tw", "https://10.0.0.1", "https://gateway.example.invalid", "https://gateway.local"])
def test_malformed_production_gateway_never_calls_network(url: str) -> None:
    client, requests = client_with(lambda request: httpx.Response(200, json=VALID_RESPONSE))
    with client:
        adapter = NlscGatewayAdapter(client=client, environ={**CONFIG, "NLSC_GATEWAY_BASE_URL": url})
        assert adapter.available is False
        assert adapter.configuration_status == "malformed"
        assert adapter.terrain_point(25.03, 121.56, 500) == UNAVAILABLE
    assert requests == []


@pytest.mark.parametrize("payload", [
    [],
    {"status": "available", "slope_value": None, "slope_class": None, "elevation_m": None, "source": "NLSC"},
    {**VALID_RESPONSE, "slope_value": None},
    {**VALID_RESPONSE, "elevation_m": None},
    {**VALID_RESPONSE, "source": "gateway"},
    {**VALID_RESPONSE, "status": "no_risk"},
    {**VALID_RESPONSE, "slope_value": math.nan},
    {**VALID_RESPONSE, "slope_value": True},
    {**VALID_RESPONSE, "elevation_m": 100000},
    {**VALID_RESPONSE, "slope_class": "x" * 1000},
    {**VALID_RESPONSE, "slope_class": TOKEN},
    {**VALID_RESPONSE, "slope_class": "unrecognized"},
])
def test_malformed_gateway_data_cannot_become_available(payload: object) -> None:
    client, _ = client_with(lambda request: httpx.Response(200, json=payload))
    with client:
        assert NlscGatewayAdapter(client=client, environ=CONFIG).terrain_point(25.03, 121.56, 500) == UNAVAILABLE


@pytest.mark.parametrize("lat,lng,radius", [
    (math.nan, 121.56, 500),
    (math.inf, 121.56, 500),
    (10 ** 1000, 121.56, 500),
    (25.03, -math.inf, 500),
    (20.99, 121.56, 500),
    (25.03, 123.01, 500),
    (121.56, 25.03, 500),
    (25.03, 121.56, 99),
    (25.03, 121.56, 2001),
    (25.03, 121.56, 500.5),
    (True, 121.56, 500),
])
def test_invalid_point_is_rejected_before_egress(lat: object, lng: object, radius: object) -> None:
    client, requests = client_with(lambda request: httpx.Response(200, json=VALID_RESPONSE))
    with client:
        result = NlscGatewayAdapter(client=client, environ=CONFIG).terrain_point(lat, lng, radius)
    assert result == UNAVAILABLE
    assert requests == []


def test_provider_delegates_only_with_available_gateway_and_keeps_nlsc_provenance() -> None:
    client, requests = client_with(lambda request: httpx.Response(200, json=VALID_RESPONSE))
    with client:
        configured = NlscTerrainProvider(gateway=NlscGatewayAdapter(client=client, environ=CONFIG))
        result = configured.analyze(25.03, 121.56, 500)
        absent = NlscTerrainProvider(gateway=NlscGatewayAdapter(client=client, environ={"APP_ENV": "production"}))
        fallback = absent.analyze(25.03, 121.56, 500)
    assert len(requests) == 1
    assert result["status"] == "available"
    assert result["slope_value"] == 12.5
    assert result["source"]["name"].startswith("NLSC")
    assert result["source"]["agency"] == "內政部國土測繪中心"
    assert result["source"]["source_url"] == "https://maps.nlsc.gov.tw/"
    assert result["source"]["status"] == "available"
    assert fallback["status"] == "unavailable"
    assert fallback["source"]["status"] == "unavailable"


def test_provider_closes_its_own_gateway_client(monkeypatch) -> None:
    client, requests = client_with(lambda request: httpx.Response(200, json=VALID_RESPONSE))
    for key, value in CONFIG.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("services.adapters.nlsc_gateway_adapter.httpx.Client", lambda: client)

    assert NlscTerrainProvider().analyze(25.03, 121.56, 500)["status"] == "available"
    assert len(requests) == 1
    assert client.is_closed


def test_gateway_credential_has_no_frontend_source_or_bundle_reference() -> None:
    frontend = ROOT / "frontend_next"
    for path in frontend.rglob("*"):
        if not path.is_file() or any(part in {"node_modules", ".next", ".git"} for part in path.parts):
            continue
        if path.suffix in {".ts", ".tsx", ".js", ".jsx", ".json"} or path.name.startswith(".env"):
            assert b"NLSC_GATEWAY_CLIENT_TOKEN" not in path.read_bytes(), str(path)
