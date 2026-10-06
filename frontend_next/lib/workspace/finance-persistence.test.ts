import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildFinanceModel } from "./finance-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { createStoredFinanceEvidence, normalizeStoredFinanceEvidence, restoreFinanceModelFromSnapshot } from "./finance-persistence.ts";

const calculatedAt = "2026-10-06T08:30:00.000Z";

const loanResult = {
  property_price_wan: 1_850,
  down_payment_ratio: 0.2,
  down_payment_wan: 370,
  loan_amount_wan: 1_480,
  annual_interest_rate: 2.2,
  loan_years: 30,
  grace_period_years: 0,
  monthly_income_wan: null,
  monthly_payment: 56_196,
  grace_period_monthly_payment: null,
  post_grace_monthly_payment: null,
  total_payment: 20_230_560,
  total_interest: 5_430_560,
  income_burden_ratio: null,
  affordability_level: "unknown" as const,
  affordability_message: "未提供收入",
  sensitivity: [{ annual_interest_rate: 2.7, monthly_payment: 60_012, total_interest: 6_804_320, difference_from_base: 3_816 }],
  disclaimer: "raw loan disclaimer",
};

const holdingResult = {
  input: { property_price_wan: 1_850, loan_monthly_payment: 56_196, monthly_income_wan: null, area_ping: null, management_fee_per_ping: 80, repair_reserve_per_ping: 50, annual_home_tax_rate: 0.0012, annual_land_tax_rate: 0.001, annual_insurance: 3_000, include_tax_estimate: true },
  property_price_wan: 1_850,
  loan_monthly_payment: 56_196,
  monthly_management_fee: 0,
  monthly_repair_reserve: 0,
  monthly_tax_estimate: 3_392,
  annual_home_tax_estimate: 22_200,
  annual_land_tax_estimate: 18_500,
  monthly_insurance: 250,
  monthly_total_holding_cost: 59_838,
  annual_total_holding_cost: 718_056,
  income_burden_ratio: null,
  affordability_level: "unknown" as const,
  affordability_message: "未提供收入",
  cost_breakdown: [
    { key: "loan", label: "raw", monthly_amount: 56_196 },
    { key: "management", label: "raw", monthly_amount: 0 },
    { key: "repair_reserve", label: "raw", monthly_amount: 0 },
    { key: "tax_estimate", label: "raw", monthly_amount: 3_392 },
    { key: "insurance", label: "raw", monthly_amount: 250 },
  ],
  disclaimer: "raw holding disclaimer",
};

function currentModel() {
  return buildFinanceModel({
    caseId: "property-a",
    revision: 7,
    identityAnchorId: "journey-browser-aaaaaaaa-2222-4333-8444-555555555555",
    identityState: "confirmed",
    activePriceBasis: "asking",
    activePriceWan: 1_850,
    askingPriceWan: 1_850,
    areaPing: null,
    loanResult,
    holdingResult,
    taxResult: {
      eligibility_status: "manual_review",
      risk_score: 100,
      signal_color: "red",
      hard_fail_rules: ["TX001"],
      manual_review_rules: ["TX009"],
      missing_docs: ["戶籍資料"],
      reminder_timeline: ["raw reminder"],
      rule_traces: [{ code: "TX001", title: "raw", outcome: "fail", detail: "secret", risk_points: 100 }],
      ai_explanation: { headline: "raw", customer_script: "raw", source: "raw" },
      disclaimer: "raw tax disclaimer",
      case_input: { case_id: "private-id", client_name: "private-name", sold_self_occupied: false, residency_condition_met: false, purchase_within_reasonable_period: false, purchased_self_occupied: false, same_owner: false, land_value_available: false, required_docs_complete: false, enters_five_year_monitoring: false, exceptional_circumstances: false },
      official_rule_trace: { rule_version: "2026.1", jurisdiction: "TW", effective_date: "2026-01-01", source_name: "財政部", source_status: "available", calculation_kind: "deterministic", limitation: "raw" },
    },
    calculatedAt,
  });
}

test("stored finance evidence contains only the bounded v1 snapshot", () => {
  const stored = createStoredFinanceEvidence(currentModel(), { caseId: "property-a", revision: 7, areaPing: null });
  const json = JSON.stringify(stored);

  assert.equal(stored.version, 1);
  assert.equal(stored.case_id, "property-a");
  assert.equal(stored.revision, 7);
  assert.equal(stored.calculated_at, calculatedAt);
  assert.equal(stored.affordability.status, "unassessed");
  assert.equal(stored.loan.monthly_income_wan, null);
  assert.equal(stored.holding.assumptions.management_fee_per_ping_twd, 80);
  assert.equal(stored.holding.breakdown.find((row) => row.key === "management")?.monthly_amount_twd, null);
  for (const forbidden of ["rule_traces", "risk_score", "signal_color", "case_input", "client_name", "ai_explanation", "disclaimer", "total_payment", "reminder_timeline"]) {
    assert.equal(json.includes(forbidden), false, `${forbidden} must not be persisted`);
  }
});

test("saved compact finance evidence reopens as distinguishable saved evidence", () => {
  const stored = createStoredFinanceEvidence(currentModel(), { caseId: "property-a", revision: 7, areaPing: null });
  const reopened = restoreFinanceModelFromSnapshot(stored, {
    caseId: "property-a",
    revision: 7,
    identityAnchorId: "journey-browser-aaaaaaaa-2222-4333-8444-555555555555",
    identityState: "confirmed",
    activePriceBasis: "asking",
    activePriceWan: 1_850,
    areaPing: null,
  });

  assert.equal(reopened.freshness.status, "current");
  assert.equal(reopened.freshness.source, "saved_snapshot");
  assert.equal(reopened.freshness.calculatedAt, calculatedAt);
  assert.equal(reopened.loan.monthlyPaymentTwd, 56_196);
  assert.equal(reopened.holding.totalKind, "known_subtotal");
  assert.equal(reopened.affordability.status, "unassessed");
});

test("property or price changes reopen saved finance evidence as stale", () => {
  const stored = createStoredFinanceEvidence(currentModel(), { caseId: "property-a", revision: 7, areaPing: null });
  const propertyB = restoreFinanceModelFromSnapshot(stored, { caseId: "property-b", revision: 8, identityState: "confirmed", activePriceBasis: "asking", activePriceWan: 1_900, areaPing: null });

  assert.equal(propertyB.freshness.status, "stale");
  assert.equal(propertyB.calculation.usability, "stale");
  assert.equal(propertyB.priceBasis.amountWan, 1_900);
  assert.equal(propertyB.loan.status, "stale");
});

test("identity-anchor changes make same-case same-price finance evidence stale", () => {
  const stored = createStoredFinanceEvidence(currentModel(), { caseId: "property-a", revision: 7, areaPing: null });
  const reopened = restoreFinanceModelFromSnapshot(stored, {
    caseId: "property-a",
    revision: 7,
    identityAnchorId: "journey-browser-bbbbbbbb-2222-4333-8444-555555555555",
    identityState: "confirmed",
    activePriceBasis: "asking",
    activePriceWan: 1_850,
    areaPing: null,
  });

  assert.equal(reopened.freshness.status, "stale");
  assert.equal(reopened.loan.status, "stale");
});

test("malformed stored evidence is rejected instead of reconstructed", () => {
  assert.equal(normalizeStoredFinanceEvidence({ version: 1, case_id: "property-a", revision: 1, input_fingerprint: "bad" }), null);
  assert.equal(normalizeStoredFinanceEvidence({ ...createStoredFinanceEvidence(currentModel(), { caseId: "property-a", revision: 7, areaPing: null }), loan: { monthly_payment_twd: -1 } }), null);
});

test("normalization reconstructs only the allowlisted bounded snapshot", () => {
  const stored = createStoredFinanceEvidence(currentModel(), { caseId: "property-a", revision: 7, areaPing: null });
  const normalized = normalizeStoredFinanceEvidence({
    ...stored,
    raw_backend_response: { secret: true },
    assumptions: { ...stored.assumptions, provider_debug: "hidden" },
    loan: { ...stored.loan, provider_debug: "hidden" },
    tax: { ...stored.tax, summary: stored.tax.summary ? { ...stored.tax.summary, rule_traces: ["hidden"] } : null },
  });

  assert.ok(normalized);
  assert.equal("raw_backend_response" in normalized, false);
  assert.equal("provider_debug" in normalized.loan, false);
  assert.equal("provider_debug" in normalized.assumptions, false);
  assert.equal(normalized.tax.summary ? "rule_traces" in normalized.tax.summary : false, false);
});
