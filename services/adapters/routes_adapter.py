"""Google Routes (computeRoutes) adapter with a normalized, provider-neutral response.

This adapter estimates travel duration and distance between a single origin and a
single destination for one bounded travel mode. It follows the same conventions as
``google_places_adapter``: backend-only credential, explicit field mask, bounded
timeout, normalized output that never exposes the raw Google payload, and fail-closed
handling of malformed data. It performs no route optimization, alternatives, waypoints,
or matrix routing.
"""

from __future__ import annotations

import math
import os
from typing import Any, Protocol

import httpx


ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Explicit field mask keeps billing and payload minimal and prevents pulling
# polylines, alternatives, or other unrequested (and out-of-scope) fields.
FIELD_MASK = "routes.duration,routes.distanceMeters"

# Only modes that can be safely and cheaply supported in this slice. The mapping
# converts our neutral mode names into Google Routes travelMode enums.
SUPPORTED_MODES: dict[str, str] = {
    "transit": "TRANSIT",
    "driving": "DRIVE",
    "walking": "WALK",
}


class RoutesAdapterError(RuntimeError):
    """Raised for sanitized routes adapter failures (never leaks provider detail)."""


class RouteUnavailableError(RoutesAdapterError):
    """Raised when the provider cannot currently answer (timeout, HTTP, quota, malformed)."""


class RouteNotFoundError(RoutesAdapterError):
    """Raised when the provider responds successfully but finds no route."""


def is_supported_mode(mode: str) -> bool:
    """Return whether a travel mode is supported in this bounded slice."""

    return mode in SUPPORTED_MODES


def _is_valid_coordinate(latitude: Any, longitude: Any) -> bool:
    try:
        lat = float(latitude)
        lng = float(longitude)
    except (TypeError, ValueError):
        return False
    return math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180


def _parse_duration_seconds(value: Any) -> int | None:
    """Parse a Google protobuf duration string like ``"1234s"`` into whole seconds."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text.endswith("s"):
        return None
    number = text[:-1]
    try:
        seconds = float(number)
    except ValueError:
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return int(round(seconds))


class RoutesAdapter(Protocol):
    """Estimate a single origin -> destination route without provider-specific shapes."""

    @property
    def available(self) -> bool:
        """Return whether the adapter can attempt a real lookup."""

    def compute_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
    ) -> dict[str, Any]:
        """Return a normalized ``{duration_seconds, distance_m}`` route observation."""


class GoogleRoutesAdapter:
    """Estimate travel time/distance via Google Routes without exposing the API key."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 4.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._owns_client = client is None

    @property
    def available(self) -> bool:
        """Return whether a backend-only Google API key is configured."""

        return bool(self.api_key)

    def compute_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
    ) -> dict[str, Any]:
        """Return a normalized route observation or raise a sanitized error."""

        if not self.available:
            raise RouteUnavailableError("Google Routes credential is not configured")
        if not is_supported_mode(mode):
            raise RoutesAdapterError(f"Unsupported travel mode: {mode}")
        origin_lat, origin_lng = origin
        dest_lat, dest_lng = destination
        if not _is_valid_coordinate(origin_lat, origin_lng):
            raise RoutesAdapterError("Invalid origin coordinate")
        if not _is_valid_coordinate(dest_lat, dest_lng):
            raise RoutesAdapterError("Invalid destination coordinate")

        payload = {
            "origin": {"location": {"latLng": {"latitude": float(origin_lat), "longitude": float(origin_lng)}}},
            "destination": {"location": {"latLng": {"latitude": float(dest_lat), "longitude": float(dest_lng)}}},
            "travelMode": SUPPORTED_MODES[mode],
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        try:
            response = self._get_client().post(ROUTES_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise RouteUnavailableError("Google Routes response timed out") from exc
        except httpx.HTTPStatusError as exc:
            # Covers quota/rate (429) and other HTTP failures without leaking body.
            raise RouteUnavailableError("Google Routes is currently unavailable") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise RouteUnavailableError("Google Routes returned an unusable response") from exc

        return self._normalize(data, mode)

    @staticmethod
    def _normalize(data: Any, mode: str) -> dict[str, Any]:
        """Extract only whitelisted fields; fail closed on malformed data."""

        if not isinstance(data, dict):
            raise RouteUnavailableError("Google Routes payload shape was unusable")
        routes = data.get("routes")
        if not isinstance(routes, list) or not routes:
            # Successful response with no route.
            raise RouteNotFoundError("No route found between the requested points")
        first = routes[0]
        if not isinstance(first, dict):
            raise RouteUnavailableError("Google Routes route shape was unusable")
        duration_seconds = _parse_duration_seconds(first.get("duration"))
        distance_raw = first.get("distanceMeters")
        distance_m: int | None
        if isinstance(distance_raw, bool):  # bool is a subclass of int; reject explicitly
            distance_m = None
        elif isinstance(distance_raw, (int, float)) and math.isfinite(float(distance_raw)) and distance_raw >= 0:
            distance_m = int(round(float(distance_raw)))
        else:
            distance_m = None
        if duration_seconds is None or distance_m is None:
            raise RouteUnavailableError("Google Routes payload was missing required fields")
        return {
            "duration_seconds": duration_seconds,
            "distance_m": distance_m,
            "mode": mode,
            "source": "google_routes",
        }

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            timeout = httpx.Timeout(
                self.timeout_seconds,
                connect=min(1.5, self.timeout_seconds),
                pool=min(1.0, self.timeout_seconds),
            )
            self._client = httpx.Client(timeout=timeout)
        return self._client

    def close(self) -> None:
        """Close an internally owned client; injected clients remain caller-owned."""

        if not self._owns_client:
            return
        client, self._client = self._client, None
        if client is not None:
            client.close()

    def __enter__(self) -> "GoogleRoutesAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class MockRoutesAdapter:
    """Deterministic offline estimate used when Google Routes is unavailable.

    The result is explicitly marked ``source="mock"`` so it can never be mistaken
    for a real Google observation. It uses a haversine great-circle distance and a
    conservative per-mode average speed. It is a demonstration estimate only.
    """

    # Conservative average speeds (meters/second) for a rough, clearly non-authoritative estimate.
    _MODE_SPEED_MPS: dict[str, float] = {
        "transit": 7.5,   # ~27 km/h including stops
        "driving": 8.5,   # ~30 km/h urban
        "walking": 1.3,   # ~4.7 km/h
    }
    # A simple detour factor so straight-line distance is not presented as road distance.
    _ROUTE_FACTOR = 1.3

    @property
    def available(self) -> bool:
        return True

    def compute_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
    ) -> dict[str, Any]:
        if not is_supported_mode(mode):
            raise RoutesAdapterError(f"Unsupported travel mode: {mode}")
        origin_lat, origin_lng = origin
        dest_lat, dest_lng = destination
        if not _is_valid_coordinate(origin_lat, origin_lng):
            raise RoutesAdapterError("Invalid origin coordinate")
        if not _is_valid_coordinate(dest_lat, dest_lng):
            raise RoutesAdapterError("Invalid destination coordinate")
        straight = _haversine_meters(float(origin_lat), float(origin_lng), float(dest_lat), float(dest_lng))
        distance_m = int(round(straight * self._ROUTE_FACTOR))
        speed = self._MODE_SPEED_MPS[mode]
        duration_seconds = int(round(distance_m / speed)) if speed > 0 else 0
        return {
            "duration_seconds": duration_seconds,
            "distance_m": distance_m,
            "mode": mode,
            "source": "mock",
        }


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    value = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
