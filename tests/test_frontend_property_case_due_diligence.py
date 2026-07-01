"""Contracts for Property Case Due Diligence & Decision Review Board v1."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DUE_DILIGENCE = ROOT / "frontend_next/lib/property-case-due-diligence.ts"
COMMAND_CENTER = ROOT / "frontend_next/components/property-case-command-center.tsx"
CASE_MODEL = ROOT / "frontend_next/lib/property-case.ts"
VIEWING_DECISION_PANEL = ROOT / "frontend_next/components/viewing-decision-panel.tsx"
DECISION_REPORT = ROOT / "frontend_next/components/decision-report.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_due_diligence_template_and_status_contract() -> None:
    source = read(DUE_DILIGENCE)

    for status in ("not_started", "reviewing", "confirmed", "blocked", "not_applicable"):
        assert status in source
    for category in (
        "basic_property",
        "building_condition",
        "community_management",
        "financing_tax",
        "contract_negotiation",
        "location_market_reference",
    ):
        assert category in source
    status_block = source.split("export const DUE_DILIGENCE_STATUS_OPTIONS", 1)[1].split("];", 1)[0]
    for forbidden in ("unsafe", "pass", "fail", "approved", "rejected", "recommended", "not_recommended"):
        assert forbidden not in status_block


def test_due_diligence_ui_exists_without_auto_queries_or_storage() -> None:
    source = read(COMMAND_CENTER)

    for text in (
        "盡職調查與決策審查板",
        "檢查狀態",
        "使用者確認備註",
        "參考依據備註",
        "下一步行動",
        "目標日期（YYYY-MM-DD）",
        "決策審查摘要",
        "不會自動查詢市場、通勤、地勢、地圖或任何外部服務",
    ):
        assert text in source

    for forbidden in (
        "fetch(",
        "api.",
        "/market-insights",
        "/commute",
        "/terrain",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "URLSearchParams",
        "location.search",
    ):
        assert forbidden not in source


def test_property_case_model_round_trips_due_diligence_fields() -> None:
    source = read(CASE_MODEL)

    for field in (
        "due_diligence_items",
        "decision_review_summary",
        "decision_open_questions",
        "decision_next_step",
        "due_diligence",
        "normalizeDueDiligenceItems",
        "buildDueDiligenceReadiness",
    ):
        assert field in source

    for forbidden in ("raw payload", "provider raw", "token", "secret", "database URL", "SQL"):
        assert forbidden not in source


def test_due_diligence_helper_runtime_rules_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
function load(path) {
  const source = fs.readFileSync(path, 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Number, Object, String, Map, Set, Array, RegExp, exports: {}, require };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.exports;
}
const due = load('frontend_next/lib/property-case-due-diligence.ts');
const defaults = due.buildDefaultDueDiligenceItems();
if (defaults.length !== 20) throw new Error('expected 20 due diligence items');
if (new Set(defaults.map((item) => item.category_id)).size !== 6) throw new Error('expected 6 categories');
if (!defaults.every((item) => item.status === 'not_started')) throw new Error('default status must be not_started');

const normalized = due.normalizeDueDiligenceItems([
  { item_id: 'basic_property_price_identity', status: 'confirmed', note: 'ok', reference_note: 'doc', next_action: 'ask seller', target_date: '2026-01-02' },
  { item_id: 'basic_property_area_age', status: 'pass', target_date: 'bad-date' },
]);
if (normalized.find((item) => item.item_id === 'basic_property_price_identity').target_date !== '2026-01-02') throw new Error('valid target date lost');
if (normalized.find((item) => item.item_id === 'basic_property_area_age').status !== 'not_started') throw new Error('invalid status should normalize');
if (normalized.find((item) => item.item_id === 'basic_property_area_age').target_date !== '') throw new Error('invalid target date should clear');

const emptyReadiness = due.buildDueDiligenceReadiness(defaults, {});
if (emptyReadiness.readiness !== 'not_provided') throw new Error('empty checklist should be not_provided');

const partial = due.buildDueDiligenceReadiness(normalized, { decision_review_summary: 'summary' });
if (partial.readiness !== 'partial') throw new Error('partial checklist should be partial');

const completedItems = defaults.map((item) => ({ ...item, status: item.item_id.endsWith('_price_identity') || item.item_id.endsWith('_visible_issues') || item.item_id.endsWith('_fee') || item.item_id.endsWith('_funding_plan') || item.item_id.endsWith('_price_terms') || item.item_id.endsWith('_livability') ? 'confirmed' : 'not_applicable' }));
const completed = due.buildDueDiligenceReadiness(completedItems, { decision_review_summary: 'summary', decision_next_step: 'next' });
if (completed.readiness !== 'completed') throw new Error('completed checklist should be completed');

const blocked = due.buildDueDiligenceReadiness(completedItems.map((item, index) => index === 0 ? { ...item, status: 'blocked' } : item), { decision_review_summary: 'summary', decision_next_step: 'next' });
if (blocked.readiness === 'completed') throw new Error('blocked item must prevent completed readiness');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_property_case_runtime_round_trip_with_due_diligence() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
const dueSource = fs.readFileSync('frontend_next/lib/property-case-due-diligence.ts', 'utf8');
const dueJs = ts.transpileModule(dueSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const dueSandbox = { console, Number, Object, String, Map, Set, Array, RegExp, exports: {}, require };
vm.createContext(dueSandbox);
vm.runInContext(dueJs, dueSandbox);
const financialSource = fs.readFileSync('frontend_next/lib/property-case-financials.ts', 'utf8');
const financialJs = ts.transpileModule(financialSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const financialSandbox = { console, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {}, require };
vm.createContext(financialSandbox);
vm.runInContext(financialJs, financialSandbox);
const viewingSource = fs.readFileSync('frontend_next/lib/property-case-viewing-offer.ts', 'utf8');
const viewingJs = ts.transpileModule(viewingSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const viewingSandbox = { console, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {}, require: (name) => name === '@/lib/property-case-financials' ? financialSandbox.exports : require(name) };
vm.createContext(viewingSandbox);
vm.runInContext(viewingJs, viewingSandbox);
const caseSource = fs.readFileSync('frontend_next/lib/property-case.ts', 'utf8')
  .replace(/import \{[\s\S]*?\} from "@\/lib\/property-case-due-diligence";/, '')
  .replace(/import \{[\s\S]*?\} from "@\/lib\/property-case-viewing-offer";/, '')
  .replace(/import type[\s\S]*?from "@\/lib\/api";/, '')
  .replace(/import type[\s\S]*?from "@\/lib\/risk-summary";/, '')
  .replace(/import type[\s\S]*?from "@\/lib\/valuation-share";/, '');
const caseJs = ts.transpileModule(caseSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const sandbox = { console, Number, Object, String, Map, Set, Date, exports: {}, require, ...dueSandbox.exports, ...viewingSandbox.exports };
vm.createContext(sandbox);
vm.runInContext(caseJs, sandbox);
const buildPropertyCaseDraft = sandbox.exports.buildPropertyCaseDraft;
const inputs = { city: 'Demo City', district: 'Demo District', road: 'Demo Road', building_type: 'Apartment', area_ping: 30, building_age_years: 10, floor: 5 };
const draft = buildPropertyCaseDraft({
  caseName: 'Demo Case',
  inputs,
  listingPrice: 2000,
  dueDiligenceItems: [
    { item_id: 'basic_property_price_identity', status: 'confirmed', note: 'checked', reference_note: 'paper', next_action: 'ask', target_date: '2026-01-02' },
  ],
  decisionReviewSummary: 'summary',
  decisionOpenQuestions: 'questions',
  decisionNextStep: 'next',
}, '2026-01-01T00:00:00.000Z');
if (draft.due_diligence_items.length !== 20) throw new Error('due diligence template not round-tripped');
if (draft.due_diligence_items[0].note !== 'checked') throw new Error('due diligence note lost');
if (draft.decision_review_summary !== 'summary') throw new Error('review summary lost');
if (draft.decision_open_questions !== 'questions') throw new Error('open questions lost');
if (draft.decision_next_step !== 'next') throw new Error('next step lost');
if (draft.readiness.due_diligence !== 'partial') throw new Error('due diligence readiness should be partial');
if (draft.decision_status !== 'draft') throw new Error('due diligence must not change decision status');
if (JSON.stringify(draft).includes('raw_payload')) throw new Error('raw payload leaked');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_viewing_decision_files_not_rewired_to_due_diligence() -> None:
    combined = read(VIEWING_DECISION_PANEL) + read(DECISION_REPORT)

    assert "property-case-due-diligence" not in combined
    assert "due_diligence_items" not in combined
