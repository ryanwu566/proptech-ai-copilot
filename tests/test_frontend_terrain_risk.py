"""Static contracts for reference-only terrain and disaster risk frontend integration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "terrain-risk-analysis.tsx").read_text(encoding="utf-8")
LOCATION = (ROOT / "frontend_next" / "components" / "location-insight.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
REPORT = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
RISK = (ROOT / "frontend_next" / "lib" / "risk-summary.ts").read_text(encoding="utf-8")
CASE_STORAGE = (ROOT / "frontend_next" / "lib" / "case-storage.ts").read_text(encoding="utf-8")
CASE_COMPARISON = (ROOT / "frontend_next" / "lib" / "case-comparison.ts").read_text(encoding="utf-8")
DEMO_RUNNER = (ROOT / "frontend_next" / "lib" / "demo-runner.ts").read_text(encoding="utf-8")
GUIDED_DEMO = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")


def test_terrain_risk_component_has_real_api_flow_and_conservative_states() -> None:
    assert "export function TerrainRiskAnalysis" in COMPONENT
    assert "api.terrainRiskAnalyze" in COMPONENT
    assert "ErrorState" in COMPONENT
    assert "setTimeout" not in COMPONENT
    assert "TERRAIN_REFERENCE_EVIDENCE_EVENT" in COMPONENT
    assert "加入案件作為參考資料" in COMPONENT


def test_terrain_risk_displays_required_layers_and_official_links() -> None:
    for text in ("地勢", "淹水", "坡地災害", "地質敏感", "液化", "活動斷層", "官方來源", "風險資料來源與限制"):
        assert text in COMPONENT
    assert "HELP_CONTENT.terrainRisk" in COMPONENT


def test_terrain_risk_is_integrated_with_location_and_safe_report() -> None:
    assert "TerrainRiskAnalysis" in LOCATION
    assert "location={result}" in LOCATION
    assert "terrainRiskAnalyze" in API
    assert "/terrain-risk/analyze" in API
    assert "地勢與災害參考資料" in REPORT
    assert "StoredTerrainReferenceEvidenceV1" in REPORT


def test_terrain_result_is_runtime_only_and_not_auto_persisted() -> None:
    assert 'TERRAIN_RISK_RESULT_EVENT = "proptech:terrain-risk-result-ready"' in COMPONENT
    assert "new CustomEvent<TerrainRiskResult>(TERRAIN_RISK_RESULT_EVENT" in COMPONENT
    assert "window.sessionStorage.setItem" not in COMPONENT
    assert "TERRAIN_RISK_SESSION_KEY" not in PAGE
    assert "terrainRiskValue=window.sessionStorage.getItem" not in PAGE
    assert "TERRAIN_RISK_SESSION_KEY" not in GUIDED_DEMO
    assert "saved.data.terrainReference" in PAGE


def test_terrain_is_reference_only_in_summary_case_demo_and_comparison() -> None:
    assert "terrainRisk?: TerrainRiskResult" in RISK
    assert "buildTerrainReferenceEvidence" in RISK
    assert "referenceNotes" in RISK
    assert "StoredTerrainReferenceEvidenceV1" in CASE_STORAGE
    assert "migrateLegacyTerrainReference" in CASE_STORAGE
    assert "source_transparency: { notice: evidence.notice" not in CASE_STORAGE
    assert "terrainRiskLevel" in CASE_COMPARISON
    assert "saved.data.terrainRisk" not in CASE_COMPARISON
    assert "terrainReference" in CASE_COMPARISON
    assert "buildRiskSummary({ propertySearch: search, valuation, trend, loan, holding: holdingResult, location, terrainRisk })" in WORKSPACE
    assert "api.terrainRiskAnalyze" in DEMO_RUNNER
    # Keep the contract file terminated by a non-empty line for diff --check.
    assert "僅作看房風險參考，不形成安全結論" in DEMO_RUNNER
