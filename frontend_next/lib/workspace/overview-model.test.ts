import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildWorkspaceOverview } from "./overview-model.ts";
import type { PropertyCaseWorkspace } from "./workspace-model.ts";

const NOW = "2026-10-07T03:00:00.000Z";

function workspace(overrides: Partial<PropertyCaseWorkspace> = {}): PropertyCaseWorkspace {
  const base = {
    caseId: "case-b",
    revision: 2,
    title: "臺灣大道案件",
    displayAddress: "臺中市西屯區臺灣大道三段100號",
    updatedAt: NOW,
    identity: { state: "confirmed", scope: "journey_browser_anchor", anchor: { journey_anchor_id: "anchor-b", coordinates: { latitude: 24.16525, longitude: 120.64555 } } },
    assumptions: { activePriceBasis: "asking", activePriceWan: 2480, askingPriceWan: 2480, areaPing: 30 },
    evidence: {
      market: { query: "not_started", completeness: "not_started", summaryOnly: false },
      valuation: { query: "not_started", completeness: "not_started", summaryOnly: false },
      location: { query: "not_started", completeness: "not_started", summaryOnly: false },
      commute: { query: "not_started", completeness: "not_started", summaryOnly: false },
      risk: { query: "not_started", completeness: "not_started", summaryOnly: false },
      finance: { query: "not_started", completeness: "not_started", summaryOnly: false },
    },
    marketPrice: {
      isStale: false,
      priceContext: {
        askingPrice: { label: "開價", formatted: "2,480 萬元" },
        activePrice: { label: "開價", formatted: "2,480 萬元" },
        estimateRange: null,
        marketMedianTotal: null,
        marketMedianUnit: null,
      },
      market: { status: "not_started", result: null, history: [], scopeLabel: null, analysisLevel: null, sampleCount: null, fallbackApplied: false },
      valuation: { status: "not_started", result: null, trend: null, estimate: null, comparablesAvailable: false, comparables: [] },
      source: { sourceName: null, effectivePeriod: null, updatedAt: null },
      primaryFinding: "已記錄開價，但成交證據尚未查詢。",
      overview: { priceBasis: "asking", evidenceStatus: "not_started", estimateRange: null, marketRange: null, unresolvedChecks: [], freshness: null },
    },
    location: {
      property: {
        address: "臺中市西屯區臺灣大道三段100號",
        normalizedAddress: "臺中市西屯區臺灣大道三段100號",
        coordinates: { latitude: 24.16525, longitude: 120.64555 },
        checkedAt: NOW,
        village: { name: "潮洋里", code: "66000060-020" },
        sourceIds: ["google_geocoding"],
      },
      routeInvalidated: false,
    },
    risk: null,
    finance: {
      inputFingerprint: "finance-b",
      priceBasis: { basis: "asking", amountWan: 2480, source: "case" },
      calculation: { query: "not_started", usability: null, completeness: "not_started" },
      loan: { status: "not_started", propertyPriceWan: null, downPaymentRatio: null, downPaymentWan: null, principalWan: null, annualInterestRate: null, loanYears: null, gracePeriodYears: null, monthlyIncomeWan: null, monthlyPaymentTwd: null, gracePeriodMonthlyPaymentTwd: null, postGraceMonthlyPaymentTwd: null, totalInterestTwd: null, sensitivity: [] },
      holding: { status: "not_started", knownMonthlySubtotalTwd: null, knownAnnualSubtotalTwd: null, totalKind: "unavailable", assumptions: { loanMonthlyPaymentTwd: null, monthlyIncomeWan: null, areaPing: 30, managementFeePerPingTwd: null, repairReservePerPingTwd: null, annualHomeTaxRatePercent: null, annualLandTaxRatePercent: null, annualInsuranceTwd: null }, breakdown: [] },
      affordability: { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null },
      tax: { query: "not_started", summary: null },
      missingCosts: ["持有成本明細（尚未估算）"],
      unresolvedActions: ["尚未計算房貸情境"],
      freshness: { status: "not_calculated", calculatedAt: null, source: null },
      overview: { activePriceBasis: "asking", calculationStatus: "not_started", monthlyPaymentTwd: null, knownRecurringMonthlyTwd: null, missingCosts: ["持有成本明細（尚未估算）"], affordabilityStatus: "unassessed", unresolvedActions: ["尚未計算房貸情境"], freshness: "not_calculated" },
      comparison: { activePriceWan: 2480, downPaymentWan: null, loanPrincipalWan: null, monthlyPaymentTwd: null, knownRecurringMonthlyTwd: null, knownOneTimeCostsTwd: null, missingCosts: ["持有成本明細（尚未估算）"] },
    },
    saveState: "saved",
  } as unknown as PropertyCaseWorkspace;
  return { ...base, ...overrides };
}

test("all bounded E4-E7 evidence produces separate domain summaries without a score or recommendation", () => {
  const current = workspace();
  current.evidence.market = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };
  current.evidence.valuation = { query: "failed", usability: "unavailable", completeness: "insufficient", summaryOnly: true };
  current.evidence.location = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };
  current.evidence.commute = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };
  current.evidence.risk = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };
  current.evidence.finance = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };
  current.marketPrice.market.status = "limited";
  current.marketPrice.market.sampleCount = 18;
  current.marketPrice.priceContext.marketMedianUnit = { label: "市場成交中位數", formatted: "52.4 萬元／坪" };
  current.marketPrice.valuation.status = "unavailable";
  current.marketPrice.overview.evidenceStatus = "limited";
  current.location.routeEvidence = {
    status: "resolved", source: "google_routes", fallback: false, partial: false, checked_at: NOW,
    origin: { latitude: 24.16525, longitude: 120.64555 }, destination: { address: "臺中車站", latitude: 24.1368, longitude: 120.685 },
    mode: "driving", distance_m: 9800, duration_min: 24,
  } as never;
  current.location.transitContext = { status: "unavailable" } as never;
  current.risk = {
    rows: [{ key: "flood", label: "淹水潛勢", queryStatus: "succeeded", usability: "no_match", interpretation: "unknown", matched: false, result: "已儲存的查詢摘要為未命中；此結果不代表安全。", source: "水利署", sourceLevel: "unknown", effectivePeriod: "2026", limitation: "仍需查證", nextVerification: "查看官方來源", coverage: "covered" }],
    materialEvidenceCount: 0,
    unknownEvidenceCount: 0,
    verificationActions: ["查看官方來源"],
    freshness: { checkedAt: NOW, status: "saved_summary" },
    overview: { materialMatchedEvidence: [], noMatchEvidence: [{ key: "flood", label: "淹水潛勢", result: "已儲存的查詢摘要為未命中；此結果不代表安全。" }], unknownOrUnavailableEvidence: [], unknownOrUnavailableCount: 0, outstandingVerificationActions: ["查看官方來源"], evidenceFreshness: NOW, freshnessStatus: "saved_summary" },
  };
  current.finance = {
    ...current.finance!,
    calculation: { query: "succeeded", usability: "usable", completeness: "partial" },
    loan: { ...current.finance!.loan, status: "available", downPaymentWan: 496, monthlyPaymentTwd: 75_312 },
    affordability: { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null },
    freshness: { status: "current", calculatedAt: NOW, source: "saved_snapshot" },
    overview: { activePriceBasis: "asking", calculationStatus: "succeeded", monthlyPaymentTwd: 75_312, knownRecurringMonthlyTwd: 75_312, missingCosts: ["管理費（缺少坪數）"], affordabilityStatus: "unassessed", unresolvedActions: ["提供月收入以評估負擔"], freshness: "current" },
  };

  const result = buildWorkspaceOverview(current);

  assert.equal(result.domains.market.valuationStatus, "unavailable");
  assert.equal(result.domains.market.freshness, "partial");
  assert.equal(result.domains.location.route?.destination, "臺中車站");
  assert.equal(result.domains.location.secondaryTransitStatus, "unavailable");
  assert.equal(result.domains.risk.noMatchEvidence[0]?.label, "淹水潛勢");
  assert.equal(result.domains.finance.calculationStatus, "succeeded");
  assert.equal(result.domains.finance.affordabilityStatus, "unassessed");
  assert.equal(result.known.some((item) => item.id === "commute-route"), true);
  assert.equal(result.unknown.some((item) => item.id === "valuation-unavailable"), true);
  assert.equal("overallScore" in result, false);
  assert.equal("recommendation" in result, false);
  assert.equal(result.actions.length >= 3 && result.actions.length <= 5, true);
});

test("one completed module remains useful while unopened modules stay explicitly not started", () => {
  const current = workspace();
  current.evidence.location = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };

  const result = buildWorkspaceOverview(current);

  assert.equal(result.domains.location.mapReady, true);
  assert.deepEqual(result.unknown.filter((item) => item.state === "not_started").map((item) => item.id), [
    "market-not-started", "valuation-not-started", "commute-not-started", "risk-not-started", "finance-not-started",
  ]);
});

test("saved snapshot freshness is explicit and never labeled live", () => {
  const current = workspace();
  current.evidence.market = { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true };

  const result = buildWorkspaceOverview(current);

  assert.equal(result.snapshot.kind, "saved_snapshot");
  assert.equal(result.snapshot.savedAt, NOW);
  assert.equal(result.snapshot.isLive, false);
  assert.equal(result.domains.market.freshness, "partial");
});

test("stale identity blocks synthesis and Property B cannot inherit Property A evidence", () => {
  const current = workspace({
    identity: { state: "revalidation_required", scope: "journey_browser_anchor", anchor: null },
    displayAddress: "臺北市信義區市府路1號",
  });
  current.evidence.market = { query: "succeeded", usability: "stale", completeness: "partial", summaryOnly: true };
  current.marketPrice.primaryFinding = "Property A market finding";
  current.marketPrice.overview.evidenceStatus = "stale";

  const result = buildWorkspaceOverview(current);

  assert.equal(result.blockers[0]?.id, "identity-revalidation");
  assert.equal(result.readiness.value, "blocked");
  assert.equal(JSON.stringify(result.known).includes("Property A"), false);
  assert.equal(result.property.displayAddress, "臺北市信義區市府路1號");
  assert.equal(result.domains.market.freshness, "stale");
  assert.equal(result.actions[0]?.href, "/");
});

test("stale finance remains historical and cannot surface as a current known result", () => {
  const current = workspace({
    identity: { state: "revalidation_required", scope: "journey_browser_anchor", anchor: null },
  });
  current.evidence.finance = { query: "succeeded", usability: "stale", completeness: "partial", summaryOnly: true };
  current.finance = {
    ...current.finance!,
    calculation: { query: "succeeded", usability: "stale", completeness: "partial" },
    loan: { ...current.finance!.loan, status: "stale", monthlyPaymentTwd: 75_312 },
    freshness: { status: "stale", calculatedAt: NOW, source: "saved_snapshot" },
    affordability: { status: "assessed", ratio: 0.32, reason: "先前收入評估", basis: "total_housing_cost" },
    overview: { activePriceBasis: "asking", calculationStatus: "succeeded", monthlyPaymentTwd: 75_312, knownRecurringMonthlyTwd: 75_312, missingCosts: [], affordabilityStatus: "assessed", unresolvedActions: ["重新確認物件"], freshness: "stale" },
  };

  const result = buildWorkspaceOverview(current);

  assert.equal(result.domains.finance.freshness, "stale");
  assert.equal(result.domains.finance.monthlyPaymentTwd, null);
  assert.equal(result.domains.finance.knownRecurringMonthlyTwd, null);
  assert.equal(result.domains.finance.affordabilityStatus, "stale");
  assert.equal(result.known.some((row) => row.id === "finance-calculation"), false);
  assert.equal(result.attention.some((row) => row.id === "finance-stale"), true);
});
