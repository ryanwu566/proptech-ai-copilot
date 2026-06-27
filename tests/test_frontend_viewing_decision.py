"""Behavioral contracts for the property viewing decision workflow."""

import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "frontend_next" / "lib" / "viewing-decision.ts"
PANEL = ROOT / "frontend_next" / "components" / "viewing-decision-panel.tsx"
WORKSPACE = ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx"
REPORT = ROOT / "frontend_next" / "components" / "decision-report.tsx"


def run_decision_case(case_name: str) -> dict:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const path = require("path");
        const vm = require("vm");
        const ts = require(path.join({json.dumps(str(ROOT))}, "frontend_next", "node_modules", "typescript"));
        const source = fs.readFileSync({json.dumps(str(HELPER))}, "utf8");
        const js = ts.transpileModule(source, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS }} }}).outputText;
        const module = {{ exports: {{}} }};
        const sandbox = {{ module, exports: module.exports }};
        vm.runInNewContext(js, sandbox);
        const {{ buildViewingDecision }} = module.exports;
        const valuation = {{ price_range: {{ low: 900, mid: 1000, high: 1100 }} }};
        const loan = {{ affordability_level: "comfortable" }};
        const holding = {{ affordability_level: "comfortable" }};
        const location = {{ poi_summary: {{ risk_facility_count: 0 }} }};
        const terrainRisk = {{ overall: {{ level: "low", summary: "目前可用圖資未比對到明確風險" }}, data_quality: {{ status: "good" }} }};
        const baseRisk = {{ overallSignal: "green", riskFactors: [] }};
        const cases = {{
          missing: {{ valuation, loan, holding, location, riskSummary: baseRisk }},
          highRisk: {{ valuation, loan: {{ affordability_level: "risky" }}, holding, location, terrainRisk, riskSummary: {{ overallSignal: "red", riskFactors: [{{ level: "high", title: "負擔風險", message: "月付偏高" }}] }} }},
          ready: {{ valuation, loan, holding, location, terrainRisk, riskSummary: baseRisk }},
          terrainUnavailable: {{ valuation, loan, holding, location, terrainRisk: {{ overall: {{ level: "unknown", summary: "資料不足" }}, data_quality: {{ status: "unavailable" }} }}, riskSummary: baseRisk }},
        }};
        console.log(JSON.stringify(buildViewingDecision(cases[{json.dumps(case_name)}])));
        """
    )
    output = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8")
    return json.loads(output)


def test_missing_critical_data_requires_more_data_and_target() -> None:
    decision = run_decision_case("missing")
    assert decision["status"] == "needs_more_data"
    assert decision["label"] == "建議補資料後再判斷"
    assert "地勢與災害風險" in decision["missingCriticalData"]
    assert decision["nextAction"]["targetId"] == "terrain-risk-analysis"


def test_high_risk_requires_clarification_first() -> None:
    decision = run_decision_case("highRisk")
    assert decision["status"] == "clarify_risk_first"
    assert decision["label"] == "先釐清風險再看屋"
    assert decision["nextAction"]["targetId"] in {"risk-summary", "loan-calculator"}
    assert decision["riskSources"]


def test_complete_data_without_known_high_risk_can_schedule_viewing() -> None:
    decision = run_decision_case("ready")
    assert decision["status"] == "ready_to_view"
    assert decision["label"] == "可安排看屋"
    assert decision["missingCriticalData"] == []
    assert decision["nextAction"]["targetId"] == "decision-report"


def test_unavailable_terrain_is_missing_not_low_risk() -> None:
    decision = run_decision_case("terrainUnavailable")
    assert decision["status"] == "needs_more_data"
    assert "地勢與災害風險" in decision["missingCriticalData"]
    assert decision["label"] != "可安排看屋"


def test_panel_reuses_view_mode_and_existing_disclosure() -> None:
    panel = PANEL.read_text(encoding="utf-8")
    assert "useViewMode" in panel
    assert "DetailDisclosure" in panel
    assert "viewMode === \"beginner\"" in panel
    assert "viewMode === \"pro\"" in panel
    assert "ViewingDecisionPanel" in WORKSPACE.read_text(encoding="utf-8")
    assert "ViewingDecisionPanel" in REPORT.read_text(encoding="utf-8")
