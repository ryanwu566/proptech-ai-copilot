/** Pure offer/loan arithmetic shared by Money and the Scenario Lab. No storage, copy or catalogue:
 * the Lab engine (saved drafts under its storage key) stays behind the Lab's own lazy boundary. */
export type ScenarioInput = {
  offerTwd: number | null;
  downMode: "amount" | "ratio";
  downValue: number | null;
  ratePercent: number | null;
  loanYears: number | null;
  acquisitionTwd: number | null;
  recurringTwd: number | null;
  renovationTwd: number | null;
  holdingYears: number | null;
  commuteMinutes: number | null;
};
export type ScenarioField = Exclude<keyof ScenarioInput, "downMode">;
export const SCENARIO_FIELDS: ScenarioField[] = ["offerTwd", "downValue", "ratePercent", "loanYears", "acquisitionTwd", "recurringTwd", "renovationTwd", "holdingYears", "commuteMinutes"];

export function emptyScenario(): ScenarioInput {
  return { offerTwd: null, downMode: "ratio", downValue: null, ratePercent: null, loanYears: null, acquisitionTwd: null, recurringTwd: null, renovationTwd: null, holdingYears: null, commuteMinutes: null };
}

export function calculateScenario(input: Readonly<ScenarioInput>) {
  const errors: Partial<Record<ScenarioField, "positive" | "range" | "integer">> = {};
  for (const field of SCENARIO_FIELDS) {
    const value = input[field];
    if (value === null) continue;
    const max = field === "ratePercent" || (field === "downValue" && input.downMode === "ratio") ? 100
      : field === "loanYears" || field === "holdingYears" ? 100 : field === "commuteMinutes" ? 1440 : 1e12;
    if (!Number.isFinite(value) || value < 0 || value > max) errors[field] = "range";
    else if ((field === "offerTwd" || field === "loanYears" || field === "holdingYears") && value === 0) errors[field] = "positive";
    else if ((field === "loanYears" || field === "holdingYears") && !Number.isInteger(value)) errors[field] = "integer";
  }
  if (input.downMode === "amount" && input.downValue !== null && input.offerTwd !== null && input.downValue > input.offerTwd) errors.downValue = "range";
  const valid = Object.keys(errors).length === 0;
  const downTwd = valid && input.offerTwd !== null && input.downValue !== null
    ? input.downMode === "ratio" ? input.offerTwd * (input.downValue / 100) : input.downValue : null;
  const principalTwd = downTwd !== null ? input.offerTwd! - downTwd : null;
  const cashPurchase = principalTwd === 0;
  const unknown = SCENARIO_FIELDS.filter((field) => input[field] === null && !(cashPurchase && (field === "ratePercent" || field === "loanYears")));
  let paymentTwd: number | null = cashPurchase ? 0 : null;
  if (valid && principalTwd !== null && input.ratePercent !== null && input.loanYears !== null) {
    // Port of loan_calculator_service.py::_amortized_payment. expm1/log1p
    // preserve the same annuity equation at rates near zero; no provider call.
    const monthlyRate = input.ratePercent / 100 / 12;
    const months = input.loanYears * 12;
    paymentTwd = monthlyRate === 0 ? principalTwd / months
      : principalTwd * monthlyRate / -Math.expm1(-months * Math.log1p(monthlyRate));
  }
  const costsComplete = [input.acquisitionTwd, input.recurringTwd, input.renovationTwd].every((value) => value !== null);
  // Unknown costs are omitted from explicitly labelled known subtotals.
  // Invalid costs suppress outputs rather than disappearing into a subtotal.
  const oneTime = (input.acquisitionTwd ?? 0) + (input.renovationTwd ?? 0);
  const purchaseCashTwd = valid && downTwd !== null ? downTwd + oneTime : null;
  const acquisitionTotalTwd = valid && input.offerTwd !== null ? input.offerTwd + oneTime : null;
  const monthlyOwnershipTwd = paymentTwd !== null ? paymentTwd + (input.recurringTwd ?? 0) : null;
  const firstYearTwd = purchaseCashTwd !== null && monthlyOwnershipTwd !== null ? purchaseCashTwd + monthlyOwnershipTwd * 12 : null;
  const holdingCashTwd = purchaseCashTwd !== null && paymentTwd !== null && input.holdingYears !== null
    ? purchaseCashTwd + paymentTwd * Math.min(input.holdingYears * 12, cashPurchase ? 0 : input.loanYears! * 12) + (input.recurringTwd ?? 0) * input.holdingYears * 12 : null;
  return { errors, unknown, costsComplete, downTwd, principalTwd, paymentTwd, purchaseCashTwd, acquisitionTotalTwd, monthlyOwnershipTwd, firstYearTwd, holdingCashTwd };
}
export type ScenarioResult = ReturnType<typeof calculateScenario>;
