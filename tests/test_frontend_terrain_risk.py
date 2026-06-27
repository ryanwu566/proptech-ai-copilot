"""Static contracts for terrain and disaster risk frontend integration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "terrain-risk-analysis.tsx").read_text(encoding="utf-8")
LOCATION = (ROOT / "frontend_next" / "components" / "location-insight.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
SIDEBAR = (ROOT / "frontend_next" / "components" / "sidebar.tsx").read_text(encoding="utf-8")
REPORT = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
HELP = (ROOT / "frontend_next" / "lib" / "help-content.ts").read_text(encoding="utf-8")
RISK = (ROOT / "frontend_next" / "lib" / "risk-summary.ts").read_text(encoding="utf-8")
CASE_STORAGE = (ROOT / "frontend_next" / "lib" / "case-storage.ts").read_text(encoding="utf-8")
CASE_COMPARISON = (ROOT / "frontend_next" / "lib" / "case-comparison.ts").read_text(encoding="utf-8")
DEMO_RUNNER = (ROOT / "frontend_next" / "lib" / "demo-runner.ts").read_text(encoding="utf-8")
GUIDED_DEMO = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")


def test_lexprop_is_not_a_frontend_main_entry() -> None:
    assert "LexProp Lite" not in SIDEBAR
    assert "判決風險摘要" not in PAGE
    assert "api.lexprop" not in PAGE
    assert "Terrain Risk" in SIDEBAR


def test_terrain_risk_component_has_real_api_flow_and_states() -> None:
    assert "export function TerrainRiskAnalysis" in COMPONENT
    assert "api.terrainRiskAnalyze" in COMPONENT
    assert "開始分析地勢風險" in COMPONENT
    assert "分析中..." in COMPONENT
    assert "ErrorState" in COMPONENT
    assert "尚未分析" in COMPONENT
    assert "setTimeout" not in COMPONENT
    assert "@/components/detail-disclosure" not in COMPONENT
    assert "@/lib/view-mode" not in COMPONENT
    assert "@/components/view-mode-toggle" not in COMPONENT


def test_terrain_risk_displays_required_layers_and_official_links() -> None:
    for text in ("坡度", "淹水", "坡地災害", "地質敏感", "土壤液化", "活動斷層", "官方來源", "前往官方圖台查看"):
        assert text in COMPONENT
    assert "無風險" not in COMPONENT
    assert "HELP_CONTENT.terrainRisk" in COMPONENT
    assert "不代表建築結構鑑定" in HELP


def test_terrain_risk_is_integrated_with_location_and_report() -> None:
    assert "TerrainRiskAnalysis" in LOCATION
    assert "location={result}" in LOCATION
    assert "terrainRiskAnalyze" in API
    assert "/terrain-risk/analyze" in API
    assert "地勢與災害風險" in REPORT
    assert "readTerrainRiskResult" in REPORT


def test_terrain_risk_session_event_and_workflow_data_flow() -> None:
    assert 'TERRAIN_RISK_SESSION_KEY = "proptech:terrain-risk-result"' in COMPONENT
    assert 'TERRAIN_RISK_RESULT_EVENT = "proptech:terrain-risk-result-ready"' in COMPONENT
    assert "window.sessionStorage.setItem(TERRAIN_RISK_SESSION_KEY" in COMPONENT
    assert "new CustomEvent<TerrainRiskResult>(TERRAIN_RISK_RESULT_EVENT" in COMPONENT
    assert "TERRAIN_RISK_SESSION_KEY" in PAGE
    assert "terrainRiskValue=window.sessionStorage.getItem(TERRAIN_RISK_SESSION_KEY)" in PAGE
    assert "terrainRisk})" in PAGE
    assert "saved.data.terrainRisk" in PAGE


def test_terrain_risk_flows_into_summary_case_demo_and_comparison() -> None:
    assert "terrainRisk?: TerrainRiskResult" in RISK
    assert "addTerrainRisk(terrainRisk" in RISK
    assert "地勢與災害風險資料不足" in RISK
    assert "可用官方圖資目前未比對到明確風險，仍需實地確認" in RISK
    assert "terrainRisk?: TerrainRiskResult" in CASE_STORAGE
    assert "proptech:terrain-risk-result" in CASE_STORAGE
    assert "risk_factors: data.terrainRisk.risk_factors.slice(0, 10)" in CASE_STORAGE
    assert "map_layers: data.terrainRisk.map_layers.slice(0, 10)" in CASE_STORAGE
    assert "terrainRiskLevel" in CASE_COMPARISON
    assert "地勢風險" in CASE_COMPARISON
    assert "terrainRisk" in WORKSPACE
    assert "buildRiskSummary({ propertySearch: search, valuation, trend, loan, holding: holdingResult, location, terrainRisk })" in WORKSPACE
    assert "POST /terrain-risk/analyze（optional）" in DEMO_RUNNER
    assert "api.terrainRiskAnalyze" in DEMO_RUNNER
    assert "TERRAIN_RISK_SESSION_KEY" in GUIDED_DEMO
