"""Static contracts for the immersive viewing workspace."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
FINDER = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_workspace_exists_and_preserves_original_map_insight() -> None:
    assert "useExperienceLocale" in WORKSPACE
    assert "ImmersiveViewingWorkspace" in FINDER
    assert "function MapInsight()" in PAGE
    assert "GeoMap" in PAGE
    assert 'id="immersive-workspace"' in WORKSPACE
    assert 'id="map-insight"' in PAGE

def test_workspace_has_flow_summary_and_sticky_location_panel() -> None:
    assert "activeWizardStep={activeWizardStep.id}" in WORKSPACE
    assert "lg:sticky" in WORKSPACE
    assert "min-w-0" in WORKSPACE
    assert "WorkflowCommandCenter" in WORKSPACE
    for key in ("finder.title", "location.title", "valuation.title", "loan.title"):
        assert f'copy("{key}")' in WORKSPACE

def test_workspace_uses_existing_results_without_api_calls() -> None:
    assert "publishWorkspaceContext" in PAGE
    assert "sessionStorage" in WORKSPACE
    assert "api." not in WORKSPACE
    assert "buildRiskSummary" in WORKSPACE
    assert "RiskSummaryPanel" in WORKSPACE
    assert "WorkflowCommandCenter" in WORKSPACE
