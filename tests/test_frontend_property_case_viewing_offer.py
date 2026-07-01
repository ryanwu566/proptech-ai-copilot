"""Contracts for Property Case Viewing & Offer Planning Board v1."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWING_OFFER = ROOT / "frontend_next/lib/property-case-viewing-offer.ts"
COMMAND_CENTER = ROOT / "frontend_next/components/property-case-command-center.tsx"
CASE_MODEL = ROOT / "frontend_next/lib/property-case.ts"
VIEWING_DECISION_PANEL = ROOT / "frontend_next/components/viewing-decision-panel.tsx"
DECISION_REPORT = ROOT / "frontend_next/components/decision-report.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_viewing_offer_domain_contract() -> None:
    source = read(VIEWING_OFFER)

    for token in (
        "planned",
        "completed",
        "cancelled",
        "open",
        "awaiting_response",
        "user_recorded_response",
        "resolved_by_user",
        "no_longer_needed",
        "draft",
        "discussed",
        "submitted_by_user",
        "withdrawn",
        "not_pursuing",
        "MAX_OFFER_PLANS = 3",
    ):
        assert token in source

    for forbidden in ("success_probability", "formal_offer", "legal_document", "recommended", "not_recommended"):
        assert forbidden not in source


def test_viewing_offer_ui_exists_without_auto_queries_or_storage() -> None:
    source = read(COMMAND_CENTER)

    for text in (
        "看屋、提問與出價規劃",
        "新增看屋紀錄",
        "新增提問",
        "新增出價情境",
        "不產生正式出價",
        "尚未輸入擬出價，因此財務試算仍是不完整，不會用 0 代替",
        "最多保留",
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


def test_property_case_model_round_trips_viewing_offer_fields() -> None:
    source = read(CASE_MODEL)

    for field in (
        "viewing_logs",
        "viewing_questions",
        "offer_plans",
        "viewing_offer",
        "normalizeViewingLogs",
        "normalizeViewingQuestions",
        "normalizeOfferPlans",
        "buildViewingOfferReadiness",
    ):
        assert field in source

    for forbidden in ("raw payload", "provider raw", "token", "secret", "database URL", "SQL"):
        assert forbidden not in source


def test_viewing_offer_helper_runtime_rules_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
function load(path, extraRequire = {}) {
  const source = fs.readFileSync(path, 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {}, require: (name) => extraRequire[name] || require(name) };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.exports;
}
const financials = load('frontend_next/lib/property-case-financials.ts');
const offer = load('frontend_next/lib/property-case-viewing-offer.ts', { '@/lib/property-case-financials': financials });
const logs = offer.normalizeViewingLogs([
  { id: 'v1', viewed_on: '2026-01-02', status: 'completed', summary: 'seen', concerns: 'ask', follow_up_action: 'call' },
  { id: 'v2', viewed_on: 'bad-date', status: 'done' },
]);
if (logs.length !== 2) throw new Error('viewing logs lost');
if (logs[0].viewed_on !== '2026-01-02') throw new Error('valid viewing date lost');
if (logs[1].viewed_on !== '') throw new Error('invalid viewing date should clear');
if (logs[1].status !== 'planned') throw new Error('invalid viewing status should normalize');

const questions = offer.normalizeViewingQuestions([
  { id: 'q1', category: 'contract_negotiation', question: 'ask seller', status: 'resolved_by_user', target_date: '2026-01-03' },
  { id: 'q2', category: 'bad', question: '', status: 'bad' },
]);
if (questions.length !== 1) throw new Error('blank question should be removed');
if (questions[0].category !== 'contract_negotiation') throw new Error('question category lost');

const plans = offer.normalizeOfferPlans([
  { id: 'o1', scenario_name: 'Offer A', proposed_price: 1800, reservation_or_earnest_amount: 0, intended_response_date: '2026-01-04', status: 'submitted_by_user' },
  { id: 'o2', scenario_name: '', proposed_price: -1, status: 'bad' },
  { id: 'o3', scenario_name: 'Offer B', proposed_price: 1750, status: 'withdrawn' },
  { id: 'o4', scenario_name: 'Offer C', proposed_price: 1700, status: 'not_pursuing' },
  { id: 'o5', scenario_name: 'Offer D', proposed_price: 1600, status: 'draft' },
]);
if (plans.length !== 2) throw new Error('offer plan normalization should cap before filtering and remove blank scenario');
if (plans[0].reservation_or_earnest_amount !== 0) throw new Error('zero earnest amount should be valid');

const empty = offer.buildViewingOfferReadiness([], [], []);
if (empty.readiness !== 'not_provided') throw new Error('empty readiness should be not_provided');
const partial = offer.buildViewingOfferReadiness(logs, [{ id: 'q1', category: 'property', question: 'ask', status: 'open', recorded_response: '', response_source_note: '', follow_up_action: '', target_date: '' }], plans);
if (partial.readiness !== 'partial') throw new Error('open question should be partial');
const completed = offer.buildViewingOfferReadiness([logs[0]], [{ id: 'q1', category: 'property', question: 'ask', status: 'resolved_by_user', recorded_response: '', response_source_note: '', follow_up_action: '', target_date: '' }], [plans[0]]);
if (completed.readiness !== 'completed') throw new Error('completed viewing offer readiness failed');
if (completed.active_offer_plan_count !== 1) throw new Error('active offer count failed');

const previews = offer.buildOfferPlanFinancialPreviews({
  listingPrice: 2000,
  userEstimatedValue: 1900,
  fundingMode: 'loan_amount',
  fundingValue: 1500,
  annualInterestRate: 0,
  loanYears: 30,
  estimatedBuyerCosts: 80,
  renovationReserve: 100,
  availableLiquidCash: 600,
  monthlyHouseholdIncome: 150000,
  monthlyFixedObligations: 20000,
  monthlyOwnershipReserve: 10000,
}, [plans[0]]);
if (previews[0].analysis.listingPrice.value !== 1800) throw new Error('offer proposed price should override only preview price');
if (previews[0].analysis.monthlyPayment.value === null) throw new Error('offer finance preview should calculate');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_property_case_runtime_round_trip_with_viewing_offer() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
function load(path, extraRequire = {}) {
  const source = fs.readFileSync(path, 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Number, Object, String, Map, Set, Array, RegExp, Math, Date, exports: {}, require: (name) => extraRequire[name] || require(name) };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.exports;
}
const due = load('frontend_next/lib/property-case-due-diligence.ts');
const financials = load('frontend_next/lib/property-case-financials.ts');
const viewingOffer = load('frontend_next/lib/property-case-viewing-offer.ts', { '@/lib/property-case-financials': financials });
const caseSource = fs.readFileSync('frontend_next/lib/property-case.ts', 'utf8');
const caseJs = ts.transpileModule(caseSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const sandbox = {
  console, Number, Object, String, Map, Set, Date, exports: {},
  require: (name) => {
    if (name === '@/lib/property-case-due-diligence') return due;
    if (name === '@/lib/property-case-viewing-offer') return viewingOffer;
    return require(name);
  }
};
vm.createContext(sandbox);
vm.runInContext(caseJs, sandbox);
const draft = sandbox.exports.buildPropertyCaseDraft({
  caseName: 'Demo Case',
  inputs: { city: 'Demo City', district: 'Demo District', road: 'Demo Road', building_type: 'Apartment', area_ping: 30, building_age_years: 10, floor: 5 },
  listingPrice: 2000,
  viewingLogs: [{ id: 'v1', viewed_on: '2026-01-02', participant_note: 'family', summary: 'seen', positive_observations: 'light', concerns: 'noise', follow_up_action: 'ask again', status: 'completed' }],
  viewingQuestions: [{ id: 'q1', category: 'property', question: 'ask', recorded_response: 'answer', response_source_note: 'user note', follow_up_action: '', target_date: '2026-01-03', status: 'resolved_by_user' }],
  offerPlans: [{ id: 'o1', scenario_name: 'Offer A', proposed_price: 1800, reservation_or_earnest_amount: 0, intended_response_date: '2026-01-04', conditions_note: 'conditions', negotiation_note: 'negotiate', status: 'submitted_by_user' }],
}, '2026-01-01T00:00:00.000Z');
if (draft.viewing_logs.length !== 1) throw new Error('viewing log lost');
if (draft.viewing_questions.length !== 1) throw new Error('question lost');
if (draft.offer_plans.length !== 1) throw new Error('offer plan lost');
if (draft.offer_plans[0].proposed_price !== 1800) throw new Error('offer proposed price lost');
if (draft.readiness.viewing_offer !== 'completed') throw new Error('viewing offer readiness failed');
if (draft.decision_status !== 'draft') throw new Error('viewing offer must not change decision status');
if (JSON.stringify(draft).includes('raw_payload')) throw new Error('raw payload leaked');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_viewing_decision_files_not_rewired_to_viewing_offer() -> None:
    combined = read(VIEWING_DECISION_PANEL) + read(DECISION_REPORT)

    assert "property-case-viewing-offer" not in combined
    assert "offer_plans" not in combined
