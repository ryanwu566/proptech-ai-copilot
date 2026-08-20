"""Truthful cadastral reference metadata for Terrain results.

NLSC publishes cadastral services, but its current official integration
documentation classifies cadastral WMS/WMTS/API access as an application-
restricted service.  This repository has no verified subscription or vector
contract, so the runtime contract deliberately exposes only the analyzed
point and an explicit not-configured state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


NLSC_CADASTRAL_SOURCE_URL = "https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH"
POINT_REFERENCE_LIMITATION = (
    "POINT_REFERENCE_ONLY：標記僅代表本次分析座標；系統未取得法定地籍向量，"
    "不掌握精確宗地範圍、不計算宗地交集、法定面積或地號。地籍界址仍應以地政事務所鑑界及核發資料為準。"
)


def build_cadastral_evidence(
    latitude: float,
    longitude: float,
    *,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Return safe cadastral reference metadata without a secret or tile URL."""

    return {
        "status": "not_configured",
        "mode": "point_reference_only",
        "provider": "NLSC",
        "provider_name": "內政部國土測繪中心",
        "center": {"lat": float(latitude), "lng": float(longitude)},
        "raster_status": "not_configured",
        "vector_status": "not_configured",
        "attribution": "內政部國土測繪中心（NLSC）",
        "source_url": NLSC_CADASTRAL_SOURCE_URL,
        "limitation": POINT_REFERENCE_LIMITATION,
        "checked_at": checked_at or datetime.now(timezone.utc).isoformat(),
    }
