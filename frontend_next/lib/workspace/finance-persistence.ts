import type { PropertyIdentityState } from "../commercial/state";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { createFinanceInputFingerprint, type FinanceBreakdownRow, type FinanceInputFingerprintInput, type FinanceModel, type FinanceTaxSummary } from "./finance-model.ts";

export type StoredFinanceEvidenceV1 = {
  version: 1;
  case_id: string;
  revision: number;
  input_fingerprint: string;
  assumptions: {
    price_basis: FinanceModel["priceBasis"]["basis"];
    active_price_wan: number;
    area_ping: number | null;
  };
  calculation: FinanceModel["calculation"];
  loan: {
    property_price_wan: number | null;
    down_payment_ratio: number | null;
    down_payment_wan: number | null;
    principal_wan: number | null;
    annual_interest_rate: number | null;
    loan_years: number | null;
    grace_period_years: number | null;
    monthly_income_wan: number | null;
    monthly_payment_twd: number | null;
    grace_period_monthly_payment_twd: number | null;
    post_grace_monthly_payment_twd: number | null;
    total_interest_twd: number | null;
  };
  holding: {
    known_monthly_subtotal_twd: number | null;
    known_annual_subtotal_twd: number | null;
    total_kind: FinanceModel["holding"]["totalKind"];
    assumptions: {
      loan_monthly_payment_twd: number | null;
      monthly_income_wan: number | null;
      area_ping: number | null;
      management_fee_per_ping_twd: number | null;
      repair_reserve_per_ping_twd: number | null;
      annual_home_tax_rate_percent: number | null;
      annual_land_tax_rate_percent: number | null;
      annual_insurance_twd: number | null;
    };
    breakdown: Array<{
      key: string;
      label: string;
      status: FinanceBreakdownRow["status"];
      monthly_amount_twd: number | null;
      missing_reason: string | null;
    }>;
  };
  affordability: FinanceModel["affordability"];
  tax: { query: FinanceModel["tax"]["query"]; summary: FinanceTaxSummary | null };
  missing_costs: string[];
  unresolved_actions: string[];
  calculated_at: string;
};

type SnapshotContext = FinanceInputFingerprintInput & { identityState: PropertyIdentityState };

function finiteNonNegative(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function finitePositive(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function nullableAmount(value: unknown): value is number | null {
  return value === null || finiteNonNegative(value);
}

function text(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= 500;
}

function validBreakdown(value: unknown): value is StoredFinanceEvidenceV1["holding"]["breakdown"] {
  return Array.isArray(value) && value.length <= 20 && value.every((row) => {
    if (!row || typeof row !== "object") return false;
    const item = row as Record<string, unknown>;
    return text(item.key)
      && text(item.label)
      && (item.status === "estimated" || item.status === "unestimated")
      && nullableAmount(item.monthly_amount_twd)
      && (item.missing_reason === null || text(item.missing_reason));
  });
}

function validTaxSummary(value: unknown): value is FinanceTaxSummary | null {
  if (value === null) return true;
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return ["eligible", "manual_review", "not_eligible"].includes(String(item.outcome))
    && finiteNonNegative(item.failedConditionCount)
    && finiteNonNegative(item.reviewItemCount)
    && finiteNonNegative(item.missingInformationCount)
    && (item.sourceName === null || text(item.sourceName))
    && (item.effectiveDate === null || (typeof item.effectiveDate === "string" && /^\d{4}-\d{2}-\d{2}$/.test(item.effectiveDate)));
}

export function createStoredFinanceEvidence(
  model: FinanceModel,
  context: { caseId: string; revision: number; areaPing?: number | null },
): StoredFinanceEvidenceV1 {
  if (model.priceBasis.amountWan === null || model.freshness.calculatedAt === null) {
    throw new Error("finance evidence requires a calculated price-bound result");
  }
  return {
    version: 1,
    case_id: context.caseId,
    revision: context.revision,
    input_fingerprint: model.inputFingerprint,
    assumptions: {
      price_basis: model.priceBasis.basis,
      active_price_wan: model.priceBasis.amountWan,
      area_ping: finiteNonNegative(context.areaPing) ? context.areaPing : null,
    },
    calculation: { ...model.calculation },
    loan: {
      property_price_wan: model.loan.propertyPriceWan,
      down_payment_ratio: model.loan.downPaymentRatio,
      down_payment_wan: model.loan.downPaymentWan,
      principal_wan: model.loan.principalWan,
      annual_interest_rate: model.loan.annualInterestRate,
      loan_years: model.loan.loanYears,
      grace_period_years: model.loan.gracePeriodYears,
      monthly_income_wan: model.loan.monthlyIncomeWan,
      monthly_payment_twd: model.loan.monthlyPaymentTwd,
      grace_period_monthly_payment_twd: model.loan.gracePeriodMonthlyPaymentTwd,
      post_grace_monthly_payment_twd: model.loan.postGraceMonthlyPaymentTwd,
      total_interest_twd: model.loan.totalInterestTwd,
    },
    holding: {
      known_monthly_subtotal_twd: model.holding.knownMonthlySubtotalTwd,
      known_annual_subtotal_twd: model.holding.knownAnnualSubtotalTwd,
      total_kind: model.holding.totalKind,
      assumptions: {
        loan_monthly_payment_twd: model.holding.assumptions.loanMonthlyPaymentTwd,
        monthly_income_wan: model.holding.assumptions.monthlyIncomeWan,
        area_ping: model.holding.assumptions.areaPing,
        management_fee_per_ping_twd: model.holding.assumptions.managementFeePerPingTwd,
        repair_reserve_per_ping_twd: model.holding.assumptions.repairReservePerPingTwd,
        annual_home_tax_rate_percent: model.holding.assumptions.annualHomeTaxRatePercent,
        annual_land_tax_rate_percent: model.holding.assumptions.annualLandTaxRatePercent,
        annual_insurance_twd: model.holding.assumptions.annualInsuranceTwd,
      },
      breakdown: model.holding.breakdown.map((row) => ({
        key: row.key,
        label: row.label,
        status: row.status,
        monthly_amount_twd: row.monthlyAmountTwd,
        missing_reason: row.missingReason,
      })),
    },
    affordability: { ...model.affordability },
    tax: { query: model.tax.query, summary: model.tax.summary ? { ...model.tax.summary } : null },
    missing_costs: [...model.missingCosts],
    unresolved_actions: [...model.unresolvedActions],
    calculated_at: model.freshness.calculatedAt,
  };
}

export function normalizeStoredFinanceEvidence(value: unknown): StoredFinanceEvidenceV1 | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Partial<StoredFinanceEvidenceV1>;
  if (row.version !== 1 || !text(row.case_id) || !Number.isInteger(row.revision) || Number(row.revision) < 0 || !text(row.input_fingerprint)) return null;
  if (!row.assumptions || !["asking", "estimate", "manual"].includes(row.assumptions.price_basis) || !finitePositive(row.assumptions.active_price_wan) || !nullableAmount(row.assumptions.area_ping)) return null;
  if (!row.calculation
    || !["not_started", "input_required", "in_progress", "succeeded", "failed", "cancelled"].includes(row.calculation.query)
    || ![null, "usable", "limited", "no_match", "no_coverage", "unavailable", "stale", "unverified", "unsupported"].includes(row.calculation.usability)
    || !["not_started", "insufficient", "partial", "sufficient_for_task", "blocked"].includes(row.calculation.completeness)) return null;
  if (!row.loan || !nullableAmount(row.loan.property_price_wan) || !nullableAmount(row.loan.down_payment_ratio) || !nullableAmount(row.loan.down_payment_wan) || !nullableAmount(row.loan.principal_wan) || !nullableAmount(row.loan.annual_interest_rate) || !nullableAmount(row.loan.loan_years) || !nullableAmount(row.loan.grace_period_years) || !nullableAmount(row.loan.monthly_income_wan) || !nullableAmount(row.loan.monthly_payment_twd) || !nullableAmount(row.loan.grace_period_monthly_payment_twd) || !nullableAmount(row.loan.post_grace_monthly_payment_twd) || !nullableAmount(row.loan.total_interest_twd)) return null;
  const holdingAssumptions = row.holding?.assumptions;
  if (!row.holding || !holdingAssumptions || !nullableAmount(row.holding.known_monthly_subtotal_twd) || !nullableAmount(row.holding.known_annual_subtotal_twd) || !["complete_estimate", "known_subtotal", "unavailable"].includes(row.holding.total_kind) || !validBreakdown(row.holding.breakdown)) return null;
  if (![holdingAssumptions.loan_monthly_payment_twd, holdingAssumptions.monthly_income_wan, holdingAssumptions.area_ping, holdingAssumptions.management_fee_per_ping_twd, holdingAssumptions.repair_reserve_per_ping_twd, holdingAssumptions.annual_home_tax_rate_percent, holdingAssumptions.annual_land_tax_rate_percent, holdingAssumptions.annual_insurance_twd].every(nullableAmount)) return null;
  if (!row.affordability || !["assessed", "unassessed"].includes(row.affordability.status) || !nullableAmount(row.affordability.ratio) || (row.affordability.reason !== null && typeof row.affordability.reason !== "string") || ![null, "loan_payment", "total_housing_cost"].includes(row.affordability.basis)) return null;
  if (!row.tax || !["not_started", "input_required", "in_progress", "succeeded", "failed", "cancelled"].includes(row.tax.query) || !validTaxSummary(row.tax.summary)) return null;
  if (!Array.isArray(row.missing_costs) || row.missing_costs.length > 20 || !row.missing_costs.every(text) || !Array.isArray(row.unresolved_actions) || row.unresolved_actions.length > 20 || !row.unresolved_actions.every(text)) return null;
  if (!text(row.calculated_at) || !Number.isFinite(Date.parse(row.calculated_at))) return null;
  return {
    version: 1,
    case_id: row.case_id,
    revision: Number(row.revision),
    input_fingerprint: row.input_fingerprint,
    assumptions: {
      price_basis: row.assumptions.price_basis,
      active_price_wan: row.assumptions.active_price_wan,
      area_ping: row.assumptions.area_ping,
    },
    calculation: {
      query: row.calculation.query,
      usability: row.calculation.usability,
      completeness: row.calculation.completeness,
    },
    loan: {
      property_price_wan: row.loan.property_price_wan,
      down_payment_ratio: row.loan.down_payment_ratio,
      down_payment_wan: row.loan.down_payment_wan,
      principal_wan: row.loan.principal_wan,
      annual_interest_rate: row.loan.annual_interest_rate,
      loan_years: row.loan.loan_years,
      grace_period_years: row.loan.grace_period_years,
      monthly_income_wan: row.loan.monthly_income_wan,
      monthly_payment_twd: row.loan.monthly_payment_twd,
      grace_period_monthly_payment_twd: row.loan.grace_period_monthly_payment_twd,
      post_grace_monthly_payment_twd: row.loan.post_grace_monthly_payment_twd,
      total_interest_twd: row.loan.total_interest_twd,
    },
    holding: {
      known_monthly_subtotal_twd: row.holding.known_monthly_subtotal_twd,
      known_annual_subtotal_twd: row.holding.known_annual_subtotal_twd,
      total_kind: row.holding.total_kind,
      assumptions: {
        loan_monthly_payment_twd: holdingAssumptions.loan_monthly_payment_twd,
        monthly_income_wan: holdingAssumptions.monthly_income_wan,
        area_ping: holdingAssumptions.area_ping,
        management_fee_per_ping_twd: holdingAssumptions.management_fee_per_ping_twd,
        repair_reserve_per_ping_twd: holdingAssumptions.repair_reserve_per_ping_twd,
        annual_home_tax_rate_percent: holdingAssumptions.annual_home_tax_rate_percent,
        annual_land_tax_rate_percent: holdingAssumptions.annual_land_tax_rate_percent,
        annual_insurance_twd: holdingAssumptions.annual_insurance_twd,
      },
      breakdown: row.holding.breakdown.map((item) => ({
        key: item.key,
        label: item.label,
        status: item.status,
        monthly_amount_twd: item.monthly_amount_twd,
        missing_reason: item.missing_reason,
      })),
    },
    affordability: {
      status: row.affordability.status,
      ratio: row.affordability.ratio,
      reason: row.affordability.reason,
      basis: row.affordability.basis,
    },
    tax: {
      query: row.tax.query,
      summary: row.tax.summary ? {
        outcome: row.tax.summary.outcome,
        failedConditionCount: row.tax.summary.failedConditionCount,
        reviewItemCount: row.tax.summary.reviewItemCount,
        missingInformationCount: row.tax.summary.missingInformationCount,
        sourceName: row.tax.summary.sourceName,
        effectiveDate: row.tax.summary.effectiveDate,
      } : null,
    },
    missing_costs: [...row.missing_costs],
    unresolved_actions: [...row.unresolved_actions],
    calculated_at: row.calculated_at,
  };
}

export function restoreFinanceModelFromSnapshot(snapshotValue: unknown, context: SnapshotContext): FinanceModel {
  const snapshot = normalizeStoredFinanceEvidence(snapshotValue);
  if (!snapshot) throw new Error("invalid stored finance evidence");
  const currentFingerprint = createFinanceInputFingerprint(context);
  const stale = context.identityState !== "confirmed" || snapshot.input_fingerprint !== currentFingerprint;
  const loanPresent = snapshot.loan.monthly_payment_twd !== null;
  const holdingPresent = snapshot.holding.known_monthly_subtotal_twd !== null;
  const status = (present: boolean): FinanceModel["loan"]["status"] => !present ? "not_started" : stale ? "stale" : "available";
  const missingCosts = [...snapshot.missing_costs];
  const unresolvedActions = stale
    ? [...new Set([...snapshot.unresolved_actions, "物件或價格條件已變更，請重新計算資金與持有成本"])]
    : [...snapshot.unresolved_actions];
  const knownRecurringMonthlyTwd = snapshot.holding.known_monthly_subtotal_twd ?? snapshot.loan.monthly_payment_twd;
  const currentPrice = finiteNonNegative(context.activePriceWan) ? context.activePriceWan : null;
  return {
    inputFingerprint: currentFingerprint,
    priceBasis: { basis: context.activePriceBasis, amountWan: currentPrice, source: "case" },
    calculation: { ...snapshot.calculation, usability: stale ? "stale" : snapshot.calculation.usability },
    loan: {
      status: status(loanPresent),
      propertyPriceWan: snapshot.loan.property_price_wan,
      downPaymentRatio: snapshot.loan.down_payment_ratio,
      downPaymentWan: snapshot.loan.down_payment_wan,
      principalWan: snapshot.loan.principal_wan,
      annualInterestRate: snapshot.loan.annual_interest_rate,
      loanYears: snapshot.loan.loan_years,
      gracePeriodYears: snapshot.loan.grace_period_years,
      monthlyIncomeWan: snapshot.loan.monthly_income_wan,
      monthlyPaymentTwd: snapshot.loan.monthly_payment_twd,
      gracePeriodMonthlyPaymentTwd: snapshot.loan.grace_period_monthly_payment_twd,
      postGraceMonthlyPaymentTwd: snapshot.loan.post_grace_monthly_payment_twd,
      totalInterestTwd: snapshot.loan.total_interest_twd,
      sensitivity: [],
    },
    holding: {
      status: status(holdingPresent),
      knownMonthlySubtotalTwd: snapshot.holding.known_monthly_subtotal_twd,
      knownAnnualSubtotalTwd: snapshot.holding.known_annual_subtotal_twd,
      totalKind: snapshot.holding.total_kind,
      assumptions: {
        loanMonthlyPaymentTwd: snapshot.holding.assumptions.loan_monthly_payment_twd,
        monthlyIncomeWan: snapshot.holding.assumptions.monthly_income_wan,
        areaPing: snapshot.holding.assumptions.area_ping,
        managementFeePerPingTwd: snapshot.holding.assumptions.management_fee_per_ping_twd,
        repairReservePerPingTwd: snapshot.holding.assumptions.repair_reserve_per_ping_twd,
        annualHomeTaxRatePercent: snapshot.holding.assumptions.annual_home_tax_rate_percent,
        annualLandTaxRatePercent: snapshot.holding.assumptions.annual_land_tax_rate_percent,
        annualInsuranceTwd: snapshot.holding.assumptions.annual_insurance_twd,
      },
      breakdown: snapshot.holding.breakdown.map((row) => ({ key: row.key, label: row.label, status: row.status, monthlyAmountTwd: row.monthly_amount_twd, missingReason: row.missing_reason })),
    },
    affordability: { ...snapshot.affordability },
    tax: { query: snapshot.tax.query, summary: snapshot.tax.summary ? { ...snapshot.tax.summary } : null },
    missingCosts,
    unresolvedActions,
    freshness: { status: stale ? "stale" : "current", calculatedAt: snapshot.calculated_at, source: "saved_snapshot" },
    overview: {
      activePriceBasis: context.activePriceBasis,
      calculationStatus: snapshot.calculation.query,
      monthlyPaymentTwd: snapshot.loan.monthly_payment_twd,
      knownRecurringMonthlyTwd,
      missingCosts,
      affordabilityStatus: snapshot.affordability.status,
      unresolvedActions,
      freshness: stale ? "stale" : "current",
    },
    comparison: {
      activePriceWan: currentPrice,
      downPaymentWan: snapshot.loan.down_payment_wan,
      loanPrincipalWan: snapshot.loan.principal_wan,
      monthlyPaymentTwd: snapshot.loan.monthly_payment_twd,
      knownRecurringMonthlyTwd,
      knownOneTimeCostsTwd: null,
      missingCosts,
    },
  };
}
