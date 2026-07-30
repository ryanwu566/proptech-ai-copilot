"""Static browser-storage boundary checks for saved property cases."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = (ROOT / "frontend_next/lib/case-storage.ts").read_text(encoding="utf-8")
MANAGER = (ROOT / "frontend_next/components/case-manager.tsx").read_text(encoding="utf-8")


def test_existing_storage_key_is_reused_without_raw_transaction_persistence() -> None:
    assert "proptech.savedCases.v1" in STORAGE
    assert "matched_transactions: []" in STORAGE
    assert "comparables: []" in STORAGE
    assert "resolved_location: null" in STORAGE
    assert "nearest_pois: []" in STORAGE
    assert "StoredTerrainReferenceEvidenceV1" in STORAGE
    assert "terrainReference: normalizeStoredTerrainReferenceEvidence(data.terrainReference) ?? migrateLegacyTerrainReference(data.terrainRisk)" in STORAGE
    assert "terrainRisk: undefined" in STORAGE
    assert "source_transparency" not in STORAGE
    assert "input: {}," not in STORAGE


def test_invalid_or_incomplete_draft_is_not_saved_and_feedback_is_safe() -> None:
    assert "getDraftSaveMissingFields" in STORAGE
    assert "case_name" in STORAGE
    assert "address_or_property_identifier" in STORAGE
    assert 'copy("case.missing"' in MANAGER
    assert 'copy("case.title"' in MANAGER
    assert 'copy("case.address"' in MANAGER

def test_loading_does_not_rehydrate_analysis_results_into_session_storage() -> None:
    load_section = STORAGE.split("export function loadSavedCase", 1)[1].split("export function clearCurrentCase", 1)[0]
    assert "proptech:pending-section" in load_section
    for key in ("proptech:holding-cost-result", "proptech:location-insight-result", "proptech:terrain-risk-result", "proptech:taxoracle-result"):
        assert key not in load_section
