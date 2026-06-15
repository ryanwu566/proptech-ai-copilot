"""Static contracts for the guided buying wizard UX."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
ENTRIES = (ROOT / "frontend_next" / "components" / "workflow-entry-cards.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
STATUS = (ROOT / "frontend_next" / "lib" / "buying-wizard-status.ts").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
DEMO = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")


def test_home_has_three_task_oriented_entry_cards() -> None:
    for label in ("我想判斷一間房值不值得看", "我想快速看一次示範", "我想比較幾個候選物件"):
        assert label in ENTRIES
    for handler in ("onStartBuying", "onGuidedDemo", "onOpenCompare", "onOpenTax", "onOpenAdvanced"):
        assert handler in ENTRIES
        assert handler in PAGE
    assert 'id="advanced-tools"' in PAGE


def test_buying_wizard_has_seven_plain_language_steps() -> None:
    for step in ("property_search", "valuation", "affordability", "location", "risk", "report", "tax"):
        assert step in STATUS
    for title in (
        "先找出你預算內可能買得到的路段",
        "確認這個路段的合理價格",
        "看看月付與持有成本撐不撐得住",
        "檢查生活機能與區位條件",
        "看紅黃綠燈號，判斷是否值得看屋",
        "產出可分享的看屋報告",
        "補做稅務快篩",
    ):
        assert title in STATUS
    assert "這個流程會帶你完成一份看屋初篩報告" in WIZARD
    assert "disabled={!enabled}" in WIZARD


def test_completed_steps_and_advanced_tools_are_retained() -> None:
    assert "summaries" in WIZARD
    assert "isWizardStepCompleted" in WIZARD
    assert "wizardSummaries" in WORKSPACE
    assert "Map Insight / GeoMap" in PAGE
    assert 'setPage("Map Insight Lite")' in PAGE
    assert "GuidedDemoRunner" in WORKSPACE
    assert "一鍵 Demo 流程" in DEMO
