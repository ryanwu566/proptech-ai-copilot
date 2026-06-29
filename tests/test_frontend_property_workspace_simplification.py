"""Static contracts for Property Decision Workspace Simplification v1."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
PAGE = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")
SIDEBAR = (FRONTEND / "components" / "sidebar.tsx").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")
COMMUTE = (FRONTEND / "components" / "commute-livability-card.tsx").read_text(encoding="utf-8")
VIEWING_DECISION = (FRONTEND / "components" / "viewing-decision-panel.tsx").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "product-capability-surface-v1.md").read_text(encoding="utf-8")


def test_workspace_has_exact_primary_steps_and_progressive_sections() -> None:
    assert 'aria-label="物件決策工作台四步驟"' in PAGE
    for step in ("找物件", "看位置", "算價格與資金", "比較與做決策"):
        assert step in PAGE
    assert "WorkspaceStep" in PAGE
    assert "defaultOpen" in PAGE
    assert "CapabilityPills" in PAGE


def test_top_level_navigation_is_reduced_to_four_groups() -> None:
    for label in ('label: "工作台"', 'label: "地圖"', 'label: "案件"', 'label: "更多工具"'):
        assert label in SIDEBAR
    for old_group in ('label: "案件決策"', 'label: "區域洞察"', 'label: "風險模組"', 'label: "紀錄"'):
        assert old_group not in SIDEBAR


def test_core_capabilities_have_reachable_unique_workspace_entries() -> None:
    for text in (
        "Property Finder",
        "Location Insight",
        "Terrain Risk",
        "風險資料來源與限制",
        "Commute Livability Card",
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
    assert 'onMap={() => setPage("Map Insight Lite")}' in PAGE


def test_commute_remains_manual_and_non_decisional() -> None:
    assert "CommuteLivabilityCard" in LOCATION
    assert "api.commuteAddressLookup" in COMMUTE
    assert "api.commuteAddressLookup" not in COMMUTE.split("useEffect", 1)[1].split("async function lookupCommute", 1)[0]
    assert "不影響地勢、貸款、稅務、估價或看房決策" in PAGE
    assert "commute" not in VIEWING_DECISION.lower()


def test_workspace_overview_adds_no_api_or_browser_storage() -> None:
    workspace_section = PAGE.split("function DecisionWorkspaceSteps", 1)[1].split("function FlowStep", 1)[0]
    for forbidden in ("api.", "localStorage", "sessionStorage", "document.cookie", "location.search", "location.hash"):
        assert forbidden not in workspace_section


def test_capability_surface_documents_statuses_and_blockers() -> None:
    for status in ("ready_and_connected", "needs_user_input", "backend_only", "unavailable"):
        assert status in DOC
    assert "後端通勤快照刷新" in DOC
    assert "前端不得呼叫" in DOC
    assert "資料不足" in DOC
    for forbidden in ("https://", "http://", "Bearer ", "RENDER_API_BASE_URL="):
        assert forbidden not in DOC
