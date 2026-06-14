"""Static contracts for first-time demo quality and flow safety."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
PAGE = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")
FINDER = (FRONTEND / "components" / "property-finder.tsx").read_text(encoding="utf-8")
LOAN = (FRONTEND / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")
HOLDING = (FRONTEND / "components" / "holding-cost-calculator.tsx").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")
RISK = (FRONTEND / "components" / "risk-summary-panel.tsx").read_text(encoding="utf-8")
REPORT = (FRONTEND / "components" / "decision-report.tsx").read_text(encoding="utf-8")
CASES = (FRONTEND / "components" / "case-manager.tsx").read_text(encoding="utf-8")
COMPARE = (FRONTEND / "components" / "case-comparison-panel.tsx").read_text(encoding="utf-8")
WIZARD = (FRONTEND / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")


def test_frontend_has_no_fake_links_or_browser_feedback() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.tsx"))
    lowered = source.lower()
    assert 'href="#"' not in source
    assert "console.log" not in source
    assert "alert(" not in source
    assert "coming soon" not in lowered


def test_demo_quick_start_only_prefills_property_finder() -> None:
    assert "載入示範條件" in FINDER
    for value in ('setCity("台北市")', 'setDistrictText("大安區")', "setBudgetMin(1500)", "setBudgetMax(2500)", "setAreaMin(25)", "setAreaMax(35)", 'setBuildingType("住宅大樓")'):
        assert value in FINDER
    demo_body = FINDER.split("function loadDemoConditions", 1)[1].split("async function search", 1)[0]
    assert "api." not in demo_body
    assert "已載入示範條件，請按開始找房" in FINDER


def test_major_empty_states_explain_the_next_action() -> None:
    for source, text in (
        (FINDER, "請先輸入預算與地點"),
        (PAGE, "選擇區域與物件條件後"),
        (LOAN, "請先輸入總價、利率與貸款年限"),
        (HOLDING, "請先完成貸款或輸入月付"),
        (LOCATION, "請先輸入地址或路段"),
        (RISK, "尚需補查"),
        (REPORT, "請先完成估價與至少兩項主要分析"),
        (CASES, "尚未保存案件"),
        (COMPARE, "請至少選擇兩個案件"),
        (PAGE, "請先選擇案件，然後按開始稅務快篩"),
    ):
        assert text in source


def test_disabled_actions_explain_why_and_tables_stay_contained() -> None:
    assert "請先完成目前步驟" in WIZARD
    assert "selectedIds.length < 2" in CASES
    assert "請先輸入預算上限" in FINDER
    assert "寬限期必須小於貸款年限" in LOAN
    assert "請先完成貸款帶入" in HOLDING
    assert "請先輸入完整地址或路段" in LOCATION
    assert "請先完成稅務快篩才能輸出報告" in PAGE
    assert "max-h-[65vh]" in PAGE
    for source in (COMPARE, PAGE, FINDER, LOAN, HOLDING, LOCATION):
        assert "overflow-x-auto" in source
