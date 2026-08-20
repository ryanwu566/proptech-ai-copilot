"""Verified public NLSC LANDSECT raster context (not parcel geometry)."""

from datetime import datetime, timezone
from typing import Any

LANDSECT_SOURCE_URL = "https://maps.nlsc.gov.tw/S09SOA/pro/Wmts_ajax_spec.jsp"
LANDSECT_TILE_URL = "https://wmts.nlsc.gov.tw/wmts/LANDSECT/default/GoogleMapsCompatible/{z}/{y}/{x}"


def build_landsect_context(*, checked_at: str | None = None) -> dict[str, Any]:
    return {
        "status": "VERIFIED_PUBLIC", "semantics": "SECTION_CONTEXT_NOT_PARCEL_BOUNDARY",
        "provider": "NLSC", "layer": "LANDSECT", "tile_url_template": LANDSECT_TILE_URL,
        "attribution": "National Land Surveying and Mapping Center (NLSC)", "source_url": LANDSECT_SOURCE_URL,
        "limitation": "LANDSECT is official cadastral section map context only. It does not identify or verify a parcel boundary, legal area, ownership, or lot.",
        "checked_at": checked_at or datetime.now(timezone.utc).isoformat(),
    }
