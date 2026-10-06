import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildWorkspaceOverview } from "./overview-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildFinanceModel } from "./finance-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { createStoredFinanceEvidence } from "./finance-persistence.ts";

const NOW = "2026-09-27T08:00:00.000Z";

function identityAnchor(revalidation = false) {
  return {
    version: 1 as const,
    scope: "journey_browser_anchor" as const,
    journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
    address_input: "臺北市信義區市府路1號",
    normalized_address: "臺北市信義區市府路1號",
    coordinates: { latitude: 25.0375, longitude: 121.5637 },
    administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" },
    location_status: revalidation ? "stale" as const : "candidate" as const,
    parcel: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
    building: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: ["no_approved_building_identity_evidence"], confirmation: null },
    confidence: { level: revalidation ? "unknown" as const : "high" as const, domain: "address_spatial_correlation" as const, basis: ["normalized_address", "trusted_geocoding_coordinates"], limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"] },
    evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding" as const, checked_at: NOW }], checked_at: NOW, limitations: ["journey_browser_correlation_only"] },
    revalidation: revalidation ? { status: "needs_revalidation" as const, conflicts: ["normalized_address" as const] } : { status: "current" as const, conflicts: [] },
  };
}

function savedCase(options: { anchor?: ReturnType<typeof identityAnchor>; withMarket?: boolean; withValuation?: boolean; withCommute?: boolean; withoutJourney?: boolean } = {}) {
  return {
    id: "saved-case-1",
    title: "市府路案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1 as const,
    workflowMode: "buying_wizard" as const,
    activeWizardStep: "report" as const,
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號", propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: options.anchor,
      journeyContext: options.withoutJourney ? undefined : {
        version: 1 as const,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected" as const, askingPriceWan: 2480 },
        priceBasis: "asking" as const,
        activePriceWan: 2480,
      },
      marketInsight: options.withMarket ? { status: "partial" } : undefined,
      valuation: options.withValuation ? { status: "partial" } : undefined,
      commuteRoute: options.withCommute ? { status: "partial" } : undefined,
    },
  };
}

test("legacy adapter restores the bounded property context without promoting it to durable identity", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ anchor: identityAnchor() }) as never);

  assert.equal(workspace.caseId, "saved-case-1");
  assert.equal(workspace.displayAddress, "臺北市信義區市府路1號");
  assert.equal(workspace.identity.state, "confirmed");
  assert.equal(workspace.identity.scope, "journey_browser_anchor");
  assert.equal(workspace.assumptions.activePriceBasis, "asking");
  assert.equal(workspace.assumptions.activePriceWan, 2480);
  assert.equal(workspace.saveState, "saved");
});

test("legacy adapter keeps absent evidence not-started and compacted evidence limited", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ anchor: identityAnchor(), withMarket: true }) as never);

  assert.deepEqual(workspace.evidence.market, {
    query: "succeeded",
    usability: "limited",
    completeness: "partial",
    summaryOnly: true,
  });
  assert.deepEqual(workspace.evidence.location, {
    query: "not_started",
    completeness: "not_started",
    summaryOnly: false,
  });
});

test("legacy adapter does not present the case save time as an evidence check time", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ withMarket: true }) as never);

  assert.equal(workspace.evidence.market.checkedAt, undefined);
});

test("legacy adapter requires revalidation when the displayed address conflicts with the identity anchor", () => {
  const row = savedCase({ anchor: identityAnchor(), withMarket: true });
  row.data.journeyContext!.propertyContext.addressSummary = "臺北市大安區仁愛路四段1號";
  const workspace = adaptSavedCaseToWorkspace(row as never);

  assert.equal(workspace.identity.state, "revalidation_required");
  assert.equal(workspace.evidence.market.usability, "stale");
});

test("legacy adapter uses the asking-price fallback as the active asking price", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ withoutJourney: true }) as never);

  assert.equal(workspace.assumptions.activePriceBasis, "asking");
  assert.equal(workspace.assumptions.activePriceWan, 2480);
});

test("legacy adapter exposes identity revalidation instead of showing stale evidence as current", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ anchor: identityAnchor(true), withMarket: true }) as never);

  assert.equal(workspace.identity.state, "revalidation_required");
  assert.equal(workspace.evidence.market.usability, "stale");
});

test("overview reports honest unknowns and next routes without inventing findings", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ anchor: identityAnchor() }) as never);
  const overview = buildWorkspaceOverview(workspace);

  assert.deepEqual(overview.findings, []);
  assert.deepEqual(overview.unknowns.map((item: { id: string }) => item.id), [
    "market-not-started",
    "valuation-not-started",
    "location-not-started",
    "commute-not-started",
    "risk-not-started",
    "finance-not-started",
  ]);
  assert.deepEqual(overview.actions.map((item: { href: string }) => item.href), [
    "/cases/saved-case-1/market",
    "/cases/saved-case-1/location",
    "/cases/saved-case-1/risk",
    "/cases/saved-case-1/finance",
  ]);
  assert.equal(overview.readiness.value, "not_ready");
});

test("overview keeps missing counterparts visible when a section has mixed evidence", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ withValuation: true, withCommute: true }) as never);
  const overview = buildWorkspaceOverview(workspace);

  assert.deepEqual(overview.unknowns.map((item: { id: string }) => item.id), [
    "market-not-started",
    "location-not-started",
    "risk-not-started",
    "finance-not-started",
  ]);
  assert.deepEqual(overview.actions.map((item: { href: string }) => item.href), [
    "/cases/saved-case-1/market",
    "/cases/saved-case-1/location",
    "/cases/saved-case-1/risk",
    "/cases/saved-case-1/finance",
  ]);
});

test("overview blocks synthesis while identity requires revalidation", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ anchor: identityAnchor(true) }) as never);
  const overview = buildWorkspaceOverview(workspace);

  assert.equal(overview.readiness.value, "blocked");
  assert.equal(overview.blockers[0]?.id, "identity-revalidation");
});

test("legacy adapter reopens bounded finance evidence without restoring raw backend payloads", () => {
  const row = savedCase({ anchor: identityAnchor() });
  const finance = buildFinanceModel({
    caseId: row.id,
    revision: 1,
    identityAnchorId: row.data.propertyIdentityAnchor?.journey_anchor_id,
    identityState: "confirmed",
    activePriceBasis: "asking",
    activePriceWan: 2480,
    areaPing: 30,
    loanResult: {
      property_price_wan: 2480, down_payment_ratio: 0.2, down_payment_wan: 496, loan_amount_wan: 1984,
      annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null,
      monthly_payment: 75_312, grace_period_monthly_payment: null, post_grace_monthly_payment: null,
      total_payment: 27_112_320, total_interest: 7_272_320, income_burden_ratio: null,
      affordability_level: "unknown", affordability_message: "未提供月收入", sensitivity: [], disclaimer: "raw",
    },
    calculatedAt: NOW,
  });
  (row.data as typeof row.data & { financeEvidence?: ReturnType<typeof createStoredFinanceEvidence> }).financeEvidence = createStoredFinanceEvidence(finance, { caseId: row.id, revision: 1, areaPing: 30 });

  const workspace = adaptSavedCaseToWorkspace(row as never);

  assert.ok(workspace.finance);
  assert.equal(workspace.finance.freshness.source, "saved_snapshot");
  assert.equal(workspace.finance.loan.monthlyPaymentTwd, 75_312);
  assert.equal(workspace.finance.affordability.status, "unassessed");
  assert.equal(workspace.evidence.finance.usability, "limited");
});

test("legacy zero area remains missing when reopening a finance snapshot", () => {
  const row = savedCase({ anchor: identityAnchor() });
  delete (row.inputSummary as Partial<typeof row.inputSummary>).areaPing;
  row.data.inputs.area_ping = 0;
  const finance = buildFinanceModel({ caseId: row.id, revision: 1, identityAnchorId: row.data.propertyIdentityAnchor?.journey_anchor_id, identityState: "confirmed", activePriceBasis: "asking", activePriceWan: 2480, areaPing: null, calculatedAt: NOW });
  const stored = createStoredFinanceEvidence({
    ...finance,
    calculation: { query: "succeeded", usability: "usable", completeness: "partial" },
    loan: { ...finance.loan, status: "available", propertyPriceWan: 2480, monthlyPaymentTwd: 75_312 },
    freshness: { status: "current", calculatedAt: NOW, source: "live_calculation" },
  }, { caseId: row.id, revision: 1, areaPing: null });
  (row.data as typeof row.data & { financeEvidence?: typeof stored }).financeEvidence = stored;

  const workspace = adaptSavedCaseToWorkspace(row as never);

  assert.equal(workspace.finance?.freshness.status, "current");
  assert.equal(workspace.assumptions.areaPing, undefined);
});

test("finance-only area assumptions reopen current when the case area is missing", () => {
  const row = savedCase({ anchor: identityAnchor() });
  delete (row.inputSummary as Partial<typeof row.inputSummary>).areaPing;
  row.data.inputs.area_ping = 0;
  const finance = buildFinanceModel({
    caseId: row.id,
    revision: 1,
    identityAnchorId: row.data.propertyIdentityAnchor?.journey_anchor_id,
    identityState: "confirmed",
    activePriceBasis: "asking",
    activePriceWan: 2480,
    areaPing: 26,
    loanResult: {
      property_price_wan: 2480, down_payment_ratio: 0.2, down_payment_wan: 496, loan_amount_wan: 1984,
      annual_interest_rate: 2.65, loan_years: 25, grace_period_years: 0, monthly_income_wan: 15,
      monthly_payment: 90_000, grace_period_monthly_payment: null, post_grace_monthly_payment: null,
      total_payment: 27_000_000, total_interest: 7_160_000, income_burden_ratio: 0.6,
      affordability_level: "risky", affordability_message: "依輸入條件估算", sensitivity: [], disclaimer: "raw",
    },
    calculatedAt: NOW,
  });
  const stored = createStoredFinanceEvidence(finance, { caseId: row.id, revision: 1, areaPing: 26 });
  (row.data as typeof row.data & { financeEvidence?: typeof stored }).financeEvidence = stored;

  const workspace = adaptSavedCaseToWorkspace(row as never);

  assert.equal(workspace.finance?.freshness.status, "current");
  assert.equal(workspace.finance?.holding.assumptions.areaPing, 26);
  assert.equal(workspace.finance?.loan.annualInterestRate, 2.65);
  assert.equal(workspace.finance?.loan.loanYears, 25);
});
