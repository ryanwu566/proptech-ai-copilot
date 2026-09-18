"""Commute routing service tests: cache, fallback, and safe normalization (offline)."""

import pytest

from services import commute_routing_service as svc
from services.adapters.routes_adapter import (
    RouteNotFoundError,
    RoutesAdapterError,
    RouteUnavailableError,
)


ORIGIN = (25.0330, 121.5654)
DESTINATION = (25.0478, 121.5170)


def setup_function() -> None:
    svc.clear_route_cache()


def teardown_function() -> None:
    svc.clear_route_cache()


class FakeGoogle:
    def __init__(self, *, available=True, result=None, error: Exception | None = None) -> None:
        self._available = available
        self._result = result
        self._error = error
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._available

    def compute_route(self, origin, destination, mode):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return {**self._result, "mode": mode}


class FakeMock:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def available(self) -> bool:
        return True

    def compute_route(self, origin, destination, mode):
        self.calls += 1
        return {"duration_seconds": 1200, "distance_m": 5000, "mode": mode, "source": "mock"}


def test_resolved_google_route_is_normalized() -> None:
    google = FakeGoogle(result={"duration_seconds": 1500, "distance_m": 8200, "source": "google_routes"})
    result = svc.estimate_commute_route(ORIGIN, DESTINATION, "driving", google_adapter=google, mock_adapter=FakeMock())
    assert result["status"] == "resolved"
    assert result["source"] == "google_routes"
    assert result["mode"] == "driving"
    assert result["duration_min"] == 25
    assert result["duration_seconds"] == 1500
    assert result["distance_m"] == 8200
    assert result["partial"] is False
    assert result["fallback"] is False
    assert result["disclaimer"]


def test_missing_credential_falls_back_to_mock_marked_fallback() -> None:
    google = FakeGoogle(available=False)
    mock = FakeMock()
    result = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=mock)
    assert result["status"] == "resolved"
    assert result["source"] == "mock"
    assert result["fallback"] is True
    assert result["partial"] is True
    assert google.calls == 0
    assert mock.calls == 1


def test_google_unavailable_falls_back_to_mock() -> None:
    google = FakeGoogle(error=RouteUnavailableError("timeout"))
    mock = FakeMock()
    result = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=mock)
    assert result["status"] == "resolved"
    assert result["source"] == "mock"
    assert result["fallback"] is True
    assert mock.calls == 1


def test_zero_route_is_unresolved_not_fabricated() -> None:
    google = FakeGoogle(error=RouteNotFoundError("none"))
    mock = FakeMock()
    result = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=mock)
    assert result["status"] == "unresolved"
    assert result["source"] == "none"
    assert result["duration_min"] is None
    assert mock.calls == 0  # must not fabricate a mock for a genuine zero-result


def test_malformed_provider_error_is_unavailable() -> None:
    google = FakeGoogle(error=RoutesAdapterError("malformed"))
    result = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=FakeMock())
    assert result["status"] == "unavailable"
    assert result["source"] == "none"


def test_unsupported_mode_raises_invalid_request() -> None:
    with pytest.raises(svc.InvalidRouteRequestError):
        svc.estimate_commute_route(ORIGIN, DESTINATION, "cycling", google_adapter=FakeGoogle(available=False), mock_adapter=FakeMock())


def test_cache_hit_does_not_reinvoke_provider() -> None:
    google = FakeGoogle(result={"duration_seconds": 900, "distance_m": 4000, "source": "google_routes"})
    first = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=FakeMock())
    second = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=FakeMock())
    assert first == second
    assert google.calls == 1  # second served from cache


def test_cache_separates_by_destination_and_mode() -> None:
    google = FakeGoogle(result={"duration_seconds": 900, "distance_m": 4000, "source": "google_routes"})
    svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=FakeMock())
    svc.estimate_commute_route(ORIGIN, (25.1, 121.6), "transit", google_adapter=google, mock_adapter=FakeMock())
    svc.estimate_commute_route(ORIGIN, DESTINATION, "driving", google_adapter=google, mock_adapter=FakeMock())
    assert google.calls == 3  # each distinct key invokes the provider


def test_unavailable_is_not_cached() -> None:
    google = FakeGoogle(error=RoutesAdapterError("malformed"))
    svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=FakeMock())
    svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=FakeMock())
    assert google.calls == 2  # unavailable results are not cached


# --- Production mock-safety gate ---

def test_mock_fallback_allowed_by_environment() -> None:
    assert svc.mock_fallback_allowed({}) is True  # default development
    assert svc.mock_fallback_allowed({"APP_ENV": "development"}) is True
    assert svc.mock_fallback_allowed({"APP_ENV": "test"}) is True
    assert svc.mock_fallback_allowed({"APP_ENV": "production"}) is False
    assert svc.mock_fallback_allowed({"APP_ENV": "preview"}) is False
    # Explicit demo opt-in re-enables mock in production-like runtime.
    assert svc.mock_fallback_allowed({"APP_ENV": "production", "DEMO_ROUTES_FALLBACK": "true"}) is True


def test_production_missing_key_is_unavailable_no_mock_numbers() -> None:
    result = svc.estimate_commute_route(
        ORIGIN, DESTINATION, "transit",
        google_adapter=FakeGoogle(available=False), mock_adapter=FakeMock(), allow_mock=False,
    )
    assert result["status"] == "unavailable"
    assert result["source"] == "none"
    assert result["duration_min"] is None
    assert result["duration_seconds"] is None
    assert result["distance_m"] is None
    assert result["fallback"] is False


def test_production_timeout_is_unavailable() -> None:
    result = svc.estimate_commute_route(
        ORIGIN, DESTINATION, "transit",
        google_adapter=FakeGoogle(error=RouteUnavailableError("timeout")), mock_adapter=FakeMock(), allow_mock=False,
    )
    assert result["status"] == "unavailable"
    assert result["distance_m"] is None


def test_production_http_429_is_unavailable() -> None:
    # HTTP failures (including 429) surface as RouteUnavailableError from the adapter.
    result = svc.estimate_commute_route(
        ORIGIN, DESTINATION, "transit",
        google_adapter=FakeGoogle(error=RouteUnavailableError("429")), mock_adapter=FakeMock(), allow_mock=False,
    )
    assert result["status"] == "unavailable"
    assert result["duration_min"] is None


def test_dev_provider_failure_uses_marked_mock() -> None:
    result = svc.estimate_commute_route(
        ORIGIN, DESTINATION, "transit",
        google_adapter=FakeGoogle(error=RouteUnavailableError("timeout")), mock_adapter=FakeMock(), allow_mock=True,
    )
    assert result["status"] == "resolved"
    assert result["source"] == "mock"
    assert result["fallback"] is True
    assert "示範估算" in result["message"]


def test_mock_fallback_is_not_cached() -> None:
    google = FakeGoogle(error=RouteUnavailableError("timeout"))
    mock = FakeMock()
    svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=mock, allow_mock=True)
    svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=google, mock_adapter=mock, allow_mock=True)
    # Each call re-invokes the provider because mock/fallback is never cached.
    assert google.calls == 2
    assert mock.calls == 2


def test_provider_recovery_after_mock_invokes_google() -> None:
    # First: Google unavailable -> marked mock (not cached).
    failing = FakeGoogle(error=RouteUnavailableError("timeout"))
    first = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=failing, mock_adapter=FakeMock(), allow_mock=True)
    assert first["source"] == "mock"
    # Then: Google recovers -> next request invokes Google and returns google_routes.
    recovered = FakeGoogle(result={"duration_seconds": 900, "distance_m": 4000, "source": "google_routes"})
    second = svc.estimate_commute_route(ORIGIN, DESTINATION, "transit", google_adapter=recovered, mock_adapter=FakeMock(), allow_mock=True)
    assert recovered.calls == 1
    assert second["source"] == "google_routes"
    assert second["status"] == "resolved"


def test_genuine_google_result_is_cached() -> None:
    google = FakeGoogle(result={"duration_seconds": 900, "distance_m": 4000, "source": "google_routes"})
    svc.estimate_commute_route(ORIGIN, DESTINATION, "driving", google_adapter=google, mock_adapter=FakeMock(), allow_mock=True)
    second = svc.estimate_commute_route(ORIGIN, DESTINATION, "driving", google_adapter=google, mock_adapter=FakeMock(), allow_mock=True)
    assert google.calls == 1  # served from cache
    assert second["source"] == "google_routes"
