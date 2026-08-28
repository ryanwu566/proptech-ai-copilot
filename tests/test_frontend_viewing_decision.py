"""Behavioral contracts for the property viewing decision workflow.

Includes the Terrain Unknown Safety Gate regression matrix. The viewing
decision now depends on lib/terrain-safety-gate.ts and
lib/terrain-reference-evidence.ts, so the Node harness transpiles and wires
those modules through a minimal require shim (no bundler needed).
"""

import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "frontend_next" / "lib"
HELPER = LIB / "viewing-decision.ts"
PANEL = ROOT / "frontend_next" / "components" / "viewing-decision-panel.tsx"
WORKSPACE = ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx"
REPORT = ROOT / "frontend_next" / "components" / "decision-report.tsx"


def run_decision_case(case_name: str) -> dict:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const path = require("path");
        const vm = require("vm");
        const ROOT = {json.dumps(str(ROOT))};
        const ts = require(path.join(ROOT, "frontend_next", "node_modules", "typescript"));

        // Minimal loader that transpiles a TS lib module and resolves the
        // "@/lib/<name>" imports used by the terrain safety gate chain.
        const cache = {{}};
        function loadLib(name) {{
          if (cache[name]) return cache[name].exports;
          const file = path.join(ROOT, "frontend_next", "lib", name + ".ts");
          const source = fs.readFileSync(file, "utf8");
          const js = ts.transpileModule(source, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
          const module = {{ exports: {{}} }};
          cache[name] = module;
          const localRequire = (spec) => {{
            if (spec.startsWith("@/lib/")) return loadLib(spec.slice("@/lib/".length));
            return require(spec);
          }};
          const sandbox = {{ module, exports: module.exports, require: localRequire, console }};
          vm.runInNewContext(js, sandbox);
          return module.exports;
        }}

        const {{ buildViewingDecision }} = loadLib("viewing-decision");

        const valuation = {{ price_range: {{ low: 900, mid: 1000, high: 1100 }} }};
        const loan = {{ affordability_level: "comfortable" }};
        const holding = {{ affordability_level: "comfortable" }};
        const location = {{ poi_summary: {{ risk_facility_count: 0 }} }};
        const baseRisk = {{ overallSignal: "green", riskFactors: [] }};

        // Terrain fixtures. data_quality.status drives the reference overall
        // state; overall.level carries the provider risk level.
        const terrainKnownLow = {{ overall: {{ level: "low", summary: "ref" }}, data_quality: {{ status: "good", warnings: [] }}, source_transparency: {{ layers: [{{ layer_id: "flood", display_name: "F", source_name: "NLSC", source_kind: "hazard", assessment_status: "matched", coverage_status: "covered", data_updated_at: "2026-01", caveat: "" }}] }}, hazards: {{}}, terrain: {{ status: "available", explanation: "" }} }};
        const terrainKnownHigh = {{ overall: {{ level: "high", summary: "ref" }}, data_quality: {{ status: "good", warnings: [] }}, source_transparency: {{ layers: [{{ layer_id: "landslide", display_name: "L", source_name: "NLSC", source_kind: "hazard", assessment_status: "matched", coverage_status: "covered", data_updated_at: "2026-01", caveat: "" }}] }}, hazards: {{}}, terrain: {{ status: "available", explanation: "" }} }};
        const terrainUnknown = {{ overall: {{ level: "unknown", summary: "資料不足" }}, data_quality: {{ status: "good", warnings: [] }}, hazards: {{}}, terrain: {{ status: "skipped", explanation: "" }} }};
        const terrainUnavailable = {{ overall: {{ level: "unknown", summary: "資料不足" }}, data_quality: {{ status: "unavailable", warnings: [] }}, hazards: {{}}, terrain: {{ status: "unavailable", explanation: "" }} }};
        const terrainError = {{ overall: {{ level: "unknown", summary: "檢查失敗" }}, data_quality: {{ status: "good", warnings: [] }}, hazards: {{ landslide: {{ key: "landslide", label: "L", status: "error", level: "unknown", matched: false, distance_m: null, value: null, explanation: "" }} }}, terrain: {{ status: "error", explanation: "" }} }};
        const terrainLimited = {{ overall: {{ level: "low", summary: "部分" }}, data_quality: {{ status: "limited", warnings: [] }}, hazards: {{}}, terrain: {{ status: "limited", explanation: "" }} }};
        const terrainNoMatch = {{ overall: {{ level: "low", summary: "未命中" }}, data_quality: {{ status: "good", warnings: [] }}, hazards: {{ flood: {{ key: "flood", label: "F", status: "available", level: "low", matched: false, distance_m: null, value: null, explanation: "" }} }}, terrain: {{ status: "available", explanation: "" }} }};

        const cases = {{
          knownLow: {{ valuation, loan, holding, location, terrainRisk: terrainKnownLow, riskSummary: baseRisk }},
          knownHigh: {{ valuation, loan, holding, location, terrainRisk: terrainKnownHigh, riskSummary: baseRisk }},
          unknown: {{ valuation, loan, holding, location, terrainRisk: terrainUnknown, riskSummary: baseRisk }},
          unavailable: {{ valuation, loan, holding, location, terrainRisk: terrainUnavailable, riskSummary: baseRisk }},
          error: {{ valuation, loan, holding, location, terrainRisk: terrainError, riskSummary: baseRisk }},
          notAssessed: {{ valuation, loan, holding, location, riskSummary: baseRisk }},
          limited: {{ valuation, loan, holding, location, terrainRisk: terrainLimited, riskSummary: baseRisk }},
          noMatch: {{ valuation, loan, holding, location, terrainRisk: terrainNoMatch, riskSummary: baseRisk }},
          otherHighPlusTerrainUnknown: {{ valuation, loan: {{ affordability_level: "risky" }}, holding, location, terrainRisk: terrainUnknown, riskSummary: {{ overallSignal: "red", riskFactors: [{{ level: "high", title: "負擔風險", message: "月付偏高" }}] }} }},
          missingCritical: {{ valuation, loan, holding, riskSummary: baseRisk }},
        }};
        console.log(JSON.stringify(buildViewingDecision(cases[{json.dumps(case_name)}])));
        """
    )
    output = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8")
    return json.loads(output)


# ── Case 1 — known low + positive other dimensions ───────────────────────────
def test_case1_known_low_terrain_allows_ready() -> None:
    decision = run_decision_case("knownLow")
    assert decision["status"] == "ready_to_view"
    assert decision["missingCriticalData"] == []


# ── Case 2 — known high terrain ──────────────────────────────────────────────
def test_case2_known_high_terrain_clarifies_risk() -> None:
    decision = run_decision_case("knownHigh")
    assert decision["status"] == "clarify_risk_first"
    assert "terrain_high" in decision["riskSources"]
    assert decision["nextAction"]["targetId"] == "terrain-risk-analysis"


# ── Case 3 — terrain unknown ─────────────────────────────────────────────────
def test_case3_unknown_terrain_needs_more_data() -> None:
    decision = run_decision_case("unknown")
    assert decision["status"] == "needs_more_data"
    assert decision["status"] != "ready_to_view"


# ── Case 4 — terrain unavailable (the original bug) ──────────────────────────
def test_case4_unavailable_terrain_needs_more_data() -> None:
    decision = run_decision_case("unavailable")
    assert decision["status"] == "needs_more_data"


# ── Case 5 — terrain error ───────────────────────────────────────────────────
def test_case5_error_terrain_needs_more_data() -> None:
    decision = run_decision_case("error")
    assert decision["status"] == "needs_more_data"


# ── Case 6 — terrain not assessed / missing ──────────────────────────────────
def test_case6_not_assessed_terrain_needs_more_data() -> None:
    decision = run_decision_case("notAssessed")
    assert decision["status"] == "needs_more_data"


# ── Case 7 — terrain partial / limited ───────────────────────────────────────
def test_case7_limited_terrain_not_all_clear() -> None:
    decision = run_decision_case("limited")
    assert decision["status"] != "ready_to_view"
    # Not forced to a hard risk state; it is an incomplete-evidence gate.
    assert decision["status"] == "needs_more_data"


# ── Case 8 — terrain no_match ────────────────────────────────────────────────
def test_case8_no_match_terrain_not_all_clear() -> None:
    decision = run_decision_case("noMatch")
    assert decision["status"] != "ready_to_view"


# ── Case 9 — other domain high risk + terrain unknown (known risk wins) ──────
def test_case9_known_risk_dominates_terrain_uncertainty() -> None:
    decision = run_decision_case("otherHighPlusTerrainUnknown")
    assert decision["status"] == "clarify_risk_first"
    assert decision["status"] != "needs_more_data"
    assert decision["riskSources"]


# ── Case 10 — missing critical data still needs more data ────────────────────
def test_case10_missing_critical_still_needs_more_data() -> None:
    decision = run_decision_case("missingCritical")
    assert decision["status"] == "needs_more_data"
    assert "location" in decision["missingCriticalData"]


def test_panel_reuses_view_mode_and_existing_disclosure() -> None:
    panel = PANEL.read_text(encoding="utf-8")
    assert "useViewMode" in panel
    assert "DetailDisclosure" in panel
    assert "viewMode === \"beginner\"" in panel
    assert "viewMode === \"pro\"" in panel
    assert "ViewingDecisionPanel" in WORKSPACE.read_text(encoding="utf-8")
    assert "ViewingDecisionPanel" in REPORT.read_text(encoding="utf-8")


def test_workspace_passes_terrain_to_viewing_decision() -> None:
    workspace = WORKSPACE.read_text(encoding="utf-8")
    # Every buildViewingDecision call with terrain in scope must pass terrainRisk.
    for line in workspace.splitlines():
        if "buildViewingDecision(" in line:
            assert "terrainRisk" in line, f"call site missing terrainRisk: {line.strip()}"
