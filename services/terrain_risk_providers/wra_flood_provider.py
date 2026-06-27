"""WRA flood hazard provider."""

from __future__ import annotations

from typing import Any

from .base import source_meta, unavailable_layer


class WraFloodProvider:
    source_url = "https://fhy.wra.gov.tw/"

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
        source = source_meta(
            "淹水潛勢與防災資訊",
            "經濟部水利署",
            self.source_url,
            "unavailable",
        )
        return unavailable_layer(
            "flood",
            "淹水潛勢",
            source,
            "目前未設定可合法直接查詢座標淹水深度級距的官方 API；請至水利署防災圖台依降雨情境確認。",
        )
