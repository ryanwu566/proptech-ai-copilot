"""Terrain safety invariant for the rule-based DecisionSummary / DecisionReport /
export-share quick conclusion.

Ensures no user-facing surface shows an unrestricted positive all-clear
("值得進一步看屋" / green) unless terrain evidence positively supports it.
"""

import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION_SUMMARY = ROOT / "frontend_next" / "lib" / "decision-summary.ts"
DECISION_REPORT = ROOT / "frontend_next" / "components" / "decision-report.tsx"
SHARE = ROOT / "frontend_next" / "lib" / "valuation-share.ts"

POSITIVE = "值得進一步看屋"


def run_summary_case(case_name: str) -> dict:
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
        const {{ buildDecisionSummary }} = loadLib("decision-summary");
        const {{ classifyTerrainSafety }} = loadLib("terrain-safety-gate");

        // Positive non-terrain baseline.
        const valuation = {{ confidence: "high", confidence_score: 90, confidence_reason: "ok", price_range: {{ low: 900, mid: 1000, high: 1100 }}, valuation_explanation: {{ sample_count: 5 }} }};
        const loan = {{ affordability_level: "comfortable", monthly_payment: 30000, affordability_message: "ok" }};
        const holding = {{ affordability_level: "comfortable", affordability_message: "ok" }};
        const location = {{ location_score: 85, data_quality: {{ status: "good", missing_sources: [] }}, valuation_context: {{ explanation: "ok" }} }};
        const propertySearch = {{ summary: {{ matched_count: 10 }} }};
        const matched = (id) => ({{ layers: [{{ layer_id: id, display_name: id, source_name: "NLSC", source_kind: "hazard", assessment_status: "matched", coverage_status: "covered", data_updated_at: "2026-01", caveat: "" }}] }});

        const terrains = {{
          knownLow: {{ overall: {{ level: "low" }}, data_quality: {{ status: "good", warnings: [] }}, source_transparency: matched("flood"), hazards: {{}}, terrain: {{ status: "available", explanation: "" }} }},
          knownHigh: {{ overall: {{ level: "high" }}, data_quality: {{ status: "good", warnings: [] }}, source_transparency: matched("slide"), hazards: {{}}, terrain: {{ status: "available", explanation: "" }} }},
          unknown: {{ overall: {{ level: "unknown" }}, data_quality: {{ status: "good", warnings: [] }}, hazards: {{}}, terrain: {{ status: "skipped", explanation: "" }} }},
          unavailable: {{ overall: {{ level: "unknown" }}, data_quality: {{ status: "unavailable", warnings: [] }}, hazards: {{}}, terrain: {{ status: "unavailable", explanation: "" }} }},
          error: {{ overall: {{ level: "unknown" }}, data_quality: {{ status: "good", warnings: [] }}, hazards: {{ h: {{ key: "h", label: "h", status: "error", level: "unknown", matched: false, distance_m: null, value: null, explanation: "" }} }}, terrain: {{ status: "error", explanation: "" }} }},
          limited: {{ overall: {{ level: "low" }}, data_quality: {{ status: "limited", warnings: [] }}, hazards: {{}}, terrain: {{ status: "limited", explanation: "" }} }},
          noMatch: {{ overall: {{ level: "low" }}, data_quality: {{ status: "good", warnings: [] }}, hazards: {{ f: {{ key: "f", label: "f", status: "available", level: "low", matched: false, distance_m: null, value: null, explanation: "" }} }}, terrain: {{ status: "available", explanation: "" }} }},
        }};

        function summaryFor(name) {{
          if (name === "notAssessed") return buildDecisionSummary(propertySearch, valuation, loan, holding, location, classifyTerrainSafety(undefined));
          if (name === "storedRefOnly") return buildDecisionSummary(propertySearch, valuation, loan, holding, location, "unproven");
          return buildDecisionSummary(propertySearch, valuation, loan, holding, location, classifyTerrainSafety(terrains[name]));
        }}
        console.log(JSON.stringify(summaryFor({json.dumps(case_name)})));
        """
    )
    output = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8")
    return json.loads(output)


def _viewing_checklist(summary: dict) -> dict:
    return next(item for item in summary["checklist"] if item["label"] == "是否建議實地看屋")


def test_known_low_allows_positive_headline() -> None:
    summary = run_summary_case("knownLow")
    assert summary["recommendation"] == POSITIVE
    assert _viewing_checklist(summary)["status"] == "通過"


def test_known_high_blocks_positive_headline() -> None:
    summary = run_summary_case("knownHigh")
    assert summary["recommendation"] != POSITIVE
    assert _viewing_checklist(summary)["status"] != "通過"


def test_unknown_blocks_positive_headline() -> None:
    summary = run_summary_case("unknown")
    assert summary["recommendation"] != POSITIVE
    assert _viewing_checklist(summary)["status"] != "通過"


def test_unavailable_blocks_positive_headline() -> None:
    summary = run_summary_case("unavailable")
    assert summary["recommendation"] != POSITIVE
    assert _viewing_checklist(summary)["status"] != "通過"


def test_error_blocks_positive_headline() -> None:
    summary = run_summary_case("error")
    assert summary["recommendation"] != POSITIVE


def test_not_assessed_blocks_positive_headline() -> None:
    summary = run_summary_case("notAssessed")
    assert summary["recommendation"] != POSITIVE
    assert _viewing_checklist(summary)["status"] != "通過"


def test_limited_blocks_positive_headline() -> None:
    summary = run_summary_case("limited")
    assert summary["recommendation"] != POSITIVE


def test_no_match_blocks_positive_headline() -> None:
    summary = run_summary_case("noMatch")
    assert summary["recommendation"] != POSITIVE


def test_stored_reference_only_export_is_conservative() -> None:
    # Export/share path has only stored terrain reference evidence -> "unproven"
    # -> the quick conclusion must not be an unrestricted all-clear.
    summary = run_summary_case("storedRefOnly")
    assert summary["recommendation"] != POSITIVE
    assert _viewing_checklist(summary)["status"] != "通過"


def test_decision_report_wires_terrain_classification() -> None:
    report = DECISION_REPORT.read_text(encoding="utf-8")
    assert "classifyTerrainSafety(terrainRisk)" in report
    assert "buildDecisionSummary(" in report
    # The buildDecisionSummary call must include the terrain classification arg.
    for line in report.splitlines():
        if "buildDecisionSummary(" in line:
            assert "classifyTerrainSafety(terrainRisk)" in line


def test_share_export_passes_unproven_terrain() -> None:
    share = SHARE.read_text(encoding="utf-8")
    for line in share.splitlines():
        if "buildDecisionSummary(" in line:
            assert '"unproven"' in line


def test_share_export_does_not_infer_known_low_from_stored_status() -> None:
    share = SHARE.read_text(encoding="utf-8")
    # Guard against reintroducing: treating stored reference status "available"
    # as a known-low safety proof.
    assert 'terrainReference.status === "available"' not in share
    assert "known_low" not in share


# ── Preserved original static contracts (decision report v2) ─────────────────
def test_decision_report_uses_rule_based_summary_and_checklist() -> None:
    report = DECISION_REPORT.read_text(encoding="utf-8")
    assert "buildDecisionSummary" in report
    for key in ("tour.clientReport", "valuation.basis", "location.risk", "valuation.confidence", "case.status"):
        assert f'copy("{key}")' in report
    assert "riskSummary" in report
    assert "checklist" in report


def test_html_is_upgraded_to_viewing_decision_report_v2() -> None:
    html = SHARE.read_text(encoding="utf-8")
    for text in ("看屋決策報告 v2", "快速結論", "主要理由", "主要風險", "資料信心", "決策 checklist", "年持有成本", "市場趨勢摘要", "風險總評 / 開價合理性", "補查清單"):
        assert text in html
    for text in ("不代表銀行核貸", "不代表正式鑑價", "不代表正式稅務申報", "不代表即時待售物件", "實地確認"):
        assert text in html
