import type {
  HoldingCostResult,
  LoanCalculationResult,
  LocationInsightResult,
  PropertySearchResult,
  TaxResult,
  TerrainRiskResult,
  ValuationResult,
  ValuationTrendResult,
} from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";
import type { ValuationInputs } from "@/lib/valuation-share";
import {
  buildDueDiligenceReadiness,
  normalizeDueDiligenceItems,
  type DueDiligenceItem,
  type DueDiligenceReadiness,
} from "@/lib/property-case-due-diligence";

export type PropertyCaseStatus = "completed" | "missing" | "unavailable" | "incomplete";
export type PropertyDecisionStatus = "draft" | "reviewing" | "shortlisted" | "rejected" | "purchased";

export const PARTIAL_CASE_PRINT_NOTICE = "本案件資料尚未完整，報告僅彙整目前可用資訊。";

export type PropertyCaseDraftInput = {
  caseName?: string;
  address?: string;
  propertyType?: string;
  listingPrice?: number | null;
  floorAreaPing?: number | null;
  buildingAgeYears?: number | null;
  notes?: string;
  downPayment?: number | null;
  loanAmount?: number | null;
  loanYears?: number | null;
  loanRate?: number | null;
  fundingMode?: "loan_amount" | "down_payment";
  fundingValue?: number | null;
  estimatedBuyerCosts?: number | null;
  renovationReserve?: number | null;
  availableLiquidCash?: number | null;
  monthlyHouseholdIncome?: number | null;
  monthlyFixedObligations?: number | null;
  monthlyOwnershipReserve?: number | null;
  estimatedMonthlyPayment?: number | null;
  userEstimatedValue?: number | null;
  userEstimatedTaxCost?: number | null;
  valuationNote?: string;
  taxNote?: string;
  decisionStatus?: PropertyDecisionStatus;
  decisionNote?: string;
  dueDiligenceItems?: Partial<DueDiligenceItem>[];
  decisionReviewSummary?: string;
  decisionOpenQuestions?: string;
  decisionNextStep?: string;
  inputs: ValuationInputs;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holding?: HoldingCostResult;
  location?: LocationInsightResult;
  terrainRisk?: TerrainRiskResult;
  riskSummary?: RiskSummary;
  taxOracle?: TaxResult;
};

export type PropertyCaseDraft = {
  case_id: string;
  case_name: string;
  decision_status: PropertyDecisionStatus;
  decision_note: string;
  decision_review_summary: string;
  decision_open_questions: string;
  decision_next_step: string;
  last_reviewed_at: string;
  created_at: string;
  updated_at: string;
  property_input: {
    address: string;
    listing_price: number | null;
    building_area: number | null;
    property_type: string;
    building_age: number | null;
    floor: number | null;
    total_floors: number | null;
    parking_type: string;
    parking_price: number | null;
    notes: string;
  };
  location_input: {
    address_status: PropertyCaseStatus;
    location_analysis_status: PropertyCaseStatus;
    terrain_analysis_status: PropertyCaseStatus;
    commute_analysis_status: PropertyCaseStatus;
    map_available: boolean;
  };
  financial_input: {
    down_payment: number | null;
    loan_amount: number | null;
    loan_years: number | null;
    interest_rate: number | null;
    funding_mode: "loan_amount" | "down_payment" | null;
    funding_value: number | null;
    estimated_buyer_costs: number | null;
    renovation_reserve: number | null;
    available_liquid_cash: number | null;
    grace_period_months: number | null;
    monthly_income: number | null;
    other_monthly_debt: number | null;
    monthly_ownership_reserve: number | null;
    estimated_holding_cost: number | null;
  };
  valuation_tax_input: {
    user_estimated_value: number | null;
    user_estimated_tax_cost: number | null;
    valuation_note: string;
    tax_note: string;
  };
  due_diligence_items: DueDiligenceItem[];
  analysis_status: Record<"property" | "location" | "terrain" | "commute" | "valuation" | "loan" | "holding" | "tax" | "decision", PropertyCaseStatus>;
  analysis_summary: string[];
  readiness: {
    draft_ready: boolean;
    compare_ready: boolean;
    print_ready: boolean;
    print_notice: string | null;
    due_diligence: DueDiligenceReadiness;
    missing_required: string[];
    unavailable_or_incomplete: string[];
  };
};

export function buildPropertyCaseDraft(input: PropertyCaseDraftInput, now = new Date().toISOString()): PropertyCaseDraft {
  const address = input.address?.trim() || buildAddress(input.inputs);
  const caseName = input.caseName?.trim() || "";
  const listingPrice = finiteNumber(input.listingPrice)
    ?? finiteNumber(input.userEstimatedValue)
    ?? input.valuation?.price_range.mid
    ?? input.loan?.property_price_wan
    ?? input.holding?.property_price_wan
    ?? null;
  const locationStatus = input.location ? dataQualityToStatus(input.location.data_quality.status) : "missing";
  const terrainStatus = input.terrainRisk ? terrainToStatus(input.terrainRisk) : "missing";
  const commuteStatus: PropertyCaseStatus = "missing";
  const dueDiligenceItems = normalizeDueDiligenceItems(input.dueDiligenceItems);
  const dueDiligenceReadiness = buildDueDiligenceReadiness(dueDiligenceItems, {
    decision_review_summary: input.decisionReviewSummary,
    decision_open_questions: input.decisionOpenQuestions,
    decision_next_step: input.decisionNextStep,
  });
  const analysisStatus = {
    property: input.propertySearch ? "completed" : "missing",
    location: locationStatus,
    terrain: terrainStatus,
    commute: commuteStatus,
    valuation: input.valuation ? "completed" : "missing",
    loan: input.loan ? "completed" : "missing",
    holding: input.holding ? "completed" : "missing",
    tax: input.taxOracle ? "completed" : "missing",
    decision: input.riskSummary ? "completed" : "missing",
  } satisfies PropertyCaseDraft["analysis_status"];
  const missingRequired = requiredMissing(caseName, address, listingPrice, analysisStatus);
  const unavailableOrIncomplete = Object.entries(analysisStatus)
    .filter(([, status]) => status === "unavailable" || status === "incomplete")
    .map(([key]) => key);
  const hasBasicCaseInfo = Boolean(caseName && address);
  const hasLocationOrRiskResultOrStatus = Boolean(input.location || input.terrainRisk || analysisStatus.location || analysisStatus.terrain);
  const hasPriceOrFinanceResultOrStatus = Boolean(
    listingPrice ||
    input.valuation ||
    input.loan ||
    input.holding ||
    input.taxOracle ||
    analysisStatus.valuation ||
    analysisStatus.loan ||
    analysisStatus.holding ||
    analysisStatus.tax,
  );
  const printReady = hasBasicCaseInfo && hasLocationOrRiskResultOrStatus && hasPriceOrFinanceResultOrStatus;

  return {
    case_id: stableCaseId(caseName, address),
    case_name: caseName,
    decision_status: input.decisionStatus ?? "draft",
    decision_note: input.decisionNote?.trim() || "",
    decision_review_summary: safeText(input.decisionReviewSummary),
    decision_open_questions: safeText(input.decisionOpenQuestions),
    decision_next_step: safeText(input.decisionNextStep),
    last_reviewed_at: now,
    created_at: now,
    updated_at: now,
    property_input: {
      address,
      listing_price: listingPrice,
      building_area: finiteNumber(input.floorAreaPing) ?? finiteNumber(input.inputs.area_ping),
      property_type: input.propertyType?.trim() || input.inputs.building_type || "",
      building_age: finiteNumber(input.buildingAgeYears) ?? finiteNumber(input.inputs.building_age_years),
      floor: finiteNumber(input.inputs.floor),
      total_floors: null,
      parking_type: "",
      parking_price: null,
      notes: input.notes?.trim() || "",
    },
    location_input: {
      address_status: address ? "completed" : "missing",
      location_analysis_status: locationStatus,
      terrain_analysis_status: terrainStatus,
      commute_analysis_status: commuteStatus,
      map_available: Boolean(input.location?.resolved_location),
    },
    financial_input: {
      down_payment: finiteNumber(input.downPayment) ?? input.loan?.down_payment_wan ?? null,
      loan_amount: finiteNumber(input.loanAmount) ?? input.loan?.loan_amount_wan ?? null,
      loan_years: finiteNumber(input.loanYears) ?? input.loan?.loan_years ?? null,
      interest_rate: finiteNumber(input.loanRate) ?? input.loan?.annual_interest_rate ?? null,
      funding_mode: input.fundingMode ?? null,
      funding_value: finiteNumber(input.fundingValue),
      estimated_buyer_costs: finiteNumberOrZero(input.estimatedBuyerCosts),
      renovation_reserve: finiteNumberOrZero(input.renovationReserve),
      available_liquid_cash: finiteNumberOrZero(input.availableLiquidCash),
      grace_period_months: input.loan?.grace_period_years ? input.loan.grace_period_years * 12 : null,
      monthly_income: finiteNumberOrZero(input.monthlyHouseholdIncome) ?? input.loan?.monthly_income_wan ?? input.holding?.input.monthly_income_wan ?? null,
      other_monthly_debt: finiteNumberOrZero(input.monthlyFixedObligations),
      monthly_ownership_reserve: finiteNumberOrZero(input.monthlyOwnershipReserve),
      estimated_holding_cost: finiteNumber(input.estimatedMonthlyPayment) ?? input.holding?.monthly_total_holding_cost ?? null,
    },
    valuation_tax_input: {
      user_estimated_value: finiteNumber(input.userEstimatedValue),
      user_estimated_tax_cost: finiteNumber(input.userEstimatedTaxCost),
      valuation_note: input.valuationNote?.trim() || "",
      tax_note: input.taxNote?.trim() || "",
    },
    due_diligence_items: dueDiligenceItems,
    analysis_status: analysisStatus,
    analysis_summary: buildAnalysisSummary(input, analysisStatus),
    readiness: {
      draft_ready: hasBasicCaseInfo,
      compare_ready: Boolean(hasBasicCaseInfo && listingPrice),
      print_ready: printReady,
      print_notice: printReady ? PARTIAL_CASE_PRINT_NOTICE : null,
      due_diligence: dueDiligenceReadiness.readiness,
      missing_required: missingRequired,
      unavailable_or_incomplete: unavailableOrIncomplete,
    },
  };
}

function buildAddress(inputs: ValuationInputs): string {
  return [inputs.city, inputs.district, inputs.road].map((value) => String(value || "").trim()).filter(Boolean).join("");
}

function stableCaseId(caseName: string, address: string): string {
  const base = `${caseName}|${address}`.trim() || "property-case";
  let hash = 0;
  for (const char of base) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return `case-${hash.toString(16)}`;
}

function finiteNumber(value: unknown): number | null {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function finiteNumberOrZero(value: unknown): number | null {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function dataQualityToStatus(status?: string): PropertyCaseStatus {
  if (status === "good") return "completed";
  if (status === "limited") return "incomplete";
  if (status === "unavailable") return "unavailable";
  return "missing";
}

function terrainToStatus(terrain: TerrainRiskResult): PropertyCaseStatus {
  if (terrain.data_quality.status === "unavailable" || terrain.overall.level === "unknown") return "unavailable";
  if (terrain.data_quality.status === "limited") return "incomplete";
  return "completed";
}

function requiredMissing(
  caseName: string,
  address: string,
  listingPrice: number | null,
  _status: PropertyCaseDraft["analysis_status"],
): string[] {
  const missing: string[] = [];
  if (!caseName) missing.push("case_name");
  if (!address) missing.push("address");
  if (!listingPrice) missing.push("listing_price");
  return missing;
}

function buildAnalysisSummary(input: PropertyCaseDraftInput, status: PropertyCaseDraft["analysis_status"]): string[] {
  const rows: string[] = [];
  if (input.valuation) rows.push(`估價中位數 ${input.valuation.price_range.mid.toLocaleString()} 萬`);
  if (input.loan) rows.push(`貸款月付 ${input.loan.monthly_payment.toLocaleString()} 元`);
  if (input.holding) rows.push(`持有成本 ${input.holding.monthly_total_holding_cost.toLocaleString()} 元/月`);
  if (input.location) rows.push(`位置分析 ${status.location}`);
  if (input.terrainRisk) rows.push(`地勢風險 ${input.terrainRisk.overall.label}`);
  if (input.dueDiligenceItems?.some((item) => item.status && item.status !== "not_started")) rows.push("Due diligence review board has user-entered checklist progress.");
  if (!rows.length) rows.push("尚未完成可比較的分析");
  return rows;
}

function safeText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
