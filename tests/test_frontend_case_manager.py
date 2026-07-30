"""Static contracts for recent cases and save/load controls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = (ROOT / "frontend_next" / "components" / "case-manager.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_case_manager_has_save_recent_load_and_clear_controls() -> None:
    for key in ("case.save", "case.recent", "case.clearCurrent", "case.load", "case.delete", "case.clearAll", "case.compare"):
        assert f'copy("{key}"' in MANAGER
    assert "alert(" not in MANAGER

def test_case_manager_has_empty_feedback_and_optional_html_export() -> None:
    for key in ("case.empty", "case.missing", "case.export", "case.confirmDelete"):
        assert f'copy("{key}"' in MANAGER
    assert "onExport" in MANAGER

def test_case_manager_is_available_on_home_and_buying_wizard() -> None:
    assert "<CaseManager listOnly" in PAGE
    assert "<CaseManager current={currentCase}" in WORKSPACE
    assert "buildValuationSummaryHtml" in WORKSPACE
    assert "buildValuationShareUrl" in PAGE
