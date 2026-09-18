"""Commute /route API contract tests (offline; no live Google call)."""

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app
from services import commute_routing_service
from services.adapters.routes_adapter import GoogleRoutesAdapter


client = TestClient(app)

ALLOWED_KEYS = {
    "status", "source", "mode", "duration_min", "duration_seconds",
    "distance_m", "partial", "fallback", "message", "disclaimer",
}


@pytest.fixture(autouse=True)
def _offline_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Guarantee no live Google call regardless of inherited environment:
    # the default adapter is forced unavailable so the service uses the mock.
    monkeypatch.setattr(commute_routing_service, "_DEFAULT_GOOGLE_ADAPTER", GoogleRoutesAdapter(api_key=""))
    commute_routing_service.clear_route_cache()
    yield
    commute_routing_service.clear_route_cache()


def _assert_safe_contract(body: dict) -> None:
    assert set(body.keys()) == ALLOWED_KEYS
    serialized = str(body)
    for forbidden in ("api_key", "X-Goog-Api-Key", "secret", "token", "polyline", "latLng", "raw"):
        assert forbidden not in serialized


def test_coordinate_destination_returns_mock_fallback_without_key() -> None:
    # Dev/test runtime (no APP_ENV) allows a clearly marked mock estimate.
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
        "mode": "transit",
    })
    assert response.status_code == 200
    body = response.json()
    _assert_safe_contract(body)
    assert body["status"] == "resolved"
    assert body["source"] == "mock"
    assert body["fallback"] is True
    assert body["mode"] == "transit"
    assert isinstance(body["duration_min"], int)
    assert isinstance(body["distance_m"], int)


def test_production_without_key_is_unavailable_no_mock_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DEMO_ROUTES_FALLBACK", raising=False)
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
        "mode": "transit",
    })
    assert response.status_code == 200
    body = response.json()
    _assert_safe_contract(body)
    assert body["status"] == "unavailable"
    assert body["source"] == "none"
    assert body["duration_min"] is None
    assert body["distance_m"] is None
    assert body["fallback"] is False


def test_production_demo_optin_allows_marked_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_ROUTES_FALLBACK", "true")
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
        "mode": "walking",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["source"] == "mock"
    assert body["fallback"] is True


def test_default_mode_is_transit() -> None:
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
    })
    assert response.status_code == 200
    assert response.json()["mode"] == "transit"


def test_unsupported_mode_is_validation_error() -> None:
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
        "mode": "cycling",
    })
    assert response.status_code == 422


def test_missing_destination_is_validation_error() -> None:
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "mode": "driving",
    })
    assert response.status_code == 422


def test_both_destination_forms_is_validation_error() -> None:
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_address": "台北市信義區市府路45號",
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
        "mode": "driving",
    })
    assert response.status_code == 422


def test_half_destination_coordinate_is_validation_error() -> None:
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "mode": "driving",
    })
    assert response.status_code == 422


def test_address_destination_without_providers_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stub resolution to the unavailable path so the test never performs a network call.
    from backend.api import routes_commute

    monkeypatch.setattr(
        routes_commute.location_resolver,
        "resolve_address",
        lambda address: {"status": "unavailable", "source": "none", "message": "unavailable"},
    )
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_address": "台北市信義區市府路45號",
        "mode": "transit",
    })
    assert response.status_code == 503
    body = response.json()
    _assert_safe_contract(body)
    assert body["status"] == "unavailable"
    assert body["source"] == "none"


def test_address_destination_resolved_then_estimated(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.api import routes_commute

    monkeypatch.setattr(
        routes_commute.location_resolver,
        "resolve_address",
        lambda address: {"status": "resolved", "source": "tgos", "latitude": 25.0478, "longitude": 121.5170, "message": "ok"},
    )
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_address": "台北市信義區市府路45號",
        "mode": "walking",
    })
    assert response.status_code == 200
    body = response.json()
    _assert_safe_contract(body)
    assert body["status"] == "resolved"
    assert body["source"] == "mock"  # offline fixture forces fallback
    assert body["mode"] == "walking"


def test_extra_field_is_rejected() -> None:
    response = client.post("/commute/route", json={
        "origin_latitude": 25.0330,
        "origin_longitude": 121.5654,
        "destination_latitude": 25.0478,
        "destination_longitude": 121.5170,
        "mode": "transit",
        "waypoints": ["extra"],
    })
    assert response.status_code == 422
