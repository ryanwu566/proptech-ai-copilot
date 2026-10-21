import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildHoldingCostRequest, buildLoanRequest, validateHoldingAssumptions, validateLoanAssumptions } from "./finance-calculation.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import * as calculation from "./finance-calculation.ts";

test("loan form parsing keeps wan, percentages and optional income at the request boundary", () => {
  assert.equal(typeof calculation.loanAssumptionsFromFields, "function");
  const input = calculation.loanAssumptionsFromFields(2480, { downPaymentRatioPercent: "25", annualInterestRatePercent: "2.2", loanYears: "30", gracePeriodYears: "2", monthlyIncomeWan: "12.5" });
  assert.deepEqual(buildLoanRequest(input), { property_price: 2480, down_payment_ratio: 0.25, annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 2, monthly_income: 12.5, include_sensitivity: true });
});

test("blank required loan fields stay invalid while blank income stays unknown", () => {
  assert.equal(typeof calculation.loanAssumptionsFromFields, "function");
  const input = calculation.loanAssumptionsFromFields(2480, { downPaymentRatioPercent: "20", annualInterestRatePercent: "", loanYears: "", gracePeriodYears: "0", monthlyIncomeWan: "" });
  assert.equal(input.monthlyIncomeWan, null);
  assert.deepEqual(Object.keys(validateLoanAssumptions(input)).sort(), ["annualInterestRatePercent", "loanYears"]);
});

test("holding form parsing preserves payment conversion, optional unknowns and annual rate units", () => {
  assert.equal(typeof calculation.holdingAssumptionsFromFields, "function");
  const input = calculation.holdingAssumptionsFromFields(2480, { loanMonthlyPaymentWan: "5.6196", monthlyIncomeWan: "", areaPing: "", managementFeePerPingTwd: "80", repairReservePerPingTwd: "50", annualHomeTaxRatePercent: "0.12", annualLandTaxRatePercent: "0.1", annualInsuranceTwd: "3000" });
  assert.deepEqual(buildHoldingCostRequest(input), { property_price: 2480, loan_monthly_payment: 56196, monthly_income: undefined, area_ping: undefined, management_fee_per_ping: 80, repair_reserve_per_ping: 50, annual_home_tax_rate: 0.0012, annual_land_tax_rate: 0.001, annual_insurance: 3000, include_tax_estimate: true });
});

test("holding form parsing distinguishes a legitimate zero payment from a missing payment", () => {
  assert.equal(typeof calculation.holdingAssumptionsFromFields, "function");
  const fields = { loanMonthlyPaymentWan: "0", monthlyIncomeWan: "", areaPing: "0", managementFeePerPingTwd: "0", repairReservePerPingTwd: "0", annualHomeTaxRatePercent: "0", annualLandTaxRatePercent: "0", annualInsuranceTwd: "0" };
  assert.deepEqual(validateHoldingAssumptions(calculation.holdingAssumptionsFromFields(2480, fields)), {});
  assert.deepEqual(Object.keys(validateHoldingAssumptions(calculation.holdingAssumptionsFromFields(2480, { ...fields, loanMonthlyPaymentWan: "" }))), ["loanMonthlyPaymentWan"]);
});

test("loan request preserves wan inputs and optional income without inventing values", () => {
  assert.deepEqual(buildLoanRequest({ propertyPriceWan: 1_850, downPaymentRatioPercent: 20, annualInterestRatePercent: 2.2, loanYears: 30, gracePeriodYears: 0, monthlyIncomeWan: null }), {
    property_price: 1_850,
    down_payment_ratio: 0.2,
    annual_interest_rate: 2.2,
    loan_years: 30,
    grace_period_years: 0,
    monthly_income: undefined,
    include_sensitivity: true,
  });
});

test("invalid loan assumptions report field-specific problems", () => {
  assert.deepEqual(validateLoanAssumptions({ propertyPriceWan: 0, downPaymentRatioPercent: 101, annualInterestRatePercent: -1, loanYears: 0, gracePeriodYears: 1, monthlyIncomeWan: 0 }), {
    propertyPriceWan: "物件價格必須大於 0。",
    downPaymentRatioPercent: "自備款比例必須介於 0% 與 100%。",
    annualInterestRatePercent: "利率不可小於 0%。",
    loanYears: "貸款年期必須大於 0 年。",
    gracePeriodYears: "寬限期必須小於貸款年期。",
    monthlyIncomeWan: "月收入如有填寫，必須大於 0。",
  });
});

test("holding request converts only the manual monthly payment boundary to canonical TWD", () => {
  assert.deepEqual(buildHoldingCostRequest({ propertyPriceWan: 1_850, loanMonthlyPaymentWan: 5.6196, monthlyIncomeWan: null, areaPing: null, managementFeePerPingTwd: 80, repairReservePerPingTwd: 50, annualHomeTaxRatePercent: 0.12, annualLandTaxRatePercent: 0.1, annualInsuranceTwd: 3_000 }), {
    property_price: 1_850,
    loan_monthly_payment: 56_196,
    monthly_income: undefined,
    area_ping: undefined,
    management_fee_per_ping: 80,
    repair_reserve_per_ping: 50,
    annual_home_tax_rate: 0.0012,
    annual_land_tax_rate: 0.001,
    annual_insurance: 3_000,
    include_tax_estimate: true,
  });
});

test("legitimate zero holding assumptions survive validation", () => {
  assert.deepEqual(validateHoldingAssumptions({ propertyPriceWan: 1_850, loanMonthlyPaymentWan: 0, monthlyIncomeWan: null, areaPing: 0, managementFeePerPingTwd: 0, repairReservePerPingTwd: 0, annualHomeTaxRatePercent: 0, annualLandTaxRatePercent: 0, annualInsuranceTwd: 0 }), {});
});

test("invalid holding inputs fail before reaching the API", () => {
  const errors = validateHoldingAssumptions({ propertyPriceWan: 1_850, loanMonthlyPaymentWan: -1, monthlyIncomeWan: -1, areaPing: -1, managementFeePerPingTwd: -1, repairReservePerPingTwd: -1, annualHomeTaxRatePercent: -1, annualLandTaxRatePercent: -1, annualInsuranceTwd: -1 });

  assert.deepEqual(Object.keys(errors).sort(), ["annualHomeTaxRatePercent", "annualInsuranceTwd", "annualLandTaxRatePercent", "areaPing", "loanMonthlyPaymentWan", "managementFeePerPingTwd", "monthlyIncomeWan", "repairReservePerPingTwd"].sort());
  assert.throws(() => buildHoldingCostRequest({ propertyPriceWan: 1_850, loanMonthlyPaymentWan: Number.NaN, monthlyIncomeWan: null, areaPing: null, managementFeePerPingTwd: 80, repairReservePerPingTwd: 50, annualHomeTaxRatePercent: 0.12, annualLandTaxRatePercent: 0.1, annualInsuranceTwd: 3_000 }), /invalid holding assumptions/);
});
