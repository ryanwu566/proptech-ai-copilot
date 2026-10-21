import assert from "node:assert/strict";
import test from "node:test";
import type { SavedCase } from "../case-storage";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildConfirmedLocationAnchor, interpretLocationResolution, locationRequestFailure, needsLocationConfirmation, planIdentityConfirmation } from "./location-confirmation.ts";
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
// @ts-expect-error Native TS runner extension.
import { hasCompleteAdministrativeArea, normalizeJourneyPropertyIdentityAnchor } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { locationConfirmationCopy } from "./location-confirmation-copy.ts";
// @ts-expect-error Native TS runner extension.
import { identityConfirmationCopy, identityConfirmationKind } from "./identity-confirmation-copy.ts";

const NOW = "2026-10-18T08:00:00.000Z";
const ADDRESS = "臺北市信義區市府路1號";
const RESOLVED = { status: "resolved", source: "tgos", formatted_address: "臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, confidence: "high", message: "ok", county: "臺北市", district: "信義區" };
const options = { now: () => NOW, idFactory: () => "11111111-2222-4333-8444-555555555555" };
const draft = (): SavedCase => buildAddressDraftCase(ADDRESS, { id: "draft-1", now: NOW })!;

test("neutral copy is derived separately from changed confirmed identity in all four locales", () => {
  const pending = adaptSavedCaseToWorkspace(draft());
  const changedRow = confirmed();
  changedRow.data.journeyContext!.propertyContext.addressSummary = "臺中市西屯區臺灣大道三段100號";
  const changed = adaptSavedCaseToWorkspace(changedRow);
  assert.equal(identityConfirmationKind(pending.identity), "pending");
  assert.equal(identityConfirmationKind(changed.identity), "reconfirmation");
  assert.equal(identityConfirmationKind(adaptSavedCaseToWorkspace(confirmed()).identity), "confirmed");
  assert.equal(identityConfirmationKind({ ...changed.identity, anchor: { ...changed.identity.anchor!, confidence: { ...changed.identity.anchor!.confidence, level: "low" } } }), "pending");
  assert.equal(identityConfirmationKind({ ...pending.identity, state: "conflict" }), "pending");
  assert.doesNotMatch(buildLocationOverviewHandoff(pending).unresolved.join(" "), /變更|重新/);
  assert.match(buildLocationOverviewHandoff(changed).unresolved.join(" "), /重新確認/);
  for (const copy of Object.values(identityConfirmationCopy)) {
    for (const domain of ["Title", "Location", "Risk", "Report", "Route", "Action"] as const) {
      assert.ok(copy[`pending${domain}`].trim());
      assert.notEqual(copy[`pending${domain}`], copy[`reconfirmation${domain}`]);
      assert.doesNotMatch(copy[`pending${domain}`], /變更|重新|changed|again|reconfirm|再確認|変更|다시|변경/i);
    }
  }
  // Both remain blocked; changing copy never grants report/risk permissions.
  for (const workspace of [pending, changed]) {
    assert.equal(buildRiskQueryContext(workspace), null);
    assert.deepEqual(buildReportModel(projectCaseEvidence(workspace), NOW).sections, []);
  }
});

test("location request failures distinguish capacity, provider and network unavailability", () => {
  assert.equal(locationRequestFailure(429), "capacity_unavailable");
  assert.equal(locationRequestFailure(503), "provider_unavailable");
  assert.equal(locationRequestFailure(), "unavailable");
});

test("four locales distinguish administrative incompleteness from resolution failure", () => {
  const keys = Object.keys(locationConfirmationCopy["zh-TW"]).sort();
  for (const copy of Object.values(locationConfirmationCopy)) {
    assert.deepEqual(Object.keys(copy).sort(), keys);
    for (const key of ["adminUnknown", "adminPendingTitle", "adminIncomplete", "capacity_unavailable", "provider_unavailable"] as const) assert.ok(copy[key].trim());
    assert.notEqual(copy.adminIncomplete, copy.unavailable);
    assert.notEqual(copy.capacity_unavailable, copy.provider_unavailable);
  }
});

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
  ];
  for (const [value, reason] of cases) assert.deepEqual(interpretLocationResolution(value, ADDRESS), { kind: "blocked", reason }, String(reason));
  assert.deepEqual(interpretLocationResolution(RESOLVED, "  "), { kind: "blocked", reason: "invalid" });
});

test("trusted coordinates without administrative area confirm spatially and survive reopen without invented geography", () => {
  for (const area of [{ county: undefined, district: undefined }, { county: null, district: null }, { county: "臺北市", district: "  " }, { county: null, district: "信義區" }]) {
    const result = interpretLocationResolution({ ...RESOLVED, ...area }, ADDRESS);
    assert.equal(result.kind, "candidate");
    const anchor = buildConfirmedLocationAnchor(result.candidate, options)!;
    assert.ok(anchor);
    assert.equal(hasCompleteAdministrativeArea(anchor), false);
    assert.deepEqual(normalizeJourneyPropertyIdentityAnchor(anchor), anchor);
    assert.equal(anchor.administrative_location.city, area.county ?? null);
    assert.equal(anchor.administrative_location.district, area.district?.trim() || null);
    assert.equal(anchor.confidence.level, "medium");
    assert.equal(anchor.parcel.status, "unavailable");
    assert.equal(anchor.building.status, "unavailable");
    assert.ok(anchor.confidence.limitations.includes("not_parcel_building_ownership_or_legal_boundary_confirmation"));
    const row = draft();
    assert.equal(planIdentityConfirmation(row, anchor, JSON.stringify(row)).kind, "write");
    const reopened = JSON.parse(JSON.stringify({ ...row, data: { ...row.data, propertyIdentityAnchor: anchor } }));
    const workspace = adaptSavedCaseToWorkspace(reopened);
    assert.equal(workspace.identity.state, "confirmed");
    assert.equal(needsLocationConfirmation(workspace), false);
    assert.equal(buildLocationOverviewHandoff(workspace).mapReady, true);
    assert.notEqual(buildLocationOverviewHandoff(workspace).commuteReadiness, "blocked");
    assert.equal(buildMarketRefreshContext(workspace, reopened), null);
    assert.deepEqual(workspace.identity.anchor?.administrative_location, anchor.administrative_location);
    assert.deepEqual(workspace.location.property.coordinates, anchor.coordinates);
  }
});

test("confirmed anchor carries the typed address, geocode and area but never parcel or building identity", () => {
  const anchor = buildConfirmedLocationAnchor(candidate(), options)!;
  assert.equal(anchor.address_input, ADDRESS);
  assert.deepEqual(anchor.coordinates, { latitude: 25.0375, longitude: 121.5637 });
  assert.deepEqual(anchor.administrative_location, { city: "臺北市", district: "信義區", village: null, village_code: null });
  assert.equal(hasCompleteAdministrativeArea(anchor), true);
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
