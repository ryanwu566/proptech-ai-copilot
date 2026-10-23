"""Representative Google fixtures, not captured customer/provider payloads.

Assert the actual HTTP API produces exactly the fixture consumed by frontend
unit/browser journeys. No live Google/TGOS calls are made.
"""
from copy import deepcopy
import json
from pathlib import Path

from fastapi.testclient import TestClient
import httpx
import pytest

from backend.api_main import app
from services import location_resolver

FIXTURES = json.loads((Path(__file__).parent / "fixtures/location_market_google.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda fixture: fixture["name"])
@pytest.mark.parametrize("district_level", [2, 3])
def test_google_to_http_admin_contract(monkeypatch, fixture, district_level):
    payload = deepcopy(fixture["google"])
    for component in payload["results"][0]["address_components"]:
        if "administrative_area_level_3" in component["types"]:
            component["types"] = [f"administrative_area_level_{district_level}", "political"]
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        assert url == location_resolver.GOOGLE_GEOCODING_URL
        assert kwargs["params"]["address"] == fixture["address"]
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fixture-only")
    monkeypatch.delenv("TGOS_APP_ID", raising=False)
    monkeypatch.delenv("TGOS_API_KEY", raising=False)
    monkeypatch.setattr(location_resolver.httpx, "get", get)
    location_resolver._RESOLVED_ADDRESS_CACHE.clear()
    try:
        response = TestClient(app).post("/location/resolve", json={"address": fixture["address"]})
        assert response.status_code == 200
        assert response.json() == fixture["response"]
        assert calls == [location_resolver.GOOGLE_GEOCODING_URL]
    finally:
        location_resolver._RESOLVED_ADDRESS_CACHE.clear()


@pytest.mark.parametrize("returned_district", ["樹林區", "新莊區"])
def test_exact_incident_and_structured_cross_district_contradiction_stay_rejected(monkeypatch, returned_district):
    """Reject both a wrong formatted district and metadata hidden behind a matching string."""
    address = "新北市新莊區中正路191號"
    payload = {"status": "OK", "results": [{
        "formatted_address": f"新北市{returned_district}中正路191號",
        "partial_match": False,
        "geometry": {"location_type": "ROOFTOP", "location": {"lat": 25.0359, "lng": 121.4326}},
        "address_components": [
            {"long_name": "新北市", "types": ["administrative_area_level_1", "political"]},
            {"long_name": "樹林區", "types": ["administrative_area_level_3", "political"]},
            {"long_name": "中正路", "types": ["route"]},
            {"long_name": "191", "types": ["street_number"]},
        ],
    }]}
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "incident-fixture-only")
    monkeypatch.delenv("TGOS_APP_ID", raising=False)
    monkeypatch.delenv("TGOS_API_KEY", raising=False)
    monkeypatch.setattr(location_resolver.httpx, "get", get)
    location_resolver._RESOLVED_ADDRESS_CACHE.clear()
    try:
        response = TestClient(app).post("/location/resolve", json={"address": address})
        assert response.status_code == 200
        body = response.json()
        assert (body["status"], body["confidence"]) == ("unresolved", "unknown")
        assert body["latitude"] is body["longitude"] is None
        assert calls == [location_resolver.GOOGLE_GEOCODING_URL]
    finally:
        location_resolver._RESOLVED_ADDRESS_CACHE.clear()
