"""GeologyCloud geological hazard provider."""

from __future__ import annotations

from typing import Any

from .base import source_meta, unavailable_layer


class GeologyCloudProvider:
    source_url = "https://www.geologycloud.tw/"

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
        source = source_meta(
            "地質雲與地質敏感圖資",
            "經濟部地質調查及礦業管理中心",
            self.source_url,
            "unavailable",
        )
        explanation = "目前未設定可合法直接比對座標的官方圖資查詢 API；請至地質雲官方圖台確認。"
        return {
            "geological_sensitivity": unavailable_layer("geological_sensitivity", "地質敏感區", source, explanation),
            "liquefaction": unavailable_layer("liquefaction", "土壤液化潛勢", source, explanation),
            "active_fault": unavailable_layer("active_fault", "活動斷層", source, explanation),
        }
