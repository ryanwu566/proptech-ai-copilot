import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
// @ts-expect-error Native TS runner extension.
import { acquireLocationResolution, buildConfirmedLocationAnchor } from "./location-confirmation.ts";
// @ts-expect-error Native TS runner extension.
import { buildAddressDraftCase } from "./case-draft.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { buildMarketRefreshContext } from "./market-price-refresh.ts";
// @ts-expect-error Native TS runner extension.
import { hasCompleteAdministrativeArea } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { planAdministrativeAreaRepair } from "./administrative-area-repair.ts";
import type { SavedCase } from "../case-storage";
import type { LocationCandidate } from "./location-confirmation";

const fixtures = JSON.parse(readFileSync(new URL("../../../tests/fixtures/location_market_google.json", import.meta.url), "utf8"));
const options = { now: () => "2026-10-23T10:00:00.000Z", idFactory: () => "11111111-2222-4333-8444-555555555555" };

for (const fixture of fixtures) test(`${fixture.name}: API contract through acquisition, confirmation, Market and reopen`, async () => {
  let calls = 0;
  const result = await acquireLocationResolution(fixture.address, async () => { calls++; return fixture.response; });
  assert.equal(result.kind, "candidate");
  if (result.kind !== "candidate") return;
  const anchor = buildConfirmedLocationAnchor(result.candidate, options)!;
  assert.equal(anchor.administrative_location.city, "臺北市");
  assert.equal(anchor.administrative_location.district, fixture.response.district);
  assert.equal(hasCompleteAdministrativeArea(anchor), true);
  const row = buildAddressDraftCase(fixture.address, { id: fixture.name, now: options.now() })!;
  row.data.propertyIdentityAnchor = anchor;
  for (const saved of [row, JSON.parse(JSON.stringify(row))]) {
    const workspace = adaptSavedCaseToWorkspace(saved);
    assert.equal(workspace.identity.state, "confirmed");
    assert.deepEqual(buildMarketRefreshContext(workspace, saved)?.payload, { county: "臺北市", district: fixture.response.district });
  }
  assert.equal(calls, 1);
});

function legacy(): { row: SavedCase; candidate: LocationCandidate } {
  const fixture = fixtures[0];
  const candidate: LocationCandidate = { addressInput: fixture.address, interpretedAddress: fixture.response.formatted_address,
    latitude: fixture.response.latitude, longitude: fixture.response.longitude, county: "臺北市", district: "信義區", source: "google" };
  const row = buildAddressDraftCase(fixture.address, { id: "old-case", now: options.now() })!;
  row.data.propertyIdentityAnchor = buildConfirmedLocationAnchor({ ...candidate, county: null, district: null }, options)!;
  return { row, candidate };
}

test("repair fills administrative area only and preserves saved identity and evidence", () => {
  const { row, candidate } = legacy();
  const before = JSON.stringify(row);
  const plan = planAdministrativeAreaRepair(row, candidate, before, options.now());
  assert.equal(plan.kind, "write");
  if (plan.kind !== "write") return;
  assert.equal(JSON.stringify(row), before);
  assert.equal(plan.anchor.journey_anchor_id, row.data.propertyIdentityAnchor!.journey_anchor_id);
  assert.deepEqual(plan.anchor.coordinates, row.data.propertyIdentityAnchor!.coordinates);
  assert.equal(plan.anchor.normalized_address, row.data.propertyIdentityAnchor!.normalized_address);
  assert.deepEqual(plan.anchor.parcel, row.data.propertyIdentityAnchor!.parcel);
  assert.deepEqual(plan.anchor.building, row.data.propertyIdentityAnchor!.building);
  assert.equal(hasCompleteAdministrativeArea(plan.anchor), true);
  assert.deepEqual(plan.anchor.administrative_location, { city: "臺北市", district: "信義區", village: null, village_code: null });
});

test("repair rejects incomplete, foreign, stale or coordinate-changing candidates", () => {
  const { row, candidate } = legacy();
  const version = JSON.stringify(row);
  for (const patch of [{ county: null }, { district: null }, { county: "新北市" }, { district: "中正區" },
    { addressInput: "臺北市中正區中山南路21號" }, { interpretedAddress: "臺北市信義區市府路2號" },
    { latitude: candidate.latitude + 0.001 }, { longitude: Number.NaN }, { source: "none" }]) {
    assert.equal(planAdministrativeAreaRepair(row, { ...candidate, ...patch } as LocationCandidate, version, options.now()).kind, "blocked");
  }
  assert.equal(JSON.stringify(row), version);
  assert.equal(planAdministrativeAreaRepair(row, candidate, "old version", options.now()).kind, "blocked");
  row.data.propertyIdentityAnchor!.revalidation.status = "needs_revalidation";
  assert.equal(planAdministrativeAreaRepair(row, candidate, JSON.stringify(row), options.now()).kind, "blocked");
});

test("repair rejects changed display address, conflicting partial admin and already complete cases", () => {
  for (const change of ["display", "admin", "complete", "low-confidence"] as const) {
    const { row, candidate } = legacy();
    if (change === "display") row.data.journeyContext!.propertyContext.addressSummary = "臺北市中正區中山南路21號";
    if (change === "admin") row.data.propertyIdentityAnchor!.administrative_location.city = "新北市";
    if (change === "complete") row.data.propertyIdentityAnchor!.administrative_location = { city: "臺北市", district: "信義區", village: null, village_code: null };
    if (change === "low-confidence") row.data.propertyIdentityAnchor!.confidence.level = "low";
    assert.equal(planAdministrativeAreaRepair(row, candidate, JSON.stringify(row), options.now()).kind, "blocked");
  }
});

test("repair cannot install unvalidated geography on a prefixless or county-only legacy address", () => {
  for (const address of ["市府路1號", "臺北市市府路1號"]) {
    const { row, candidate } = legacy();
    row.data.journeyContext!.propertyContext.addressSummary = address;
    row.data.propertyIdentityAnchor!.address_input = address;
    row.data.propertyIdentityAnchor!.normalized_address = address;
    assert.equal(planAdministrativeAreaRepair(row, { ...candidate, addressInput: address, interpretedAddress: address }, JSON.stringify(row), options.now()).kind, "blocked");
  }
});
