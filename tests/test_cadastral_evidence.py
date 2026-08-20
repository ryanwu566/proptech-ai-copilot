"""Cadastral reference contract and legal-safety tests."""

from __future__ import annotations

import json
from pathlib import Path

from services.cadastral_evidence import build_cadastral_evidence


def test_default_cadastral_contract_is_point_reference_only() -> None:
    evidence = build_cadastral_evidence(25.0375, 121.5645, checked_at="2026-08-20T00:00:00Z")

    assert evidence == {
        "status": "not_configured",
        "mode": "point_reference_only",
        "provider": "NLSC",
        "provider_name": "內政部國土測繪中心",
        "center": {"lat": 25.0375, "lng": 121.5645},
        "raster_status": "not_configured",
        "vector_status": "not_configured",
        "attribution": "內政部國土測繪中心（NLSC）",
        "source_url": "https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH",
        "limitation": evidence["limitation"],
        "checked_at": "2026-08-20T00:00:00Z",
    }
    assert "POINT_REFERENCE_ONLY" in evidence["limitation"]
    assert "精確宗地範圍" in evidence["limitation"]
    assert "tile_url_template" not in evidence


def test_cadastral_contract_contains_no_secret_or_false_vector_claim() -> None:
    serialized = json.dumps(build_cadastral_evidence(25.0375, 121.5645), ensure_ascii=False).lower()

    for secret_marker in ("api_key", "apikey", "token", "credential", "secret"):
        assert secret_marker not in serialized
    for unsafe_claim in ("法定界址已驗證", "精確宗地交集", "已確認地號", "verified parcel polygon"):
        assert unsafe_claim.lower() not in serialized


def test_cadastral_reference_does_not_publish_raster_or_vector_capability() -> None:
    evidence = build_cadastral_evidence(25.0375, 121.5645)

    assert evidence["raster_status"] == "not_configured"
    assert evidence["vector_status"] == "not_configured"
    assert evidence["status"] != "available"


def test_live_cadastral_surface_has_no_affirmative_legal_parcel_claim() -> None:
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "frontend_next/components/terrain-cadastral-evidence.tsx",
            "frontend_next/components/map/terrain-evidence-leaflet-map.tsx",
            "frontend_next/lib/surface-copy.ts",
        )
    ).lower()

    for unsafe_claim in (
        "legal boundary verified",
        "verified parcel polygon",
        "confirmed lot polygon",
        "parcel intersects hazard",
        "exact parcel area",
    ):
        assert unsafe_claim not in source
