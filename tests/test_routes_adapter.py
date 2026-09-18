"""Google Routes adapter normalization, safety, and error-handling tests (offline)."""

import httpx
import pytest

from services.adapters.routes_adapter import (
    GoogleRoutesAdapter,
    MockRoutesAdapter,
    RouteNotFoundError,
    RoutesAdapterError,
    RouteUnavailableError,
    is_supported_mode,
)


ORIGIN = (25.0330, 121.5654)
DESTINATION = (25.0478, 121.5170)


class _Response:
    def __init__(self, payload, *, error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self):
        return self._payload


class _Client:
    def __init__(self, response=None, *, raise_on_post: Exception | None = None) -> None:
        self._response = response
        self._raise_on_post = raise_on_post
        self.calls = 0
        self.last_headers: dict | None = None
        self.last_json: dict | None = None

    def post(self, url, json=None, headers=None):
        self.calls += 1
        self.last_headers = headers
        self.last_json = json
        if self._raise_on_post is not None:
            raise self._raise_on_post
        return self._response


def test_supported_modes() -> None:
    assert is_supported_mode("transit")
    assert is_supported_mode("driving")
    assert is_supported_mode("walking")
    assert not is_supported_mode("cycling")


def test_no_key_is_unavailable_and_does_not_call() -> None:
    adapter = GoogleRoutesAdapter(api_key="")
    assert adapter.available is False
    with pytest.raises(RouteUnavailableError):
        adapter.compute_route(ORIGIN, DESTINATION, "transit")


def test_successful_fake_response_normalizes() -> None:
    client = _Client(_Response({"routes": [{"duration": "1500s", "distanceMeters": 8200}]}))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    result = adapter.compute_route(ORIGIN, DESTINATION, "driving")
    assert result == {"duration_seconds": 1500, "distance_m": 8200, "mode": "driving", "source": "google_routes"}
    # Field mask is explicit and minimal; API key is sent via header, never returned.
    assert client.last_headers["X-Goog-FieldMask"] == "routes.duration,routes.distanceMeters"
    assert client.last_headers["X-Goog-Api-Key"] == "test"


def test_raw_google_fields_are_not_exposed() -> None:
    client = _Client(_Response({"routes": [{"duration": "600s", "distanceMeters": 3000, "polyline": {"encodedPolyline": "abc"}, "legs": [{"secret": "x"}]}]}))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    result = adapter.compute_route(ORIGIN, DESTINATION, "transit")
    assert set(result.keys()) == {"duration_seconds", "distance_m", "mode", "source"}
    assert "polyline" not in result
    assert "legs" not in result


def test_timeout_is_sanitized() -> None:
    client = _Client(raise_on_post=httpx.TimeoutException("boom"))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    with pytest.raises(RouteUnavailableError):
        adapter.compute_route(ORIGIN, DESTINATION, "transit")


def test_http_status_error_is_sanitized() -> None:
    error = httpx.HTTPStatusError("429", request=httpx.Request("POST", "https://x"), response=httpx.Response(429))
    client = _Client(_Response(None, error=error))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    with pytest.raises(RouteUnavailableError):
        adapter.compute_route(ORIGIN, DESTINATION, "transit")


def test_malformed_response_fails_closed() -> None:
    for payload in ([], {"routes": [{"duration": "not-seconds", "distanceMeters": 10}]}, {"routes": [{"distanceMeters": 10}]}, {"routes": [{"duration": "10s"}]}):
        client = _Client(_Response(payload))
        adapter = GoogleRoutesAdapter(api_key="test", client=client)
        with pytest.raises(RoutesAdapterError):
            adapter.compute_route(ORIGIN, DESTINATION, "transit")


def test_zero_route_raises_not_found() -> None:
    client = _Client(_Response({"routes": []}))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    with pytest.raises(RouteNotFoundError):
        adapter.compute_route(ORIGIN, DESTINATION, "transit")


def test_unsupported_mode_raises() -> None:
    client = _Client(_Response({"routes": [{"duration": "10s", "distanceMeters": 10}]}))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    with pytest.raises(RoutesAdapterError):
        adapter.compute_route(ORIGIN, DESTINATION, "flying")


def test_invalid_coordinates_raise() -> None:
    adapter = GoogleRoutesAdapter(api_key="test", client=_Client(_Response({"routes": []})))
    with pytest.raises(RoutesAdapterError):
        adapter.compute_route((999, 0), DESTINATION, "transit")
    with pytest.raises(RoutesAdapterError):
        adapter.compute_route(ORIGIN, (0, 999), "transit")


def test_injected_client_remains_caller_owned() -> None:
    client = _Client(_Response({"routes": [{"duration": "10s", "distanceMeters": 10}]}))
    adapter = GoogleRoutesAdapter(api_key="test", client=client)
    adapter.close()
    # close() must not attempt to close a caller-owned client (no attribute error / no flag set)
    assert client.calls == 0


def test_mock_adapter_is_marked_mock_and_deterministic() -> None:
    adapter = MockRoutesAdapter()
    assert adapter.available is True
    first = adapter.compute_route(ORIGIN, DESTINATION, "walking")
    second = adapter.compute_route(ORIGIN, DESTINATION, "walking")
    assert first == second
    assert first["source"] == "mock"
    assert first["mode"] == "walking"
    assert first["distance_m"] > 0
    assert first["duration_seconds"] > 0


def test_mock_adapter_rejects_unsupported_mode() -> None:
    with pytest.raises(RoutesAdapterError):
        MockRoutesAdapter().compute_route(ORIGIN, DESTINATION, "teleport")
