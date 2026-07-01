"""Static and helper tests for Property Case Decision System v1."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE_MODEL = ROOT / "frontend_next/lib/property-case.ts"
READINESS = ROOT / "frontend_next/lib/property-case-readiness.ts"
READINESS_COMPONENT = ROOT / "frontend_next/components/property-case-readiness.tsx"
WORKSPACE = (ROOT / "frontend_next/components/immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
VIEWING_DECISION = (ROOT / "frontend_next/lib/viewing-decision.ts").read_text(encoding="utf-8")
DOCS = (ROOT / "docs/property-case-decision-system-v1.md").read_text(encoding="utf-8")
PARTIAL_PRINT_NOTICE = "本案件資料尚未完整，報告僅彙整目前可用資訊。"


def test_property_case_domain_files_define_minimal_case_model() -> None:
    source = CASE_MODEL.read_text(encoding="utf-8")

    for field in ("property_input", "location_input", "financial_input", "analysis_status", "analysis_summary", "readiness"):
        assert field in source
    for field in ("case_id", "case_name", "created_at", "updated_at"):
        assert field in source
    assert "PARTIAL_CASE_PRINT_NOTICE" in source
    assert "provider raw" not in source.lower()
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_readiness_rules_are_conservative_about_missing_and_unavailable_data() -> None:
    source = READINESS.read_text(encoding="utf-8")

    assert "待補案件基本資料" in source
    assert "待補比較資料" in source
    assert "不能推論為低風險或已完成" in source
    assert "缺少價格資料時，不會顯示為低價、0 元或比較完成" in source
    assert "完整度不是投資評分或買賣建議" in source
    assert "值得買" not in source
    assert "保證" not in source


def test_property_case_readiness_ui_reuses_existing_workspace_and_case_manager() -> None:
    component = READINESS_COMPONENT.read_text(encoding="utf-8")

    assert "PropertyCaseReadiness" in WORKSPACE
    assert "buildPropertyCaseDraft" in WORKSPACE
    assert WORKSPACE.index("PropertyCaseReadiness") < WORKSPACE.index("CaseManager current={currentCase}")
    assert "CaseManager current={currentCase}" in WORKSPACE
    assert "ViewingDecisionPanel" in WORKSPACE
    assert "DecisionReport" in WORKSPACE
    assert "案件決策完整度" in component
    assert "可列印目前摘要" in component
    assert "資料限制" in component
    assert "待補案件名稱" in component
    assert "待補物件地址／識別" in component


def test_no_new_api_calls_or_client_storage_for_case_decision_system() -> None:
    source = "\n".join(
        [
            CASE_MODEL.read_text(encoding="utf-8"),
            READINESS.read_text(encoding="utf-8"),
            READINESS_COMPONENT.read_text(encoding="utf-8"),
        ]
    )

    assert "fetch(" not in source
    assert "api." not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "document.cookie" not in source
    assert "URLSearchParams" not in source


def test_viewing_decision_logic_not_modified_by_property_case_system() -> None:
    assert "PropertyCaseReadiness" not in VIEWING_DECISION
    assert "buildPropertyCaseDraft" not in VIEWING_DECISION
    assert "property-case" not in VIEWING_DECISION


def test_docs_capture_boundaries_and_no_sensitive_data() -> None:
    assert "does not replace Property Finder" in DOCS
    assert "Unavailable or incomplete" in DOCS
    assert "does not change loan formulas" in DOCS
    assert "call new APIs" in DOCS
    assert "persist new state" in DOCS
    assert "case name plus address" in DOCS
    assert PARTIAL_PRINT_NOTICE in DOCS
    assert "Case completeness is not an investment score" in DOCS
    for forbidden in ("token value", "database URL", "API key value", "raw payload example"):
        assert forbidden not in DOCS


def test_property_case_helper_runtime_rules_with_node() -> None:
    script = rf"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
const dueSource = fs.readFileSync('frontend_next/lib/property-case-due-diligence.ts', 'utf8');
const dueJs = ts.transpileModule(dueSource, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
const dueSandbox = {{ console, Date, Number, Object, String, Map, Set, Array, RegExp, exports: {{}}, require }};
vm.createContext(dueSandbox);
vm.runInContext(dueJs, dueSandbox);
const financialSource = fs.readFileSync('frontend_next/lib/property-case-financials.ts', 'utf8');
const financialJs = ts.transpileModule(financialSource, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
const financialSandbox = {{ console, Date, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {{}}, require }};
vm.createContext(financialSandbox);
vm.runInContext(financialJs, financialSandbox);
const viewingSource = fs.readFileSync('frontend_next/lib/property-case-viewing-offer.ts', 'utf8');
const viewingJs = ts.transpileModule(viewingSource, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
const viewingSandbox = {{ console, Date, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {{}}, require: (name) => name === '@/lib/property-case-financials' ? financialSandbox.exports : require(name) }};
vm.createContext(viewingSandbox);
vm.runInContext(viewingJs, viewingSandbox);
const timelineSource = fs.readFileSync('frontend_next/lib/property-case-timeline.ts', 'utf8')
  .replace(/import type[\s\S]*?from "@\/lib\/property-case";/, '');
const timelineJs = ts.transpileModule(timelineSource, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
const timelineSandbox = {{ console, Date, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {{}}, require }};
vm.createContext(timelineSandbox);
vm.runInContext(timelineJs, timelineSandbox);
const source = fs.readFileSync('frontend_next/lib/property-case.ts', 'utf8');
const js = ts.transpileModule(source, {{ compilerOptions: {{ module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }} }}).outputText;
const sandbox = {{ console, Date, Number, Object, String, Map, Set, Array, RegExp, exports: {{}}, require: (name) => {{
  if (name === '@/lib/property-case-due-diligence') return dueSandbox.exports;
  if (name === '@/lib/property-case-viewing-offer') return viewingSandbox.exports;
  if (name === '@/lib/property-case-timeline') return timelineSandbox.exports;
  return require(name);
}} }};
vm.createContext(sandbox);
vm.runInContext(js, sandbox);
const buildPropertyCaseDraft = sandbox.exports.buildPropertyCaseDraft;
const baseInputs = {{ city: 'Demo City', district: 'Demo District', road: 'Demo Road', building_type: 'Apartment', area_ping: 30, building_age_years: 10, floor: 5 }};
const onlyAddress = buildPropertyCaseDraft({{ inputs: baseInputs }}, '2026-01-01T00:00:00.000Z');
if (onlyAddress.readiness.draft_ready) throw new Error('address-only case should not be draft ready');
if (!onlyAddress.readiness.missing_required.includes('case_name')) throw new Error('missing case name not detected');
if (onlyAddress.case_name) throw new Error('case name should not be auto-filled from address');
const onlyName = buildPropertyCaseDraft({{ caseName: 'Demo Case', inputs: {{ building_type: 'Apartment' }} }}, '2026-01-01T00:00:00.000Z');
if (onlyName.readiness.draft_ready) throw new Error('name-only case should not be draft ready');
if (!onlyName.readiness.missing_required.includes('address')) throw new Error('missing address not detected');
const draft = buildPropertyCaseDraft({{ caseName: 'Demo Case', inputs: baseInputs }}, '2026-01-01T00:00:00.000Z');
if (!draft.readiness.draft_ready) throw new Error('case name and address should be draft ready');
if (draft.readiness.compare_ready) throw new Error('draft without price should not be compare ready');
if (!draft.readiness.print_ready) throw new Error('draft with explicit pending statuses should be printable as current summary');
if (draft.readiness.print_notice !== '{PARTIAL_PRINT_NOTICE}') throw new Error('partial print notice missing');
if (!draft.readiness.missing_required.includes('listing_price')) throw new Error('missing listing price not detected');
const complete = buildPropertyCaseDraft({{
  caseName: 'Complete Demo',
  inputs: baseInputs,
  valuation: {{ price_range: {{ mid: 2000 }} }},
  loan: {{ property_price_wan: 2000, down_payment_wan: 400, loan_amount_wan: 1600, loan_years: 30, annual_interest_rate: 2, grace_period_years: 0, monthly_income_wan: 10, monthly_payment: 60000 }},
  holding: {{ property_price_wan: 2000, monthly_total_holding_cost: 80000, input: {{ monthly_income_wan: 10 }} }},
  location: {{ data_quality: {{ status: 'good' }}, resolved_location: {{}} }},
  terrainRisk: {{ data_quality: {{ status: 'good' }}, overall: {{ level: 'low', label: 'Low' }} }},
  riskSummary: {{}},
  taxOracle: {{}},
  propertySearch: {{}},
}}, '2026-01-01T00:00:00.000Z');
if (!complete.readiness.compare_ready) throw new Error('complete case should be compare ready');
if (!complete.readiness.print_ready) throw new Error('complete case should be print ready');
if (JSON.stringify(complete).includes('raw_payload')) throw new Error('raw payload leaked');
if (JSON.stringify(complete).includes('commute_rank')) throw new Error('commute should not affect ranking');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
