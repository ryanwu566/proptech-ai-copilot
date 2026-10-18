import assert from "node:assert/strict";
import test from "node:test";
import type { SavedCase } from "../case-storage";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildConfirmedLocationAnchor, interpretLocationResolution, needsLocationConfirmation, planIdentityConfirmation } from "./location-confirmation.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildAddressDraftCase } from "./case-draft.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildMarketRefreshContext } from "./market-price-refresh.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildRiskQueryContext } from "./risk-evidence-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildLocationOverviewHandoff } from "./location-context.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildComparisonModel, buildReportModel } from "./compare-report-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildWorkspaceOverview } from "./overview-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { e9Case } from "./e9-test-fixtures.ts";

const NOW = "2026-10-18T08:00:00.000Z";
const ADDRESS = "臺北市信義區市府路1號";
const RESOLVED = { status: "resolved", source: "tgos", formatted_address: "臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, confidence: "high", message: "ok", county: "臺北市", district: "信義區" };
const options = { now: () => NOW, idFactory: () => "11111111-2222-4333-8444-555555555555" };
const draft = (): SavedCase => buildAddressDraftCase(ADDRESS, { id: "draft-1", now: NOW })!;

function candidate() {
  const result = interpretLocationResolution(RESOLVED, ADDRESS);
  assert.equal(result.kind, "candidate");
  return result.candidate;
}

function confirmed(): SavedCase {
  const row = draft();
  return { ...row, updatedAt: "2026-10-18T08:05:00.000Z", data: { ...row.data, propertyIdentityAnchor: buildConfirmedLocationAnchor(candidate(), options)! } };
}

test("a resolved, high-confidence, area-complete Taiwan geocode becomes a candidate only", () => {
  assert.deepEqual(candidate(), { addressInput: ADDRESS, interpretedAddress: ADDRESS, county: "臺北市", district: "信義區", latitude: 25.0375, longitude: 121.5637, source: "tgos" });
});

test("interpretation fails closed for every non-confirmable result", () => {
  const cases: Array<[unknown, string]> = [
    [{ ...RESOLVED, status: "unresolved" }, "unresolved"],
    [{ ...RESOLVED, status: "unavailable" }, "unavailable"],
    [null, "invalid"],
    ["resolved", "invalid"],
    [{ ...RESOLVED, source: "none" }, "invalid"],
    [{ ...RESOLVED, confidence: "unknown" }, "low_confidence"],
    [{ ...RESOLVED, latitude: null }, "missing_coordinates"],
    [{ ...RESOLVED, longitude: Number.NaN }, "missing_coordinates"],
    [{ ...RESOLVED, latitude: 35.68, longitude: 139.76 }, "invalid"],
    [{ ...RESOLVED, county: null }, "missing_area"],
    [{ ...RESOLVED, district: "  " }, "missing_area"],
  ];
  for (const [value, reason] of cases) assert.deepEqual(interpretLocationResolution(value, ADDRESS), { kind: "blocked", reason }, String(reason));
  assert.deepEqual(interpretLocationResolution(RESOLVED, "  "), { kind: "blocked", reason: "invalid" });
});

test("confirmed anchor carries the typed address, geocode and area but never parcel or building identity", () => {
  const anchor = buildConfirmedLocationAnchor(candidate(), options)!;
  assert.equal(anchor.address_input, ADDRESS);
  assert.deepEqual(anchor.coordinates, { latitude: 25.0375, longitude: 121.5637 });
  assert.deepEqual(anchor.administrative_location, { city: "臺北市", district: "信義區", village: null, village_code: null });
  assert.equal(anchor.parcel.status, "unavailable");
  assert.equal(anchor.building.status, "unavailable");
  assert.equal(anchor.confidence.level, "medium");
  assert.equal(anchor.revalidation.status, "current");
  assert.deepEqual(anchor.evidence.sources.map((source: { source_id: string }) => source.source_id), ["property_selection", "tgos_geocoding"]);
  assert.deepEqual(buildConfirmedLocationAnchor(candidate(), options), anchor);
});

test("only a never-located case asks for location confirmation", () => {
  assert.equal(needsLocationConfirmation(adaptSavedCaseToWorkspace(draft())), true);
  assert.equal(needsLocationConfirmation(adaptSavedCaseToWorkspace(confirmed())), false);
  assert.equal(needsLocationConfirmation(adaptSavedCaseToWorkspace(e9Case())), false);
});

test("confirmation write is compare-and-swap and never overwrites an existing anchor", () => {
  const row = draft();
  const anchor = buildConfirmedLocationAnchor(candidate(), options)!;
  const version = JSON.stringify(row);
  assert.equal(planIdentityConfirmation(row, anchor, version).kind, "write");
  assert.deepEqual(planIdentityConfirmation(row, anchor, JSON.stringify({ ...row, title: "changed" })), { kind: "blocked", reason: "case_changed" });
  assert.deepEqual(planIdentityConfirmation(undefined, anchor, version), { kind: "blocked", reason: "case_changed" });
  const located = confirmed();
  assert.deepEqual(planIdentityConfirmation(located, anchor, JSON.stringify(located)), { kind: "blocked", reason: "already_identified" });
  assert.deepEqual(planIdentityConfirmation(row, { ...anchor, address_input: "臺中市西屯區臺灣大道三段100號" }, version), { kind: "blocked", reason: "invalid_anchor" });
  assert.deepEqual(planIdentityConfirmation(row, { ...anchor, coordinates: null }, version), { kind: "blocked", reason: "invalid_anchor" });
  assert.deepEqual(planIdentityConfirmation(row, { junk: true }, version), { kind: "blocked", reason: "invalid_anchor" });
});

test("before confirmation every identity-gated capability stays blocked", () => {
  const row = draft();
  const workspace = adaptSavedCaseToWorkspace(row);
  assert.equal(buildMarketRefreshContext(workspace, row), null);
  assert.equal(buildRiskQueryContext(workspace), null);
  assert.equal(buildLocationOverviewHandoff(workspace).mapReady, false);
  assert.equal(buildReportModel(projectCaseEvidence(workspace), NOW).status, "identity_requires_revalidation");
  assert.equal(buildComparisonModel([projectCaseEvidence(workspace), projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case()))], ["draft-1", "case-a"]).status, "identity_requires_revalidation");
  const overview = buildWorkspaceOverview(workspace);
  assert.equal(overview.blockers[0].id, "identity-confirm-location");
  assert.match(overview.blockers[0].href, /\/cases\/draft-1\/location$/);
});

test("after confirmation identity unlocks downstream actions without creating any evidence", () => {
  const row = confirmed();
  const workspace = adaptSavedCaseToWorkspace(row);
  assert.equal(workspace.identity.state, "confirmed");
  for (const state of Object.values(workspace.evidence) as Array<{ query: string }>) assert.equal(state.query, "not_started");
  // Market: identity no longer blocks; the payload is the confirmed area only.
  assert.deepEqual(buildMarketRefreshContext(workspace, row)?.payload, { county: "臺北市", district: "信義區" });
  // Location / Commute: confirmed coordinates feed the map and route origin.
  assert.equal(buildLocationOverviewHandoff(workspace).mapReady, true);
  assert.deepEqual(workspace.location.property.coordinates, { latitude: 25.0375, longitude: 121.5637 });
  // Risk: the explicit query action has a context.
  assert.notEqual(buildRiskQueryContext(workspace), null);
  // Report and Compare: no longer blocked by identity.
  const evidence = projectCaseEvidence(workspace);
  assert.notEqual(buildReportModel(evidence, NOW).status, "identity_requires_revalidation");
  const other = adaptSavedCaseToWorkspace(e9Case());
  assert.notEqual(buildComparisonModel([evidence, projectCaseEvidence(other)], ["draft-1", "case-a"]).status, "identity_requires_revalidation");
  // Overview: the confirm-location blocker is gone.
  assert.equal(buildWorkspaceOverview(workspace).blockers.some((blocker: { id: string }) => blocker.id === "identity-confirm-location"), false);
});

test("a legacy case with saved address parts but no journey summary can be confirmed against those parts", () => {
  const legacy = e9Case();
  const row: SavedCase = { ...legacy, data: { ...legacy.data, propertyIdentityAnchor: undefined, journeyContext: undefined } };
  const address = `${legacy.inputSummary.city}${legacy.inputSummary.district}${legacy.inputSummary.road}`;
  const result = interpretLocationResolution({ ...RESOLVED, county: "臺中市", district: "西屯區", latitude: 24.16, longitude: 120.64 }, address);
  assert.equal(result.kind, "candidate");
  const anchor = buildConfirmedLocationAnchor(result.candidate, options)!;
  assert.equal(planIdentityConfirmation(row, anchor, JSON.stringify(row)).kind, "write");
  assert.equal(adaptSavedCaseToWorkspace({ ...row, data: { ...row.data, propertyIdentityAnchor: anchor } }).identity.state, "confirmed");
});
