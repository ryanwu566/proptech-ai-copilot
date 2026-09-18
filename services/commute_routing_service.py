"""Commute route enrichment service (Google Routes with gated mock fallback).

This service estimates travel duration and distance from a resolved property
origin to a user-selected destination for one bounded travel mode.

Production safety: a synthetic ``MockRoutesAdapter`` estimate is ONLY used when the
runtime is not production-like (development/test) or an explicit demo flag is set.
In a production-like runtime, a Google failure returns ``unavailable`` (degraded) and
never a fabricated duration/distance. A ``source=mock``/``fallback=true`` label alone
is intentionally not relied upon.

The result is external travel/accessibility observation only. It does not touch
Property Identity, cadastral evidence, or any persistent store.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Mapping

from services.adapters.routes_adapter import (
    GoogleRoutesAdapter,
    MockRoutesAdapter,
    RouteNotFoundError,
    RoutesAdapter,
    RoutesAdapterError,
    RouteUnavailableError,
    SUPPORTED_MODES,
    is_supported_mode,
)
from services.production_config import PRODUCTION_MODES


ROUTE_DISCLAIMER = "通勤時間為外部路線估算，僅供生活機能與可及性參考，不代表實際交通、估價或看房結論。"
MOCK_ROUTE_NOTE = "示範估算：非即時 Google 路線結果，僅供操作展示，不可作為真實通勤依據。"

APP_ENV_ENV = "APP_ENV"
DEMO_ROUTES_FALLBACK_ENV = "DEMO_ROUTES_FALLBACK"

CACHE_TTL_SECONDS = 600
_CACHE_COORD_PRECISION = 5

_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()

# A single default Google adapter reuses its connection pool across requests.
_DEFAULT_GOOGLE_ADAPTER = GoogleRoutesAdapter()
_DEFAULT_MOCK_ADAPTER = MockRoutesAdapter()


def mock_fallback_allowed(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether synthetic mock route estimates may be shown.

    Allowed only when the runtime is not production-like, unless an operator has
    explicitly opted in with ``DEMO_ROUTES_FALLBACK`` (demo mode). Production-like
    runtimes never surface a fabricated route.
    """

    values = environ if environ is not None else os.environ
    mode = (values.get(APP_ENV_ENV, "development") or "development").strip().lower()
    if mode in PRODUCTION_MODES:
        # Production/preview: only an explicit demo opt-in enables mock estimates.
        return (values.get(DEMO_ROUTES_FALLBACK_ENV, "") or "").strip().lower() in {"1", "true", "yes", "on"}
    return True


class InvalidRouteRequestError(ValueError):
    """Raised for client-correctable route request problems (e.g. unsupported mode)."""


def supported_modes() -> list[str]:
    """Return the bounded set of supported travel modes."""

    return list(SUPPORTED_MODES)


def _cache_key(
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str,
) -> tuple[Any, ...]:
    return (
        round(float(origin[0]), _CACHE_COORD_PRECISION),
        round(float(origin[1]), _CACHE_COORD_PRECISION),
        round(float(destination[0]), _CACHE_COORD_PRECISION),
        round(float(destination[1]), _CACHE_COORD_PRECISION),
        mode,
    )


def clear_route_cache() -> None:
    """Clear the in-memory route cache (used by tests)."""

    with _cache_lock:
        _cache.clear()


def _minutes(seconds: int) -> int:
    return int(round(seconds / 60))


def _resolved_response(route: dict[str, Any]) -> dict[str, Any]:
    source = route["source"]
    fallback = source == "mock"
    return {
        "status": "resolved",
        "source": source,
        "mode": route["mode"],
        "duration_min": _minutes(int(route["duration_seconds"])),
        "duration_seconds": int(route["duration_seconds"]),
        "distance_m": int(route["distance_m"]),
        "partial": fallback,
        "fallback": fallback,
        "message": MOCK_ROUTE_NOTE if fallback else "已取得路線估算。",
        "disclaimer": ROUTE_DISCLAIMER,
    }


def _unresolved_response(mode: str) -> dict[str, Any]:
    return {
        "status": "unresolved",
        "source": "none",
        "mode": mode,
        "duration_min": None,
        "duration_seconds": None,
        "distance_m": None,
        "partial": False,
        "fallback": False,
        "message": "找不到可用路線，請確認起點與目的地是否正確。",
        "disclaimer": ROUTE_DISCLAIMER,
    }


def _unavailable_response(mode: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "none",
        "mode": mode,
        "duration_min": None,
        "duration_seconds": None,
        "distance_m": None,
        "partial": False,
        "fallback": False,
        "message": "路線服務暫時無法完成查詢，請稍後再試。",
        "disclaimer": ROUTE_DISCLAIMER,
    }


def estimate_commute_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str,
    *,
    google_adapter: RoutesAdapter | None = None,
    mock_adapter: RoutesAdapter | None = None,
    use_cache: bool = True,
    allow_mock: bool | None = None,
) -> dict[str, Any]:
    """Estimate a single origin -> destination route with cache and gated fallback.

    Order: cache -> Google Routes (if configured) -> gated Mock fallback.

    In a production-like runtime a Google failure returns ``unavailable`` and never a
    synthetic route. Mock fallback is used only when ``allow_mock`` resolves True
    (dev/test, or explicit demo opt-in). Mock/fallback results are never cached, so a
    later Google recovery is not masked.
    """

    if not is_supported_mode(mode):
        raise InvalidRouteRequestError(f"Unsupported travel mode: {mode}")

    google = google_adapter if google_adapter is not None else _DEFAULT_GOOGLE_ADAPTER
    mock = mock_adapter if mock_adapter is not None else _DEFAULT_MOCK_ADAPTER
    mock_ok = mock_fallback_allowed() if allow_mock is None else allow_mock

    key = _cache_key(origin, destination, mode)
    if use_cache:
        with _cache_lock:
            cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
            return dict(cached[1])

    response: dict[str, Any]
    if google.available:
        try:
            route = google.compute_route(origin, destination, mode)
            response = _resolved_response(route)
        except RouteNotFoundError:
            response = _unresolved_response(mode)
        except RouteUnavailableError:
            response = _fallback_or_unavailable(mock, origin, destination, mode, allow_mock=mock_ok)
        except RoutesAdapterError:
            # Malformed provider data or provider-side validation: fail closed to unavailable.
            response = _unavailable_response(mode)
    else:
        response = _fallback_or_unavailable(mock, origin, destination, mode, allow_mock=mock_ok)

    # Cache only genuine Google observations and deterministic non-fallback outcomes.
    # Never cache mock/fallback results, so provider recovery is not masked.
    cacheable = (
        response.get("status") in {"resolved", "unresolved"}
        and not response.get("fallback")
        and response.get("source") != "mock"
    )
    if use_cache and cacheable:
        with _cache_lock:
            _cache[key] = (time.monotonic(), dict(response))
    return response


def _fallback_or_unavailable(
    mock: RoutesAdapter,
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str,
    *,
    allow_mock: bool,
) -> dict[str, Any]:
    if not allow_mock:
        # Production-like runtime: degrade rather than fabricate a travel time.
        return _unavailable_response(mode)
    try:
        route = mock.compute_route(origin, destination, mode)
    except RoutesAdapterError:
        return _unavailable_response(mode)
    return _resolved_response(route)
