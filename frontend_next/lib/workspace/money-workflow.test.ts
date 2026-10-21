import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { buildFinanceModel } from "./finance-model.ts";
// @ts-expect-error Native TS runner extension.
import { createStoredFinanceEvidence, restoreFinanceModelFromSnapshot } from "./finance-persistence.ts";
// @ts-expect-error Native TS runner extension.
import { moneyPriceContext, projectMoneyOffer, holdingFormSeed, syncHoldingPayment } from "./money-workflow.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildComparisonModel, buildReportModel } from "./compare-report-model.ts";

const context = { caseId: "money-case", revision: 1, identityAnchorId: "anchor", identityState: "confirmed" as const, activePriceBasis: "asking" as const, activePriceWan: 1850, areaPing: 30 };
const assumptions = { downPaymentRatio: 0.3, annualInterestRate: 2.65, loanYears: 25, gracePeriodYears: 0 };
const loan = { property_price_wan: 1700, down_payment_ratio: 0.3, down_payment_wan: 510, loan_amount_wan: 1190, annual_interest_rate: 2.65, loan_years: 25, grace_period_years: 0, monthly_income_wan: 15, monthly_payment: 54292, grace_period_monthly_payment: null, post_grace_monthly_payment: null, total_payment: 16287600, total_interest: 4387600, income_burden_ratio: 0.3619, affordability_level: "unknown" as const, affordability_message: "", sensitivity: [], disclaimer: "" };

test("saved manual price and non-default assumptions survive reopen independently of asking", () => {
  const fingerprint = buildFinanceModel(context).inputFingerprint;
  const model = buildFinanceModel({ ...context, activePriceBasis: "manual", activePriceWan: 1700, loanResult: loan, calculatedAt: "2026-10-20T01:00:00Z" });
  const stored = createStoredFinanceEvidence(model, { caseId: context.caseId, revision: 1, areaPing: 30, caseInputFingerprint: fingerprint });
  const restored = restoreFinanceModelFromSnapshot(JSON.parse(JSON.stringify(stored)), context);
  assert.equal(restored.freshness.status, "current");
  assert.deepEqual(moneyPriceContext(context.activePriceWan, context.activePriceBasis, restored), { amountWan: 1700, basis: "manual" });
  assert.equal(restored.loan.downPaymentRatio, 0.3);
  assert.equal(restored.loan.annualInterestRate, 2.65);
  assert.equal(restored.loan.loanYears, 25);
  assert.equal(restored.loan.monthlyIncomeWan, 15);
  assert.equal(restored.freshness.calculatedAt, "2026-10-20T01:00:00Z");
  assert.equal(restored.priceSource, "MANUAL_SCENARIO");
  const stale = restoreFinanceModelFromSnapshot(stored, { ...context, activePriceWan: 1900 });
  assert.equal(stale.freshness.status, "stale");
  assert.equal(moneyPriceContext(1900, "asking", stale).amountWan, 1900);
  assert.equal(stale.savedAssumptions?.amountWan, 1700);
});

test("unknown legacy price provenance never becomes a manual offer assumption", () => {
  const legacy = buildFinanceModel({ ...context, activePriceWan: null, loanResult: loan, resultSource: "saved_snapshot" });
  assert.equal(legacy.priceSource, null);
  assert.equal(legacy.freshness.status, "current");
  assert.deepEqual(moneyPriceContext(null, "asking", legacy), { amountWan: null, basis: "asking" });
  assert.deepEqual(moneyPriceContext(1850, "asking", legacy), { amountWan: 1850, basis: "asking" });
});

test("asking and manual offer show different cash, principal and monthly payments without ranking", () => {
  const asking = projectMoneyOffer(1850, assumptions);
  const offer = projectMoneyOffer(1700, assumptions);
  assert.equal(asking.downPaymentTwd, 5550000);
  assert.equal(asking.loanTwd, 12950000);
  assert.equal(offer.downPaymentTwd, 5100000);
  assert.equal(offer.cashKnownSubtotalTwd, 5100000);
  assert.equal(offer.loanTwd, 11900000);
  assert.ok(offer.monthlyPaymentTwd! < asking.monthlyPaymentTwd!);
  assert.equal(offer.closingCostsTwd, null);
  assert.equal(offer.initialCashTotalTwd, null);
  assert.equal("winner" in offer || "recommendation" in offer || "score" in offer, false);
});

test("unknown financing never becomes a zero, a default rate or a complete cash total", () => {
  const unknown = projectMoneyOffer(1850, { downPaymentRatio: null, annualInterestRate: null, loanYears: null, gracePeriodYears: null });
  assert.equal(unknown.cashKnownSubtotalTwd, null);
  assert.equal(unknown.loanTwd, null);
  assert.equal(unknown.monthlyPaymentTwd, null);
  assert.equal(projectMoneyOffer(null, assumptions).monthlyPaymentTwd, null);
  assert.equal(projectMoneyOffer(-1, assumptions).downPaymentTwd, null);
  assert.equal(projectMoneyOffer(1850, { ...assumptions, annualInterestRate: null }).monthlyPaymentTwd, null);
  assert.equal(projectMoneyOffer(1850, { ...assumptions, gracePeriodYears: null }).monthlyPaymentTwd, null);
});

test("grace periods and zero-interest assumptions use the existing repayment equation", () => {
  const grace = projectMoneyOffer(1850, { ...assumptions, gracePeriodYears: 3 });
  assert.equal(grace.graceMonthlyPaymentTwd, 12950000 * 0.0265 / 12);
  assert.ok(grace.monthlyPaymentTwd! > projectMoneyOffer(1850, assumptions).monthlyPaymentTwd!);
  const zero = projectMoneyOffer(1850, { ...assumptions, annualInterestRate: 0 });
  assert.equal(zero.monthlyPaymentTwd, 12950000 / 300);
  assert.equal(projectMoneyOffer(1850, { ...assumptions, gracePeriodYears: 25 }).monthlyPaymentTwd, null);
});

test("holding form reopening retains manual mortgage, area, zero fees and unknowns", () => {
  const initial = { loanMonthlyPaymentTwd: 43210, areaPing: 26, managementFeePerPingTwd: 0, repairReservePerPingTwd: 65, monthlyIncomeWan: 15, annualHomeTaxRatePercent: 0.15, annualLandTaxRatePercent: 0, annualInsuranceTwd: 4500 };
  const seed = holdingFormSeed(initial, null, 40);
  assert.equal(seed.loanMonthlyPaymentWan, "4.321");
  assert.equal(seed.areaPing, "26");
  assert.equal(seed.managementFeePerPingTwd, "0");
  assert.equal(seed.annualHomeTaxRatePercent, "0.15");
  assert.equal(holdingFormSeed({ ...initial, areaPing: null }, null, 40).areaPing, "");
  assert.equal(holdingFormSeed(initial, 50000, 40).loanMonthlyPaymentWan, "5");
});

test("a price change clears the old automatic mortgage, but preserves an explicit manual holding assumption", () => {
  assert.deepEqual(syncHoldingPayment("5.6196", true, null), { value: "", automatic: false });
  assert.deepEqual(syncHoldingPayment("4.321", false, null), { value: "4.321", automatic: false });
  assert.deepEqual(syncHoldingPayment("4.321", false, 50000), { value: "5", automatic: true });
  assert.deepEqual(syncHoldingPayment("5", true, 0), { value: "0", automatic: true });
});

test("Money manual-scenario snapshots preserve existing Report and Compare projections", () => {
  const row = e9Case();
  const workspace = adaptSavedCaseToWorkspace(row);
  const input = { caseId: workspace.caseId, revision: workspace.revision, identityAnchorId: workspace.identity.anchor?.journey_anchor_id,
    identityState: workspace.identity.state, activePriceBasis: workspace.assumptions.activePriceBasis,
    activePriceWan: workspace.assumptions.activePriceWan, areaPing: workspace.assumptions.areaPing };
  const finance = buildFinanceModel({ ...input, activePriceBasis: "manual", activePriceWan: 1700, loanResult: loan, calculatedAt: "2026-10-20T01:00:00Z" });
  row.data.financeEvidence = createStoredFinanceEvidence(finance, { caseId: row.id, revision: workspace.revision, areaPing: 30, caseInputFingerprint: buildFinanceModel(input).inputFingerprint });
  const projected = projectCaseEvidence(adaptSavedCaseToWorkspace(JSON.parse(JSON.stringify(row))));
  assert.equal(projected.finance.price.value, 1700);
  assert.equal(projected.finance.downPayment.value, 510);
  assert.equal(projected.finance.principal.value, 1190);
  assert.equal(projected.finance.monthlyPayment.value, 54292);
  assert.equal(projected.finance.monthlyPayment.freshness.checkedAt, "2026-10-20T01:00:00Z");
  assert.equal(projected.finance.monthlyPayment.freshness.inputRelation, "matches");
  assert.equal(projected.price.asking.value, 2480);
  const report = buildReportModel(projected);
  const financeRows = report.sections.find(section => section.id === "finance")?.evidenceSection?.rows;
  assert.equal(financeRows?.find(row => row.id === "finance-payment")?.cells[0].value, 54292);
  const other = projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case("case-b")));
  const compare = buildComparisonModel([projected, other], [projected.caseId, other.caseId]);
  assert.equal(compare.status, "ready");
  assert.equal(compare.sections.find(section => section.id === "finance")?.rows.find(row => row.id === "finance-down")?.cells[0].value, 510);
});
