"""Pure frontend reference-evidence and false-safety boundary tests."""

import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "frontend_next/lib/terrain-reference-evidence.ts"
STORAGE = (ROOT / "frontend_next/lib/case-storage.ts").read_text(encoding="utf-8")
RISK = (ROOT / "frontend_next/lib/risk-summary.ts").read_text(encoding="utf-8")
VIEWING = (ROOT / "frontend_next/lib/viewing-decision.ts").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next/components/immersive-viewing-workspace.tsx").read_text(encoding="utf-8")


def run_helper(result_expression: str) -> dict:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const path = require("path");
        const vm = require("vm");
        const ts = require(path.join({json.dumps(str(ROOT))}, "frontend_next", "node_modules", "typescript"));
        const source = fs.readFileSync({json.dumps(str(HELPER))}, "utf8");
        const js = ts.transpileModule(source, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }}, reportDiagnostics: true }}).outputText;
        const module = {{ exports: {{}} }};
        vm.runInNewContext(js, {{ module, exports: module.exports, Set, Map, Object }});
        const result = {result_expression};
        console.log(JSON.stringify(module.exports.buildTerrainReferenceEvidence(result)));
        """
    )
    return json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8"))


def run_helper_export(function_name: str, argument_expression: str) -> object:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const path = require("path");
        const vm = require("vm");
        const ts = require(path.join({json.dumps(str(ROOT))}, "frontend_next", "node_modules", "typescript"));
        const source = fs.readFileSync({json.dumps(str(HELPER))}, "utf8");
        const js = ts.transpileModule(source, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }}, reportDiagnostics: true }}).outputText;
        const module = {{ exports: {{}} }};
        vm.runInNewContext(js, {{ module, exports: module.exports, Set, Map, Object }});
        const result = module.exports[{json.dumps(function_name)}]({argument_expression});
        console.log(JSON.stringify(result ?? null));
        """
    )
    return json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8"))


def test_available_reference_layers_are_allowlisted_and_attachable() -> None:
    evidence = run_helper(
        """({
          data_quality: { status: "good" },
          source_transparency: { layers: [{
            layer_id: "fake-layer",
            display_name: "虛構圖層",
            source_name: "虛構官方來源",
            source_kind: "official",
            assessment_status: "matched",
            coverage_status: "covered",
            data_updated_at: "unknown",
            caveat: "僅供參考"
          }] }
        })"""
    )
    assert evidence["status"] == "available"
    assert evidence["attachable"] is True
    assert evidence["layers"][0]["layer_id"] == "fake-layer"
    assert "latitude" not in json.dumps(evidence)
    assert "longitude" not in json.dumps(evidence)
    assert "raw_payload" not in json.dumps(evidence)


def test_unavailable_reference_is_not_attachable_or_low_risk() -> None:
    evidence = run_helper(
        """({
          data_quality: { status: "unavailable" },
          source_transparency: { layers: [{
            layer_id: "fake-layer",
            display_name: "虛構圖層",
            source_name: "虛構官方來源",
            source_kind: "official",
            assessment_status: "unavailable",
            coverage_status: "unknown",
            data_updated_at: "unknown",
            caveat: "資料不足不代表沒有風險"
          }] }
        })"""
    )
    assert evidence["status"] == "unavailable"
    assert evidence["attachable"] is False
    assert "低風險" not in evidence["summary"]


def test_reference_states_are_preserved_without_false_safety_mapping() -> None:
    state_inputs = {
        "available": "matched",
        "no_match": "not_matched",
        "partial": "partial",
        "limited": "limited",
        "unknown": "unknown",
        "not_assessed": "not_assessed",
        "error": "error",
    }
    for expected, assessment_status in state_inputs.items():
        evidence = run_helper(
            f"""({{
              data_quality: {{ status: "good" }},
              source_transparency: {{ layers: [{{
                layer_id: "fake-layer",
                display_name: "虛構圖層",
                source_name: "虛構官方來源",
                assessment_status: {json.dumps(assessment_status)},
                coverage_status: "unknown",
                data_updated_at: "unknown",
                caveat: "僅供參考"
              }}] }}
            }})"""
        )
        assert evidence["layers"][0]["state"] == expected
        assert evidence["status"] == expected
        assert "低風險" not in evidence["summary"]


def test_terrain_is_not_a_decision_or_score_input() -> None:
    assert "addTerrainRisk(" not in RISK
    assert 'key: "terrainRisk"' not in VIEWING
    assert 'item.key !== "terrainRisk"' not in VIEWING
    assert "terrainReference: attachedTerrainReference" in WORKSPACE
    assert "terrainRisk: attachedTerrainRisk" not in WORKSPACE
    assert "TERRAIN_REFERENCE_EVIDENCE_EVENT" in WORKSPACE
    assert "sessionStorage.getItem(TERRAIN_RISK" not in WORKSPACE
    assert "cadastral_evidence" not in RISK
    assert "cadastral_evidence" not in VIEWING


def test_stored_schema_is_explicit_and_does_not_overload_terrain_result() -> None:
    assert "StoredTerrainReferenceEvidenceV1" in HELPER.read_text(encoding="utf-8")
    assert "schema_version: 1" in HELPER.read_text(encoding="utf-8")
    assert 'kind: "terrain_reference"' in HELPER.read_text(encoding="utf-8")
    assert "terrainReference?: StoredTerrainReferenceEvidenceV1" in STORAGE
    assert "terrainRisk: undefined" in STORAGE


def test_stored_sanitizer_preserves_allowed_states_and_rejects_blocked_states() -> None:
    allowed = ["available", "partial", "limited", "no_match"]
    for state in allowed:
        stored = run_helper_export(
            "toStoredTerrainReferenceEvidence",
            json.dumps({
                "status": state,
                "summary": "僅供看房風險參考",
                "notice": "資料不足不代表沒有風險",
                "attachable": True,
                "attachDisabledReason": "",
                "layers": [{
                    "layer_id": "fake-layer",
                    "display_name": "虛構圖層",
                    "state": state,
                    "source_name": "虛構官方來源",
                    "coverage_status": "unknown",
                    "caveat": "僅供參考",
                }],
            }),
        )
        assert stored["schema_version"] == 1
        assert stored["kind"] == "terrain_reference"
        assert stored["status"] == state
    for state in ("unknown", "not_assessed", "unavailable", "error"):
        blocked = run_helper_export(
            "toStoredTerrainReferenceEvidence",
            json.dumps({"status": state, "summary": "資料不足", "notice": "資料不足不代表沒有風險", "attachable": False, "attachDisabledReason": "不可附加", "layers": []}),
        )
        assert blocked is None


def test_stored_normalizer_fails_closed_and_legacy_migration_drops_raw_fields() -> None:
    invalid = run_helper_export(
        "normalizeStoredTerrainReferenceEvidence",
        json.dumps({"schema_version": 1, "kind": "terrain_reference", "status": "available", "summary": "安全", "notice": "僅供參考", "layers": [], "raw_payload": {}}),
    )
    assert invalid is None
    migrated = run_helper_export(
        "migrateLegacyTerrainReference",
        "({ data_quality: { status: 'good' }, source_transparency: { layers: [{ layer_id: 'fake-layer', display_name: '虛構圖層', source_name: '虛構來源', assessment_status: 'matched', coverage_status: 'covered', caveat: '僅供參考' }] }, input: { latitude: 1, longitude: 2 }, resolved_location: { latitude: 1, longitude: 2 }, map_layers: [{ source_url: 'https://example.invalid' }] })",
    )
    assert migrated["status"] == "available"
    serialized = json.dumps(migrated)
    for forbidden in ("latitude", "longitude", "resolved_location", "map_layers", "source_url", "raw_payload"):
        assert forbidden not in serialized
