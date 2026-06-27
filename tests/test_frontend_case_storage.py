"""Static contracts for browser-only saved analysis cases."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = (ROOT / "frontend_next" / "lib" / "case-storage.ts").read_text(encoding="utf-8")


def test_case_storage_uses_versioned_local_storage_and_ten_case_limit() -> None:
    assert 'proptech.savedCases.v1' in STORAGE
    assert "window.localStorage" in STORAGE
    assert "MAX_SAVED_CASES = 10" in STORAGE
    assert ".slice(0, MAX_SAVED_CASES)" in STORAGE
    assert "version: 1" in STORAGE


def test_case_storage_can_save_load_delete_clear_without_api_calls() -> None:
    for function in ("saveCase", "loadSavedCase", "deleteSavedCase", "clearSavedCases", "clearCurrentCase"):
        assert f"function {function}" in STORAGE
    assert "window.sessionStorage" in STORAGE
    assert "CASE_LOADED_EVENT" in STORAGE
    assert "CASE_CLEARED_EVENT" in STORAGE
    assert "api." not in STORAGE


def test_large_result_lists_are_bounded() -> None:
    for field in ("matched_transactions", "comparables", "nearest_pois", "terrainRisk"):
        assert field in STORAGE
    assert ".slice(0, 20)" in STORAGE
    assert "proptech:terrain-risk-result" in STORAGE
