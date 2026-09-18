"""Map Insight Lite FastAPI endpoint tests."""

import pytest
from fastapi.testclient import TestClient

import backend.api.routes_map as routes_map
from backend.api_main import app
from services.rate_limit import FixedWindowRateLimiter


client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_map_limiter(monkeypatch):
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter())


def test_public_map_search_rejects_after_default_budget(monkeypatch) -> None:
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"query": query})
    for _ in range(30):
        assert client.post("/map/search", json={"query": "address"}).status_code == 200
    rejected = client.post("/map/search", json={"query": "address"})
    assert rejected.status_code == 429
    assert int(rejected.headers["Retry-After"]) > 0


@pytest.mark.parametrize(
    ("path", "payload", "provider_name"),
    [
        ("/map/search", {"query": "address"}, "search_location"),
        ("/map/insight", {"query": "address"}, "get_map_insight"),
        ("/map/nearby", {"lat": 25.03, "lng": 121.53}, "get_nearby_places"),
    ],
)
def test_public_map_rejection_precedes_provider_work(monkeypatch, path, payload, provider_name) -> None:
    calls = []

    def provider(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True}

    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, provider_name, provider)
    assert client.post(path, json=payload).status_code == 200
    rejected = client.post(path, json=payload)
    assert rejected.status_code == 429
    assert int(rejected.headers["Retry-After"]) > 0
    assert len(calls) == 1


def test_malformed_map_request_does_not_consume_budget(monkeypatch) -> None:
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, "get_nearby_places", lambda *args, **kwargs: {"ok": True})
    assert client.post("/map/nearby", json={"lat": 999, "lng": 0}).status_code == 422
    assert client.post("/map/nearby", json={"lat": 25.03, "lng": 121.53}).status_code == 200
    assert client.post("/map/nearby", json={"lat": 25.03, "lng": 121.53}).status_code == 429


def test_three_provider_routes_share_one_budget(monkeypatch) -> None:
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    monkeypatch.setattr(routes_map, "get_map_insight", lambda query: {"ok": True})
    assert client.post("/map/search", json={"query": "address"}).status_code == 200
    assert client.post("/map/insight", json={"query": "address"}).status_code == 429


@pytest.mark.parametrize(
    ("header", "spoofed_value"),
    [
        ("X-Forwarded-For", "203.0.113.9"),
        ("X-Real-IP", "203.0.113.9"),
        ("Forwarded", "for=203.0.113.9"),
    ],
)
def test_forwarded_headers_cannot_select_fresh_key(monkeypatch, header, spoofed_value) -> None:
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    assert client.post("/map/search", json={"query": "address"}).status_code == 200
    rejected = client.post("/map/search", json={"query": "address"}, headers={header: spoofed_value})
    assert rejected.status_code == 429


def test_distinct_direct_peers_have_separate_budgets(monkeypatch) -> None:
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    first_peer = TestClient(app, client=("198.51.100.4", 12345))
    second_peer = TestClient(app, client=("198.51.100.5", 12345))
    assert first_peer.post("/map/search", json={"query": "address"}).status_code == 200
    assert first_peer.post("/map/search", json={"query": "address"}).status_code == 429
    assert second_peer.post("/map/search", json={"query": "address"}).status_code == 200


def test_limiter_internal_failure_fails_open(monkeypatch, caplog) -> None:
    class BrokenLimiter:
        def check(self, key):
            raise RuntimeError("limiter unavailable")

    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", BrokenLimiter())
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    assert client.post("/map/search", json={"query": "address"}).status_code == 200
    assert "rate_limiter_failed_open" in caplog.text


def test_invalid_limiter_decision_fails_open(monkeypatch) -> None:
    class BadDecisionLimiter:
        def check(self, key):
            return object()

    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", BadDecisionLimiter())
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    assert client.post("/map/search", json={"query": "address"}).status_code == 200


def test_metadata_without_provider_work_does_not_consume_map_budget(monkeypatch) -> None:
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    assert client.get("/map/regions").status_code == 200
    assert client.get("/map/poi-categories").status_code == 200
    assert client.post("/map/search", json={"query": "address"}).status_code == 200
    assert client.post("/map/search", json={"query": "address"}).status_code == 429


@pytest.mark.parametrize("raw", ["garbage", "0", "-2", ""])
def test_invalid_env_values_use_default_budget(monkeypatch, raw) -> None:
    monkeypatch.setenv(routes_map.PUBLIC_MAP_RATE_LIMIT_REQUESTS_ENV, raw)
    monkeypatch.setenv(routes_map.PUBLIC_MAP_RATE_LIMIT_WINDOW_SECONDS_ENV, raw)
    limiter = routes_map._build_map_rate_limiter()
    assert limiter.limit == 30
    assert limiter.window_seconds == 60


def test_oversized_env_values_are_clamped(monkeypatch) -> None:
    monkeypatch.setenv(routes_map.PUBLIC_MAP_RATE_LIMIT_REQUESTS_ENV, "10000000")
    monkeypatch.setenv(routes_map.PUBLIC_MAP_RATE_LIMIT_WINDOW_SECONDS_ENV, "10000000")
    limiter = routes_map._build_map_rate_limiter()
    assert limiter.limit == 100_000
    assert limiter.window_seconds == 3_600


def test_map_metadata_endpoints() -> None:
    assert client.get("/map/regions").status_code == 200
    assert client.get("/map/poi-categories").status_code == 200


def test_google_health_without_key_returns_mock(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.setattr("services.map_service.GOOGLE_HEALTH_CACHE", None)
    payload = client.get("/map/google-health").json()
    assert payload["google_key_configured"] is False
    assert payload["mode"] == "mock"


def _install_live_google_health_fakes(monkeypatch):
    """Replace only the external probes while keeping cache and route real."""

    import services.map_service as map_service

    events = []

    class Geocoding:
        available = True
        last_error = ""

        def search(self, query, regions):
            events.append("geocoding")
            return {"id": "resolved"}

    class Places:
        def nearby(self, *args):
            events.append("places")
            return []

    monkeypatch.setattr(map_service, "GoogleGeocodingAdapter", Geocoding)
    monkeypatch.setattr(map_service, "GooglePlacesAdapter", Places)
    monkeypatch.setattr(map_service, "GOOGLE_HEALTH_CACHE", None)
    return map_service, events


def test_google_health_limits_only_live_probe_before_provider_work(monkeypatch) -> None:
    map_service, events = _install_live_google_health_fakes(monkeypatch)
    limiter = FixedWindowRateLimiter(limit=1)

    class RecordingLimiter:
        def check(self, key):
            events.append("limiter")
            return limiter.check(key)

    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", RecordingLimiter())
    first = client.get("/map/google-health")
    assert first.status_code == 200
    assert first.json()["mode"] == "google"
    assert events == ["limiter", "geocoding", "places"]

    cached = client.get("/map/google-health")
    assert cached.status_code == 200
    assert cached.json() == first.json()
    assert events == ["limiter", "geocoding", "places"]

    monkeypatch.setattr(map_service, "GOOGLE_HEALTH_CACHE", None)
    rejected = client.get("/map/google-health")
    assert rejected.status_code == 429
    assert int(rejected.headers["Retry-After"]) > 0
    assert events == ["limiter", "geocoding", "places", "limiter"]


@pytest.mark.parametrize(
    ("header", "spoofed_value"),
    [
        ("X-Forwarded-For", "203.0.113.9"),
        ("X-Real-IP", "203.0.113.9"),
        ("Forwarded", "for=203.0.113.9"),
    ],
)
def test_google_health_spoofed_header_cannot_reset_live_probe_budget(monkeypatch, header, spoofed_value) -> None:
    map_service, events = _install_live_google_health_fakes(monkeypatch)
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    assert client.get("/map/google-health").status_code == 200
    monkeypatch.setattr(map_service, "GOOGLE_HEALTH_CACHE", None)
    rejected = client.get("/map/google-health", headers={header: spoofed_value})
    assert rejected.status_code == 429
    assert events == ["geocoding", "places"]


def test_google_health_without_key_does_not_spend_budget_or_probe(monkeypatch) -> None:
    import services.map_service as map_service

    class DenyLimiter:
        calls = 0

        def check(self, key):
            self.calls += 1
            return type("Decision", (), {"allowed": False, "retry_after_seconds": 5})()

    def unexpected_provider(*args, **kwargs):
        raise AssertionError("No Google key: provider probe must not run")

    limiter = DenyLimiter()
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.setattr(map_service, "GOOGLE_HEALTH_CACHE", None)
    monkeypatch.setattr(map_service.GoogleGeocodingAdapter, "search", unexpected_provider)
    monkeypatch.setattr(map_service.GooglePlacesAdapter, "nearby", unexpected_provider)
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", limiter)
    response = client.get("/map/google-health")
    assert response.status_code == 200
    assert response.json()["mode"] == "mock"
    assert limiter.calls == 0


def test_google_health_live_probe_shares_post_route_budget(monkeypatch) -> None:
    _, events = _install_live_google_health_fakes(monkeypatch)
    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", FixedWindowRateLimiter(limit=1))
    monkeypatch.setattr(routes_map, "search_location", lambda query: {"ok": True})
    assert client.post("/map/search", json={"query": "address"}).status_code == 200
    rejected = client.get("/map/google-health")
    assert rejected.status_code == 429
    assert int(rejected.headers["Retry-After"]) > 0
    assert events == []


def test_google_health_limiter_failure_fails_open(monkeypatch, caplog) -> None:
    _, events = _install_live_google_health_fakes(monkeypatch)

    class BrokenLimiter:
        def check(self, key):
            raise RuntimeError("limiter unavailable")

    monkeypatch.setattr(routes_map, "_MAP_RATE_LIMITER", BrokenLimiter())
    response = client.get("/map/google-health")
    assert response.status_code == 200
    assert events == ["geocoding", "places"]
    assert "rate_limiter_failed_open" in caplog.text


def test_map_search_and_insight_endpoints() -> None:
    payload = {"query": "台北市大安區和平東路二段"}
    search = client.post("/map/search", json=payload)
    insight = client.post("/map/insight", json=payload)
    assert search.status_code == 200
    assert search.json()["matched"] is True
    assert search.json()["source_chain"] == ["google_geocoding", "tgos_geocoding", "mock"]
    assert insight.status_code == 200
    assert insight.json()["source"] == "mock"


def test_map_search_can_feed_nearby_mock_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    # Disable the module-level cached Google adapters to force mock path
    import services.map_service as _map_svc
    from services.adapters.google_places_adapter import GooglePlacesAdapter
    monkeypatch.setattr(_map_svc, "DEFAULT_GOOGLE_PLACES_ADAPTER", GooglePlacesAdapter(api_key=""))
    search = client.post("/map/search", json={"query": "台北市大安區和平東路二段"})
    assert search.json()["source"] == "mock"
    center = search.json()["center"]
    nearby = client.post(
        "/map/nearby",
        json={
            "lat": center["lat"],
            "lng": center["lng"],
            "radius_m": 800,
            "categories": ["transport", "school", "park", "medical", "shopping", "food"],
            "language_code": "zh-TW",
        },
    )
    assert nearby.status_code == 200
    payload = nearby.json()
    assert payload["source"] == "mock"
    assert len(payload["categories"]) == 6
    assert 0 <= payload["livability_score"] <= 100
    assert all(0 <= item["score"] <= 100 for item in payload["category_scores"])
    assert payload["livability_level"] in {"極佳", "良好", "普通", "偏弱", "不足"}
    assert all({"level", "poi_count", "nearest_distance_m", "explanation"} <= set(item) for item in payload["category_scores"])
    assert len(payload["nearest_places"]) == 3
    assert payload["recommendation_text"]
    assert payload["scoring_criteria"]["radius_m"] == 800
