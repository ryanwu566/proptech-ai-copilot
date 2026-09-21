"""Bounded satellite reference API and Earth Engine adapter tests."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
from datetime import date
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import inspect
import logging
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import api_main
from backend.api_main import app
from backend.api import routes_satellite_reference
from services import satellite_reference as satellite


client = TestClient(app)


def jpeg_with_dimensions(width: int, height: int) -> bytes:
    """Return a minimal JPEG marker stream with a baseline SOF dimension record."""

    sof_payload = (
        bytes([8])
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + bytes([3, 1, 0x11, 0, 2, 0x11, 0, 3, 0x11, 0])
    )
    return b"\xff\xd8\xff\xc0" + (len(sof_payload) + 2).to_bytes(2, "big") + sof_payload + b"\xff\xd9"


def test_thumbnail_download_does_not_log_provider_url_or_token(caplog) -> None:
    """The server-side download transport must never log the signed provider URL."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")

    class ThumbnailHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            payload = b"\xff\xd8bounded-jpeg\xff\xd9"
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ThumbnailHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    token = "must-not-leak"
    url = f"http://127.0.0.1:{server.server_port}/thumbnail?token={token}"
    try:
        with caplog.at_level(logging.DEBUG):
            payload = adapter_module._download_thumbnail(url, 1_000, 1.0)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)

    assert payload == b"\xff\xd8bounded-jpeg\xff\xd9"
    assert token not in caplog.text
    assert url not in caplog.text


def test_satellite_reference_is_fail_closed_when_feature_flag_is_off(monkeypatch) -> None:
    """Removing the default-off gate must make this test fail."""

    from services.earth_engine_worker_pool import EarthEngineWorkerManager

    manager = EarthEngineWorkerManager()
    manager.start(enabled=False, project="server-project")
    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: manager)

    response = client.post(
        "/terrain/satellite-reference",
        json={"latitude": 25.0375, "longitude": 121.5645},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason_code"] == "feature_disabled"
    assert response.json()["image_reference"] is None


def test_satellite_reference_is_unavailable_without_project_and_returns_only_allowlisted_fields(monkeypatch) -> None:
    """Reading ADC or leaking configuration when the project is absent is a bug."""

    from services.earth_engine_worker_pool import EarthEngineWorkerManager

    manager = EarthEngineWorkerManager()
    manager.start(enabled=True, project="")
    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: manager)

    response = client.post(
        "/terrain/satellite-reference",
        json={"latitude": 25.0375, "longitude": 121.5645},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "status",
        "reason_code",
        "source",
        "dataset",
        "window_start",
        "window_end",
        "retrieval_time",
        "aoi_radius_m",
        "composite_method",
        "cloud_filter_percent",
        "image_reference",
        "attribution",
        "limitations",
        "disclaimer",
    }
    assert payload["status"] == "unavailable"
    assert payload["reason_code"] == "credential_unavailable"
    assert payload["dataset"] == "COPERNICUS/S2_SR_HARMONIZED"
    assert payload["aoi_radius_m"] == 500
    assert payload["cloud_filter_percent"] == 35
    assert (date.fromisoformat(payload["window_end"]) - date.fromisoformat(payload["window_start"])).days == 90
    assert payload["image_reference"] is None
    assert "Cloud filtering and masking may leave residual cloud, haze, or incomplete coverage." in payload["limitations"]
    assert payload["disclaimer"] == "Satellite reference imagery — not cadastral or statutory evidence."
    serialized = response.text.lower()
    for forbidden in ("google_application_credentials", "access_token", "refresh_token", "private_key", "project_id"):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (90.0001, 121.5),
        (-90.0001, 121.5),
        (25.0, 180.0001),
        (25.0, -180.0001),
        ("NaN", 121.5),
        ("Infinity", 121.5),
        (25.0, "-Infinity"),
    ],
)
def test_satellite_reference_rejects_non_finite_or_out_of_range_coordinates(latitude, longitude) -> None:
    """Relaxing coordinate validation must fail at the HTTP boundary."""

    response = client.post(
        "/terrain/satellite-reference",
        json={"latitude": latitude, "longitude": longitude},
    )

    assert response.status_code == 422


def test_route_does_not_reread_project_per_request(monkeypatch) -> None:
    """Bypassing the service or accepting extra provider controls must fail this route contract."""

    captured = {}

    async def fake_fetch(**kwargs):
        captured.update(kwargs)
        return satellite.build_response(
            status="available",
            reason_code=None,
            image_reference="data:image/jpeg;base64,/9j/2Q==",
            now=datetime(2026, 9, 20, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(routes_satellite_reference, "fetch_satellite_reference", fake_fetch, raising=False)
    response = client.post(
        "/terrain/satellite-reference",
        json={"latitude": 25.0375, "longitude": 121.5645},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert captured == {
        "latitude": 25.0375,
        "longitude": 121.5645,
    }

    rejected = client.post(
        "/terrain/satellite-reference",
        json={
            "latitude": 25.0375,
            "longitude": 121.5645,
            "dataset": "caller-controlled",
            "geometry": {"type": "Polygon", "coordinates": []},
            "date_range": ["2000-01-01", "2030-01-01"],
        },
    )
    assert rejected.status_code == 422


def test_fastapi_serves_health_while_earth_engine_manager_is_starting(monkeypatch) -> None:
    """Earth Engine readiness must not become a whole-application startup gate."""

    calls = []

    class Manager:
        state = "starting"

        def start(self, **kwargs):
            calls.append(("start", kwargs))
            raise RuntimeError("ADC/provider details must remain optional")

        def shutdown(self):
            calls.append(("shutdown", None))

    manager = Manager()
    monkeypatch.setattr(api_main, "_get_earth_engine_worker_manager", lambda: manager, raising=False)
    monkeypatch.setenv("EARTH_ENGINE_SATELLITE_REFERENCE_V1", "true")
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "server-project")

    with TestClient(app) as lifespan_client:
        assert lifespan_client.get("/health").status_code == 200

    assert calls == [
        ("start", {"enabled": True, "project": "server-project"}),
        ("shutdown", None),
    ]


def test_satellite_route_fails_closed_while_manager_is_starting(monkeypatch) -> None:
    """A starting optional capability must fail only its own route and return promptly."""

    class Manager:
        state = "starting"

        def start(self, **_kwargs):
            return None

        def shutdown(self):
            return None

        async def fetch(self, **_kwargs):
            raise satellite.EarthEngineProviderError("not ready")

    manager = Manager()
    monkeypatch.setattr(api_main, "_get_earth_engine_worker_manager", lambda: manager, raising=False)
    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: manager)
    monkeypatch.setenv("EARTH_ENGINE_SATELLITE_REFERENCE_V1", "true")
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "server-project")

    with TestClient(app) as lifespan_client:
        assert lifespan_client.get("/health").status_code == 200
        started_at = time.monotonic()
        response = lifespan_client.post(
            "/terrain/satellite-reference",
            json={"latitude": 25.0375, "longitude": 121.5645},
        )

    assert time.monotonic() - started_at < 0.5
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason_code"] == "provider_error"


class RecordingAdapter:
    def __init__(self, result=None, error: Exception | None = None, delay_seconds: float = 0) -> None:
        self.result = result
        self.error = error
        self.delay_seconds = delay_seconds
        self.queries = []

    def fetch(self, query):
        self.queries.append(query)
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        if self.error:
            raise self.error
        return self.result


def test_service_builds_fixed_query_and_returns_bounded_available_image() -> None:
    """Any caller-controlled Earth Engine parameter or missing image bound is a bug."""

    image_bytes = b"\xff\xd8bounded-jpeg\xff\xd9"
    adapter = RecordingAdapter(satellite.SatelliteAdapterResult(image_bytes=image_bytes))
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    result = asyncio.run(
        satellite.fetch_satellite_reference(
            latitude=25.0375,
            longitude=121.5645,
            adapter=adapter,
            now=now,
        )
    )

    assert result.status == "available"
    assert result.reason_code is None
    assert result.image_reference is not None
    prefix, encoded = result.image_reference.split(",", 1)
    assert prefix == "data:image/jpeg;base64"
    assert base64.b64decode(encoded) == image_bytes
    assert len(result.model_dump_json().encode("utf-8")) <= satellite.MAX_RESPONSE_BYTES
    assert len(adapter.queries) == 1
    query = adapter.queries[0]
    assert query.dataset == "COPERNICUS/S2_SR_HARMONIZED"
    assert query.latitude == 25.0375
    assert query.longitude == 121.5645
    assert query.window_start == "2026-06-22"
    assert query.window_end == "2026-09-20"
    assert query.aoi_radius_m == 500
    assert query.cloud_filter_percent == 35
    assert query.rgb_bands == ("B4", "B3", "B2")
    assert query.excluded_scl_classes == (3, 8, 9, 10, 11)
    assert query.dimensions == (512, 512)
    assert query.image_format == "jpg"
    assert satellite.EXTERNAL_TIMEOUT_SECONDS == 8.0


@pytest.mark.parametrize(
    ("error_type_name", "message", "reason_code"),
    [
        ("EarthEngineCredentialUnavailable", "private_key=must-not-leak", "credential_unavailable"),
        ("EarthEngineInitializationUnavailable", "provider-url=must-not-leak", "provider_error"),
        ("EarthEngineProviderTimeout", "request-url=must-not-leak", "provider_timeout"),
        ("EarthEngineProviderError", "access_token=must-not-leak", "provider_error"),
        ("EarthEngineImageGenerationError", "signed-url=must-not-leak", "image_generation_failed"),
    ],
)
def test_service_maps_provider_failures_without_exception_or_secret_leakage(error_type_name, message, reason_code) -> None:
    """Returning provider exceptions or secret material must fail this test."""

    error_type = getattr(satellite, error_type_name)
    result = asyncio.run(
        satellite.fetch_satellite_reference(
            latitude=25.0375,
            longitude=121.5645,
            adapter=RecordingAdapter(error=error_type(message)),
        )
    )

    assert result.status == "unavailable"
    assert result.reason_code == reason_code
    assert result.image_reference is None
    serialized = result.model_dump_json().lower()
    for forbidden in ("must-not-leak", "private_key", "access_token", "signed-url", "server-project"):
        assert forbidden not in serialized


def test_service_dispatches_to_lifecycle_manager_without_per_request_project(monkeypatch) -> None:
    """The manager's startup snapshot is the only Earth Engine project authority."""

    captured = {}

    class Manager:
        async def fetch(self, **kwargs):
            captured.update(kwargs)
            return b"\xff\xd8bounded-jpeg\xff\xd9"

    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: Manager(), raising=False)
    result = asyncio.run(
        satellite.fetch_satellite_reference(
            latitude=25.0375,
            longitude=121.5645,
            now=datetime(2026, 9, 20, tzinfo=timezone.utc),
        )
    )

    assert result.status == "available"
    assert set(captured) == {"latitude", "longitude", "window_start", "window_end", "deadline"}
    assert captured["window_start"] == "2026-06-22"
    assert captured["window_end"] == "2026-09-20"
    assert "project" not in inspect.signature(satellite.fetch_satellite_reference).parameters


def test_absolute_deadline_is_rechecked_after_response_construction(monkeypatch) -> None:
    """Encoding and model construction consume the same original eight-second budget."""

    clock = {"now": 100.0}
    original_dump = satellite.SatelliteReferenceResponse.model_dump_json

    def timed_dump(self, *args, **kwargs):
        serialized = original_dump(self, *args, **kwargs)
        clock["now"] = 108.01
        return serialized

    monkeypatch.setattr(satellite, "time", SimpleNamespace(monotonic=lambda: clock["now"]))
    monkeypatch.setattr(satellite.SatelliteReferenceResponse, "model_dump_json", timed_dump)
    result = asyncio.run(
        satellite.fetch_satellite_reference(
            latitude=25.0375,
            longitude=121.5645,
            adapter=RecordingAdapter(
                satellite.SatelliteAdapterResult(image_bytes=b"\xff\xd8bounded-jpeg\xff\xd9")
            ),
        )
    )

    assert result.status == "unavailable"
    assert result.reason_code == "provider_timeout"
    assert result.image_reference is None


def test_service_rejects_provider_image_that_exceeds_fixed_byte_bound() -> None:
    """Returning an oversized provider payload must fail closed."""

    result = asyncio.run(
        satellite.fetch_satellite_reference(
            latitude=25.0375,
            longitude=121.5645,
            adapter=RecordingAdapter(
                satellite.SatelliteAdapterResult(
                    image_bytes=b"x" * (satellite.MAX_PROVIDER_IMAGE_BYTES + 1),
                )
            ),
        )
    )

    assert result.status == "unavailable"
    assert result.reason_code == "image_generation_failed"
    assert result.image_reference is None
    assert len(result.model_dump_json().encode("utf-8")) <= satellite.MAX_RESPONSE_BYTES


class FakeInfo:
    def __init__(self, value) -> None:
        self.value = value

    def getInfo(self):
        return self.value


class FakeRegion:
    def __init__(self, calls, label="point") -> None:
        self.calls = calls
        self.label = label

    def buffer(self, radius):
        self.calls.append(("buffer", radius))
        return FakeRegion(self.calls, "buffer")

    def bounds(self):
        self.calls.append(("bounds",))
        return FakeRegion(self.calls, "bounds")


class FakeMask:
    def __init__(self, excluded) -> None:
        self.excluded = excluded

    def And(self, other):
        return FakeMask(self.excluded + other.excluded)


class FakeScl:
    def neq(self, value):
        return FakeMask([value])


class FakeSourceImage:
    def __init__(self, calls) -> None:
        self.calls = calls

    def select(self, band):
        self.calls.append(("mask_select", band))
        return FakeScl()

    def updateMask(self, mask):
        self.calls.append(("update_mask", tuple(mask.excluded)))
        return self


class FakeComposite:
    def __init__(self, calls, thumbnail_url) -> None:
        self.calls = calls
        self.thumbnail_url = thumbnail_url

    def select(self, bands):
        self.calls.append(("rgb_select", tuple(bands)))
        return self

    def visualize(self, **kwargs):
        self.calls.append(("visualize", kwargs))
        return self

    def getThumbURL(self, params):
        self.calls.append(("thumbnail", params))
        return self.thumbnail_url


class FakeCollection:
    def __init__(self, calls, scene_count, thumbnail_url) -> None:
        self.calls = calls
        self.scene_count = scene_count
        self.thumbnail_url = thumbnail_url

    def filterBounds(self, region):
        self.calls.append(("filter_bounds", region))
        return self

    def filterDate(self, start, end):
        self.calls.append(("filter_date", start, end))
        return self

    def filter(self, expression):
        self.calls.append(("filter", expression))
        return self

    def map(self, callback):
        callback(FakeSourceImage(self.calls))
        self.calls.append(("map",))
        return self

    def size(self):
        self.calls.append(("size",))
        raise AssertionError("scene count is not part of preview availability")

    def median(self):
        self.calls.append(("median",))
        return FakeComposite(self.calls, self.thumbnail_url)


class FakeGeometryFactory:
    def __init__(self, calls) -> None:
        self.calls = calls

    def Point(self, coordinates):
        self.calls.append(("point", tuple(coordinates)))
        return FakeRegion(self.calls)


class FakeFilterFactory:
    @staticmethod
    def lte(field, value):
        return ("lte", field, value)


class FakeEarthEngineData:
    def __init__(self, calls) -> None:
        self.calls = calls

    def setMaxRetries(self, retries):
        self.calls.append(("set_max_retries", retries))


class FakeEarthEngine:
    def __init__(self, scene_count=3, thumbnail_url="https://earthengine.googleapis.com/v1/projects/public/thumbnails/opaque?token=ephemeral") -> None:
        self.calls = []
        self.scene_count = scene_count
        self.thumbnail_url = thumbnail_url
        self.Geometry = FakeGeometryFactory(self.calls)
        self.Filter = FakeFilterFactory()
        self.data = FakeEarthEngineData(self.calls)

    def Initialize(self, **kwargs):
        self.calls.append(("initialize", kwargs))

    def ImageCollection(self, dataset):
        self.calls.append(("collection", dataset))
        return FakeCollection(self.calls, self.scene_count, self.thumbnail_url)


def test_adapter_initializes_once_sets_zero_retries_and_reuses_state_concurrently() -> None:
    """Concurrent first use must perform one bounded initialization with SDK retries disabled."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()
    auth_calls = []
    refresh_calls = []
    refresh_transport_calls = []

    class Credentials:
        valid = False

        def refresh(self, request):
            refresh_calls.append(request)
            request(url="https://oauth2.googleapis.com/token", method="POST", body=b"fixed")
            self.valid = True

    credentials = Credentials()

    def auth_default(**_kwargs):
        auth_calls.append(True)
        time.sleep(0.02)
        return credentials, "ignored-adc-project"

    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=auth_default,
        auth_request_factory=lambda: lambda **kwargs: refresh_transport_calls.append(kwargs),
        download_image=lambda *_: jpeg_with_dimensions(512, 512),
    )
    failures = []

    def initialize():
        try:
            adapter.initialize()
        except Exception as exc:  # pragma: no cover - assertion reports thread failure
            failures.append(exc)

    threads = [threading.Thread(target=initialize) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)

    assert failures == []
    assert auth_calls == [True]
    assert len(refresh_calls) == 1
    assert len(refresh_transport_calls) == 1
    assert [call[0] for call in fake_ee.calls[:2]] == ["set_max_retries", "initialize"]
    assert fake_ee.calls.count(("set_max_retries", 0)) == 1
    assert sum(call[0] == "initialize" for call in fake_ee.calls) == 1


def test_adapter_maps_adc_refresh_failure_to_credential_unavailable() -> None:
    """Credential discovery or refresh errors are safe credential failures, never provider details."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")

    class Credentials:
        valid = False

        def refresh(self, _request):
            raise RuntimeError("refresh_token=must-not-leak")

    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=FakeEarthEngine(),
        auth_default=lambda **_kwargs: (Credentials(), None),
        auth_request_factory=lambda: object(),
        download_image=lambda *_: b"",
    )

    with pytest.raises(satellite.EarthEngineCredentialUnavailable) as raised:
        adapter.initialize()

    assert "must-not-leak" not in str(raised.value)


def test_adapter_maps_ee_initialize_failure_to_initialization_unavailable() -> None:
    """Provider initialization failures must not be misreported as missing credentials."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()

    def fail_initialize(**_kwargs):
        raise RuntimeError("provider-url=must-not-leak")

    fake_ee.Initialize = fail_initialize
    credentials = type("Credentials", (), {"valid": True})()
    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=lambda **_kwargs: (credentials, None),
        auth_request_factory=lambda: object(),
        download_image=lambda *_: b"",
    )

    with pytest.raises(satellite.EarthEngineInitializationUnavailable) as raised:
        adapter.initialize()

    assert "must-not-leak" not in str(raised.value)


def test_adapter_passes_fixed_earth_engine_scopes_to_adc() -> None:
    """Removing the scopes argument would break service-account ADC before EE initialization."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    observed = {}
    credentials = type("Credentials", (), {"valid": True})()

    def auth_default(**kwargs):
        observed.update(kwargs)
        return credentials, None

    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=FakeEarthEngine(),
        auth_default=auth_default,
        auth_request_factory=lambda: object(),
        download_image=lambda *_: b"",
    )

    adapter.initialize()

    assert observed["scopes"] == (
        "https://www.googleapis.com/auth/earthengine",
        "https://www.googleapis.com/auth/cloud-platform",
    )
    assert callable(observed["request"])


def test_adapter_blocks_duplicate_credential_transport_attempts() -> None:
    """A credential refresh must not repeat the same outbound token request."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    transport_calls = []

    def low_level_request(**kwargs):
        transport_calls.append(kwargs)
        return object()

    class Credentials:
        valid = False

        def refresh(self, request):
            request(url="https://oauth2.googleapis.com/token", method="POST", body=b"fixed")
            request(url="https://oauth2.googleapis.com/token", method="POST", body=b"fixed")

    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=FakeEarthEngine(),
        auth_default=lambda **_kwargs: (Credentials(), None),
        auth_request_factory=lambda: low_level_request,
        download_image=lambda *_: b"",
    )

    with pytest.raises(satellite.EarthEngineCredentialUnavailable):
        adapter.initialize()

    assert len(transport_calls) == 1


def test_adapter_disables_authorized_http_401_replay() -> None:
    """A 401 from Earth Engine must not refresh credentials and replay the request."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    import google_auth_httplib2

    class Credentials:
        valid = True
        quota_project_id = None

        def before_request(self, _request, _method, _url, _headers):
            return None

        def refresh(self, _request):
            refresh_calls.append(True)

    class UnauthorizedHttp:
        def request(self, *_args, **_kwargs):
            http_calls.append(True)
            return SimpleNamespace(status=401), b"unauthorized"

    class InitializingEarthEngine(FakeEarthEngine):
        def Initialize(self, *, credentials, project, **_kwargs):
            del project
            authorized = google_auth_httplib2.AuthorizedHttp(
                credentials,
                http=UnauthorizedHttp(),
            )
            authorized.request("https://earthengine.googleapis.com/v1/projects/fixed")

    http_calls = []
    refresh_calls = []
    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=InitializingEarthEngine(),
        auth_default=lambda **_kwargs: (Credentials(), None),
        auth_request_factory=lambda: object(),
        download_image=lambda *_: b"",
    )

    adapter.initialize()

    assert http_calls == [True]
    assert refresh_calls == []


def fixed_query() -> satellite.SatelliteQuery:
    return satellite.SatelliteQuery(
        latitude=25.0375,
        longitude=121.5645,
        dataset="COPERNICUS/S2_SR_HARMONIZED",
        window_start="2026-06-22",
        window_end="2026-09-20",
        aoi_radius_m=500,
        cloud_filter_percent=35,
        rgb_bands=("B4", "B3", "B2"),
        excluded_scl_classes=(3, 8, 9, 10, 11),
        dimensions=(512, 512),
        image_format="jpg",
    )


def test_adapter_does_not_issue_collection_size_request() -> None:
    """Preview availability must be established without a separate scene-count operation."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()
    expected = jpeg_with_dimensions(512, 512)
    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=lambda **_kwargs: (object(), None),
        download_image=lambda *_: expected,
    )

    adapter.initialize()
    result = adapter.fetch_initialized(fixed_query())

    assert result.image_bytes == expected
    assert not any(call[0] == "size" for call in fake_ee.calls)


def test_earth_engine_adapter_uses_adc_fixed_collection_mask_and_server_side_thumbnail_download() -> None:
    """Changing auth, dataset, geometry, mask, composite, or browser-delivery behavior must fail."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()
    credentials = object()
    downloaded_urls = []

    def download_image(url, max_bytes, timeout_seconds):
        downloaded_urls.append((url, max_bytes, timeout_seconds))
        return jpeg_with_dimensions(512, 512)

    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=lambda **_kwargs: (credentials, "ignored-adc-project"),
        download_image=download_image,
    )
    result = adapter.fetch(fixed_query())

    assert result == satellite.SatelliteAdapterResult(image_bytes=jpeg_with_dimensions(512, 512))
    assert fake_ee.calls[:2] == [
        ("set_max_retries", 0),
        ("initialize", {"credentials": credentials, "project": "server-project"}),
    ]
    assert ("point", (121.5645, 25.0375)) in fake_ee.calls
    assert ("buffer", 500) in fake_ee.calls
    assert ("bounds",) not in fake_ee.calls
    assert ("collection", "COPERNICUS/S2_SR_HARMONIZED") in fake_ee.calls
    assert ("filter_date", "2026-06-22", "2026-09-20") in fake_ee.calls
    assert ("filter", ("lte", "CLOUDY_PIXEL_PERCENTAGE", 35)) in fake_ee.calls
    assert ("update_mask", (3, 8, 9, 10, 11)) in fake_ee.calls
    assert ("median",) in fake_ee.calls
    assert ("rgb_select", ("B4", "B3", "B2")) in fake_ee.calls
    assert ("visualize", {"min": 0, "max": 3000}) in fake_ee.calls
    thumbnail_call = next(call for call in fake_ee.calls if call[0] == "thumbnail")
    assert thumbnail_call[1]["dimensions"] == "512x512"
    assert thumbnail_call[1]["format"] == "jpg"
    assert downloaded_urls == [
        (
            "https://earthengine.googleapis.com/v1/projects/public/thumbnails/opaque?token=ephemeral",
            satellite.MAX_PROVIDER_IMAGE_BYTES,
            satellite.EXTERNAL_TIMEOUT_SECONDS,
        )
    ]
    assert "earthengine.googleapis.com" not in repr(result)


def test_earth_engine_adapter_rejects_tampered_internal_query_before_authentication() -> None:
    """An internal regression that permits a different dataset must fail closed."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()
    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=lambda **_kwargs: (object(), None),
        download_image=lambda *_: b"\xff\xd8x\xff\xd9",
    )

    with pytest.raises(satellite.EarthEngineProviderError):
        adapter.fetch(replace(fixed_query(), dataset="users/arbitrary/expression"))

    assert fake_ee.calls == []


def test_earth_engine_adapter_maps_adc_failure_without_interactive_authentication() -> None:
    """Falling back to interactive OAuth when ADC is absent must fail this test."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()

    def unavailable_adc(**_kwargs):
        raise RuntimeError("private_key=must-not-leak")

    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=unavailable_adc,
        download_image=lambda *_: b"",
    )

    with pytest.raises(satellite.EarthEngineCredentialUnavailable) as raised:
        adapter.fetch(fixed_query())

    assert "must-not-leak" not in str(raised.value)
    assert fake_ee.calls == []


def test_earth_engine_adapter_rejects_non_provider_or_credential_bearing_thumbnail_url() -> None:
    """A redirectable or credential-bearing provider URL must never reach the downloader or browser."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    for unsafe_url in (
        "https://evil.example/thumbnail.jpg",
        "https://earthengine.googleapis.com/v1/thumb?access_token=secret",
        "http://earthengine.googleapis.com/v1/thumb",
    ):
        fake_ee = FakeEarthEngine(thumbnail_url=unsafe_url)
        downloads = []
        adapter = adapter_module.EarthEngineSatelliteAdapter(
            project="server-project",
            ee_module=fake_ee,
            auth_default=lambda **_kwargs: (object(), None),
            download_image=lambda *args: downloads.append(args),
        )

        with pytest.raises(satellite.EarthEngineImageGenerationError):
            adapter.fetch(fixed_query())
        assert downloads == []


def test_earth_engine_adapter_rejects_jpeg_exceeding_decoded_dimension_bound() -> None:
    """A compressed image wider or taller than 512 pixels must fail closed."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=FakeEarthEngine(),
        auth_default=lambda **_kwargs: (object(), None),
        download_image=lambda *_: jpeg_with_dimensions(513, 512),
    )

    with pytest.raises(satellite.EarthEngineImageGenerationError):
        adapter.fetch(fixed_query())


def test_earth_engine_adapter_uses_circular_buffer_as_exact_aoi() -> None:
    """The advertised 500 m AOI must not be widened to the buffer's bounding box."""

    adapter_module = importlib.import_module("services.adapters.earth_engine_adapter")
    fake_ee = FakeEarthEngine()
    adapter = adapter_module.EarthEngineSatelliteAdapter(
        project="server-project",
        ee_module=fake_ee,
        auth_default=lambda **_kwargs: (object(), None),
        download_image=lambda *_: jpeg_with_dimensions(512, 512),
    )

    adapter.fetch(fixed_query())

    filtered_region = next(call[1] for call in fake_ee.calls if call[0] == "filter_bounds")
    thumbnail_region = next(call[1]["region"] for call in fake_ee.calls if call[0] == "thumbnail")
    assert filtered_region.label == "buffer"
    assert thumbnail_region.label == "buffer"
    assert not any(call[0] == "bounds" for call in fake_ee.calls)
