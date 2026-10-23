import type { FinanceModel, FinancePriceBasis } from "./finance-model";
// @ts-expect-error Native TS runner extension.
import { calculateScenario, emptyScenario } from "./scenario-calculator.ts";

/** A current saved scenario is distinct from the property's asking price. */
export function moneyPriceContext(amountWan: number | null | undefined, basis: FinancePriceBasis, finance?: FinanceModel) {
  return finance?.freshness.status === "current" && finance.priceSource != null && finance.savedAssumptions
    ? { amountWan: finance.savedAssumptions.amountWan, basis: finance.savedAssumptions.basis }
    : { amountWan: amountWan ?? null, basis };
}

export function projectMoneyOffer(priceWan: number | null, loan: Pick<FinanceModel["loan"], "downPaymentRatio" | "annualInterestRate" | "loanYears" | "gracePeriodYears">) {
  const validPrice = priceWan !== null && Number.isFinite(priceWan) && priceWan > 0;
  const validGrace = loan.gracePeriodYears !== null && Number.isInteger(loan.gracePeriodYears) && loan.gracePeriodYears >= 0
    && loan.loanYears !== null && loan.gracePeriodYears < loan.loanYears;
  const result = calculateScenario({ ...emptyScenario(), offerTwd: validPrice ? priceWan * 10000 : null,
    downValue: loan.downPaymentRatio === null ? null : loan.downPaymentRatio * 100,
    ratePercent: loan.annualInterestRate, loanYears: validGrace ? loan.loanYears! - loan.gracePeriodYears! : null });
  return {
    downPaymentTwd: result.downTwd,
    cashKnownSubtotalTwd: result.downTwd,
    loanTwd: result.principalTwd,
    monthlyPaymentTwd: validGrace ? result.paymentTwd : null,
    graceMonthlyPaymentTwd: validGrace && loan.gracePeriodYears! > 0 && result.principalTwd !== null && loan.annualInterestRate !== null
      ? result.principalTwd * loan.annualInterestRate / 100 / 12 : null,
    closingCostsTwd: null,
    initialCashTotalTwd: null,
  };
}

export function holdingFormSeed(initial: FinanceModel["holding"]["assumptions"] | null | undefined, loanPaymentTwd: number | null, areaPing: number | null) {
  const saved = initial && Object.entries(initial).some(([key, value]) => key !== "areaPing" && value !== null);
  const value = (key: keyof FinanceModel["holding"]["assumptions"], fallback: number | null) => {
    const amount = saved ? initial[key] : fallback;
    return amount === null ? "" : String(amount);
  };
  const payment = loanPaymentTwd ?? initial?.loanMonthlyPaymentTwd ?? null;
  return {
    loanMonthlyPaymentWan: payment === null ? "" : String(payment / 10000),
    monthlyIncomeWan: value("monthlyIncomeWan", null),
    areaPing: value("areaPing", areaPing),
    managementFeePerPingTwd: value("managementFeePerPingTwd", 80),
    repairReservePerPingTwd: value("repairReservePerPingTwd", 50),
    annualHomeTaxRatePercent: value("annualHomeTaxRatePercent", 0.12),
    annualLandTaxRatePercent: value("annualLandTaxRatePercent", 0.1),
    annualInsuranceTwd: value("annualInsuranceTwd", 3000),
  };
}

/** Never promote a previous scenario's automatic mortgage into a manual input. */
export function syncHoldingPayment(value: string, automatic: boolean, loanPaymentTwd: number | null) {
  if (loanPaymentTwd !== null) return { value: String(loanPaymentTwd / 10000), automatic: true };
  return automatic ? { value: "", automatic: false } : { value, automatic: false };
}
