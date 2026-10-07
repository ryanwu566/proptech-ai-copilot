import assert from "node:assert/strict";
import test from "node:test";

import type { SavedCase, SavedCaseIdentityExpectation } from "../case-storage.ts";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
const saveModule = await import("./case-snapshot-save.ts").catch(() => null);

const CREATED_AT = "2026-10-06T03:00:00.000Z";
const SAVED_AT = "2026-10-07T03:00:00.000Z";
const ADDRESS = "臺中市西屯區臺灣大道三段100號";

function anchor(options: { stale?: boolean; address?: string; latitude?: number } = {}) {
  const stale = options.stale === true;
  return {
    version: 1 as const,
    scope: "journey_browser_anchor" as const,
    journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
    address_input: options.address ?? ADDRESS,
    normalized_address: options.address ?? ADDRESS,
    coordinates: { latitude: options.latitude ?? 24.16525, longitude: 120.64555 },
    administrative_location: { city: "臺中市", district: "西屯區", village: "潮洋里", village_code: "66000060-020" },
    location_status: stale ? "stale" as const : "candidate" as const,
    parcel: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
    building: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: ["no_approved_building_identity_evidence"], confirmation: null },
    confidence: { level: stale ? "unknown" as const : "high" as const, domain: "address_spatial_correlation" as const, basis: ["normalized_address", "trusted_geocoding_coordinates"], limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"] },
    evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding" as const, checked_at: CREATED_AT }], checked_at: CREATED_AT, limitations: ["journey_browser_correlation_only"] },
    revalidation: stale ? { status: "needs_revalidation" as const, conflicts: ["normalized_address" as const] } : { status: "current" as const, conflicts: [] },
  };
}

function savedCase(options: { stale?: boolean; valuationUnavailable?: boolean; rawDetail?: boolean } = {}): SavedCase {
  return {
    id: "case-1",
    title: "臺灣大道案件",
    createdAt: CREATED_AT,
    updatedAt: CREATED_AT,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "report",
    progress: 60,
    inputSummary: { city: "臺中市", district: "西屯區", road: "臺灣大道三段100號", propertyPrice: 2480 },
    data: {
      inputs: { city: "臺中市", district: "西屯區", road: "臺灣大道三段100號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: anchor({ stale: options.stale }),
      journeyContext: { version: 1, propertyContext: { city: "臺中市", district: "西屯區", road: "臺灣大道三段", addressSummary: ADDRESS, sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 }, priceBasis: "asking", activePriceWan: 2480, ...(options.valuationUnavailable ? { valuationStatus: "unavailable" as const } : {}) },
      ...(options.rawDetail ? { propertySearch: { matched_transactions: [{ address: "raw row" }] } as never } : {}),
    },
  };
}

function expectation(overrides: Partial<SavedCaseIdentityExpectation> = {}): SavedCaseIdentityExpectation {
  return {
    journeyAnchorId: "journey-browser-11111111-2222-4333-8444-555555555555",
    normalizedAddress: ADDRESS,
    coordinates: { latitude: 24.16525, longitude: 120.64555 },
    ...overrides,
  };
}

function resave(
  rows: SavedCase[],
  caseId: string,
  expected: SavedCaseIdentityExpectation,
  expectedUpdatedAt = CREATED_AT,
  identityState: "confirmed" | "unconfirmed" | "revalidation_required" | "conflict" = "confirmed",
) {
  const candidate = saveModule?.buildSavedCaseSnapshotUpdate;
  return candidate
    ? candidate(rows, caseId, expected, identityState, expectedUpdatedAt, () => SAVED_AT, (data) => ({ ...data, propertySearch: data.propertySearch ? { ...data.propertySearch, matched_transactions: [] } : undefined }))
    : { result: { status: "missing" as const }, rows };
}

test("identity-valid partial evidence can be saved without becoming complete", () => {
  const update = resave([savedCase()], "case-1", expectation());
  assert.equal(update.result.status, "saved");
  assert.equal(update.rows[0]?.progress, 60);
  assert.equal(update.rows[0]?.updatedAt, SAVED_AT);
  assert.equal(update.rows[0]?.data.valuation, undefined);
});

test("attempted unavailable valuation survives re-save and reopen", () => {
  const update = resave([savedCase({ valuationUnavailable: true })], "case-1", expectation());
  assert.equal(update.result.status, "saved");
  assert.equal(update.rows[0]?.data.journeyContext?.valuationStatus, "unavailable");
});

test("re-save compacts the current bounded snapshot instead of retaining row-level provider detail", () => {
  const update = resave([savedCase({ rawDetail: true })], "case-1", expectation());
  assert.equal(update.result.status, "saved");
  assert.deepEqual(update.rows[0]?.data.propertySearch?.matched_transactions, []);
});

test("stale identity blocks save with an actionable reason and preserves the prior snapshot", () => {
  const original = savedCase({ stale: true, valuationUnavailable: true });
  const update = resave([original], "case-1", expectation(), CREATED_AT, "revalidation_required");
  assert.equal(update.result.status, "blocked");
  if (update.result.status === "blocked") {
    assert.equal(update.result.reason, "identity_revalidation_required");
    assert.match(update.result.message, /重新確認/);
  }
  assert.equal(update.rows[0]?.updatedAt, CREATED_AT);
  assert.equal(update.rows[0]?.data.journeyContext?.valuationStatus, "unavailable");
});

test("derived unconfirmed identity blocks save even when an anchor has current flags", () => {
  const original = savedCase({ valuationUnavailable: true });
  const update = resave([original], "case-1", expectation(), CREATED_AT, "unconfirmed");
  assert.equal(update.result.status, "blocked");
  if (update.result.status === "blocked") assert.equal(update.result.reason, "identity_unconfirmed");
  assert.equal(update.rows[0]?.updatedAt, CREATED_AT);
});

test("derived display-address conflict blocks save even when the stored anchor is current", () => {
  const original = savedCase({ valuationUnavailable: true });
  const update = resave([original], "case-1", expectation(), CREATED_AT, "revalidation_required");
  assert.equal(update.result.status, "blocked");
  if (update.result.status === "blocked") assert.equal(update.result.reason, "identity_revalidation_required");
  assert.equal(update.rows[0]?.updatedAt, CREATED_AT);
});

test("anchor mismatch blocks save instead of attaching another property's expectation", () => {
  const update = resave([savedCase()], "case-1", expectation({ normalizedAddress: "臺北市信義區市府路1號" }));
  assert.equal(update.result.status, "blocked");
  if (update.result.status === "blocked") {
    assert.equal(update.result.reason, "identity_mismatch");
    assert.match(update.result.message, /目前物件/);
  }
  assert.equal(update.rows[0]?.updatedAt, CREATED_AT);
});

test("a newer stored snapshot blocks an older open workspace without overwriting it", () => {
  const newer = { ...savedCase({ valuationUnavailable: true }), updatedAt: SAVED_AT };
  const update = resave([newer], "case-1", expectation(), CREATED_AT);
  assert.equal(update.result.status, "blocked");
  if (update.result.status === "blocked") {
    assert.equal(update.result.reason, "revision_mismatch");
    assert.match(update.result.message, /重新開啟/);
  }
  assert.equal(update.rows[0]?.updatedAt, SAVED_AT);
  assert.equal(update.rows[0]?.data.journeyContext?.valuationStatus, "unavailable");
});

test("missing case reports the exact recovery path", () => {
  const update = resave([], "missing", expectation());
  assert.equal(update.result.status, "blocked");
  if (update.result.status === "blocked") {
    assert.equal(update.result.reason, "case_not_found");
    assert.match(update.result.message, /已儲存案件/);
  }
});
