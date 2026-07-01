"""Contracts for Property Case Timeline & Executive Decision Pack v1."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "frontend_next/lib/property-case-timeline.ts"
CASE_MODEL = ROOT / "frontend_next/lib/property-case.ts"
COMMAND_CENTER = ROOT / "frontend_next/components/property-case-command-center.tsx"
VIEWING_DECISION_PANEL = ROOT / "frontend_next/components/viewing-decision-panel.tsx"
DECISION_REPORT = ROOT / "frontend_next/components/decision-report.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_timeline_domain_contract_and_allowlists() -> None:
    source = read(TIMELINE)

    for event_type in (
        "created",
        "viewing",
        "question",
        "due_diligence",
        "financial_review",
        "offer",
        "decision_review",
        "status_change",
        "custom",
    ):
        assert event_type in source

    for section in (
        "basic",
        "financial",
        "due_diligence",
        "viewing_offer",
        "market_reference",
        "location_reference",
        "decision",
        "other",
    ):
        assert section in source

    for milestone in (
        "basic_info_reviewed",
        "first_viewing_recorded",
        "financial_review_started",
        "due_diligence_started",
        "questions_tracked",
        "offer_plan_created",
        "decision_review_written",
        "report_ready_for_print",
    ):
        assert milestone in source

    for forbidden in ("risk_score", "ranking", "recommended", "approved", "guarantee"):
        assert forbidden not in source.lower()


def test_timeline_command_center_ui_without_auto_queries_or_storage() -> None:
    source = read(COMMAND_CENTER)

    for text in (
        "案件時間軸與決策包",
        "Executive Summary",
        "Executive Decision Pack",
        "Executive summary note",
        "Final review note",
        "timelineReadiness.event_count",
        "timelineReadiness.milestone_done_count",
        "draft.readiness.timeline_summary",
    ):
        assert text in source

    executive_section = source.split("G. EXECUTIVE PACK", 1)[1]
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
        assert forbidden not in executive_section


def test_property_case_model_round_trips_timeline_fields() -> None:
    source = read(CASE_MODEL)

    for field in (
        "timeline_events",
        "case_milestones",
        "executive_summary_note",
        "final_review_note",
        "timeline_summary",
        "normalizeTimelineEvents",
        "normalizeCaseMilestones",
        "buildTimelineReadiness",
    ):
        assert field in source

    for forbidden in ("raw payload", "provider raw", "token", "secret", "database URL", "SQL"):
        assert forbidden not in source


def test_timeline_helper_runtime_rules_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
function load(path) {
  const source = fs.readFileSync(path, 'utf8')
    .replace(/import type[\s\S]*?from "@\/lib\/property-case";/, '');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Number, Object, String, Map, Set, Array, RegExp, Math, Date, exports: {}, require };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.exports;
}
const timeline = load('frontend_next/lib/property-case-timeline.ts');
const events = timeline.normalizeTimelineEvents([
  { id: 't1', event_date: '2026-01-02', event_type: 'viewing', title: 'Recorded viewing', summary: 'User note', related_section: 'viewing_offer', note: 'Follow up' },
  { id: 't2', event_date: 'bad-date', event_type: 'offer', title: 'Invalid date' },
  { id: 't3', event_date: '2026-01-03', event_type: 'bad-type', related_section: 'bad-section', title: 'Normalize me' },
  { id: 't4', event_date: '2026-01-04', event_type: 'custom', title: '   ' },
]);
if (events.length !== 2) throw new Error('timeline event validation failed');
if (events[0].event_type !== 'viewing') throw new Error('valid event type lost');
if (events[1].event_type !== 'custom') throw new Error('invalid event type should normalize');
if (events[1].related_section !== 'other') throw new Error('invalid related section should normalize');

const defaults = timeline.buildDefaultMilestones();
if (defaults.length !== 8) throw new Error('expected 8 milestones');
if (!defaults.every((milestone) => milestone.is_done === false)) throw new Error('default milestones must be undone');

const milestones = timeline.normalizeCaseMilestones([
  { milestone_id: 'basic_info_reviewed', is_done: true, done_date: '2026-01-05', note: 'reviewed' },
  { milestone_id: 'offer_plan_created', is_done: true, done_date: 'bad-date', note: 'offer' },
]);
if (milestones.find((milestone) => milestone.milestone_id === 'basic_info_reviewed').done_date !== '2026-01-05') throw new Error('valid milestone date lost');
if (milestones.find((milestone) => milestone.milestone_id === 'offer_plan_created').done_date !== '') throw new Error('invalid milestone date should clear');

const empty = timeline.buildTimelineReadiness([], defaults, '', '');
if (empty.readiness !== 'not_provided') throw new Error('empty readiness should be not_provided');
const partial = timeline.buildTimelineReadiness(events, defaults, '', '');
if (partial.readiness !== 'partial') throw new Error('event-only readiness should be partial');
const completed = timeline.buildTimelineReadiness(events, milestones, 'exec note', '');
if (completed.readiness !== 'completed') throw new Error('timeline readiness should be completed');
if (completed.event_count !== 2) throw new Error('event count failed');
if (completed.milestone_done_count !== 2) throw new Error('milestone count failed');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_property_case_runtime_round_trip_with_timeline_and_executive_summary() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
function load(path, extraRequire = {}) {
  const source = fs.readFileSync(path, 'utf8')
    .replace(/import type[\s\S]*?from "@\/lib\/property-case";/, '');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Number, Object, String, Map, Set, Array, RegExp, Math, Date, exports: {}, require: (name) => extraRequire[name] || require(name) };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.exports;
}
const due = load('frontend_next/lib/property-case-due-diligence.ts');
const financials = load('frontend_next/lib/property-case-financials.ts');
const viewingOffer = load('frontend_next/lib/property-case-viewing-offer.ts', { '@/lib/property-case-financials': financials });
const timeline = load('frontend_next/lib/property-case-timeline.ts');
const caseSource = fs.readFileSync('frontend_next/lib/property-case.ts', 'utf8');
const caseJs = ts.transpileModule(caseSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const sandbox = {
  console, Number, Object, String, Map, Set, Date, exports: {},
  require: (name) => {
    if (name === '@/lib/property-case-due-diligence') return due;
    if (name === '@/lib/property-case-viewing-offer') return viewingOffer;
    if (name === '@/lib/property-case-timeline') return timeline;
    return require(name);
  }
};
vm.createContext(sandbox);
vm.runInContext(caseJs, sandbox);
const draft = sandbox.exports.buildPropertyCaseDraft({
  caseName: 'Demo Case',
  inputs: { city: 'Demo City', district: 'Demo District', road: 'Demo Road', building_type: 'Apartment', area_ping: 30, building_age_years: 10, floor: 5 },
  listingPrice: 2000,
  timelineEvents: [{ id: 't1', event_date: '2026-01-02', event_type: 'decision_review', title: 'Review', summary: 'User entered', related_section: 'decision', note: 'next action' }],
  caseMilestones: [{ milestone_id: 'decision_review_written', is_done: true, done_date: '2026-01-03', note: 'written' }],
  executiveSummaryNote: 'Executive user note',
  finalReviewNote: 'Final user note',
}, '2026-01-01T00:00:00.000Z');
if (draft.timeline_events.length !== 1) throw new Error('timeline event lost');
if (draft.case_milestones.filter((milestone) => milestone.is_done).length !== 1) throw new Error('milestone lost');
if (draft.executive_summary_note !== 'Executive user note') throw new Error('executive note lost');
if (draft.final_review_note !== 'Final user note') throw new Error('final review note lost');
if (draft.readiness.timeline_summary !== 'completed') throw new Error('timeline readiness failed');
if (draft.decision_status !== 'draft') throw new Error('timeline must not change decision status');
const summary = timeline.buildExecutiveDecisionSummary(draft);
if (!summary.missing_sections.includes('due_diligence')) throw new Error('missing sections should include due diligence');
if (summary.active_next_actions_count < 1) throw new Error('next actions should be counted from user notes');
if (JSON.stringify(draft).includes('raw_payload')) throw new Error('raw payload leaked');
if (JSON.stringify(draft).includes('token')) throw new Error('token leaked');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_viewing_decision_files_not_rewired_to_timeline_pack() -> None:
    combined = read(VIEWING_DECISION_PANEL) + read(DECISION_REPORT)

    assert "property-case-timeline" not in combined
    assert "timeline_events" not in combined
