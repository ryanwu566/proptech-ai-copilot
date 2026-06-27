"""Static contracts for plain-language, click-friendly help tooltips."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLTIP = (ROOT / "frontend_next" / "components" / "help-tooltip.tsx").read_text(encoding="utf-8")
CONTENT = (ROOT / "frontend_next" / "lib" / "help-content.ts").read_text(encoding="utf-8")
PRODUCT_UI = (ROOT / "frontend_next" / "components" / "product-ui.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")


def test_help_tooltip_is_click_and_keyboard_accessible() -> None:
    assert "export function HelpTooltip" in TOOLTIP
    assert "onClick={() => setOpen" in TOOLTIP
    assert 'aria-label={`說明：${title}`}' in TOOLTIP
    assert "aria-expanded={open}" in TOOLTIP
    assert 'event.key === "Escape"' in TOOLTIP
    assert 'role="tooltip"' in TOOLTIP


def test_help_content_is_centralized_and_has_required_limits() -> None:
    for key in ("propertyFinder", "valuation", "trend", "loan", "holdingCost", "location", "terrainRisk", "risk", "decisionReport", "taxOracle", "caseSave", "caseComparison", "guidedDemo", "mapInsight", "geoMap", "dataStatus"):
        assert key in CONTENT
    assert "不代表建築結構鑑定" in CONTENT
    for limit in ("不是即時待售物件清單", "不代表正式鑑價", "不代表正式稅務申報建議"):
        assert limit in CONTENT


def test_major_features_receive_shared_help_entries() -> None:
    assert "inferHelpKey" in PRODUCT_UI
    for keyword in ("找房雷達", "估價", "市場趨勢", "貸款月付", "持有成本", "區位分析", "風險總評", "看屋決策報告", "TaxOracle", "Map Insight", "資料狀態"):
        assert keyword in PRODUCT_UI
    assert "HelpTooltip" in WIZARD
    for operation in ("caseSave", "caseComparison", "htmlExport", "shareLink"):
        assert f"HELP_CONTENT.{operation}" in WORKSPACE
