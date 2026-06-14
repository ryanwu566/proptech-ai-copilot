"""Static contracts for the guided buying wizard UX."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
ENTRIES = (ROOT / "frontend_next" / "components" / "workflow-entry-cards.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
STATUS = (ROOT / "frontend_next" / "lib" / "buying-wizard-status.ts").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")


def test_home_has_three_clear_entry_cards() -> None:
    for label in ("開始看房分析", "稅務快篩", "進階工具"):
        assert label in ENTRIES
    for handler in ("onStartBuying", "onOpenTax", "onOpenAdvanced"):
        assert handler in ENTRIES
        assert handler in PAGE
    assert 'id="advanced-tools"' in PAGE


def test_buying_wizard_has_seven_steps_and_locked_future_steps() -> None:
    for step in ("property_search", "valuation", "affordability", "location", "risk", "report", "tax"):
        assert step in STATUS
    assert "BUYING_WIZARD_STEPS" in WIZARD
    assert "disabled={!enabled}" in WIZARD
    assert "isWizardStepCompleted" in WIZARD
    assert "status.nextActionLabel" in WIZARD
    assert "請先完成目前步驟" in WIZARD


def test_completed_steps_use_summary_cards_and_return_to_edit() -> None:
    assert "查看已完成步驟摘要" in WIZARD
    assert "返回修改" in WIZARD
    assert "wizardSummaries" in WORKSPACE
    assert "open={activeWizardStep.id" in WORKSPACE
    assert "<CaseManager current={currentCase}" in WORKSPACE


def test_advanced_tools_retain_map_insight_and_geomap() -> None:
    assert "Map Insight / GeoMap" in PAGE
    assert 'setPage("Map Insight Lite")' in PAGE
