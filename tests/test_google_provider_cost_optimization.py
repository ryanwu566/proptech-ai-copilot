"""Deterministic physical Google-call budgets; no live provider traffic."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Barrier, Event, Lock, current_thread

import httpx
import pytest

from services import commute_routing_service as routes
from services import location_resolver
from services.adapters.geocoding_adapter import GoogleGeocodingAdapter
from services.adapters.google_places_adapter import GooglePlacesAdapter
from services.adapters.routes_adapter import GoogleRoutesAdapter
from services.map_service import get_nearby_places
from services.provider_cost_metrics import PROVIDER_COST_METRICS


ORIGIN = (25.033, 121.5654)
DESTINATION = (25.0478, 121.517)
GEOCODE = {"status": "OK", "results": [{"place_id": "a", "formatted_address": "Taipei Road 1", "types": ["street_address"], "geometry": {"location": {"lat": ORIGIN[0], "lng": ORIGIN[1]}, "location_type": "ROOFTOP"}, "address_components": []}]}
ROUTE = {"routes": [{"duration": "900s", "distanceMeters": 4000}]}


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class PhysicalCalls:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
        self.headers = None
        self.error = None
        self.started = Event()
        self.second_arrived = Event()
        self.release = Event()
        self.release.set()
        self.lock = Lock()

    def post(self, *args, **kwargs):
        with self.lock:
            self.calls += 1
            self.headers = kwargs.get("headers")
            if self.calls > 1:
                self.second_arrived.set()
        self.started.set()
        assert self.release.wait(5), "physical provider test was not released"
        if self.error:
            raise self.error
        return Response(self.payload)


def concurrent_pair(monkeypatch, calls, action):
    """Wait for physical duplicate OR a cache Future waiter, without sleep races."""
    original_result = Future.result

    def observe_waiter(future, *args, **kwargs):
        if current_thread().name.startswith("google-cost") and not future.done():
            calls.second_arrived.set()
        return original_result(future, *args, **kwargs)

    monkeypatch.setattr(Future, "result", observe_waiter)
    calls.release.clear()
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="google-cost") as executor:
        first = executor.submit(action)
        assert calls.started.wait(5)
        second = executor.submit(action)
        try:
            assert calls.second_arrived.wait(5), "second request did not enter provider/cache"
        finally:
            calls.release.set()
        return first.result(5), second.result(5)


def test_geocoding_concurrent_physical_call_budget(monkeypatch):
    calls = PhysicalCalls(GEOCODE)
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", calls.post)
    adapter = GoogleGeocodingAdapter(api_key="test")
    first, second = concurrent_pair(monkeypatch, calls, lambda: adapter.search("Taipei Road 1", []))
    assert first == second
    assert calls.calls == 1


def test_places_concurrent_physical_call_budget(monkeypatch):
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    first, second = concurrent_pair(monkeypatch, calls, lambda: adapter.nearby(*ORIGIN, 800, "food"))
    assert first == second == []
    assert calls.calls == 1


def test_routes_concurrent_physical_call_budget(monkeypatch):
    routes.clear_route_cache()
    calls = PhysicalCalls(ROUTE)
    adapter = GoogleRoutesAdapter(api_key="test", client=calls)
    action = lambda: routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter, allow_mock=False)
    first, second = concurrent_pair(monkeypatch, calls, action)
    assert first["duration_seconds"] == second["duration_seconds"] == 900
    assert calls.calls == 1
    routes.clear_route_cache()


def test_places_duplicate_category_dispatch_budget():
    class Categories:
        available = True

        def __init__(self):
            self.calls = []
            self.lock = Lock()

        def nearby(self, lat, lng, radius, category, language):
            with self.lock:
                self.calls.append(category)
            return []

    adapter = Categories()
    result = get_nearby_places(*ORIGIN, 800, ["food", "food", "park"], adapter=adapter)
    assert result["source"] == "google_places"
    assert len(adapter.calls) == 2


def test_existing_sequential_places_and_routes_cache_baseline():
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    for _ in range(2):
        adapter.nearby(*ORIGIN, 800, "food")
    assert calls.calls == 1
    routes.clear_route_cache()
    route_calls = PhysicalCalls(ROUTE)
    google = GoogleRoutesAdapter(api_key="test", client=route_calls)
    for _ in range(2):
        routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google)
    assert route_calls.calls == 1
    routes.clear_route_cache()


def test_places_material_key_changes_never_share_observations():
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    adapter.nearby(*ORIGIN, 800, "food")
    adapter.nearby(ORIGIN[0] + 0.000001, ORIGIN[1], 800, "food")
    adapter.nearby(*ORIGIN, 900, "food")
    adapter.nearby(*ORIGIN, 800, "food", "en")
    adapter.nearby(*ORIGIN, 800, "park")
    assert calls.calls == 5


def test_route_nearby_coordinates_and_provider_change_invalidate():
    routes.clear_route_cache()
    calls = PhysicalCalls(ROUTE)
    adapter = GoogleRoutesAdapter(api_key="test", client=calls)
    routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter)
    routes.estimate_commute_route((ORIGIN[0] + 0.000001, ORIGIN[1]), DESTINATION, "transit", google_adapter=adapter)
    assert calls.calls == 2
    other = PhysicalCalls({"routes": [{"duration": "1200s", "distanceMeters": 5000}]})
    changed_provider = GoogleRoutesAdapter(api_key="test-other", client=other)
    result = routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=changed_provider)
    assert other.calls == 1
    assert result["duration_seconds"] == 1200
    routes.clear_route_cache()


def test_geocoding_reason_codes_are_request_local(monkeypatch):
    finished = Barrier(2)

    def fetch(url, *, params, **kwargs):
        if params["address"] == "timeout":
            raise httpx.TimeoutException("private")
        return Response(GEOCODE)

    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", fetch)
    adapter = GoogleGeocodingAdapter(api_key="test")

    def search(query):
        result = adapter.search(query, [])
        finished.wait(5)
        return result, adapter.last_reason_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        success = executor.submit(search, "success")
        timeout = executor.submit(search, "timeout")
        assert success.result(5)[1] == "success"
        assert timeout.result(5) == (None, "provider_timeout")


def test_geocoding_does_not_retain_finished_provider_payload(monkeypatch):
    calls = PhysicalCalls(GEOCODE)
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", calls.post)
    adapter = GoogleGeocodingAdapter(api_key="test")
    assert adapter.search("Taipei Road 1", []) is not None
    assert adapter.search("Taipei Road 1", []) is not None
    assert calls.calls == 2


def test_places_failure_cleanup_and_recovery():
    calls = PhysicalCalls({"places": []})
    calls.error = httpx.TimeoutException("private")
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    with pytest.raises(httpx.TimeoutException):
        adapter.nearby(*ORIGIN, 800, "food")
    calls.error = None
    assert adapter.nearby(*ORIGIN, 800, "food") == []
    assert adapter.nearby(*ORIGIN, 800, "food") == []
    assert calls.calls == 2


def test_route_failure_is_not_stored_and_recovery_is_cached():
    routes.clear_route_cache()
    calls = PhysicalCalls(ROUTE)
    calls.error = httpx.TimeoutException("private")
    adapter = GoogleRoutesAdapter(api_key="test", client=calls)
    first = routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter, allow_mock=False)
    assert first["status"] == "unavailable"
    calls.error = None
    recovered = routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter, allow_mock=False)
    again = routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter, allow_mock=False)
    assert recovered == again
    assert recovered["status"] == "resolved"
    assert calls.calls == 2
    routes.clear_route_cache()


def test_commute_google_destination_resolution_concurrent_budget(monkeypatch):
    calls = PhysicalCalls(GEOCODE)
    monkeypatch.setattr("services.location_resolver.httpx.get", calls.post)
    google = location_resolver.GoogleAddressProvider(api_key="test")
    first, second = concurrent_pair(monkeypatch, calls, lambda: google.resolve("Taipei Road 1"))
    assert first == second
    assert first.status == "resolved"
    assert calls.calls == 1


def test_places_whole_fanout_shares_partial_and_retries_only_failed_category(monkeypatch):
    calls = PhysicalCalls({"places": []})
    physical_post = calls.post
    by_category = {}
    category_lock = Lock()

    def post(url, *, json, headers):
        category = json["includedTypes"][0]
        with category_lock:
            by_category[category] = by_category.get(category, 0) + 1
        response = physical_post(url, json=json, headers=headers)
        if category == "school":
            raise httpx.TimeoutException("private")
        return response

    calls.post = post
    # Provider's second category must not be confused with the second logical
    # caller. Signal the outer fan-out wait via the fixed-label metrics instead.
    entered = Event()
    record = PROVIDER_COST_METRICS.record

    def observe(capability, event, count=1):
        if capability == "places_request" and event == "coalesced":
            entered.set()
        return record(capability, event, count)

    monkeypatch.setattr(PROVIDER_COST_METRICS, "record", observe)
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    calls.release.clear()
    action = lambda: get_nearby_places(*ORIGIN, 800, ["school", "park", "park"], adapter=adapter)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(action)
        assert calls.started.wait(5)
        second = executor.submit(action)
        try:
            assert entered.wait(5)
        finally:
            calls.release.set()
        result, shared = first.result(5), second.result(5)
    assert result == shared
    assert result["source"] == "google_places"
    assert result["partial"] is True
    assert result["failed_categories"] == ["school"]
    assert result["category_status"]["school"]["status"] == "error"
    assert result["category_status"]["park"]["status"] == "available"
    assert result["categories"][0]["count"] == 0
    assert by_category == {"school": 1, "park": 1}
    retried = action()
    assert retried["partial"] is True
    assert by_category == {"school": 2, "park": 1}
    assert retried["checked_at"] == result["checked_at"]


def test_places_cache_preserves_observation_time_and_evicts_expires(monkeypatch):
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    now = [0.0]
    adapter._cache.clock = lambda: now[0]
    adapter._cache.max_entries = 2
    first = get_nearby_places(*ORIGIN, 800, ["food"], adapter=adapter)
    second = get_nearby_places(*ORIGIN, 800, ["food"], adapter=adapter)
    assert first["checked_at"] == second["checked_at"]
    assert calls.calls == 1
    adapter.nearby(*ORIGIN, 801, "food")
    adapter.nearby(*ORIGIN, 802, "food")
    adapter.nearby(*ORIGIN, 800, "food")
    assert calls.calls == 4  # LRU-evicted initial query invokes Google again.
    now[0] = 601
    adapter.nearby(*ORIGIN, 800, "food")
    assert calls.calls == 5


def test_places_field_mask_matches_existing_ui_evidence_consumers():
    calls = PhysicalCalls({"places": []})
    GooglePlacesAdapter(api_key="test", client=calls).nearby(*ORIGIN, 800, "food")
    fields = set(calls.headers["X-Goog-FieldMask"].split(","))
    assert fields == {"places.id", "places.displayName", "places.location", "places.formattedAddress", "places.rating", "places.userRatingCount", "places.businessStatus", "places.currentOpeningHours.openNow", "places.regularOpeningHours.periods", "places.types"}


def test_routes_cache_expiry_eviction_and_observation_time(monkeypatch):
    routes.clear_route_cache()
    calls = PhysicalCalls(ROUTE)
    adapter = GoogleRoutesAdapter(api_key="test", client=calls)
    now = [0.0]
    monkeypatch.setattr(routes._cache, "clock", lambda: now[0])
    monkeypatch.setattr(routes._cache, "max_entries", 2)
    action = lambda destination: routes.estimate_commute_route(ORIGIN, destination, "driving", google_adapter=adapter, allow_mock=False)
    first = action(DESTINATION)
    assert action(DESTINATION) == first
    assert calls.calls == 1
    action((25.1, 121.6))
    action((25.2, 121.6))
    action(DESTINATION)
    assert calls.calls == 4
    now[0] = 601
    action(DESTINATION)
    assert calls.calls == 5
    routes.clear_route_cache()


def test_places_configuration_version_changes_key(monkeypatch):
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    adapter.nearby(*ORIGIN, 800, "food")
    monkeypatch.setattr("services.adapters.google_places_adapter.FIELD_MASK", "places.id,places.types")
    adapter.nearby(*ORIGIN, 800, "food")
    assert calls.calls == 2


def test_routes_configuration_version_changes_key(monkeypatch):
    routes.clear_route_cache()
    calls = PhysicalCalls(ROUTE)
    adapter = GoogleRoutesAdapter(api_key="test", client=calls)
    action = lambda: routes.estimate_commute_route(ORIGIN, DESTINATION, "walking", google_adapter=adapter, allow_mock=False)
    action()
    monkeypatch.setattr("services.adapters.routes_adapter.FIELD_MASK", "routes.duration,routes.distanceMeters,another-option")
    action()
    assert calls.calls == 2
    routes.clear_route_cache()


def test_places_malformed_response_is_not_cached_as_successful_zero():
    calls = PhysicalCalls({"error": {"message": "private"}})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    with pytest.raises(ValueError):
        adapter.nearby(*ORIGIN, 800, "food")
    calls.payload = {"places": []}
    assert adapter.nearby(*ORIGIN, 800, "food") == []
    assert calls.calls == 2


@pytest.mark.parametrize("capability", ["geocoding", "places", "routes"])
def test_concurrent_failure_waiters_share_error_and_retry_cleanly(monkeypatch, capability):
    calls = PhysicalCalls({"places": []})
    calls.error = httpx.TimeoutException("private")
    if capability == "geocoding":
        calls.payload = GEOCODE
        monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", calls.post)
        adapter = GoogleGeocodingAdapter(api_key="test")

        def action():
            value = adapter.search("Taipei Road 1", [])
            return value, adapter.last_reason_code

    elif capability == "places":
        adapter = GooglePlacesAdapter(api_key="test", client=calls)

        def action():
            try:
                return adapter.nearby(*ORIGIN, 800, "food")
            except httpx.TimeoutException:
                return "provider_timeout"

    else:
        routes.clear_route_cache()
        calls.payload = ROUTE
        adapter = GoogleRoutesAdapter(api_key="test", client=calls)
        action = lambda: routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter, allow_mock=False)
    first, second = concurrent_pair(monkeypatch, calls, action)
    assert first == second
    assert calls.calls == 1
    calls.error = None
    result = action()
    assert calls.calls == 2
    if capability == "geocoding":
        assert result[1] == "success"
    elif capability == "places":
        assert result == []
    else:
        assert result["status"] == "resolved"
        routes.clear_route_cache()


def test_geocoding_map_entrypoint_shares_default_adapter_without_cached_payload(monkeypatch):
    from services import map_service

    calls = PhysicalCalls(GEOCODE)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test")
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", calls.post)
    monkeypatch.setattr(map_service.DEFAULT_TGOS_GEOCODING_ADAPTER, "search", lambda *args: None)
    action = lambda: map_service.search_location("Taipei Road 1")
    first, second = concurrent_pair(monkeypatch, calls, action)
    assert first["center"] == second["center"]
    assert calls.calls == 1
    action()
    assert calls.calls == 2


def test_routes_cache_keys_do_not_retain_credential_bearing_adapters():
    routes.clear_route_cache()
    adapter = GoogleRoutesAdapter(api_key="private-key", client=PhysicalCalls(ROUTE))
    routes.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=adapter, allow_mock=False)
    for key in routes._cache._entries:
        assert all(not isinstance(part, GoogleRoutesAdapter) for part in key)
        assert "private-key" not in repr(key)
    routes.clear_route_cache()


def test_geocoding_provider_recovery_logs_never_include_address(monkeypatch, caplog):
    from services import map_service

    private_address = "Private Address Road 123"
    calls = PhysicalCalls(GEOCODE)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test")
    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", calls.post)
    monkeypatch.setattr(map_service.DEFAULT_TGOS_GEOCODING_ADAPTER, "search", lambda *args: None)
    with caplog.at_level("INFO", logger="services.map_service"):
        map_service.search_location(private_address)
    assert private_address not in caplog.text


def test_route_accepted_coordinate_endpoints_bypass_address_resolution(monkeypatch):
    from backend.api import routes_commute
    from backend.api_main import app
    from fastapi.testclient import TestClient

    geocoding_calls = []

    def forbidden_resolution(address):
        geocoding_calls.append(address)
        raise AssertionError("accepted route coordinates must bypass geocoding")

    calls = PhysicalCalls(ROUTE)
    monkeypatch.setattr(routes_commute.location_resolver, "resolve_address", forbidden_resolution)
    monkeypatch.setattr(routes, "_DEFAULT_GOOGLE_ADAPTER", GoogleRoutesAdapter(api_key="test", client=calls))
    routes.clear_route_cache()
    body = {"origin_latitude": ORIGIN[0], "origin_longitude": ORIGIN[1], "destination_latitude": DESTINATION[0], "destination_longitude": DESTINATION[1], "mode": "transit"}
    with TestClient(app) as client:
        first = client.post("/commute/route", json=body)
        second = client.post("/commute/route", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "resolved"
    assert second.json() == first.json()
    assert geocoding_calls == []
    assert calls.calls == 1
    routes.clear_route_cache()


def test_destination_address_reuse_avoids_all_resolution_and_changed_address_isolated(monkeypatch):
    from backend.api_main import app
    from fastapi.testclient import TestClient

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-destination-context")
    monkeypatch.setenv("TGOS_APP_ID", "test")
    monkeypatch.setenv("TGOS_API_KEY", "test")
    tgos_calls = []
    google_calls = []

    def tgos(provider, address):
        tgos_calls.append(address)
        return location_resolver.LocationResolveResult(status="unavailable")

    def geocode(url, *, params, **kwargs):
        google_calls.append(params["address"])
        latitude = DESTINATION[0] + (0.01 if params["address"].endswith("2") else 0)
        return Response({"status": "OK", "results": [{"formatted_address": params["address"], "geometry": {"location": {"lat": latitude, "lng": DESTINATION[1]}}}]})

    calls = PhysicalCalls(ROUTE)
    monkeypatch.setattr(location_resolver.TgosAddressProvider, "resolve", tgos)
    monkeypatch.setattr(location_resolver.httpx, "get", geocode)
    monkeypatch.setattr(routes, "_DEFAULT_GOOGLE_ADAPTER", GoogleRoutesAdapter(api_key="test", client=calls))
    routes.clear_route_cache()
    body = {"origin_latitude": ORIGIN[0], "origin_longitude": ORIGIN[1], "destination_address": "Taipei Road 1", "mode": "transit"}
    with TestClient(app) as client:
        first = client.post("/commute/route", json=body)
        second = client.post("/commute/route", json=body)
        changed = client.post("/commute/route", json={**body, "destination_address": "Taipei Road 2"})
    assert first.status_code == second.status_code == changed.status_code == 200
    assert first.json() == second.json()
    assert changed.json()["status"] == "resolved"
    assert tgos_calls == ["Taipei Road 1", "Taipei Road 2"]
    assert google_calls == ["Taipei Road 1", "Taipei Road 2"]
    assert calls.calls == 2
    routes.clear_route_cache()


@pytest.mark.parametrize("payload", [{"error": {"message": "private"}}, {"routes": {}}, {"routes": None}, {}])
def test_routes_malformed_shape_is_unavailable_and_never_cached_as_no_route(payload):
    routes.clear_route_cache()
    calls = PhysicalCalls(payload)
    adapter = GoogleRoutesAdapter(api_key="test", client=calls)
    action = lambda: routes.estimate_commute_route(ORIGIN, DESTINATION, "walking", google_adapter=adapter, allow_mock=False)
    first = action()
    second = action()
    assert first["status"] == second["status"] == "unavailable"
    assert first["reason_code"] == "malformed_response"
    assert calls.calls == 2
    calls.payload = ROUTE
    assert action()["status"] == "resolved"
    assert calls.calls == 3
    routes.clear_route_cache()


@pytest.mark.parametrize("row", [{}, {"id": "p", "types": ["cafe"]}, {"id": "p", "location": {"latitude": 25.0, "longitude": 121.0}}, {"id": "p", "types": ["cafe"], "location": {"latitude": True, "longitude": 121.0}}])
def test_places_unverifiable_rows_never_become_cached_successful_zero(row):
    calls = PhysicalCalls({"places": [row]})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    for _ in range(2):
        with pytest.raises(ValueError):
            adapter.nearby(*ORIGIN, 800, "food")
    assert calls.calls == 2
    calls.payload = {"places": []}
    assert adapter.nearby(*ORIGIN, 800, "food") == []
    assert calls.calls == 3


def test_places_valid_omitted_empty_collection_remains_successful_zero():
    calls = PhysicalCalls({})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    assert adapter.nearby(*ORIGIN, 800, "food") == []
    assert adapter.nearby(*ORIGIN, 800, "food") == []
    assert calls.calls == 1


def test_accepted_destination_cache_bounds_expiry_failures_and_configuration(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-derived-context")
    monkeypatch.setenv("TGOS_APP_ID", "test")
    monkeypatch.setenv("TGOS_API_KEY", "test")
    monkeypatch.setattr(location_resolver.TgosAddressProvider, "resolve", lambda *args: location_resolver.LocationResolveResult(status="unavailable"))
    cache = location_resolver._RESOLVED_ADDRESS_CACHE
    cache.clear()
    now = [0.0]
    monkeypatch.setattr(cache, "clock", lambda: now[0])
    monkeypatch.setattr(cache, "max_entries", 2)
    calls = PhysicalCalls(GEOCODE)
    monkeypatch.setattr(location_resolver.httpx, "get", calls.post)
    calls.error = httpx.TimeoutException("private")
    assert location_resolver.resolve_address("address A")["status"] == "unavailable"
    calls.error = None
    first = location_resolver.resolve_address("address A")
    assert first["status"] == "resolved"
    assert set(first) == location_resolver.SAFE_RESPONSE_KEYS
    assert location_resolver.resolve_address("address A") == first
    assert calls.calls == 2
    location_resolver.resolve_address("address B")
    location_resolver.resolve_address("address C")
    location_resolver.resolve_address("address A")
    assert calls.calls == 5
    now[0] = 61
    location_resolver.resolve_address("address A")
    assert calls.calls == 6
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "changed-derived-context")
    location_resolver.resolve_address("address A")
    assert calls.calls == 7
    monkeypatch.setattr(location_resolver, "ADDRESS_RESOLVER_VERSION", "trusted-address-resolution-v2")
    location_resolver.resolve_address("address A")
    assert calls.calls == 8
    cache.clear()


def test_six_unique_places_categories_keep_bounded_fanout_on_repeat():
    from services.map_service import CATEGORY_LABELS

    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="test", client=calls)
    first = get_nearby_places(*ORIGIN, 800, list(CATEGORY_LABELS), adapter=adapter)
    assert calls.calls == 6
    second = get_nearby_places(*ORIGIN, 800, [*CATEGORY_LABELS, "food"], adapter=adapter)
    assert calls.calls == 6
    assert first["checked_at"] == second["checked_at"]
    assert len(second["categories"]) == 6
    assert second["partial"] is False


def test_route_cache_does_not_keep_custom_credential_adapter_alive():
    import gc
    import weakref

    class CustomProvider:
        available = True

        def __init__(self):
            self.api_key = "private-custom-credential"

        def compute_route(self, origin, destination, mode):
            return {"duration_seconds": 900, "distance_m": 4000, "mode": mode, "source": "google_routes"}

    routes.clear_route_cache()
    adapter = CustomProvider()
    reference = weakref.ref(adapter)
    first = routes.estimate_commute_route(ORIGIN, DESTINATION, "walking", google_adapter=adapter, allow_mock=False)
    assert first["status"] == "resolved"
    del adapter
    gc.collect()
    assert reference() is None
    for key in routes._cache._entries:
        assert all(not isinstance(part, CustomProvider) for part in key)
        assert "private-custom-credential" not in repr(key)
    routes.clear_route_cache()


def test_unweakrefable_custom_route_provider_bypasses_cache():
    class CustomProvider:
        __slots__ = ("calls",)
        available = True

        def __init__(self):
            self.calls = 0

        def compute_route(self, origin, destination, mode):
            self.calls += 1
            return {"duration_seconds": 900, "distance_m": 4000, "mode": mode, "source": "google_routes"}

    routes.clear_route_cache()
    adapter = CustomProvider()
    for _ in range(2):
        assert routes.estimate_commute_route(ORIGIN, DESTINATION, "walking", google_adapter=adapter, allow_mock=False)["status"] == "resolved"
    assert adapter.calls == 2
    assert not routes._cache._entries
    routes.clear_route_cache()
