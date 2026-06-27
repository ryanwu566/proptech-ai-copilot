"""NLSC terrain provider.

The current implementation exposes official source metadata and an unavailable
status when no confirmed point-query endpoint is configured. It deliberately
does not scrape map pages or infer slope from unrelated data.
"""

from __future__ import annotations

from typing import Any

from .base import source_meta


class NlscTerrainProvider:
    key = "terrain"
    label = "地形／坡度"
    source_url = "https://maps.nlsc.gov.tw/"

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
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
