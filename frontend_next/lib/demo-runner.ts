import { API_BASE, api, type HoldingCostResult, type LoanCalculationResult, type LocationInsightResult, type PropertySearchResult, type TaxResult, type ValuationResult, type ValuationTrendResult } from "@/lib/api";
import { buildRiskSummary, type RiskSummary } from "@/lib/risk-summary";
import type { ValuationInputs } from "@/lib/valuation-share";

export const START_GUIDED_DEMO_EVENT = "proptech:start-guided-demo";
export const GUIDED_DEMO_RESULT_EVENT = "proptech:guided-demo-result";
export const GUIDED_DEMO_PENDING_KEY = "proptech:guided-demo-pending";

export const DEMO_INPUT = {
  city: "台北市", district: "大安區", road: "和平東路二段", budgetMin: 1500, budgetMax: 2500,
  areaMin: 25, areaMax: 35, buildingType: "住宅大樓", propertyPrice: 2000, areaPing: 30,
  annualInterestRate: 2.2, loanYears: 30, downPaymentRatio: 0.2, monthlyIncome: 12,
  managementFeePerPing: 80, repairReservePerPing: 50, radiusM: 800,
} as const;

export type DemoPreflightStatus = "checking" | "ready" | "waking" | "failed";
export type DemoStepId = "propertySearch" | "valuation" | "trend" | "loan" | "holdingCost" | "locationInsight" | "riskSummary";
export type DemoStepStatus = "queued" | "running" | "done" | "failed" | "skipped";
export type DemoStepState = { id: DemoStepId; label: string; endpoint: string; status: DemoStepStatus; summary?: string; error?: string; recovery?: string };
export type DemoResults = {
  inputs: ValuationInputs;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holdingCost?: HoldingCostResult;
  locationInsight?: LocationInsightResult;
  riskSummary?: RiskSummary;
  taxOracle?: TaxResult;
};

export const DEMO_STEPS: Array<Pick<DemoStepState, "id" | "label" | "endpoint">> = [
  { id: "propertySearch", label: "搜尋找房", endpoint: "POST /valuation/property-search" },
  { id: "valuation", label: "實價估價", endpoint: "POST /valuation/estimate" },
  { id: "trend", label: "市場趨勢", endpoint: "POST /valuation/trend" },
  { id: "loan", label: "貸款月付", endpoint: "POST /loan/calculate" },
  { id: "holdingCost", label: "持有成本", endpoint: "POST /holding-cost/calculate" },
  { id: "locationInsight", label: "區位分析", endpoint: "POST /location/insight" },
  { id: "riskSummary", label: "風險總評", endpoint: "前端 rule-based" },
];

export async function runDemoPreflight(onStatus: (status: DemoPreflightStatus, message: string) => void): Promise<void> {
  onStatus("checking", "正在確認 API 設定與後端服務狀態。");
  if (!API_BASE) {
    const message = "未設定 API base URL，請確認 NEXT_PUBLIC_API_BASE_URL。";
    onStatus("failed", message);
    throw new DemoPreflightError(message);
  }
  onStatus("waking", "後端服務可能正在喚醒，請稍候。");
  try {
    await api.valuationDataStatus();
    onStatus("ready", "API 連線正常，可以開始 Demo。");
  } catch (caught) {
    const message = `API 暫時無法連線，請稍後重試。${errorMessage(caught)}`;
    onStatus("failed", message);
    throw new DemoPreflightError(message);
  }
}

export async function runGuidedDemo(options: {
  startIndex?: number;
  existing?: DemoResults;
  isCancelled: () => boolean;
  onStep: (index: number, state: DemoStepState) => void;
  onResults: (results: DemoResults) => void;
}): Promise<DemoResults> {
  const inputs: ValuationInputs = { city: DEMO_INPUT.city, district: DEMO_INPUT.district, road: DEMO_INPUT.road, building_type: DEMO_INPUT.buildingType, area_ping: DEMO_INPUT.areaPing, building_age_years: 15, floor: 8 };
  const results: DemoResults = { inputs, ...options.existing };
  for (let index = options.startIndex ?? 0; index < DEMO_STEPS.length; index += 1) {
    if (options.isCancelled()) return results;
    const step = DEMO_STEPS[index];
    options.onStep(index, { ...step, status: "running" });
    try {
      const summary = await runStep(step.id, results);
      if (options.isCancelled()) return results;
      options.onResults({ ...results });
      options.onStep(index, { ...step, status: "done", summary });
    } catch (caught) {
      const error = friendlyError(step.id, caught);
      options.onStep(index, { ...step, status: "failed", error, recovery: recoveryHint(step.id) });
      for (let skipped = index + 1; skipped < DEMO_STEPS.length; skipped += 1) {
        options.onStep(skipped, { ...DEMO_STEPS[skipped], status: "skipped", summary: "等待前一步成功後再繼續。" });
      }
      throw new DemoRunError(index, error, results);
    }
  }
  return results;
}

export async function runOptionalTaxOracleDemo(): Promise<TaxResult> {
  const cases = await api.demoCases();
  const lowRisk = cases.find((item) => /LOW/i.test(item.case_id)) ?? cases[0];
  if (!lowRisk) throw new Error("目前沒有可使用的 TaxOracle 示範案件。");
  return api.runTaxOracleCase(lowRisk);
}

export class DemoPreflightError extends Error {}
export class DemoRunError extends Error {
  constructor(public stepIndex: number, message: string, public results: DemoResults) { super(message); }
}

async function runStep(step: DemoStepId, results: DemoResults): Promise<string> {
  if (step === "propertySearch") {
    results.propertySearch = await api.propertySearch({ city: DEMO_INPUT.city, districts: [DEMO_INPUT.district], budget_min: DEMO_INPUT.budgetMin, budget_max: DEMO_INPUT.budgetMax, area_ping_min: DEMO_INPUT.areaMin, area_ping_max: DEMO_INPUT.areaMax, building_type: DEMO_INPUT.buildingType, limit: 50 });
    if (!results.propertySearch.summary.matched_count) throw new Error("NO_PROPERTY_RESULTS");
    return `找到 ${results.propertySearch.summary.matched_count} 筆符合條件的成交資料`;
  }
  const valuationPayload = { city: DEMO_INPUT.city, district: DEMO_INPUT.district, road: DEMO_INPUT.road, address_text: "", building_type: DEMO_INPUT.buildingType, area_ping: DEMO_INPUT.areaPing, building_age_years: 15, floor: 8 };
  if (step === "valuation") {
    results.valuation = await api.valuation(valuationPayload);
    return `估價中位數 ${results.valuation.price_range.mid.toLocaleString()} 萬`;
  }
  if (step === "trend") {
    results.trend = await api.valuationTrend({ ...valuationPayload, horizon_months: [6, 12, 36] });
    return `取得 ${results.trend.monthly_series.length} 期趨勢資料`;
  }
  if (step === "loan") {
    results.loan = await api.loanCalculate({ property_price: DEMO_INPUT.propertyPrice, down_payment_ratio: DEMO_INPUT.downPaymentRatio, annual_interest_rate: DEMO_INPUT.annualInterestRate, loan_years: DEMO_INPUT.loanYears, grace_period_years: 0, monthly_income: DEMO_INPUT.monthlyIncome, include_sensitivity: true });
    return `每月月付 ${results.loan.monthly_payment.toLocaleString()} 元`;
  }
  if (step === "holdingCost") {
    if (!results.loan) throw new Error("MISSING_LOAN");
    results.holdingCost = await api.holdingCostCalculate({ property_price: DEMO_INPUT.propertyPrice, loan_monthly_payment: results.loan.monthly_payment, monthly_income: DEMO_INPUT.monthlyIncome, area_ping: DEMO_INPUT.areaPing, management_fee_per_ping: DEMO_INPUT.managementFeePerPing, repair_reserve_per_ping: DEMO_INPUT.repairReservePerPing, annual_home_tax_rate: 0.0012, annual_land_tax_rate: 0.001, annual_insurance: 3000, include_tax_estimate: true });
    return `每月持有成本 ${results.holdingCost.monthly_total_holding_cost.toLocaleString()} 元`;
  }
  if (step === "locationInsight") {
    results.locationInsight = await api.locationInsight({ city: DEMO_INPUT.city, district: DEMO_INPUT.district, road: DEMO_INPUT.road, radius_m: DEMO_INPUT.radiusM, property_price: DEMO_INPUT.propertyPrice, area_ping: DEMO_INPUT.areaPing, building_type: DEMO_INPUT.buildingType, use_existing_poi_sources: true });
    if (results.locationInsight.data_quality.status === "unavailable") throw new Error("LOCATION_UNAVAILABLE");
    return `區位分數 ${results.locationInsight.location_score ?? "資料不足"}`;
  }
  results.riskSummary = buildRiskSummary({ propertySearch: results.propertySearch, valuation: results.valuation, trend: results.trend, loan: results.loan, holding: results.holdingCost, location: results.locationInsight });
  return `${results.riskSummary.overallLabel}，總分 ${results.riskSummary.overallScore ?? "資料不足"}`;
}

function friendlyError(step: DemoStepId, caught: unknown): string {
  const message = errorMessage(caught);
  if (message === "NO_PROPERTY_RESULTS") return "找房資料不足，示範條件目前沒有符合結果。";
  if (message === "LOCATION_UNAVAILABLE") return "區位 API 暫時無法定位此路段。";
  return `${DEMO_STEPS.find((item) => item.id === step)?.label ?? "此步驟"}無法完成：${message || "API 暫時無回應"}`;
}

function recoveryHint(step: DemoStepId): string {
  if (step === "propertySearch") return "請放寬預算或改用手動流程，亦可稍後重試。";
  if (step === "valuation" || step === "trend") return "可能是該路段可比成交不足，可改用手動估價條件。";
  if (step === "locationInsight") return "請改用手動輸入完整地址，或稍後重試。";
  return "請稍後重試；已完成的步驟會保留。";
}

function errorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught ?? "");
}
