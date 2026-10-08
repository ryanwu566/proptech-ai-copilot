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
import weakref
from datetime import datetime, timezone
from typing import Any, Mapping

from services.adapters.routes_adapter import (
    GoogleRoutesAdapter,
    MockRoutesAdapter,
    RouteNotFoundError,
    RoutesAdapter,
    RoutesAdapterError,
    RouteUnavailableError,
    RouteReasonCode,
    SUPPORTED_MODES,
    is_supported_mode,
)
from services.production_config import PRODUCTION_MODES
from services.provider_observability import observe_response
from services.provider_request_cache import BoundedRequestCache


ROUTE_DISCLAIMER = "通勤時間為外部路線估算，僅供生活機能與可及性參考，不代表實際交通、估價或看房結論。"
MOCK_ROUTE_NOTE = "示範估算：非即時 Google 路線結果，僅供操作展示，不可作為真實通勤依據。"

APP_ENV_ENV = "APP_ENV"
DEMO_ROUTES_FALLBACK_ENV = "DEMO_ROUTES_FALLBACK"

CACHE_TTL_SECONDS = 600
_cache = BoundedRequestCache("routes", ttl_seconds=CACHE_TTL_SECONDS, max_entries=256)

# A single default Google adapter reuses its connection pool across requests.
_DEFAULT_GOOGLE_ADAPTER = GoogleRoutesAdapter()
_DEFAULT_MOCK_ADAPTER = MockRoutesAdapter()


class _AdapterIdentity:
    """A weak identity key cannot retain credentials or collide after ID reuse."""

    __slots__ = ("_object_id", "_reference")

    def __init__(self, adapter: RoutesAdapter) -> None:
        self._object_id = id(adapter)
        self._reference = weakref.ref(adapter)

    def __hash__(self) -> int:
        return self._object_id

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, _AdapterIdentity):
            return NotImplemented
        adapter = self._reference()
        return adapter is not None and adapter is other._reference()


def mock_fallback_allowed(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether synthetic mock route estimates may be shown.

    Allowed only when the runtime is not production-like. Production and preview
    runtimes never surface a fabricated route, even if a legacy demo flag is set.
    """

    values = environ if environ is not None else os.environ
    mode = (values.get(APP_ENV_ENV, "development") or "development").strip().lower()
    if mode in PRODUCTION_MODES:
        return False
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
        float(origin[0]),
        float(origin[1]),
        float(destination[0]),
        float(destination[1]),
        mode,
    )


def clear_route_cache() -> None:
    """Clear the in-memory route cache (used by tests)."""

    _cache.clear()


def _minutes(seconds: int) -> int:
    return int(round(seconds / 60))


def checked_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolved_response(route: dict[str, Any]) -> dict[str, Any]:
    source = route["source"]
    fallback = source == "mock"
    return observe_response("routes", {
        "status": "resolved",
        "source": source,
        "mode": route["mode"],
        "duration_min": _minutes(int(route["duration_seconds"])),
        "duration_seconds": int(route["duration_seconds"]),
        "distance_m": int(route["distance_m"]),
        "partial": fallback,
        "fallback": fallback,
        "reason_code": "success",
        "checked_at": checked_at(),
        "message": MOCK_ROUTE_NOTE if fallback else "已取得路線估算。",
        "disclaimer": ROUTE_DISCLAIMER,
    })


def _unresolved_response(mode: str) -> dict[str, Any]:
    return observe_response("routes", {
        "status": "unresolved",
        "source": "none",
        "mode": mode,
        "duration_min": None,
        "duration_seconds": None,
        "distance_m": None,
        "partial": False,
        "fallback": False,
        "reason_code": "route_not_found",
        "checked_at": checked_at(),
        "message": "找不到可用路線，請確認起點與目的地是否正確。",
        "disclaimer": ROUTE_DISCLAIMER,
    })


def _unavailable_response(mode: str, reason_code: RouteReasonCode = "provider_error") -> dict[str, Any]:
    return observe_response("routes", {
        "status": "unavailable",
        "source": "none",
        "mode": mode,
        "duration_min": None,
        "duration_seconds": None,
        "distance_m": None,
        "partial": False,
        "fallback": False,
        "reason_code": reason_code,
        "checked_at": checked_at(),
        "message": "路線服務暫時無法完成查詢，請稍後再試。",
        "disclaimer": ROUTE_DISCLAIMER,
    })


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

    # Provider identity is process-local and opaque; credentials never enter keys.
    configuration = google.request_configuration() if isinstance(google, GoogleRoutesAdapter) else ("routes-v1",)
    if isinstance(google, GoogleRoutesAdapter):
        namespace = google.cache_namespace
    else:
        try:
            namespace = _AdapterIdentity(google)
        except TypeError:
            # Some caller-owned Protocol adapters cannot be weakly referenced.
            # Bypass reuse instead of retaining their credential-bearing object.
            namespace = None
    key = (namespace, bool(google.available), configuration, mock_ok, *_cache_key(origin, destination, mode))
    if use_cache and namespace is not None:
        return _cache.run(
            key,
            lambda: _estimate_uncached(origin, destination, mode, google, mock, mock_ok),
            cacheable=lambda response: response.get("status") in {"resolved", "unresolved"} and not response.get("fallback") and response.get("source") != "mock",
        )
    return _estimate_uncached(origin, destination, mode, google, mock, mock_ok)


def _estimate_uncached(
    origin: tuple[float, float], destination: tuple[float, float], mode: str,
    google: RoutesAdapter, mock: RoutesAdapter, mock_ok: bool,
) -> dict[str, Any]:

    response: dict[str, Any]
    if google.available:
        try:
            route = google.compute_route(origin, destination, mode)
            response = _resolved_response(route)
        except RouteNotFoundError:
            response = _unresolved_response(mode)
        except RouteUnavailableError as exc:
            response = _fallback_or_unavailable(
                mock,
                origin,
                destination,
                mode,
                allow_mock=mock_ok,
                reason_code=exc.reason_code,
            )
        except RoutesAdapterError as exc:
            # Malformed provider data or provider-side validation: fail closed to unavailable.
            response = _unavailable_response(mode, exc.reason_code)
    else:
        response = _fallback_or_unavailable(
            mock,
            origin,
            destination,
            mode,
            allow_mock=mock_ok,
            reason_code="configuration_error",
        )

    return response


def _fallback_or_unavailable(
    mock: RoutesAdapter,
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str,
    *,
    allow_mock: bool,
    reason_code: RouteReasonCode = "provider_error",
) -> dict[str, Any]:
    if not allow_mock:
        # Production-like runtime: degrade rather than fabricate a travel time.
        return _unavailable_response(mode, reason_code)
    try:
        route = mock.compute_route(origin, destination, mode)
    except RoutesAdapterError:
        return _unavailable_response(mode, "provider_error")
    return _resolved_response(route)
