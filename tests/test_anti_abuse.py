"""Offline regression tests for process-local admission and physical work guards."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.anti_abuse import AbuseControls, AbuseRejected, Policy, provider_operation
from backend.api.abuse_middleware import AbuseMiddleware


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


def controls(clock=None):
    return AbuseControls({name: Policy(2, 60, 1, 2, 60) for name in ("places", "routes", "satellite")}, clock=clock or Clock())


def test_request_boundary_window_and_independence():
    clock = Clock()
    guard = controls(clock)
    guard.admit("places", "peer")
    guard.admit("places", "peer")
    with pytest.raises(AbuseRejected) as error:
        guard.admit("places", "peer")
    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "60"}
    guard.admit("routes", "peer")
    clock.now += 60
    guard.admit("places", "peer")


def test_atomic_concurrency_and_exception_recovery():
    guard = controls()
    with guard.operation("places"):
        with pytest.raises(AbuseRejected) as error:
            with guard.operation("places"):
                pytest.fail("excess work admitted")
        assert error.value.detail["reason_code"] == "capacity_exhausted"
        with guard.operation("routes"):
            pass
    with pytest.raises(TimeoutError):
        with guard.operation("places"):
            raise TimeoutError()
    with pytest.raises(AbuseRejected) as error:
        with guard.operation("places"):
            pytest.fail("exhausted budget admitted")
    assert error.value.detail["reason_code"] == "provider_budget_exhausted"


def test_atomic_requests_many_keys_and_independent_instances():
    guard = controls()
    def admit(_):
        try:
            guard.admit("places", "peer")
            return True
        except AbuseRejected:
            return False
    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(admit, range(100))) == 2
    for index in range(10000):
        try:
            guard.admit("routes", str(index))
        except AbuseRejected:
            pass
    assert guard.request_limiters["routes"].tracked_key_count() <= 4096
    controls().admit("places", "peer")  # cold start / another process has fresh state


def test_kill_switch_and_budget_precede_work(monkeypatch):
    guard = controls()
    monkeypatch.setenv("ANTI_ABUSE_PLACES_DISABLED", "true")
    with pytest.raises(AbuseRejected) as error:
        with guard.operation("places"):
            pytest.fail("disabled work ran")
    assert error.value.status_code == 503
    assert error.value.detail["reason_code"] == "capability_disabled"
    with guard.operation("routes"):
        pass


def test_async_cancel_retains_permit_until_work_stops(monkeypatch):
    guard = controls()
    monkeypatch.setattr("services.anti_abuse.CONTROLS", guard)
    async def scenario():
        started = asyncio.Event()
        finish = asyncio.Event()
        @provider_operation("satellite")
        async def work():
            started.set()
            await finish.wait()
        task = asyncio.create_task(work())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(AbuseRejected):
            with guard.operation("satellite"):
                pass
        finish.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        with guard.operation("satellite"):
            pass
    asyncio.run(scenario())


def test_spoofed_headers_and_health_exemption():
    app = FastAPI()
    guard = controls()
    calls = []
    @app.post("/map/nearby")
    def endpoint():
        calls.append(1)
        return {"ok": True}
    @app.get("/health")
    def health():
        return {"ok": True}
    app.add_middleware(AbuseMiddleware, controls=guard)
    client = TestClient(app)
    for ip in ("1.1.1.1", "2.2.2.2"):
        assert client.post("/map/nearby", headers={"X-Forwarded-For": ip}).status_code == 200
    blocked = client.post("/map/nearby", headers={"Forwarded": "for=3.3.3.3", "X-Real-IP": "4.4.4.4", "X-Client-IP": "5.5.5.5"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) == 60
    assert len(calls) == 2
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("declared", [None, "1", "1000001"])
def test_streamed_oversize_never_reaches_parser_or_work(declared):
    called = []
    async def app(scope, receive, send):
        called.append(True)
    middleware = AbuseMiddleware(app, controls=controls())
    headers = [] if declared is None else [(b"content-length", declared.encode())]
    scope = {"type": "http", "path": "/other", "method": "POST", "headers": headers, "client": None}
    messages = iter([{"type": "http.request", "body": b"x" * 600000, "more_body": True}, {"type": "http.request", "body": b"x" * 600000, "more_body": False}])
    sent = []
    async def receive():
        return next(messages)
    async def send(message):
        sent.append(message)
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["status"] == 413
    assert not called


def test_places_budget_cache_hit_and_no_spend_after_rejection(monkeypatch):
    from services.adapters.google_places_adapter import GooglePlacesAdapter
    from tests.test_google_provider_cost_optimization import PhysicalCalls
    guard = controls()
    monkeypatch.setattr("services.anti_abuse.CONTROLS", guard)
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="fixture", client=calls)
    assert adapter.nearby(25, 121, 800, "food") == []
    assert adapter.nearby(25, 121, 800, "food") == []
    assert calls.calls == 1
    assert adapter.nearby(25, 121, 800, "park") == []
    with pytest.raises(AbuseRejected):
        adapter.nearby(25, 121, 800, "school")
    assert calls.calls == 2


def test_routes_budget_material_keys_and_disabled_no_fallback(monkeypatch):
    from services.adapters.routes_adapter import GoogleRoutesAdapter
    from services import commute_routing_service as routing
    from tests.test_google_provider_cost_optimization import PhysicalCalls, ROUTE
    monkeypatch.setattr("services.anti_abuse.CONTROLS", controls())
    routing.clear_route_cache()
    calls = PhysicalCalls(ROUTE)
    adapter = GoogleRoutesAdapter(api_key="fixture", client=calls)
    def run(dest=(25.1, 121.1), mode="walking"):
        return routing.estimate_commute_route((25, 121), dest, mode, google_adapter=adapter, allow_mock=True)
    assert run()["status"] == "resolved"
    assert run()["status"] == "resolved"
    assert calls.calls == 1
    assert run(mode="driving")["status"] == "resolved"
    with pytest.raises(AbuseRejected):
        run(dest=(25.2, 121.2))
    monkeypatch.setenv("ANTI_ABUSE_ROUTES_DISABLED", "true")
    with pytest.raises(AbuseRejected):
        run()  # even a completed cache result returns an explicit disabled reason
    assert calls.calls == 2


@pytest.mark.parametrize("path,payload", [
    ("/map/search", {"query": "x" * 513}),
    ("/location/resolve", {"address": "x" * 513}),
    ("/map/nearby", {"lat": 25, "lng": 121, "categories": ["food"] * 7}),
    ("/terrain-risk/analyze", {"latitude": 25, "longitude": 121, "include_layers": ["flood"] * 17}),
    ("/commute/route", {"origin_latitude": 25, "origin_longitude": 121, "destination_address": "x" * 513}),
])
def test_bounded_provider_inputs(path, payload, monkeypatch):
    from backend.api_main import app
    monkeypatch.setattr("backend.api.routes_map.search_location", lambda *args: {})
    monkeypatch.setattr("backend.api.routes_map.get_nearby_places", lambda *args: {})
    monkeypatch.setattr("backend.api.routes_terrain_risk.analyze_terrain_risk", lambda **kwargs: {})
    monkeypatch.setattr("backend.api.routes_location_insight.location_resolver.resolve_address", lambda *args: {"status": "unavailable", "source": "none", "confidence": "unknown", "message": "fixture"})
    assert TestClient(app).post(path, json=payload).status_code == 422


def test_places_all_budget_failures_never_fabricate_mock_evidence(monkeypatch):
    from services.adapters.google_places_adapter import GooglePlacesAdapter
    from services.map_service import get_nearby_places
    from tests.test_google_provider_cost_optimization import PhysicalCalls
    guard = controls()
    monkeypatch.setattr("services.anti_abuse.CONTROLS", guard)
    with guard.operation("places"):
        pass
    with guard.operation("places"):
        pass
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="fixture", client=calls)
    with pytest.raises(AbuseRejected):
        get_nearby_places(25, 121, 800, ["food", "park"], adapter=adapter)
    assert calls.calls == 0


def test_geometry_limit_precedes_shapely(monkeypatch):
    from backend.api_main import app
    import services.parcel_geometry as parcel
    calls = []
    monkeypatch.setattr(parcel, "shape", lambda value: calls.append(1))
    body = {"type": "Polygon", "coordinates": [[[121, 25]] * 100001]}
    response = TestClient(app).post("/parcel-geometry/consistency", json={"geometry": body, "latitude": 25, "longitude": 121})
    assert response.status_code in {413, 422}
    assert not calls


def test_satellite_request_limit_and_kill_zero_calls(monkeypatch):
    from backend.api_main import app
    from services.satellite_reference import build_response
    calls = []
    async def generate(**kwargs):
        calls.append(1)
        return build_response(status="unavailable", reason_code="fixture")
    monkeypatch.setattr("backend.api.routes_satellite_reference.fetch_satellite_reference", generate)
    client = TestClient(app)
    payload = {"latitude": 25, "longitude": 121}
    assert client.post("/terrain/satellite-reference", json=payload).status_code == 200
    assert client.post("/terrain/satellite-reference", json=payload).status_code == 200
    rejected = client.post("/terrain/satellite-reference", json=payload)
    assert rejected.status_code == 429
    assert 1 <= int(rejected.headers["Retry-After"]) <= 300
    monkeypatch.setenv("ANTI_ABUSE_SATELLITE_DISABLED", "true")
    assert client.post("/terrain/satellite-reference", json=payload).status_code == 503
    assert client.get("/terrain-risk/sources").status_code == 200
    assert len(calls) == 2


def test_partial_places_budget_is_not_complete_or_zero(monkeypatch):
    from services.adapters.google_places_adapter import GooglePlacesAdapter
    from services.map_service import get_nearby_places
    from tests.test_google_provider_cost_optimization import PhysicalCalls
    guard = AbuseControls({"places": Policy(2, 60, 4, 1)})
    monkeypatch.setattr("services.anti_abuse.CONTROLS", guard)
    calls = PhysicalCalls({"places": []})
    adapter = GooglePlacesAdapter(api_key="fixture", client=calls)
    response = get_nearby_places(25, 121, 800, ["food", "park"], adapter=adapter)
    assert response["partial"] is True
    assert response["fallback"] is False
    assert response["source"] == "google_places"
    assert len(response["failed_categories"]) == 1
    failed = response["failed_categories"][0]
    assert response["category_status"][failed]["reason_code"] == "provider_budget_exhausted"
    assert calls.calls == 1


def test_limiter_failure_releases_operation_permit(monkeypatch):
    guard = controls()
    class Broken:
        def check(self, key):
            raise RuntimeError("secret internal payload")
    original = guard.operation_limiters["places"]
    guard.operation_limiters["places"] = Broken()
    with pytest.raises(AbuseRejected) as error:
        with guard.operation("places"):
            pass
    assert error.value.status_code == 503
    assert "secret" not in str(error.value.detail)
    guard.operation_limiters["places"] = original
    with guard.operation("places"):
        pass


def test_cancellation_during_sync_work_retains_capacity(monkeypatch):
    guard = controls()
    monkeypatch.setattr("services.anti_abuse.CONTROLS", guard)
    started, finish = threading.Event(), threading.Event()
    def blocking():
        started.set()
        assert finish.wait(5)
    async def scenario():
        @provider_operation("satellite")
        async def work():
            await asyncio.to_thread(blocking)
        task = asyncio.create_task(work())
        await asyncio.to_thread(started.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        try:
            with pytest.raises(AbuseRejected):
                with guard.operation("satellite"):
                    pass
        finally:
            finish.set()
        # Wait on producer completion, not an arbitrary timer.
        pending = [item for item in asyncio.all_tasks() if item is not asyncio.current_task()]
        await asyncio.gather(*pending)
        with guard.operation("satellite"):
            pass
    asyncio.run(scenario())


def test_body_capacity_rejects_without_reading_and_health_stays_available(monkeypatch):
    import backend.api.abuse_middleware as middleware_module
    monkeypatch.setattr(middleware_module, "BODY_SLOTS", threading.BoundedSemaphore(0), raising=False)
    app = FastAPI()
    @app.post("/test")
    def write():
        return {"ok": True}
    @app.get("/health")
    def health():
        return {"ok": True}
    app.add_middleware(AbuseMiddleware, controls=controls())
    client = TestClient(app)
    assert client.post("/test", json={}).status_code == 503
    assert client.get("/health").status_code == 200


def test_unauthorized_market_operator_cannot_spend_public_or_operator_work(monkeypatch):
    from backend.api_main import app
    from services import anti_abuse
    guard = AbuseControls({"market": Policy(20, 60, 4, 2), "market_ops": Policy(20, 60, 1, 2), "metadata": Policy(20, 60, 4, 20)})
    monkeypatch.setattr(anti_abuse, "CONTROLS", guard)
    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "fixture-operator-token")
    client = TestClient(app)
    for _ in range(2):
        assert client.post("/market-insights/refresh").status_code == 403
    assert guard.operation_limiters["market"].tracked_key_count() == 0
    assert guard.operation_limiters["market_ops"].tracked_key_count() == 0


def test_uploaded_geojson_limit_precedes_native_construction(monkeypatch):
    import json
    from services import parcel_geometry as parcel
    called = []
    monkeypatch.setattr(parcel, "shape", lambda value: called.append(1))
    data = json.dumps({"type": "Polygon", "coordinates": [[[121, 25]] * 100001]}).encode()
    assert len(data) < parcel.MAX_UPLOAD_BYTES
    with pytest.raises(parcel.ParcelGeometryError):
        parcel.UploadedParcelProvider().resolve(filename="fixture.geojson", data=data)
    assert not called


def test_uploaded_kml_limit_precedes_native_construction(monkeypatch):
    from services import parcel_geometry as parcel
    called = []
    monkeypatch.setattr(parcel, "Polygon", lambda *args: called.append(1))
    data = ('<kml><Polygon><outerBoundaryIs><LinearRing><coordinates>' + '121,25 ' * 100001 + '</coordinates></LinearRing></outerBoundaryIs></Polygon></kml>').encode()
    with pytest.raises(parcel.ParcelGeometryError):
        parcel._kml(data)
    assert not called


def test_allowed_frontend_can_read_rejection_and_retry_after(monkeypatch):
    from backend.api_main import app
    from services import anti_abuse
    monkeypatch.setattr(anti_abuse, "CONTROLS", controls())
    monkeypatch.setattr("backend.api.routes_map.get_nearby_places", lambda *args: {})
    client = TestClient(app)
    headers = {"Origin": "http://localhost:3000"}
    payload = {"lat": 25, "lng": 121}
    for _ in range(2):
        assert client.post("/map/nearby", json=payload, headers=headers).status_code == 200
    limited = client.post("/map/nearby", json=payload, headers=headers)
    assert limited.status_code == 429
    monkeypatch.setenv("ANTI_ABUSE_PLACES_DISABLED", "true")
    disabled = client.post("/map/nearby", json=payload, headers=headers)
    oversized = client.post("/other", content=b"x" * 1000001, headers=headers)
    assert disabled.status_code == 503
    assert oversized.status_code == 413
    for response in (limited, disabled, oversized):
        assert response.headers.get("Access-Control-Allow-Origin") == headers["Origin"]
        assert "retry-after" in response.headers.get("Access-Control-Expose-Headers", "").lower()


def test_default_places_fanout_can_complete_without_self_rejection(monkeypatch):
    from services import anti_abuse
    from services.adapters.google_places_adapter import GooglePlacesAdapter
    from services.map_service import get_nearby_places
    from tests.test_google_provider_cost_optimization import Response
    guard = anti_abuse.AbuseControls(anti_abuse.POLICIES)
    monkeypatch.setattr(anti_abuse, "CONTROLS", guard)
    lock, complete, release = threading.Lock(), threading.Event(), threading.Event()
    dispatches = []
    def observed():
        with lock:
            dispatches.append(1)
            if len(dispatches) == 6:
                complete.set()
    original_reject = guard.reject
    def rejected(*args, **kwargs):
        observed()
        return original_reject(*args, **kwargs)
    monkeypatch.setattr(guard, "reject", rejected)
    class Calls:
        def post(self, *args, **kwargs):
            observed()
            assert release.wait(5)
            return Response({"places": []})
    adapter = GooglePlacesAdapter(api_key="fixture", client=Calls())
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(get_nearby_places, 25, 121, 800, ["food", "park", "school", "medical", "shopping", "transport"], adapter=adapter)
        try:
            assert complete.wait(5)
        finally:
            release.set()
        response = request.result(5)
    assert response["partial"] is False
    assert response["failed_categories"] == []
    assert len(response["categories"]) == 6


def test_unconfigured_tgos_does_not_consume_provider_budget(monkeypatch):
    from services import anti_abuse
    from services.adapters.tgos_geocoding_adapter import TgosGeocodingAdapter
    guard = anti_abuse.CONTROLS
    adapter = TgosGeocodingAdapter(app_id="", api_key="")
    assert adapter.search("fixture", []) is None
    assert guard.operation_limiters["tgos"].tracked_key_count() == 0


def test_guard_after_response_start_does_not_emit_second_response():
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise AbuseRejected("capacity_exhausted", status=503)
    middleware = AbuseMiddleware(app, controls=controls())
    sent = []
    async def send(message):
        sent.append(message)
    async def receive():
        return {"type": "http.request", "body": b""}
    with pytest.raises(AbuseRejected):
        asyncio.run(middleware({"type": "http", "method": "GET", "path": "/stream", "headers": []}, receive, send))
    assert len(sent) == 1


@pytest.mark.parametrize("reason,status", [("provider_budget_exhausted", 429), ("capacity_exhausted", 503)])
def test_vnext_provider_guard_preserves_safe_status(reason, status):
    import json
    from backend.api_main import api_http_exception_handler
    from starlette.requests import Request
    response = asyncio.run(api_http_exception_handler(Request({"type": "http", "path": "/v1/property-resolutions", "headers": []}), AbuseRejected(reason, status=status)))
    assert response.status_code == status
    assert response.headers["Retry-After"] == "1"
    assert json.loads(response.body)["error"]["details"]["reason_code"] == reason


def test_satellite_kill_switch_prevents_worker_startup(monkeypatch):
    from backend import api_main
    calls = []
    class Manager:
        def start(self, **kwargs):
            calls.append(kwargs["enabled"])
        def shutdown(self):
            pass
    monkeypatch.setattr(api_main, "_get_earth_engine_worker_manager", lambda: Manager())
    monkeypatch.setenv("EARTH_ENGINE_SATELLITE_REFERENCE_V1", "true")
    monkeypatch.setenv("ANTI_ABUSE_SATELLITE_DISABLED", "true")
    async def lifespan():
        async with api_main.app_lifespan(api_main.app):
            pass
    asyncio.run(lifespan())
    assert calls == [False]


def test_valuation_trend_and_finder_do_not_share_request_quota():
    from backend.api.abuse_middleware import capability
    assert [capability({"path": path, "method": "POST"}) for path in ("/valuation/estimate", "/valuation/trend", "/valuation/property-search")] == ["valuation", "trend", "finder"]


def test_actual_roads_routes_get_metadata_protection():
    from backend.api.abuse_middleware import capability
    assert capability({"path": "/roads/roads", "method": "GET"}) == "metadata"
