"""Static contracts for the immersive viewing workspace."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
FINDER = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_workspace_exists_and_preserves_original_map_insight() -> None:
    assert "沉浸式看房工作台" in WORKSPACE
    assert "ImmersiveViewingWorkspace" in FINDER
    assert "function MapInsight()" in PAGE
    assert "GeoMap" in PAGE


def test_workspace_has_flow_summary_and_sticky_location_panel() -> None:
    for text in ("找房雷達", "估價", "市場趨勢", "貸款月付", "持有成本", "區位分析", "區位地圖摘要卡", "分析區位", "匯出看屋報告"):
        assert text in WORKSPACE
    assert "lg:sticky" in WORKSPACE
    assert "lg:grid-cols-[minmax(0,1fr)_340px]" in WORKSPACE
    assert "min-w-0" in WORKSPACE
    assert "sm:grid-cols-[minmax(0,1fr)_minmax(260px,360px)]" in WORKSPACE
    assert "<PropertyGuideMascot stage={stage} />" in WORKSPACE


def test_workspace_uses_existing_results_without_api_calls() -> None:
    assert "publishWorkspaceContext" in PAGE
    assert "sessionStorage" in WORKSPACE
    assert "api." not in WORKSPACE
    assert "下一步：" in WORKSPACE
