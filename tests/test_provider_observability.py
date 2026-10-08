"""Passive provider state must never trigger billable health probes."""

import json

from fastapi.testclient import TestClient

from backend.api_main import app


def test_configured_google_health_does_not_call_google_or_consume_analysis_budget(monkeypatch):
    from services.map_service import get_google_health
    from services.provider_observability import ProviderObservations
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "private-key")
    monkeypatch.setattr("services.map_service.GoogleGeocodingAdapter.search", lambda *a, **k: (_ for _ in ()).throw(AssertionError("active health probe")))
    monkeypatch.setattr("services.map_service.GooglePlacesAdapter.nearby", lambda *a, **k: (_ for _ in ()).throw(AssertionError("active health probe")))
    monkeypatch.setattr("services.map_service.provider_observations", ProviderObservations())
    result = get_google_health(force_refresh=True, before_provider_probe=lambda: (_ for _ in ()).throw(AssertionError("analysis budget")))
    assert result["mode"] == "configured"
    assert result["geocoding_enabled"] is None
    assert result["places_enabled"] is None
    assert result["provider_status"] == "not_checked"
    assert "private-key" not in json.dumps(result)


def test_recent_actual_failures_do_not_erase_another_capability():
    from services.provider_observability import ProviderObservations
    registry = ProviderObservations()
    registry.record("routes", status="available", reason_code="success", source="google_routes")
    registry.record("tdx", status="unavailable", reason_code="provider_timeout", source="TDX")
    snapshot = registry.snapshot()
    assert snapshot["routes"]["last_success"]
    assert snapshot["routes"]["status"] == "available"
    assert snapshot["tdx"]["last_failure"]
    assert "all_available" not in snapshot


def test_observation_bounds_and_rejects_untrusted_labels():
    from services.provider_observability import ProviderObservations
    registry = ProviderObservations()
    registry.record("places", status="partial", reason_code="private-secret", source="private-secret")
    snapshot = registry.snapshot()
    assert snapshot["places"]["status"] == "partial"
    assert "private-secret" not in json.dumps(snapshot)


def test_operator_provider_status_is_protected_and_passive(monkeypatch):
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "a" * 40)
    with TestClient(app) as client:
        assert client.get("/provider-status").status_code == 404
        response = client.get("/provider-status", headers={"X-Metrics-Scrape-Token": "a" * 40})
    assert response.status_code == 200
    result = response.json()
    assert result["observation_scope"] == "process_local"
    assert result["external_provider_called"] is False
    assert "all_available" not in result


def test_real_geocoding_failure_replaces_prior_success_and_does_not_keep_green(monkeypatch):
    from services import map_service
    from services.provider_observability import ProviderObservations
    registry = ProviderObservations()
    registry.record("geocoding", status="available", reason_code="success", source="google_geocoding")
    monkeypatch.setattr(map_service, "provider_observations", registry)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "private-key")
    monkeypatch.setattr(map_service.GoogleGeocodingAdapter, "search", lambda *args, **kwargs: None)
    monkeypatch.setattr(map_service.DEFAULT_TGOS_GEOCODING_ADAPTER, "search", lambda *args, **kwargs: None)
    monkeypatch.setattr(map_service.MockGeocodingAdapter, "search", lambda *args, **kwargs: None)
    result = map_service.search_location("nonmatching fixture")
    assert result["matched"] is False
    assert registry.snapshot()["geocoding"]["status"] != "available"
    assert registry.snapshot()["geocoding"]["last_failure"]
    assert map_service.get_google_health()["geocoding_enabled"] is False


def test_tgos_recovery_is_not_google_provider_success(monkeypatch):
    from services import map_service
    from services.provider_observability import ProviderObservations
    registry = ProviderObservations()
    registry.record("geocoding", status="available", reason_code="success", source="tgos_geocoding")
    monkeypatch.setattr(map_service, "provider_observations", registry)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "private-key")
    assert map_service.get_google_health()["geocoding_enabled"] is not True
    assert map_service.get_google_health()["recent_results"]["geocoding"]["source"] == "tgos_geocoding"


def test_valuation_observation_keeps_actual_nested_freshness(monkeypatch):
    from services import provider_observability
    registry = provider_observability.ProviderObservations()
    monkeypatch.setattr(provider_observability, "provider_observations", registry)
    response = {"valuation_status": "available", "valuation_reason_code": "official_result_available", "source_details": {"backend": "green"}, "data_status": {"freshness_status": "stale"}}
    assert provider_observability.observe_response("valuation", response) is response
    assert registry.snapshot()["valuation"]["freshness"] == "stale"
