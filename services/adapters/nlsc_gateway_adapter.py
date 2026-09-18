"""Bounded backend client for NLSC terrain queries through the Taiwan gateway."""

from __future__ import annotations

import math
import os
from typing import Any, Mapping

import httpx

from services.production_config import (
    NLSC_GATEWAY_BASE_URL_ENV,
    NLSC_GATEWAY_CLIENT_TOKEN_ENV,
    load_runtime_configuration,
)


_TERRAIN_PATH = "/nlsc/terrain/point"
_TIMEOUT_SECONDS = 4.0
_SLOPE_CLASSES = frozenset({"gentle", "moderate", "steep"})


def _unavailable() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "slope_value": None,
        "slope_class": None,
        "elevation_m": None,
        "source": "NLSC",
    }


def _valid_coordinate(value: Any, minimum: float, maximum: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and minimum <= value <= maximum and math.isfinite(value)


def _normalize(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("status") != "available" or payload.get("source") != "NLSC":
        return _unavailable()
    slope = payload.get("slope_value")
    elevation = payload.get("elevation_m")
    slope_class = payload.get("slope_class")
    if not _valid_coordinate(slope, 0, 90) or not _valid_coordinate(elevation, -500, 5000):
        return _unavailable()
    if slope_class is not None and slope_class not in _SLOPE_CLASSES:
        return _unavailable()
    return {
        "status": "available",
        "slope_value": slope,
        "slope_class": slope_class,
        "elevation_m": elevation,
        "source": "NLSC",
    }


class NlscGatewayAdapter:
    """Send one validated terrain point request to a configured fixed gateway."""

    def __init__(self, *, client: httpx.Client | None = None, environ: Mapping[str, str] | None = None) -> None:
        values = dict(environ if environ is not None else os.environ)
        self._base_url = values.get(NLSC_GATEWAY_BASE_URL_ENV, "")
        self._client_token = values.get(NLSC_GATEWAY_CLIENT_TOKEN_ENV, "")
        self.configuration_status = load_runtime_configuration(values).nlsc_gateway_status
        self._client = client
        self._owns_client = client is None

    @property
    def available(self) -> bool:
        return self.configuration_status == "configured"

    def terrain_point(self, lat: float, lng: float, radius_m: int) -> dict[str, Any]:
        """Return bounded NLSC measurements or an explicit unavailable result."""

        if not self.available:
            return _unavailable()
        if not _valid_coordinate(lat, 21, 26) or not _valid_coordinate(lng, 119, 123):
            return _unavailable()
        if not isinstance(radius_m, int) or isinstance(radius_m, bool) or not 100 <= radius_m <= 2000:
            return _unavailable()
        try:
            response = self._get_client().post(
                self._base_url.rstrip("/") + _TERRAIN_PATH,
                json={"lat": float(lat), "lng": float(lng), "radius_m": radius_m},
                headers={"Authorization": f"Bearer {self._client_token}"},
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=False,
            )
            response.raise_for_status()
            return _normalize(response.json())
        except Exception:
            # Transport and decoder errors may embed request headers. Never
            # surface their text (or traceback) with the backend credential.
            return _unavailable()

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client()
        return self._client

    def close(self) -> None:
        """Close an internally owned client; injected clients remain caller owned."""

        if not self._owns_client:
            return
        client, self._client = self._client, None
        if client is not None:
            client.close()

    def __enter__(self) -> "NlscGatewayAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
