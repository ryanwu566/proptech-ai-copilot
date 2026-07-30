"""Static contracts for first-time demo quality and flow safety."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
PAGE = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")
FINDER = (FRONTEND / "components" / "property-finder.tsx").read_text(encoding="utf-8")
LOAN = (FRONTEND / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")
HOLDING = (FRONTEND / "components" / "holding-cost-calculator.tsx").read_text(encoding="utf-8")
LOAN += (FRONTEND / "components" / "data-visualization" / "loan-visual-panel.tsx").read_text(encoding="utf-8") + (FRONTEND / "components" / "data-visualization" / "calculation-evidence-details.tsx").read_text(encoding="utf-8")
HOLDING += (FRONTEND / "components" / "data-visualization" / "holding-cost-visual-panel.tsx").read_text(encoding="utf-8")
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
    assert 'copy("finder.demo")' in FINDER
    for value in ("setCity(", "setDistrictText(", "setBudgetMin(", "setBudgetMax(", "setAreaMin(", "setAreaMax(", "setBuildingType("):
        assert value in FINDER
    demo_body = FINDER.split("function loadDemoConditions", 1)[1].split("async function search", 1)[0]
    assert "api." not in demo_body
    assert 'copy("finder.search")' in FINDER

def test_major_empty_states_explain_the_next_action() -> None:
    for source, keys in ((FINDER, ("finder.empty", "finder.emptyDetail")), (LOAN, ("loan.emptyDetail",)), (LOCATION, ("location.empty",)), (CASES, ("case.empty",)), (COMPARE, ("case.compareCount",))):
        for key in keys:
            assert f'copy("{key}")' in source or f'copy("{key}"' in source
    assert 'copy("tax.emptyDetail")' in PAGE or "TaxOracle" in PAGE

def test_disabled_actions_explain_why_and_tables_stay_contained() -> None:
    assert "selectedIds.length < 2" in CASES
    assert "finder.budgetRequired" in FINDER
    assert "loan.invalid" in LOAN
    assert "location.empty" in LOCATION
    assert "max-h-[65vh]" in PAGE
    for source in (COMPARE, PAGE, FINDER, LOAN, HOLDING, LOCATION):
        assert "overflow-x-auto" in source

def test_guided_demo_has_product_recovery_actions() -> None:
    guided_demo = (FRONTEND / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
    for action in ("重試 API 預檢", "重試失敗步驟", "從目前進度繼續", "重新開始 Demo", "取消 Demo"):
        assert action in guided_demo
    assert "href=\"#\"" not in guided_demo
    assert "alert(" not in guided_demo
