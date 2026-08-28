"""Static contracts for the rule-based risk summary."""

import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIB = (ROOT / "frontend_next" / "lib" / "risk-summary.ts").read_text(encoding="utf-8")
PANEL = (ROOT / "frontend_next" / "components" / "risk-summary-panel.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
HTML = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")


def run_risk_case(case_name: str) -> dict:
    """Transpile risk-summary.ts and its @/lib deps, then run buildRiskSummary."""
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const path = require("path");
        const vm = require("vm");
        const ROOT = {json.dumps(str(ROOT))};
        const ts = require(path.join(ROOT, "frontend_next", "node_modules", "typescript"));
        const cache = {{}};
        function loadLib(name) {{
          if (cache[name]) return cache[name].exports;
          const file = path.join(ROOT, "frontend_next", "lib", name + ".ts");
          const source = fs.readFileSync(file, "utf8");
          const js = ts.transpileModule(source, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
          const module = {{ exports: {{}} }};
          cache[name] = module;
          const localRequire = (spec) => spec.startsWith("@/lib/") ? loadLib(spec.slice("@/lib/".length)) : require(spec);
          vm.runInNewContext(js, {{ module, exports: module.exports, require: localRequire, console }});
          return module.exports;
        }}
        const {{ buildRiskSummary }} = loadLib("risk-summary");

        // Inputs engineered so the numeric weighted score crosses the green
        // threshold (>=75): official high-confidence valuation, reasonable
        // price, healthy burdens, strong location.
        const valuation = {{ confidence_score: 90, estimate_data_composition: "official_plvr", price_range: {{ low: 900, mid: 1000, high: 1100 }} }};
        const loan = {{ property_price_wan: 1000, income_burden_ratio: 0.2 }};
        const holding = {{ property_price_wan: 1000, income_burden_ratio: 0.25 }};
        const location = {{ location_score: 85, data_quality: {{ status: "good", missing_sources: [] }}, poi_summary: {{ risk_facility_count: 0 }}, valuation_context: {{ supports_price_reasonableness: true, explanation: "ok" }} }};
        const propertySearch = {{}};
        const trend = {{}};

        const terrainKnownLow = {{ overall: {{ level: "low", summary: "ref" }}, data_quality: {{ status: "good", warnings: [] }}, source_transparency: {{ layers: [{{ layer_id: "flood", display_name: "F", source_name: "NLSC", source_kind: "hazard", assessment_status: "matched", coverage_status: "covered", data_updated_at: "2026-01", caveat: "" }}] }}, hazards: {{}}, terrain: {{ status: "available", explanation: "" }} }};
        const terrainKnownHigh = {{ overall: {{ level: "high", summary: "ref" }}, data_quality: {{ status: "good", warnings: [] }}, source_transparency: {{ layers: [{{ layer_id: "landslide", display_name: "L", source_name: "NLSC", source_kind: "hazard", assessment_status: "matched", coverage_status: "covered", data_updated_at: "2026-01", caveat: "" }}] }}, hazards: {{}}, terrain: {{ status: "available", explanation: "" }} }};
        const terrainUnavailable = {{ overall: {{ level: "unknown", summary: "資料不足" }}, data_quality: {{ status: "unavailable", warnings: [] }}, hazards: {{}}, terrain: {{ status: "unavailable", explanation: "" }} }};

        const base = {{ propertySearch, valuation, trend, loan, holding, location }};
        const cases = {{
          knownLow: {{ ...base, terrainRisk: terrainKnownLow }},
          knownHigh: {{ ...base, terrainRisk: terrainKnownHigh }},
          unavailable: {{ ...base, terrainRisk: terrainUnavailable }},
          absent: {{ ...base }},
        }};
        console.log(JSON.stringify(buildRiskSummary(cases[{json.dumps(case_name)}])));
        """
    )
    output = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8")
    return json.loads(output)


def test_terrain_known_low_allows_green_signal() -> None:
    summary = run_risk_case("knownLow")
    assert summary["overallSignal"] == "green"
    assert "riskSummary.missingTerrain" not in summary["missingChecks"]


def test_terrain_known_high_forces_red_signal() -> None:
    summary = run_risk_case("knownHigh")
    assert summary["overallSignal"] == "red"


def test_green_numeric_plus_unavailable_terrain_is_not_unrestricted_green() -> None:
    # Mandatory Case 10 regression: numeric score would be green, terrain
    # unavailable -> user-facing signal must not stay green, and the terrain
    # gap must be surfaced.
    summary = run_risk_case("unavailable")
    assert summary["overallSignal"] != "green"
    assert summary["overallSignal"] == "yellow"
    assert "riskSummary.missingTerrain" in summary["missingChecks"]
    # Numeric score remains internally available (formula preserved).
    assert summary["overallScore"] is not None


def test_absent_terrain_is_not_unrestricted_green() -> None:
    summary = run_risk_case("absent")
    assert summary["overallSignal"] != "green"
    assert "riskSummary.missingTerrain" in summary["missingChecks"]


def test_missing_terrain_copy_exists_in_all_locales() -> None:
    for key in ("riskSummary.missingTerrain", "decision.riskTerrainHigh"):
        occurrences = RUNTIME_COPY.count(f'"{key}": "')
        assert occurrences >= 4, f"{key} must appear in all 4 locales (found {occurrences})"


def test_risk_summary_has_explicit_rule_based_signals_and_weights() -> None:
    for signal in ('"green"', '"yellow"', '"red"', '"unknown"'):
        assert signal in LIB
    for threshold in ("score >= 75", "score >= 55", "valuationScore * 0.25", "priceScore * 0.25", "loanScore * 0.15", "holdingScore * 0.15", "locationScore * 0.15", "completenessScore * 0.05"):
        assert threshold in LIB
    assert "completedCoreModules >= 2" in LIB
    assert "api." not in LIB


def test_price_and_burden_rules_are_explicit() -> None:
    # (a) Business logic rules remain intact in risk-summary.ts
    for rule in ("valuation.price_range.low * 0.95", "valuation.price_range.high * 1.05", "0.3", "0.4", "0.35", "0.45", "location.location_score >= 75", "location.location_score < 55"):
        assert rule in LIB
    for status in ("undervalued", "reasonable", "overpriced"):
        assert status in LIB
    assert "supports_price_reasonableness" in LIB

    # (a) risk-summary.ts uses riskSummary.* semantic keys for display strings
    risk_summary_keys_in_lib = [
        "riskSummary.priceUnknown", "riskSummary.priceUndervalued",
        "riskSummary.priceOverpriced", "riskSummary.priceReasonable",
        "riskSummary.burdenHealthy", "riskSummary.burdenCaution", "riskSummary.burdenHigh",
        "riskSummary.locationGood", "riskSummary.locationMedium", "riskSummary.locationLow",
        "riskSummary.titleLoan", "riskSummary.titleHolding", "riskSummary.titleLocation",
        "riskSummary.titlePrice", "riskSummary.titleConfidence",
        "riskSummary.missingValuation", "riskSummary.missingPrice",
        "riskSummary.missingLoan", "riskSummary.missingHolding",
        "riskSummary.missingLocation", "riskSummary.missingTrend",
        "riskSummary.nextGreen", "riskSummary.nextYellow", "riskSummary.nextRed",
    ]
    for key in risk_summary_keys_in_lib:
        assert key in LIB, f"risk-summary.ts must reference semantic key {key}"

    # (b) runtime-copy.ts has all required riskSummary.* keys in all 4 locales
    required_copy_keys = [
        "riskSummary.labelGreen", "riskSummary.labelYellow", "riskSummary.labelRed", "riskSummary.labelUnknown",
        "riskSummary.suggestionGreen", "riskSummary.suggestionYellow", "riskSummary.suggestionRed", "riskSummary.suggestionUnknown",
        "riskSummary.priceUnknown", "riskSummary.priceUndervalued", "riskSummary.priceOverpriced", "riskSummary.priceReasonable",
        "riskSummary.priceUnknownExplanation", "riskSummary.priceUndervaluedExplanation", "riskSummary.priceOverpricedExplanation", "riskSummary.priceReasonableExplanation",
        "riskSummary.burdenHealthy", "riskSummary.burdenCaution", "riskSummary.burdenHigh",
        "riskSummary.locationGood", "riskSummary.locationMedium", "riskSummary.locationLow",
        "riskSummary.riskFacilityWarning",
        "riskSummary.nextGreen", "riskSummary.nextYellow", "riskSummary.nextRed", "riskSummary.nextOverpriced", "riskSummary.nextLocation",
    ]
    for key in required_copy_keys:
        occurrences = RUNTIME_COPY.count(f'"{key}"')
        assert occurrences >= 4, f"riskSummary key {key} must appear in all 4 locales (found {occurrences})"


def test_risk_panel_and_workspace_integration_exist() -> None:
    for text in ("risk.heading", "risk.priceReasonableness", "risk.positiveFactors", "risk.riskFactors", "risk.missingChecks", "risk.nextSteps"):
        assert text in PANEL
    assert "RiskSummaryPanel" in WORKSPACE
    assert "buildRiskSummary" in WORKSPACE
    assert "min-w-0" in PANEL
    assert "overflow-hidden" in PANEL
    assert 'id="risk-summary"' in PANEL


def test_html_summary_contains_risk_summary_and_disclaimer() -> None:
    for text in ("風險總評 / 開價合理性", "補查清單", "下一步建議", "主要加分", "主要風險", "不代表正式鑑價、銀行核貸或投資建議"):
        assert text in HTML


def test_risk_summary_does_not_claim_black_box_or_formal_advice() -> None:
    combined = f"{LIB}\n{PANEL}"
    assert "black-box" not in combined.lower()
    assert "正式鑑價、銀行核貸或投資建議" in PANEL or 'copy("risk.boundary")' in PANEL
