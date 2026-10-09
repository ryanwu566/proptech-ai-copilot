import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { resolveCommercialState } from "../commercial/state.ts";
// @ts-expect-error Native TS runner extension.
import { buildWorkspaceOverview } from "./overview-model.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeStoredFinanceEvidence } from "./finance-persistence.ts";
import type { LocationInsightResult } from "../api";

function scenario() {
  const saved = e9Case();
  delete saved.data.journeyContext!.propertyContext.askingPriceWan;
  delete saved.data.journeyContext!.activePriceWan;
  saved.inputSummary.propertyPrice = 3000; // Old ambiguous summary must not become asking.
  const finance = saved.data.financeEvidence!;
  delete saved.data.financeEvidence;
  saved.data.loan = {
    property_price_wan: 3000, down_payment_ratio: .2, down_payment_wan: 600,
    loan_amount_wan: 2400, annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0,
    monthly_income_wan: null, monthly_payment: 91117, grace_period_monthly_payment: null,
    post_grace_monthly_payment: null, total_payment: 32802120, total_interest: 8802120,
    income_burden_ratio: null, affordability_level: "unknown", affordability_message: "", sensitivity: [], disclaimer: "",
  };
  saved.data.locationInsight = {
    radius_m: 800, location_score: 70, category_scores: { risk_score: 50 },
    poi_summary: { transit_count: 3, risk_facility_count: 0 },
    data_quality: { status: "good", missing_sources: ["risk_facilities"], warnings: [] },
    nearest_pois: [], buyer_fit: { commuter: "適合" },
  } as unknown as LocationInsightResult;
  return { saved, finance };
}

test("browser identity is information about address/coordinates in every locale", () => {
  const identity = resolveCommercialState("identity", "confirmed");
  assert.equal(identity.role, "information");
  assert.match(identity.label["zh-TW"], /地址.*座標/);
  assert.match(identity.label.en, /Address.*coordinate/i);
  assert.match(identity.label.ja, /住所.*座標/);
  assert.match(identity.label.ko, /주소.*좌표/);
  assert.equal(resolveCommercialState("identity", "conflict").role, "error");
});

test("legacy ambiguous mortgage remains readable with unknown provenance and no asking price", () => {
  const { saved } = scenario();
  const workspace = adaptSavedCaseToWorkspace(saved);
  const evidence = projectCaseEvidence(workspace);
  assert.equal(workspace.assumptions.askingPriceWan, undefined);
  assert.equal(workspace.assumptions.activePriceWan, undefined);
  assert.equal(evidence.price.asking.value, null);
  assert.equal(evidence.finance.monthlyPayment.value, 91117);
  assert.equal(evidence.finance.price.value, 3000);
  assert.equal(evidence.finance.basis.value, "價格來源未保存");
  assert.equal(evidence.price.valuationEstimate.status, "unavailable");
});

test("legacy missing risk coverage suppresses fabricated zero and score while retaining POIs", () => {
  const { saved } = scenario();
  const workspace = adaptSavedCaseToWorkspace(saved);
  assert.equal(workspace.location.poiSummary?.risk_facility_count, null);
  assert.equal(workspace.location.insight?.category_scores.risk_score, null);
  assert.equal(workspace.location.insight?.location_score, null);
  const evidence = projectCaseEvidence(workspace);
  assert.equal(evidence.location.riskFacility.value, null);
  assert.equal(evidence.location.riskFacility.missingReason, "unavailable");
  assert.equal(evidence.location.transit.value, 3);
});

test("a bare legacy zero cannot fabricate risk coverage", () => {
  const { saved } = scenario();
  saved.data.locationInsight!.data_quality.missing_sources = [];
  assert.equal(projectCaseEvidence(adaptSavedCaseToWorkspace(saved)).location.riskFacility.value, null);
});

test("verified successful zero and no-match facility evidence survive projection", () => {
  for (const status of ["available", "no_match"]) {
    const { saved } = scenario();
    saved.data.locationInsight!.data_quality.missing_sources = [];
    saved.data.locationInsight!.risk_facility_evidence = { status, count: 0, source: "verified facility register", checked_at: saved.updatedAt, reason: "successful_query", limitation: "Radius 800m; observed zero is not safety." };
    const field = projectCaseEvidence(adaptSavedCaseToWorkspace(saved)).location.riskFacility;
    assert.equal(field.value, 0);
    assert.equal(field.source, "verified facility register");
    assert.equal(field.status, status === "no_match" ? "no_match" : "limited");
  }
});

test("saved explicit manual finance remains current within its original identity and assumptions without a case price", () => {
  const { saved, finance } = scenario();
  delete saved.data.loan;
  finance.assumptions.price_basis = "manual";
  finance.input_fingerprint = finance.input_fingerprint.replace("asking|", "manual|");
  saved.data.financeEvidence = finance;
  const workspace = adaptSavedCaseToWorkspace(saved);
  assert.equal(workspace.finance?.freshness.status, "current");
  assert.equal(projectCaseEvidence(workspace).finance.basis.value, "手動試算情境");
  assert.equal(projectCaseEvidence(workspace).finance.monthlyPayment.value, 55111);
});

test("a finance snapshot for another case cannot leak its results", () => {
  const saved = e9Case(); saved.data.financeEvidence!.case_id = "case-b";
  assert.throws(() => adaptSavedCaseToWorkspace(saved), /different case/);
});

test("Overview cannot promote finance with a stale input fingerprint to current", () => {
  const saved = e9Case(); saved.data.journeyContext!.activePriceWan = 2600;
  const overview = buildWorkspaceOverview(adaptSavedCaseToWorkspace(saved));
  assert.equal(overview.domains.finance.monthlyPaymentTwd, null);
  assert.equal(overview.domains.finance.freshness, "stale");
});

test("unknown legacy risk also invalidates overall positive narratives and price-support claims", () => {
  const { saved } = scenario();
  Object.assign(saved.data.locationInsight!, { strengths: ["各類生活機能分布相對均衡。"], weaknesses: ["未發現明顯弱項"], valuation_context: { supports_price_reasonableness: true, explanation: "區位總分 70" } });
  const insight = adaptSavedCaseToWorkspace(saved).location.insight!;
  assert.equal(insight.valuation_context.supports_price_reasonableness, "unknown");
  assert.doesNotMatch(JSON.stringify(insight.strengths) + JSON.stringify(insight.weaknesses) + insight.valuation_context.explanation, /均衡|未發現明顯弱項|總分 70/);
});

test("malformed snapshot cannot disagree about calculation price or canonical TWD", () => {
  const snapshot = e9Case().data.financeEvidence!;
  snapshot.loan.property_price_wan = 3000;
  assert.equal(normalizeStoredFinanceEvidence(snapshot), null);
});

test("a saved mortgage and holding payment must use compatible assumptions", () => {
  const snapshot = e9Case().data.financeEvidence!;
  snapshot.holding.assumptions.loan_monthly_payment_twd = 99999;
  assert.equal(normalizeStoredFinanceEvidence(snapshot), null);
});

test("mismatched manual provenance cannot bypass stale-price detection", async () => {
  // @ts-expect-error Native TS runner extension.
  const { buildFinanceModel } = await import("./finance-model.ts");
  const original = e9Case().data.financeEvidence!.loan;
  const model = buildFinanceModel({ caseId: "case-a", revision: 1, identityState: "confirmed", activePriceBasis: "asking", activePriceWan: 2480,
    resultSource: "saved_snapshot", resultPriceEvidence: { price_twd: 10000000, source: "MANUAL_SCENARIO", calculated_at: "2026-10-09T01:00:00Z" },
    loanResult: { ...original, property_price_wan: 3000, loan_amount_wan: 2400, monthly_payment: 91117, total_payment: 32802120, total_interest: 8802120, sensitivity: [], income_burden_ratio: null } as never });
  assert.equal(model.priceSource, null);
  assert.equal(model.freshness.status, "stale");
});

test("malformed facility text metadata stays renderable and does not fabricate coverage", () => {
  const { saved } = scenario();
  saved.data.locationInsight!.risk_facility_evidence = { status: "available", count: 0, source: { malformed: true }, checked_at: "bad", reason: {}, limitation: {} } as never;
  const field = projectCaseEvidence(adaptSavedCaseToWorkspace(saved)).location.riskFacility;
  assert.equal(field.value, null);
  assert.equal(typeof field.limitation, "string");
  assert.equal(typeof field.source, "string");
});

test("facility coverage for another address cannot become current property evidence", () => {
  const { saved } = scenario();
  saved.data.locationInsight!.data_quality.missing_sources = [];
  saved.data.locationInsight!.input = { address: "臺北市信義區市府路1號" };
  saved.data.locationInsight!.risk_facility_evidence = { status: "available", count: 0, source: "verified register", checked_at: saved.updatedAt, reason: "successful_query", limitation: "Observed radius" };
  assert.equal(projectCaseEvidence(adaptSavedCaseToWorkspace(saved)).location.riskFacility.value, null);
});

test("an unavailable location attempt without POI evidence does not manufacture a saved summary", () => {
  const saved = e9Case();
  saved.data.locationInsight = { data_quality: { status: "unavailable", missing_sources: [], warnings: [] } } as never;
  assert.equal(adaptSavedCaseToWorkspace(saved).location.poiSummary, undefined);
});

test("a fresh holding calculation cannot promote an incompatible saved mortgage to current", async () => {
  // @ts-expect-error Native TS runner extension.
  const { mergeFinanceEvidence, buildFinanceModel } = await import("./finance-model.ts");
  const base = adaptSavedCaseToWorkspace(e9Case()).finance!;
  base.freshness.status = "stale";
  const live = buildFinanceModel({ caseId: "case-a", revision: 2, identityState: "confirmed", activePriceBasis: "manual", activePriceWan: 3000 });
  const merged = mergeFinanceEvidence(base, live, false, true);
  assert.equal(merged.loan.monthlyPaymentTwd, null);
  assert.equal(merged.comparison.monthlyPaymentTwd, null);
});

test("an overridden holding mortgage input cannot coexist with a different saved mortgage payment", async () => {
  // @ts-expect-error Native TS runner extension.
  const { mergeFinanceEvidence } = await import("./finance-model.ts");
  const base = adaptSavedCaseToWorkspace(e9Case()).finance!;
  const live = structuredClone(base);
  base.affordability = { status: "assessed", ratio: .55111, reason: null, basis: "loan_payment" };
  live.affordability = { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null };
  live.loan.monthlyPaymentTwd = null;
  live.holding.assumptions.loanMonthlyPaymentTwd = 99999;
  live.holding.knownMonthlySubtotalTwd = 99999;
  const merged = mergeFinanceEvidence(base, live, false, true);
  assert.equal(merged.loan.monthlyPaymentTwd, null);
  assert.equal(merged.holding.assumptions.loanMonthlyPaymentTwd, 99999);
  assert.equal(merged.affordability.status, "unassessed");
  live.loan = structuredClone(base.loan);
  live.affordability = structuredClone(base.affordability);
  live.calculation.completeness = "sufficient_for_task";
  const bothLive = mergeFinanceEvidence(base, live, true, true);
  assert.equal(bothLive.loan.monthlyPaymentTwd, null);
  assert.equal(bothLive.affordability.status, "unassessed");
  assert.equal(bothLive.calculation.completeness, "partial");
});
