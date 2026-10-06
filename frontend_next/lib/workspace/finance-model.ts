import type { HoldingCostResult, LoanCalculationResult, TaxResult } from "../api";
import type { AnalysisCompletenessState, EvidenceUsabilityState, QueryExecutionState } from "../commercial/state";
import type { PropertyIdentityState } from "../commercial/state";

export type FinancePriceBasis = "asking" | "estimate" | "manual";
export type FinanceResultStatus = "not_started" | "available" | "stale" | "unavailable";

export type FinanceInputFingerprintInput = {
  caseId: string;
  revision: number;
  identityAnchorId?: string | null;
  activePriceBasis: FinancePriceBasis;
  activePriceWan?: number | null;
  areaPing?: number | null;
};

export type FinanceBreakdownRow = {
  key: string;
  label: string;
  status: "estimated" | "unestimated";
  monthlyAmountTwd: number | null;
  missingReason: string | null;
};

export type FinanceTaxSummary = {
  outcome: TaxResult["eligibility_status"];
  failedConditionCount: number;
  reviewItemCount: number;
  missingInformationCount: number;
  sourceName: string | null;
  effectiveDate: string | null;
};

export type FinanceModel = {
  inputFingerprint: string;
  priceBasis: { basis: FinancePriceBasis; amountWan: number | null; source: "case" };
  calculation: {
    query: QueryExecutionState;
    usability: EvidenceUsabilityState | null;
    completeness: AnalysisCompletenessState;
  };
  loan: {
    status: FinanceResultStatus;
    propertyPriceWan: number | null;
    downPaymentRatio: number | null;
    downPaymentWan: number | null;
    principalWan: number | null;
    annualInterestRate: number | null;
    loanYears: number | null;
    gracePeriodYears: number | null;
    monthlyIncomeWan: number | null;
    monthlyPaymentTwd: number | null;
    gracePeriodMonthlyPaymentTwd: number | null;
    postGraceMonthlyPaymentTwd: number | null;
    totalInterestTwd: number | null;
    sensitivity: LoanCalculationResult["sensitivity"];
  };
  holding: {
    status: FinanceResultStatus;
    knownMonthlySubtotalTwd: number | null;
    knownAnnualSubtotalTwd: number | null;
    totalKind: "complete_estimate" | "known_subtotal" | "unavailable";
    assumptions: {
      loanMonthlyPaymentTwd: number | null;
      monthlyIncomeWan: number | null;
      areaPing: number | null;
      managementFeePerPingTwd: number | null;
      repairReservePerPingTwd: number | null;
      annualHomeTaxRatePercent: number | null;
      annualLandTaxRatePercent: number | null;
      annualInsuranceTwd: number | null;
    };
    breakdown: FinanceBreakdownRow[];
  };
  affordability: {
    status: "assessed" | "unassessed";
    ratio: number | null;
    reason: string | null;
    basis: "loan_payment" | "total_housing_cost" | null;
  };
  tax: {
    query: QueryExecutionState;
    summary: FinanceTaxSummary | null;
  };
  missingCosts: string[];
  unresolvedActions: string[];
  freshness: { status: "current" | "stale" | "not_calculated"; calculatedAt: string | null; source: "live_calculation" | "saved_snapshot" | null };
  overview: {
    activePriceBasis: FinancePriceBasis;
    calculationStatus: QueryExecutionState;
    monthlyPaymentTwd: number | null;
    knownRecurringMonthlyTwd: number | null;
    missingCosts: string[];
    affordabilityStatus: "assessed" | "unassessed";
    unresolvedActions: string[];
    freshness: "current" | "stale" | "not_calculated";
  };
  comparison: {
    activePriceWan: number | null;
    downPaymentWan: number | null;
    loanPrincipalWan: number | null;
    monthlyPaymentTwd: number | null;
    knownRecurringMonthlyTwd: number | null;
    knownOneTimeCostsTwd: number | null;
    missingCosts: string[];
  };
};

export type BuildFinanceModelInput = FinanceInputFingerprintInput & {
  identityState: PropertyIdentityState;
  askingPriceWan?: number | null;
  loanResult?: LoanCalculationResult | null;
  holdingResult?: HoldingCostResult | null;
  taxResult?: TaxResult | null;
  taxQueryStatus?: QueryExecutionState;
  calculatedAt?: string | null;
  savedFingerprint?: string | null;
  resultSource?: "live_calculation" | "saved_snapshot";
};

const BREAKDOWN_LABELS: Record<string, string> = {
  loan: "房貸支出",
  management: "管理費",
  repair_reserve: "修繕準備",
  tax_estimate: "房屋與土地稅估算",
  insurance: "保險",
};

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function nonNegative(value: unknown): value is number {
  return finite(value) && value >= 0;
}

function positive(value: unknown): value is number {
  return finite(value) && value > 0;
}

function optionalAmount(value: unknown): number | null {
  return nonNegative(value) ? value : null;
}

function canonicalNumber(value: number | null | undefined): string {
  if (!finite(value)) return "missing";
  return Number(value.toFixed(6)).toString();
}

export function createFinanceInputFingerprint(input: FinanceInputFingerprintInput): string {
  return [
    "finance-v1",
    encodeURIComponent(input.caseId),
    Math.max(0, Math.trunc(input.revision)),
    encodeURIComponent(input.identityAnchorId ?? "missing-identity"),
    input.activePriceBasis,
    canonicalNumber(input.activePriceWan),
    canonicalNumber(input.areaPing),
  ].join("|");
}

function validLoan(result: LoanCalculationResult | null | undefined): result is LoanCalculationResult {
  if (!result) return false;
  return positive(result.property_price_wan)
    && nonNegative(result.down_payment_ratio)
    && result.down_payment_ratio <= 1
    && nonNegative(result.down_payment_wan)
    && nonNegative(result.loan_amount_wan)
    && nonNegative(result.annual_interest_rate)
    && Number.isInteger(result.loan_years)
    && result.loan_years > 0
    && Number.isInteger(result.grace_period_years)
    && result.grace_period_years >= 0
    && result.grace_period_years < result.loan_years
    && nonNegative(result.monthly_payment)
    && nonNegative(result.total_payment)
    && nonNegative(result.total_interest)
    && (result.monthly_income_wan === null || positive(result.monthly_income_wan))
    && (result.income_burden_ratio === null || nonNegative(result.income_burden_ratio))
    && Array.isArray(result.sensitivity)
    && result.sensitivity.every((point) => Boolean(point)
      && nonNegative(point.annual_interest_rate)
      && nonNegative(point.monthly_payment)
      && nonNegative(point.total_interest)
      && finite(point.difference_from_base));
}

function validHolding(result: HoldingCostResult | null | undefined): result is HoldingCostResult {
  if (!result || !result.input) return false;
  return positive(result.property_price_wan)
    && positive(result.input.property_price_wan)
    && nonNegative(result.loan_monthly_payment)
    && nonNegative(result.monthly_total_holding_cost)
    && nonNegative(result.annual_total_holding_cost)
    && (result.income_burden_ratio === null || nonNegative(result.income_burden_ratio))
    && Array.isArray(result.cost_breakdown)
    && result.cost_breakdown.every((row) => typeof row?.key === "string" && nonNegative(row.monthly_amount));
}

function samePrice(left: number | null | undefined, right: number | null | undefined): boolean {
  return positive(left) && positive(right) && Math.abs(left - right) <= Math.max(0.01, right * 0.000001);
}

function buildBreakdown(result: HoldingCostResult, areaPing: number | null): FinanceBreakdownRow[] {
  const rows = new Map(result.cost_breakdown.map((row) => [row.key, row]));
  return ["loan", "management", "repair_reserve", "tax_estimate", "insurance"].map((key) => {
    if ((key === "management" || key === "repair_reserve") && areaPing === null) {
      return { key, label: BREAKDOWN_LABELS[key], status: "unestimated" as const, monthlyAmountTwd: null, missingReason: "缺少坪數" };
    }
    const row = rows.get(key);
    return {
      key,
      label: BREAKDOWN_LABELS[key],
      status: "estimated" as const,
      monthlyAmountTwd: optionalAmount(row?.monthly_amount),
      missingReason: null,
    };
  });
}

function boundedTaxSummary(result: TaxResult | null | undefined): FinanceTaxSummary | null {
  if (!result || !["eligible", "manual_review", "not_eligible"].includes(result.eligibility_status)) return null;
  const source = result.official_rule_trace;
  return {
    outcome: result.eligibility_status,
    failedConditionCount: Array.isArray(result.hard_fail_rules) ? result.hard_fail_rules.length : 0,
    reviewItemCount: Array.isArray(result.manual_review_rules) ? result.manual_review_rules.length : 0,
    missingInformationCount: Array.isArray(result.missing_docs) ? result.missing_docs.length : 0,
    sourceName: typeof source?.source_name === "string" && source.source_name.trim() ? source.source_name.trim() : null,
    effectiveDate: typeof source?.effective_date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(source.effective_date) ? source.effective_date : null,
  };
}

export function buildFinanceModel(input: BuildFinanceModelInput): FinanceModel {
  const activePriceWan = positive(input.activePriceWan) ? input.activePriceWan : null;
  const areaPing = nonNegative(input.areaPing) ? input.areaPing : null;
  const inputFingerprint = createFinanceInputFingerprint(input);
  const loanSupplied = input.loanResult !== null && input.loanResult !== undefined;
  const holdingSupplied = input.holdingResult !== null && input.holdingResult !== undefined;
  const loanResult = validLoan(input.loanResult) ? input.loanResult : null;
  const holdingResult = validHolding(input.holdingResult) ? input.holdingResult : null;
  const loanValid = loanResult !== null;
  const holdingValid = holdingResult !== null;
  const malformed = (loanSupplied && !loanValid) || (holdingSupplied && !holdingValid);
  const fingerprintMismatch = Boolean(input.savedFingerprint && input.savedFingerprint !== inputFingerprint);
  const identityStale = input.identityState !== "confirmed";
  const priceStale = Boolean(
    activePriceWan
    && ((loanResult && !samePrice(loanResult.property_price_wan, activePriceWan))
      || (holdingResult && !samePrice(holdingResult.property_price_wan, activePriceWan))),
  );
  const stale = fingerprintMismatch || identityStale || priceStale;
  const hasResult = loanValid || holdingValid;
  const missingCosts: string[] = [];
  if (holdingValid && areaPing === null) {
    missingCosts.push("管理費（缺少坪數）", "修繕準備（缺少坪數）");
  }
  if (!holdingValid) missingCosts.push("持有成本明細（尚未估算）");
  missingCosts.push("契稅、登記規費與仲介／代書等交易成本（未納入）");

  const unresolvedActions: string[] = [];
  if (activePriceWan === null) unresolvedActions.push("需要先提供可用的物件價格");
  if (priceStale || fingerprintMismatch) unresolvedActions.push("物件價格已變更，請重新計算資金與持有成本");
  if (identityStale) unresolvedActions.push("物件資料需重新確認後再使用財務結果");
  if (!loanValid && !loanSupplied) unresolvedActions.push("尚未計算房貸情境");
  if (!holdingValid && !holdingSupplied) unresolvedActions.push("尚未估算持有成本");
  if (areaPing === null) unresolvedActions.push("提供坪數以估算管理費與修繕準備");

  const affordabilityRatio = holdingResult && holdingResultIncomePresent(holdingResult)
    ? holdingResult.income_burden_ratio
    : loanResult && loanResult.monthly_income_wan !== null
      ? loanResult.income_burden_ratio
      : null;
  const affordabilityBasis = holdingResult && holdingResultIncomePresent(holdingResult)
    ? "total_housing_cost" as const
    : loanResult && loanResult.monthly_income_wan !== null
      ? "loan_payment" as const
      : null;
  const affordability = affordabilityRatio !== null && nonNegative(affordabilityRatio)
    ? { status: "assessed" as const, ratio: affordabilityRatio, reason: null, basis: affordabilityBasis }
    : { status: "unassessed" as const, ratio: null, reason: "未提供月收入", basis: null };

  const query: QueryExecutionState = activePriceWan === null
    ? "input_required"
    : malformed
      ? "failed"
      : hasResult
        ? "succeeded"
        : "not_started";
  const usability: EvidenceUsabilityState | null = malformed
    ? "unavailable"
    : stale && hasResult
      ? "stale"
      : hasResult
        ? "usable"
        : null;
  const completeness: AnalysisCompletenessState = malformed
    ? "blocked"
    : !hasResult
      ? "not_started"
      : loanValid && holdingValid && missingCosts.length === 1 && affordability.status === "assessed"
        ? "sufficient_for_task"
        : "partial";
  const resultStatus = (valid: boolean): FinanceResultStatus => !valid
    ? malformed ? "unavailable" : "not_started"
    : stale ? "stale" : "available";
  const breakdown = holdingResult ? buildBreakdown(holdingResult, areaPing) : [];
  const freshnessStatus = !hasResult ? "not_calculated" : stale ? "stale" : "current";
  const knownMonthlySubtotal = holdingResult
    ? holdingResult.monthly_total_holding_cost
    : loanResult
      ? loanResult.monthly_payment
      : null;

  const model: FinanceModel = {
    inputFingerprint,
    priceBasis: { basis: input.activePriceBasis, amountWan: activePriceWan, source: "case" },
    calculation: { query, usability, completeness },
    loan: {
      status: resultStatus(loanValid),
      propertyPriceWan: loanResult?.property_price_wan ?? null,
      downPaymentRatio: loanResult?.down_payment_ratio ?? null,
      downPaymentWan: loanResult?.down_payment_wan ?? null,
      principalWan: loanResult?.loan_amount_wan ?? null,
      annualInterestRate: loanResult?.annual_interest_rate ?? null,
      loanYears: loanResult?.loan_years ?? null,
      gracePeriodYears: loanResult?.grace_period_years ?? null,
      monthlyIncomeWan: loanResult?.monthly_income_wan ?? null,
      monthlyPaymentTwd: loanResult?.monthly_payment ?? null,
      gracePeriodMonthlyPaymentTwd: loanResult?.grace_period_monthly_payment ?? null,
      postGraceMonthlyPaymentTwd: loanResult?.post_grace_monthly_payment ?? null,
      totalInterestTwd: loanResult?.total_interest ?? null,
      sensitivity: loanResult ? loanResult.sensitivity.filter((point) => nonNegative(point.annual_interest_rate) && nonNegative(point.monthly_payment) && nonNegative(point.total_interest) && finite(point.difference_from_base)) : [],
    },
    holding: {
      status: resultStatus(holdingValid),
      knownMonthlySubtotalTwd: holdingResult?.monthly_total_holding_cost ?? null,
      knownAnnualSubtotalTwd: holdingResult?.annual_total_holding_cost ?? null,
      totalKind: holdingValid ? areaPing === null ? "known_subtotal" : "complete_estimate" : "unavailable",
      assumptions: {
        loanMonthlyPaymentTwd: holdingResult?.input.loan_monthly_payment ?? null,
        monthlyIncomeWan: holdingResult?.input.monthly_income_wan ?? null,
        areaPing,
        managementFeePerPingTwd: holdingResult?.input.management_fee_per_ping ?? null,
        repairReservePerPingTwd: holdingResult?.input.repair_reserve_per_ping ?? null,
        annualHomeTaxRatePercent: holdingResult ? holdingResult.input.annual_home_tax_rate * 100 : null,
        annualLandTaxRatePercent: holdingResult ? holdingResult.input.annual_land_tax_rate * 100 : null,
        annualInsuranceTwd: holdingResult?.input.annual_insurance ?? null,
      },
      breakdown,
    },
    affordability,
    tax: {
      query: input.taxQueryStatus ?? (input.taxResult ? "succeeded" : "not_started"),
      summary: boundedTaxSummary(input.taxResult),
    },
    missingCosts,
    unresolvedActions: [...new Set(unresolvedActions)],
    freshness: { status: freshnessStatus, calculatedAt: hasResult && typeof input.calculatedAt === "string" ? input.calculatedAt : null, source: hasResult ? input.resultSource ?? "live_calculation" : null },
    overview: {
      activePriceBasis: input.activePriceBasis,
      calculationStatus: query,
      monthlyPaymentTwd: loanResult?.monthly_payment ?? null,
      knownRecurringMonthlyTwd: knownMonthlySubtotal,
      missingCosts,
      affordabilityStatus: affordability.status,
      unresolvedActions: [...new Set(unresolvedActions)],
      freshness: freshnessStatus,
    },
    comparison: {
      activePriceWan,
      downPaymentWan: loanResult?.down_payment_wan ?? null,
      loanPrincipalWan: loanResult?.loan_amount_wan ?? null,
      monthlyPaymentTwd: loanResult?.monthly_payment ?? null,
      knownRecurringMonthlyTwd: knownMonthlySubtotal,
      knownOneTimeCostsTwd: null,
      missingCosts,
    },
  };
  return model;
}

function holdingResultIncomePresent(result: HoldingCostResult): boolean {
  return result.input.monthly_income_wan !== null && result.income_burden_ratio !== null;
}
