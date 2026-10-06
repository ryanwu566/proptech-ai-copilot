// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { monthlyPaymentWanToTwd } from "../monetary-units.ts";

export type LoanAssumptions = {
  propertyPriceWan: number;
  downPaymentRatioPercent: number;
  annualInterestRatePercent: number;
  loanYears: number;
  gracePeriodYears: number;
  monthlyIncomeWan: number | null;
};

export type HoldingAssumptions = {
  propertyPriceWan: number;
  loanMonthlyPaymentWan: number;
  monthlyIncomeWan: number | null;
  areaPing: number | null;
  managementFeePerPingTwd: number;
  repairReservePerPingTwd: number;
  annualHomeTaxRatePercent: number;
  annualLandTaxRatePercent: number;
  annualInsuranceTwd: number;
};

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function validateLoanAssumptions(input: LoanAssumptions): Partial<Record<keyof LoanAssumptions, string>> {
  const errors: Partial<Record<keyof LoanAssumptions, string>> = {};
  if (!finite(input.propertyPriceWan) || input.propertyPriceWan <= 0) errors.propertyPriceWan = "物件價格必須大於 0。";
  if (!finite(input.downPaymentRatioPercent) || input.downPaymentRatioPercent < 0 || input.downPaymentRatioPercent > 100) errors.downPaymentRatioPercent = "自備款比例必須介於 0% 與 100%。";
  if (!finite(input.annualInterestRatePercent) || input.annualInterestRatePercent < 0) errors.annualInterestRatePercent = "利率不可小於 0%。";
  if (!Number.isInteger(input.loanYears) || input.loanYears <= 0) errors.loanYears = "貸款年期必須大於 0 年。";
  if (!Number.isInteger(input.gracePeriodYears) || input.gracePeriodYears < 0 || input.gracePeriodYears >= input.loanYears) errors.gracePeriodYears = "寬限期必須小於貸款年期。";
  if (input.monthlyIncomeWan !== null && (!finite(input.monthlyIncomeWan) || input.monthlyIncomeWan <= 0)) errors.monthlyIncomeWan = "月收入如有填寫，必須大於 0。";
  return errors;
}

export function buildLoanRequest(input: LoanAssumptions) {
  if (Object.keys(validateLoanAssumptions(input)).length > 0) throw new Error("invalid loan assumptions");
  return {
    property_price: input.propertyPriceWan,
    down_payment_ratio: input.downPaymentRatioPercent / 100,
    annual_interest_rate: input.annualInterestRatePercent,
    loan_years: input.loanYears,
    grace_period_years: input.gracePeriodYears,
    monthly_income: input.monthlyIncomeWan ?? undefined,
    include_sensitivity: true,
  };
}

export function validateHoldingAssumptions(input: HoldingAssumptions): Partial<Record<keyof HoldingAssumptions, string>> {
  const errors: Partial<Record<keyof HoldingAssumptions, string>> = {};
  if (!finite(input.propertyPriceWan) || input.propertyPriceWan <= 0) errors.propertyPriceWan = "物件價格必須大於 0。";
  for (const key of ["loanMonthlyPaymentWan", "managementFeePerPingTwd", "repairReservePerPingTwd", "annualHomeTaxRatePercent", "annualLandTaxRatePercent", "annualInsuranceTwd"] as const) {
    if (!finite(input[key]) || input[key] < 0) errors[key] = "數值不可小於 0。";
  }
  if (input.monthlyIncomeWan !== null && (!finite(input.monthlyIncomeWan) || input.monthlyIncomeWan <= 0)) errors.monthlyIncomeWan = "月收入如有填寫，必須大於 0。";
  if (input.areaPing !== null && (!finite(input.areaPing) || input.areaPing < 0)) errors.areaPing = "坪數不可小於 0。";
  return errors;
}

export function buildHoldingCostRequest(input: HoldingAssumptions) {
  if (Object.keys(validateHoldingAssumptions(input)).length > 0) throw new Error("invalid holding assumptions");
  const paymentTwd = monthlyPaymentWanToTwd(input.loanMonthlyPaymentWan);
  if (paymentTwd === null) throw new Error("invalid holding assumptions");
  return {
    property_price: input.propertyPriceWan,
    loan_monthly_payment: paymentTwd,
    monthly_income: input.monthlyIncomeWan ?? undefined,
    area_ping: input.areaPing ?? undefined,
    management_fee_per_ping: input.managementFeePerPingTwd,
    repair_reserve_per_ping: input.repairReservePerPingTwd,
    annual_home_tax_rate: input.annualHomeTaxRatePercent / 100,
    annual_land_tax_rate: input.annualLandTaxRatePercent / 100,
    annual_insurance: input.annualInsuranceTwd,
    include_tax_estimate: true,
  };
}
