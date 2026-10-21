"""Trusted address resolve API tests."""

from fastapi.testclient import TestClient
import httpx
import pytest

from backend.api_main import app
from services import location_resolver


client = TestClient(app)


SAFE_KEYS = {
    "status",
    "source",
    "formatted_address",
    "latitude",
    "longitude",
    "confidence",
    "message",
    "county",
    "district",
}


def test_location_resolve_rejects_blank_address() -> None:
    response = client.post("/location/resolve", json={"address": " \n\t "})

    assert response.status_code == 422


def test_location_resolve_returns_only_safe_fields(monkeypatch) -> None:
    def fake_resolve_address(address: str) -> dict[str, object]:
        assert address == "臺北市信義區市府路1號"
        return {
            "status": "resolved",
            "source": "google",
            "formatted_address": "測試格式化地址",
            "latitude": 25.03,
            "longitude": 121.56,
            "confidence": "high",
            "message": "已取得可信位置（Google）。",
            "raw_payload": {"token": "must not leak"},
            "api_key": "must not leak",
            "provider_raw_error": "must not leak",
        }

    monkeypatch.setattr("services.location_resolver.resolve_address", fake_resolve_address)

    response = client.post("/location/resolve", json={"address": "臺北市信義區市府路1號"})

    assert response.status_code == 200
    result = response.json()
    assert set(result) == SAFE_KEYS
    assert result["status"] == "resolved"
    assert result["source"] == "google"
    assert result["county"] is None
    assert result["district"] is None
    assert result["latitude"] == 25.03
    serialized = str(result)
    assert "raw_payload" not in serialized
    assert "api_key" not in serialized
    assert "provider_raw_error" not in serialized
    assert "must not leak" not in serialized


def test_location_resolve_returns_administrative_area_from_the_same_response(monkeypatch) -> None:
    calls: list[str] = []

    def fake_resolve_address(address: str) -> dict[str, object]:
        calls.append(address)
        return {
            "status": "resolved", "source": "tgos", "formatted_address": "臺北市信義區市府路1號",
            "latitude": 25.0375, "longitude": 121.5637, "confidence": "high",
            "message": "已取得可信位置（TGOS）。", "county": "臺北市", "district": "信義區",
        }

    monkeypatch.setattr("services.location_resolver.resolve_address", fake_resolve_address)
    monkeypatch.setattr("backend.api.routes_location_insight.analyze_location", lambda **_: (_ for _ in ()).throw(AssertionError("resolve must not run insight")))

    response = client.post("/location/resolve", json={"address": "臺北市信義區市府路1號"})

    assert response.status_code == 200
    assert response.json()["county"] == "臺北市"
    assert response.json()["district"] == "信義區"
    assert calls == ["臺北市信義區市府路1號"]


@pytest.mark.parametrize("compatible", [True, False])
def test_location_resolve_api_enforces_acceptance_before_exposing_a_candidate(monkeypatch, compatible) -> None:
    address = "新北市新莊區中正路191號"
    returned = address if compatible else "238台灣新北市樹林區金寮里中正路191號"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-api-accuracy")
    monkeypatch.setenv("TGOS_APP_ID", "test-api-accuracy")
    monkeypatch.setenv("TGOS_API_KEY", "test-api-accuracy")
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        payload = {"status": "OK", "results": [{"formatted_address": returned, "partial_match": False,
            "geometry": {"location_type": "ROOFTOP", "location": {"lat": 25.0375, "lng": 121.5637}}}]} if url == location_resolver.GOOGLE_GEOCODING_URL else {
                "AddressList": [{"FULL_ADDR": returned, "X": 121.5637, "Y": 25.0375}]}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(location_resolver.httpx, "get", get)
    location_resolver._RESOLVED_ADDRESS_CACHE.clear()
    try:
        response = client.post("/location/resolve", json={"address": address})
        assert response.status_code == 200
        body = response.json()
        assert set(body) == SAFE_KEYS
        assert "acceptance_validated" not in body
        if compatible:
            assert (body["status"], body["source"], body["confidence"]) == ("resolved", "google", "high")
            assert calls == [location_resolver.GOOGLE_GEOCODING_URL]
        else:
            assert (body["status"], body["confidence"]) == ("unresolved", "unknown")
            assert body["latitude"] is body["longitude"] is None
            assert calls == [location_resolver.GOOGLE_GEOCODING_URL, location_resolver.TGOS_URL]
    finally:
        location_resolver._RESOLVED_ADDRESS_CACHE.clear()
