"""Static contracts for Decision Flow Polish v1."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
PAGE = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")
FINDER = (FRONTEND / "components" / "property-finder.tsx").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")
COMMUTE = (FRONTEND / "components" / "commute-livability-card.tsx").read_text(encoding="utf-8")
VIEWING_PANEL = (FRONTEND / "components" / "viewing-decision-panel.tsx").read_text(encoding="utf-8")
DECISION_REPORT = (FRONTEND / "components" / "decision-report.tsx").read_text(encoding="utf-8")


def test_home_has_single_primary_property_finder_entry() -> None:
    assert "輸入物件資訊，開始看房決策" in PAGE
    assert "開始找物件" in PAGE
    assert 'openViewingFlow("property-finder")' in PAGE
    assert "物件決策工作台" in PAGE


def test_decision_flow_steps_are_visible_without_enforced_wizard() -> None:
    for text in ("找物件", "看位置", "算價格與資金", "比較與做決策"):
        assert text in PAGE
    assert "不強迫" not in PAGE
    assert "api." not in PAGE.split("function DecisionFlowEntry", 1)[1].split("function SectionTitle", 1)[0]


def test_existing_capabilities_are_grouped_progressively() -> None:
    for text in (
        "Location Insight",
        "Terrain Risk",
        "通勤與生活機能",
        "Valuation 價格合理性",
        "Aegis Credit／貸款",
        "Holding Cost",
        "TaxOracle 稅務快篩",
        "Viewing Decision Panel",
        "Decision Report",
        "Case Manager",
        "Case Comparison",
        "列印／另存 PDF",
    ):
        assert text in PAGE
    assert "保存、比較、匯出與其他下一步" in PAGE
    assert '<details id="decision-next-actions"' in PAGE


def test_commute_card_stays_in_location_livability_area() -> None:
    assert "CommuteLivabilityCard" in LOCATION
    assert "通勤與生活機能" in PAGE
    assert "不會改變任何風險或看房結論" in COMMUTE
    assert "/commute/address-lookup" not in PAGE


def test_property_finder_appears_before_workspace() -> None:
    rendered = FINDER.split("return <div", 1)[1].split("function PropertyFinderResults", 1)[0]
    assert rendered.index('id="property-finder"') < rendered.index("ImmersiveViewingWorkspace")
    assert "尚未開始找房" in FINDER
    assert "請先輸入預算與地點" in FINDER


def test_viewing_decision_logic_is_not_replaced() -> None:
    assert "ViewingDecisionPanel" in PAGE
    assert "buildViewingDecision" in PAGE
    assert "ViewingDecisionPanel" in VIEWING_PANEL
    assert "ViewingDecisionPanel" in DECISION_REPORT
    assert "commute" not in VIEWING_PANEL.lower()
    assert "commute" not in DECISION_REPORT.lower()


def test_no_new_automatic_api_or_storage_in_polish_sections() -> None:
    polish_section = PAGE.split("function DecisionFlowEntry", 1)[1].split("function SectionTitle", 1)[0]
    assert "api." not in polish_section
    assert "localStorage" not in polish_section
    assert "sessionStorage" not in polish_section
    assert "location.search" not in polish_section
    assert "location.hash" not in polish_section
