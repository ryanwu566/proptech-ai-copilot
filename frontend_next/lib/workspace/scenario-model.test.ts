import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { calculateScenario, emptyScenario, parseScenarioSave } from "./scenario-model.ts";

const complete = { offerTwd: 18_500_000, downMode: "ratio" as const, downValue: 20, ratePercent: 2.2, loanYears: 30, acquisitionTwd: 150_000, recurringTwd: 4000, renovationTwd: 500_000, holdingYears: 5, commuteMinutes: null };

test("local amortization matches trusted Python service; costs count principal only once", () => {
  const result = calculateScenario(complete);
  assert.equal(result.principalTwd, 14_800_000);
  assert.equal(Math.round(result.paymentTwd!), 56196);
  assert.equal(result.purchaseCashTwd, 4_350_000);
  assert.equal(result.acquisitionTotalTwd, 19_150_000);
  assert.equal(result.monthlyOwnershipTwd, result.paymentTwd! + 4000);
  assert.equal(result.firstYearTwd, 4_350_000 + 12 * result.monthlyOwnershipTwd!);
  assert.equal(result.holdingCashTwd, 4_350_000 + 60 * result.monthlyOwnershipTwd!);
});

test("amount down payment, zero rate, cash purchase, and holding beyond mortgage maturity", () => {
  const result = calculateScenario({ ...complete, offerTwd: 1_200_000, downMode: "amount", downValue: 0, ratePercent: 0, loanYears: 1, holdingYears: 2, acquisitionTwd: 0, renovationTwd: 0 });
  assert.equal(result.paymentTwd, 100_000);
  assert.equal(result.holdingCashTwd, 1_296_000);
  const cash = calculateScenario({ ...complete, downValue: 100, ratePercent: null, loanYears: null });
  assert.equal(cash.paymentTwd, 0);
  assert.equal(cash.principalTwd, 0);
  assert.equal(cash.monthlyOwnershipTwd, 4000);
});

test("unknown costs stay explicit while known subtotals remain useful", () => {
  const result = calculateScenario({ ...complete, acquisitionTwd: null, recurringTwd: null, renovationTwd: null });
  assert.equal(result.purchaseCashTwd, 3_700_000);
  assert.equal(result.firstYearTwd, 3_700_000 + 12 * result.paymentTwd!);
  assert.equal(result.costsComplete, false);
  assert.deepEqual(result.unknown, ["acquisitionTwd", "recurringTwd", "renovationTwd", "commuteMinutes"]);
  assert.equal(calculateScenario(emptyScenario()).paymentTwd, null);
});

test("invalid values suppress dependent totals and never masquerade as unknown zero costs", () => {
  for (const [field, value] of [["offerTwd", 0], ["downValue", 101], ["ratePercent", Infinity], ["loanYears", 1.5], ["acquisitionTwd", -1], ["recurringTwd", NaN], ["renovationTwd", -1], ["holdingYears", 0]] as const) {
    const result = calculateScenario({ ...complete, [field]: value });
    assert.ok(result.errors[field], field);
    assert.equal(result.firstYearTwd, null);
  }
  assert.equal(calculateScenario({ ...complete, downMode: "amount", downValue: complete.offerTwd + 1 }).principalTwd, null);
});

test("tiny interest rates stay finite and converge to zero-rate payment", () => {
  const result = calculateScenario({ ...complete, ratePercent: 1e-12 });
  assert.ok(Math.abs(result.paymentTwd! - 14_800_000 / 360) < 0.0001);
});

test("mortgage parity fixtures generated directly by the trusted Python service", () => {
  for (const [priceWan, ratePercent, loanYears, expected] of [[100, 0, 10, 6667], [5000, 3.5, 20, 231984], [850, 1.8, 15, 43135]]) {
    assert.equal(Math.round(calculateScenario({ ...complete, offerTwd: priceWan * 10000, ratePercent, loanYears }).paymentTwd!), expected);
  }
});

test("100 percent down payment is exactly a cash purchase even at fractional high prices", () => {
  const result = calculateScenario({ ...complete, offerTwd: 829217449647.8245, downValue: 100, ratePercent: null, loanYears: null });
  assert.equal(result.principalTwd, 0);
  assert.equal(result.paymentTwd, 0);
});

test("calculations and separately frozen baseline never mutate their inputs", () => {
  const input = Object.freeze({ ...complete });
  const before = JSON.stringify(input);
  calculateScenario(input);
  assert.equal(JSON.stringify(input), before);
});

test("saved drafts are versioned and context-bound; malformed storage is rejected", () => {
  const payload = JSON.stringify({ version: 1, context: "case-a", drafts: [complete, complete, complete], baseline: complete });
  assert.ok(parseScenarioSave(payload, "case-a"));
  assert.equal(parseScenarioSave(payload, "case-b"), null);
  assert.equal(parseScenarioSave("{", "case-a"), null);
  assert.equal(parseScenarioSave(JSON.stringify({ version: 1, context: "case-a", drafts: [complete, complete, { ...complete, ratePercent: "0" }] }), "case-a"), null);
  assert.equal(parseScenarioSave(payload.replace('"ratio"', '"bogus"'), "case-a"), null);
});
