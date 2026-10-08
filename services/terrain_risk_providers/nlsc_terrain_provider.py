"""NLSC terrain provider.

This provider uses the optional Taiwan gateway for bounded point queries.
Without a valid gateway or usable response, it preserves the unavailable
official-source fallback and never infers slope from unrelated data.
"""

from __future__ import annotations

from typing import Any

from services.adapters.nlsc_gateway_adapter import NlscGatewayAdapter
from services.provider_request_cache import BoundedRequestCache

from . import base
from .base import source_meta


QUERY_CACHE_TTL_SECONDS = 60
QUERY_CACHE_MAX_ENTRIES = 64
QUERY_CONTRACT_VERSION = "nlsc-numeric-terrain-point-v1"
_QUERY_CACHE = BoundedRequestCache("nlsc", ttl_seconds=QUERY_CACHE_TTL_SECONDS, max_entries=QUERY_CACHE_MAX_ENTRIES)


class NlscTerrainProvider:
    key = "terrain"
    label = "地形／坡度"
    source_url = "https://maps.nlsc.gov.tw/"

    def __init__(self, gateway: NlscGatewayAdapter | None = None) -> None:
        self._owns_gateway = gateway is None
        self._gateway = gateway if gateway is not None else NlscGatewayAdapter()
        self._query_cache = _QUERY_CACHE if gateway is None else BoundedRequestCache(
            "nlsc", ttl_seconds=QUERY_CACHE_TTL_SECONDS, max_entries=QUERY_CACHE_MAX_ENTRIES,
        )

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
        if self._gateway.available:
            try:
                def operation() -> dict[str, Any]:
                    return {**self._gateway.terrain_point(latitude, longitude, radius_m), "fetched_at": base.utc_now()}

                key = (latitude, longitude, type(radius_m).__name__, radius_m,
                       self._gateway.cache_identity, QUERY_CONTRACT_VERSION)
                observation = self._query_cache.run(
                    key, operation, cacheable=lambda item: item["status"] == "available",
                )
            finally:
                if self._owns_gateway:
                    self._gateway.close()
            if observation["status"] == "available":
                return {
                    "status": "available",
                    "slope_value": observation["slope_value"],
                    "slope_class": observation["slope_class"],
                    "elevation_m": observation["elevation_m"],
                    "explanation": "已取得國土測繪中心地形點位資料；實際地形仍應以官方圖資及現場確認。",
                    "source": source_meta(
                        "NLSC 國土測繪中心地形圖資",
                        "內政部國土測繪中心",
                        self.source_url,
                        "available",
                        fetched_at=observation["fetched_at"],
                    ),
                }
        source = source_meta(
            "NLSC 國土測繪中心地形圖資",
            "內政部國土測繪中心",
            self.source_url,
            "unavailable",
        )
        return {
            "status": "unavailable",
            "slope_value": None,
            "slope_class": None,
            "elevation_m": None,
            "explanation": "目前未設定可合法直接查詢單點坡度／高程的官方 API；請前往國土測繪中心圖台確認地形圖資。",
            "source": source,
        }
