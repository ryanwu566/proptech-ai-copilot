"""Runtime contracts for independent Google route and TDX commute evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_commute_channels_and_journey_state_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');

function load(path, imports = {}) {
  const source = fs.readFileSync(path, 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Date, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {}, require: (name) => imports[name] ?? require(name) };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.exports;
}

const locationMarket = load('frontend_next/lib/location-market-journey.ts');
if (typeof locationMarket.buildCommuteChannelState !== 'function') throw new Error('buildCommuteChannelState is missing');
const routeSuccess = { status: 'resolved', source: 'google_routes', mode: 'transit', duration_min: 20, duration_seconds: 1200, distance_m: 7000, partial: false, fallback: false, reason_code: 'success', checked_at: '2026-09-27T00:00:00Z', message: 'ok', disclaimer: 'reference' };
const tdxUnavailable = { status: 'unavailable', source: 'none', station_name: null, line_ids: [], distance_meters: null, source_updated_at: null, snapshot_generated_at: null, message: 'unavailable' };
const independent = locationMarket.buildCommuteChannelState(routeSuccess, 'available', tdxUnavailable, 'unavailable');
if (independent.route !== 'available') throw new Error('Google route success was not preserved');
if (independent.transit_context !== 'unavailable') throw new Error('TDX failure was hidden');
if (independent.overall !== 'partial') throw new Error('independent evidence should be partial-but-useful');

const routeUnavailable = { ...routeSuccess, status: 'unavailable', source: 'none', duration_min: null, duration_seconds: null, distance_m: null, reason_code: 'provider_timeout' };
const tdxAvailable = { ...tdxUnavailable, status: 'resolved', source: 'tdx', station_name: '市政府', line_ids: ['BL'], distance_meters: 300 };
const contextOnly = locationMarket.buildCommuteChannelState(routeUnavailable, 'unavailable', tdxAvailable, 'available');
if (contextOnly.route !== 'unavailable') throw new Error('route failure was hidden by TDX');
if (contextOnly.transit_context !== 'available') throw new Error('TDX success was lost');
if (contextOnly.overall !== 'partial') throw new Error('TDX-only evidence must not claim a complete route');

const closedLoop = load('frontend_next/lib/closed-loop-journey.ts', { '@/lib/location-market-journey': locationMarket });
if (typeof closedLoop.setJourneyCommuteRoute !== 'function') throw new Error('setJourneyCommuteRoute is missing');
let state = closedLoop.createClosedLoopJourneyState({ addressSummary: 'Property A', selectionStatus: 'selected' });
const evidence = {
  ...routeSuccess,
  origin: { latitude: 25.033, longitude: 121.5654 },
  destination: { address: 'Taipei Main Station' },
};
state = closedLoop.setJourneyCommuteRoute(state, evidence, 'available');
state = closedLoop.setJourneyCommuteRoute(state, evidence, 'available');
if (state.commuteRouteEvidence !== evidence) throw new Error('retry should replace one evidence object, not duplicate it');
if (state.commuteRouteStatus !== 'available') throw new Error('route status was not stored');
const failedEvidence = { ...evidence, status: 'unavailable', source: 'none', reason_code: 'provider_timeout', duration_min: null, duration_seconds: null, distance_m: null };
state = closedLoop.setJourneyCommuteRoute(state, failedEvidence, 'unavailable');
state = closedLoop.setJourneyCommuteRoute(state, evidence, 'available');
if (state.commuteRouteEvidence !== evidence) throw new Error('retry retained failed evidence instead of replacing it');
state = closedLoop.updateJourneyProperty(state, { addressSummary: 'Property B', selectionStatus: 'selected' });
if (state.commuteRouteEvidence !== undefined) throw new Error('origin change retained stale route evidence');
if (state.commuteRouteStatus !== 'not_started') throw new Error('origin change retained derived commute readiness');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_property_case_commute_status_is_derived_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
function load(path, imports = {}) {
  const source = fs.readFileSync(path, 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const sandbox = { console, Date, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {}, require: (name) => imports[name] ?? require(name) };
  vm.createContext(sandbox); vm.runInContext(js, sandbox); return sandbox.exports;
}
const due = load('frontend_next/lib/property-case-due-diligence.ts');
const financial = load('frontend_next/lib/property-case-financials.ts');
const viewing = load('frontend_next/lib/property-case-viewing-offer.ts', { '@/lib/property-case-financials': financial });
const timeline = load('frontend_next/lib/property-case-timeline.ts');
const model = load('frontend_next/lib/property-case.ts', {
  '@/lib/property-case-due-diligence': due,
  '@/lib/property-case-viewing-offer': viewing,
  '@/lib/property-case-timeline': timeline,
});
const base = { caseName: 'Commute case', inputs: { city: 'Taipei', district: 'Xinyi', road: 'City Hall Road' } };
const success = { status: 'resolved', source: 'google_routes', reason_code: 'success', mode: 'transit', duration_min: 20, duration_seconds: 1200, distance_m: 7000, partial: false, fallback: false, checked_at: '2026-09-27T00:00:00Z', message: 'ok', disclaimer: 'reference', origin: { latitude: 25.033, longitude: 121.5654 }, destination: { address: 'Taipei Main Station' } };
const complete = model.buildPropertyCaseDraft({ ...base, commuteRoute: success });
if (complete.analysis_status.commute !== 'completed') throw new Error('successful route should complete commute analysis');
if (complete.location_input.commute_analysis_status !== 'completed') throw new Error('location commute status did not receive route success');
const unavailable = model.buildPropertyCaseDraft({ ...base, commuteRoute: { ...success, status: 'unavailable', source: 'none', reason_code: 'provider_timeout', duration_min: null, duration_seconds: null, distance_m: null } });
if (unavailable.analysis_status.commute !== 'unavailable') throw new Error('route failure should remain unavailable');
const required = model.buildPropertyCaseDraft({ ...base, commuteRoute: { ...success, status: 'unresolved', source: 'none', reason_code: 'destination_required', duration_min: null, duration_seconds: null, distance_m: null } });
if (required.analysis_status.commute !== 'incomplete') throw new Error('missing destination should remain incomplete');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_saved_route_evidence_is_allowlisted_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
const source = fs.readFileSync('frontend_next/lib/commute-route-evidence.ts', 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const sandbox = { console, Date, Number, Object, String, Map, Set, Array, RegExp, Math, exports: {}, require: () => ({}) };
vm.createContext(sandbox); vm.runInContext(js, sandbox);
const compact = sandbox.exports.compactCommuteRouteEvidence;
if (typeof compact !== 'function') throw new Error('route evidence allowlist is missing');
const saved = compact({
  status: 'resolved', source: 'google_routes', mode: 'transit', duration_min: 20,
  duration_seconds: 1200, distance_m: 7000, partial: false, fallback: false,
  reason_code: 'success', checked_at: '2026-09-27T00:00:00Z',
  origin: { latitude: 25.033, longitude: 121.5654 }, destination: { address: 'Taipei Main Station' },
  message: 'raw provider message', disclaimer: 'provider copy', raw: { routes: [] },
  headers: { authorization: 'secret' }, api_key: 'secret', internal_error: 'debug detail',
});
const keys = Object.keys(saved).sort().join(',');
const expected = ['checked_at','destination','distance_m','duration_min','duration_seconds','fallback','mode','origin','partial','reason_code','source','status'].sort().join(',');
if (keys !== expected) throw new Error(`unexpected persisted route fields: ${keys}`);
if (JSON.stringify(saved).includes('secret') || JSON.stringify(saved).includes('raw provider')) throw new Error('sensitive provider data was persisted');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
