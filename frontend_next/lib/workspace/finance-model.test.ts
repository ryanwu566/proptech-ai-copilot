import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildFinanceModel, createFinanceInputFingerprint } from "./finance-model.ts";

const NOW = "2026-10-06T08:00:00.000Z";

const loan = {
  property_price_wan: 1_850,
  down_payment_ratio: 0.2,
  down_payment_wan: 370,
  loan_amount_wan: 1_480,
  annual_interest_rate: 2.2,
  loan_years: 30,
  grace_period_years: 0,
  monthly_income_wan: 12,
  monthly_payment: 56_196,
  grace_period_monthly_payment: null,
  post_grace_monthly_payment: null,
  total_payment: 20_230_560,
  total_interest: 5_430_560,
  income_burden_ratio: 0.4683,
  affordability_level: "tight" as const,
  affordability_message: "依輸入條件估算",
  sensitivity: [],
  disclaimer: "僅供試算",
};

const holding = {
  input: {
    property_price_wan: 1_850,
    loan_monthly_payment: 56_196,
    monthly_income_wan: 12,
    area_ping: 26,
    management_fee_per_ping: 80,
    repair_reserve_per_ping: 50,
    annual_home_tax_rate: 0.0012,
    annual_land_tax_rate: 0.001,
    annual_insurance: 3_000,
    include_tax_estimate: true,
  },
  property_price_wan: 1_850,
  loan_monthly_payment: 56_196,
  monthly_management_fee: 2_080,
  monthly_repair_reserve: 1_300,
  monthly_tax_estimate: 3_392,
  annual_home_tax_estimate: 22_200,
  annual_land_tax_estimate: 18_500,
  monthly_insurance: 250,
  monthly_total_holding_cost: 63_218,
  annual_total_holding_cost: 758_616,
  income_burden_ratio: 0.5268,
  affordability_level: "risky" as const,
  affordability_message: "依輸入條件估算",
  cost_breakdown: [
    { key: "loan", label: "房貸", monthly_amount: 56_196 },
    { key: "management", label: "管理費", monthly_amount: 2_080 },
    { key: "repair_reserve", label: "修繕準備", monthly_amount: 1_300 },
    { key: "tax_estimate", label: "房屋與土地稅估算", monthly_amount: 3_392 },
    { key: "insurance", label: "保險", monthly_amount: 250 },
  ],
  disclaimer: "僅供試算",
};

function baseInput(overrides: Record<string, unknown> = {}) {
  return {
    caseId: "property-a",
    revision: 3,
    identityAnchorId: "journey-browser-aaaaaaaa-2222-4333-8444-555555555555",
    identityState: "confirmed" as const,
    activePriceBasis: "asking" as const,
    activePriceWan: 1_850,
    askingPriceWan: 1_850,
    areaPing: 26,
    loanResult: loan,
    holdingResult: holding,
    calculatedAt: NOW,
    ...overrides,
  };
}

test("normal finance calculation keeps the active price read-only and exposes bounded handoffs", () => {
  const model = buildFinanceModel(baseInput());

  assert.deepEqual(model.priceBasis, { basis: "asking", amountWan: 1_850, source: "case" });
  assert.equal(model.loan.status, "available");
  assert.equal(model.loan.principalWan, 1_480);
  assert.equal(model.loan.downPaymentWan, 370);
  assert.equal(model.loan.monthlyPaymentTwd, 56_196);
  assert.equal(model.holding.knownMonthlySubtotalTwd, 63_218);
  assert.equal(model.holding.breakdown.find((row: { key: string }) => row.key === "management")?.status, "estimated");
  assert.equal(model.affordability.status, "assessed");
  assert.equal(model.overview.monthlyPaymentTwd, 56_196);
  assert.equal(model.comparison.knownRecurringMonthlyTwd, 63_218);
  assert.equal(model.freshness.status, "current");
});

test("legitimate zero financing and holding values remain calculated zeroes", () => {
  const model = buildFinanceModel(baseInput({
    loanResult: { ...loan, down_payment_ratio: 0, down_payment_wan: 0, loan_amount_wan: 1_850, annual_interest_rate: 0, monthly_payment: 51_389, total_interest: 0 },
    holdingResult: {
      ...holding,
      input: { ...holding.input, loan_monthly_payment: 0, management_fee_per_ping: 0, repair_reserve_per_ping: 0, annual_home_tax_rate: 0, annual_land_tax_rate: 0, annual_insurance: 0, include_tax_estimate: false },
      loan_monthly_payment: 0,
      monthly_management_fee: 0,
      monthly_repair_reserve: 0,
      monthly_tax_estimate: 0,
      annual_home_tax_estimate: 0,
      annual_land_tax_estimate: 0,
      monthly_insurance: 0,
      monthly_total_holding_cost: 0,
      annual_total_holding_cost: 0,
      income_burden_ratio: 0,
      affordability_level: "comfortable",
      cost_breakdown: holding.cost_breakdown.map((row) => ({ ...row, monthly_amount: 0 })),
    },
  }));

  assert.equal(model.loan.downPaymentWan, 0);
  assert.equal(model.loan.totalInterestTwd, 0);
  assert.equal(model.holding.knownMonthlySubtotalTwd, 0);
  assert.ok(model.holding.breakdown.every((row: { status: string; monthlyAmountTwd: number | null }) => row.status === "estimated" && row.monthlyAmountTwd === 0));
});

test("missing active price requests input instead of manufacturing a zero scenario", () => {
  const model = buildFinanceModel(baseInput({ activePriceWan: undefined, loanResult: undefined, holdingResult: undefined }));

  assert.equal(model.calculation.query, "input_required");
  assert.equal(model.priceBasis.amountWan, null);
  assert.equal(model.loan.status, "not_started");
  assert.equal(model.holding.knownMonthlySubtotalTwd, null);
  assert.ok(model.unresolvedActions.includes("需要先提供可用的物件價格"));
});

test("missing area keeps area-dependent costs unestimated rather than displaying zero", () => {
  const missingAreaHolding = {
    ...holding,
    input: { ...holding.input, area_ping: null },
    monthly_management_fee: 0,
    monthly_repair_reserve: 0,
    monthly_total_holding_cost: 59_838,
    annual_total_holding_cost: 718_056,
    cost_breakdown: holding.cost_breakdown.map((row) => row.key === "management" || row.key === "repair_reserve" ? { ...row, monthly_amount: 0 } : row),
  };

  const model = buildFinanceModel(baseInput({ areaPing: null, holdingResult: missingAreaHolding }));

  const management = model.holding.breakdown.find((row: { key: string }) => row.key === "management");
  const repair = model.holding.breakdown.find((row: { key: string }) => row.key === "repair_reserve");
  assert.deepEqual(management, { key: "management", label: "管理費", status: "unestimated", monthlyAmountTwd: null, missingReason: "缺少坪數" });
  assert.deepEqual(repair, { key: "repair_reserve", label: "修繕準備", status: "unestimated", monthlyAmountTwd: null, missingReason: "缺少坪數" });
  assert.equal(model.holding.totalKind, "known_subtotal");
  assert.ok(model.missingCosts.includes("管理費（缺少坪數）"));
  assert.ok(model.missingCosts.includes("修繕準備（缺少坪數）"));
});

test("completed calculations do not imply affordability when income is missing", () => {
  const model = buildFinanceModel(baseInput({
    loanResult: { ...loan, monthly_income_wan: null, income_burden_ratio: null, affordability_level: "unknown", affordability_message: "未提供收入" },
    holdingResult: { ...holding, input: { ...holding.input, monthly_income_wan: null }, income_burden_ratio: null, affordability_level: "unknown", affordability_message: "未提供收入" },
  }));

  assert.equal(model.calculation.query, "succeeded");
  assert.deepEqual(model.affordability, { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null });
  assert.notEqual(model.calculation.completeness, "sufficient_for_task");
});

test("affordability records whether the ratio uses loan-only or total holding cost", () => {
  const loanOnly = buildFinanceModel(baseInput({
    holdingResult: { ...holding, input: { ...holding.input, monthly_income_wan: null }, income_burden_ratio: null },
  }));
  const totalHousing = buildFinanceModel(baseInput());

  assert.equal(loanOnly.affordability.basis, "loan_payment");
  assert.equal(loanOnly.affordability.ratio, loan.income_burden_ratio);
  assert.equal(totalHousing.affordability.basis, "total_housing_cost");
  assert.equal(totalHousing.affordability.ratio, holding.income_burden_ratio);
});

test("price changes make old calculations stale without changing the active price", () => {
  const model = buildFinanceModel(baseInput({ activePriceWan: 1_900 }));

  assert.equal(model.priceBasis.amountWan, 1_900);
  assert.equal(model.loan.status, "stale");
  assert.equal(model.holding.status, "stale");
  assert.equal(model.freshness.status, "stale");
  assert.ok(model.unresolvedActions.includes("物件價格已變更，請重新計算資金與持有成本"));
});

test("a snapshot from another property revision is stale and never authoritative", () => {
  const fingerprint = createFinanceInputFingerprint({ caseId: "property-a", revision: 3, activePriceBasis: "asking", activePriceWan: 1_850, areaPing: 26 });
  const model = buildFinanceModel(baseInput({
    caseId: "property-b",
    revision: 4,
    savedFingerprint: fingerprint,
  }));

  assert.equal(model.freshness.status, "stale");
  assert.equal(model.calculation.usability, "stale");
});

test("tax evidence is bounded and tax failure does not erase valid loan evidence", () => {
  const taxResult = {
    eligibility_status: "manual_review",
    risk_score: 99,
    signal_color: "red",
    hard_fail_rules: ["TX001"],
    manual_review_rules: ["TX009"],
    missing_docs: ["戶籍資料"],
    reminder_timeline: [],
    rule_traces: [{ code: "TX001", title: "internal", outcome: "fail", detail: "raw", risk_points: 99 }],
    ai_explanation: { headline: "internal", customer_script: "internal", source: "internal" },
    disclaimer: "初步檢查",
    case_input: { case_id: "secret", client_name: "private" },
    official_rule_trace: { rule_version: "2026.1", jurisdiction: "TW", effective_date: "2026-01-01", source_name: "財政部", source_status: "available", calculation_kind: "deterministic", limitation: "初步" },
  };
  const model = buildFinanceModel(baseInput({ taxResult, taxQueryStatus: "failed" }));

  assert.equal(model.loan.status, "available");
  assert.equal(model.tax.query, "failed");
  assert.deepEqual(model.tax.summary, { outcome: "manual_review", failedConditionCount: 1, reviewItemCount: 1, missingInformationCount: 1, sourceName: "財政部", effectiveDate: "2026-01-01" });
  assert.equal("rule_traces" in model.tax.summary, false);
  assert.equal("risk_score" in model.tax.summary, false);
});

test("malformed finance results fail closed", () => {
  const model = buildFinanceModel(baseInput({ loanResult: { ...loan, monthly_payment: Number.NaN }, holdingResult: { ...holding, monthly_total_holding_cost: -1 } }));

  assert.equal(model.loan.status, "unavailable");
  assert.equal(model.loan.monthlyPaymentTwd, null);
  assert.equal(model.holding.status, "unavailable");
  assert.equal(model.holding.knownMonthlySubtotalTwd, null);
  assert.equal(model.calculation.usability, "unavailable");
});

test("malformed loan sensitivity fails locally without crashing valid holding evidence", () => {
  const malformedLoan = { ...loan, sensitivity: [null] };
  const model = buildFinanceModel(baseInput({ loanResult: malformedLoan }));

  assert.equal(model.loan.status, "unavailable");
  assert.equal(model.loan.monthlyPaymentTwd, null);
  assert.equal(model.holding.status, "available");
  assert.equal(model.holding.knownMonthlySubtotalTwd, 63_218);
});
