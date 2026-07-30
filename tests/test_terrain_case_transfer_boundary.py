"""Explicit terrain-reference attachment and privacy contracts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = (ROOT / "frontend_next/components/terrain-risk-analysis.tsx").read_text(encoding="utf-8")
STORAGE = (ROOT / "frontend_next/lib/case-storage.ts").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next/components/immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")


def test_attachment_requires_explicit_button_and_never_auto_saves() -> None:
    assert 'type="button"' in COMPONENT
    assert "onReferenceAttach" in COMPONENT
    assert "TERRAIN_REFERENCE_EVIDENCE_EVENT" in COMPONENT
    assert "window.localStorage" not in COMPONENT
    assert "window.sessionStorage.setItem" not in COMPONENT
    assert "saveCase" not in COMPONENT


def test_saved_terrain_is_a_safe_reference_shape() -> None:
    assert "StoredTerrainReferenceEvidenceV1" in STORAGE
    assert "migrateLegacyTerrainReference" in STORAGE
    assert "normalizeStoredTerrainReferenceEvidence" in STORAGE
    assert "terrainReference" in STORAGE
    assert "source_transparency" not in STORAGE
    assert "input: {}" not in STORAGE
    assert "resolved_location: {}" not in STORAGE
    assert "raw_payload" not in STORAGE
    assert "latitude" not in STORAGE
    assert "longitude" not in STORAGE
    assert "source_url" not in STORAGE


def test_guided_location_stage_exposes_explicit_reference_callback() -> None:
    assert "onTerrainReferenceReady" in STAGE
    assert "onReferenceAttach={onTerrainReferenceReady}" in STAGE


def test_workspace_only_persists_sanitized_reference_after_explicit_attachment() -> None:
    assert "attachedTerrainReference" in WORKSPACE
    assert "toStoredTerrainReferenceEvidence" in WORKSPACE
    assert "terrainReference: attachedTerrainReference" in WORKSPACE
    assert "terrainRisk: attachedTerrainRisk" not in WORKSPACE
    assert "setAttachedTerrainReference(undefined)" in WORKSPACE
