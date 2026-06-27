from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.api.location import build_location_resolver
from app.main import app
from app.services import location_resolver
from app.services.location_resolver import LocationResolver


class MockHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def test_tgos_success_resolves_first_and_marks_source_tgos(monkeypatch) -> None:
    resolver = LocationResolver(
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        assert "tgos" in url.lower()
        return MockHTTPResponse(
            {
                "AddressList": [
                    {
                        "FULL_ADDR": "臺北市信義區市府路1號",
                        "X": 121.5654,
                        "Y": 25.0329,
                    }
                ]
            }
        )

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "resolved"
    assert result.source == "tgos"
    assert result.formatted_address == "臺北市信義區市府路1號"
    assert result.latitude == 25.0329
    assert result.longitude == 121.5654
    assert result.confidence == "high"


def test_tgos_timeout_then_google_success(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    calls: list[str] = []
    request = httpx.Request("GET", "https://example.com")

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        calls.append(url)
        if "tgos" in url.lower():
            raise httpx.TimeoutException("timeout", request=request)
        return MockHTTPResponse(
            {
                "status": "OK",
                "results": [
                    {
                        "formatted_address": "臺北市信義區市府路1號",
                        "geometry": {"location": {"lat": 25.0329, "lng": 121.5654}},
                    }
                ],
            }
        )

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert len(calls) == 2
    assert result.status == "resolved"
    assert result.source == "google"
    assert result.latitude == 25.0329
    assert result.longitude == 121.5654
    assert result.confidence == "medium"


def test_tgos_http_error_then_google_success(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    calls: list[str] = []
    request = httpx.Request("GET", "https://example.com")

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        calls.append(url)
        if "tgos" in url.lower():
            raise httpx.HTTPStatusError("bad status", request=request, response=httpx.Response(500, request=request))
        return MockHTTPResponse(
            {
                "status": "OK",
                "results": [
                    {
                        "formatted_address": "臺北市信義區市府路1號",
                        "geometry": {"location": {"lat": 25.0329, "lng": 121.5654}},
                    }
                ],
            }
        )

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert len(calls) == 2
    assert result.status == "resolved"
    assert result.source == "google"
    assert result.latitude == 25.0329
    assert result.longitude == 121.5654
    assert result.confidence == "medium"


def test_google_success_after_tgos_no_result(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        calls.append(url)
        if "tgos" in url.lower():
            return MockHTTPResponse({"AddressList": []})
        return MockHTTPResponse(
            {
                "status": "OK",
                "results": [
                    {
                        "formatted_address": "臺北市信義區市府路1號",
                        "geometry": {"location": {"lat": 25.0329, "lng": 121.5654}},
                    }
                ],
            }
        )

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert len(calls) == 2
    assert result.status == "resolved"
    assert result.source == "google"
    assert result.formatted_address == "臺北市信義區市府路1號"
    assert result.latitude == 25.0329
    assert result.longitude == 121.5654
    assert result.confidence == "medium"


def test_google_zero_results_returns_unresolved(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            return MockHTTPResponse({"AddressList": []})
        return MockHTTPResponse({"status": "ZERO_RESULTS", "results": []})

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unresolved"
    assert result.source == "none"
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_google_request_denied_returns_unavailable_not_unresolved(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            return MockHTTPResponse({"AddressList": []})
        return MockHTTPResponse({"status": "REQUEST_DENIED", "results": []})

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"
    assert "REQUEST_DENIED" not in result.message


def test_google_over_daily_limit_returns_unavailable(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            return MockHTTPResponse({"AddressList": []})
        return MockHTTPResponse({"status": "OVER_DAILY_LIMIT", "results": []})

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_google_ok_missing_lat_or_lng_returns_unavailable(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            return MockHTTPResponse({"AddressList": []})
        return MockHTTPResponse(
            {
                "status": "OK",
                "results": [
                    {
                        "formatted_address": "臺北市信義區市府路1號",
                        "geometry": {"location": {"lat": 25.0329}},
                    }
                ],
            }
        )

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_unresolved_when_both_providers_return_no_result(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            return MockHTTPResponse({"AddressList": []})
        return MockHTTPResponse({"status": "ZERO_RESULTS", "results": []})

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unresolved"
    assert result.source == "none"
    assert result.formatted_address is None
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_tgos_http_500_and_google_request_denied_return_unavailable(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )
    request = httpx.Request("GET", "https://example.com")

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            raise httpx.HTTPStatusError("bad status", request=request, response=httpx.Response(500, request=request))
        return MockHTTPResponse({"status": "REQUEST_DENIED", "results": []})

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_both_missing_credentials_return_unavailable(monkeypatch) -> None:
    resolver = LocationResolver()

    def fail_get(*args, **kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("HTTP should not be called without credentials")

    monkeypatch.setattr(location_resolver.httpx, "get", fail_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.formatted_address is None
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_both_technical_failures_return_unavailable(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )
    request = httpx.Request("GET", "https://example.com")

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            raise httpx.ReadTimeout("timeout", request=request)
        raise httpx.HTTPStatusError("bad status", request=request, response=httpx.Response(500, request=request))

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.formatted_address is None
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_unavailable_when_credentials_missing(monkeypatch) -> None:
    resolver = LocationResolver()

    def fail_get(*args, **kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("HTTP should not be called without credentials")

    monkeypatch.setattr(location_resolver.httpx, "get", fail_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.formatted_address is None
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"


def test_timeout_and_http_errors_do_not_leak_and_do_not_create_fake_coordinates(monkeypatch) -> None:
    resolver = LocationResolver(
        google_maps_api_key="google-key",
        tgos_app_id="app-id",
        tgos_api_key="api-key",
    )
    request = httpx.Request("GET", "https://example.com")

    def fake_get(url: str, params=None, timeout=None):  # noqa: ANN001
        if "tgos" in url.lower():
            raise httpx.ReadTimeout("timeout", request=request)
        raise httpx.HTTPStatusError("bad status", request=request, response=httpx.Response(500, request=request))

    monkeypatch.setattr(location_resolver.httpx, "get", fake_get)

    result = resolver.resolve("臺北市信義區市府路1號")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.formatted_address is None
    assert result.latitude is None
    assert result.longitude is None
    assert result.confidence == "unknown"
    assert "timeout" not in result.message.lower()
    assert "bad status" not in result.message.lower()


def test_location_endpoint_rejects_whitespace_only_address(monkeypatch) -> None:
    class FakeResolver:
        def resolve(self, address: str):  # noqa: ANN001, ARG002
            raise AssertionError("resolver should not be called for whitespace-only address")

    app.dependency_overrides[build_location_resolver] = lambda: FakeResolver()
    client = TestClient(app)

    try:
        response = client.post("/api/location/resolve", json={"address": "   "})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_location_endpoint_validation_and_wiring(monkeypatch) -> None:
    class FakeResolver:
        def resolve(self, address: str):  # noqa: ANN001, ARG002
            return location_resolver.LocationResolveResponse(
                status="resolved",
                source="google",
                formatted_address="臺北市信義區市府路1號",
                latitude=25.0329,
                longitude=121.5654,
                confidence="medium",
                message="已由 Google Geocoding 取得可信座標，可用於後續分析。",
            )

    app.dependency_overrides[build_location_resolver] = lambda: FakeResolver()
    client = TestClient(app)

    try:
        response = client.post("/api/location/resolve", json={"address": "臺北市信義區市府路1號"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "resolved"
        assert payload["source"] == "google"
        assert payload["latitude"] == 25.0329
        assert payload["longitude"] == 121.5654

        invalid = client.post("/api/location/resolve", json={})
        assert invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()