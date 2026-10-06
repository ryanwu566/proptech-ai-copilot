import type { HoldingCostResult, LoanCalculationResult, TaxResult, ValuationResult } from "@/lib/api";
import { getValuationDisplayState } from "@/lib/valuation-result-state";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";
import type { ExperienceLocale } from "@/lib/experience-i18n";

export type PriceJourneyDisplayStatus = "not_started" | "loading" | "available" | "demo" | "no_data" | "unavailable" | "partial";
export type AffordabilityDisplayStatus = "not_started" | "available" | "unavailable" | "partial" | "unknown";
export type AffordabilityToolId = "holding" | "tax";

export function priceJourneyStatusLabel(status: PriceJourneyDisplayStatus, locale: ExperienceLocale): string {
  const labels: Record<ExperienceLocale, Record<PriceJourneyDisplayStatus, string>> = {
    "zh-TW": { not_started: "尚未執行", loading: "分析中", available: "已有估價證據", demo: "示範資料", no_data: "官方資料不足", unavailable: "已嘗試，目前無法取得", partial: "部分證據可用" },
    en: { not_started: "Not run", loading: "Analyzing", available: "Valuation evidence available", demo: "Demo data", no_data: "Insufficient official data", unavailable: "Attempted; currently unavailable", partial: "Partial evidence available" },
    ja: { not_started: "未実行", loading: "分析中", available: "評価根拠あり", demo: "デモデータ", no_data: "公的データ不足", unavailable: "実行済み・現在利用不可", partial: "一部の根拠あり" },
    ko: { not_started: "실행 전", loading: "분석 중", available: "평가 근거 있음", demo: "데모 데이터", no_data: "공식 데이터 부족", unavailable: "시도됨 · 현재 이용 불가", partial: "일부 근거 있음" },
  };
  return labels[locale][status];
}

export type JourneyPriceContext = {
  propertyContext: JourneyPropertyContext;
  askingPriceWan?: number;
  propertyAreaPing?: number;
  officialValuationStatus: PriceJourneyDisplayStatus;
  officialEstimateWan?: number;
  estimateLowWan?: number;
  estimateHighWan?: number;
  officialComparableCount?: number;
  loanTransferAvailable: boolean;
  caseTransferAvailable: boolean;
};

export type JourneyAffordabilityContext = {
  propertyPriceWan?: number;
  loanStatus: AffordabilityDisplayStatus;
  downPaymentWan?: number;
  loanAmountWan?: number;
  monthlyPayment?: number;
  incomeBurdenRatio?: number;
  holdingCostStatus: AffordabilityDisplayStatus;
  monthlyHoldingCost?: number;
  annualHoldingCost?: number;
  taxOracleStatus: "not_started" | "eligible" | "manual_review" | "not_eligible" | "unavailable";
  missingDataLabels: string[];
};

export type PriceTrustStatusItem = {
  id: "property" | "valuation" | "comparables" | "actions";
  label: string;
  status: PriceJourneyDisplayStatus;
  text: string;
};

export type AffordabilityStatusItem = {
  id: "price" | "loan" | "holding" | "tax";
  label: string;
  status: AffordabilityDisplayStatus | JourneyAffordabilityContext["taxOracleStatus"];
  text: string;
};

function finitePositive(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function valuationStatus(result: ValuationResult | undefined): PriceJourneyDisplayStatus {
  if (!result) return "not_started";
  const state = getValuationDisplayState(result);
  if (state.kind === "demo") return "demo";
  if (state.kind === "no_data") return "no_data";
  if (state.kind === "unavailable") return "unavailable";
  if (state.kind === "error") return "unavailable";
  if (state.kind === "partial") return "partial";
  return "available";
}

function actionAvailable(result: ValuationResult | undefined): boolean {
  return result ? getValuationDisplayState(result).actionable : false;
}

export function getSafePriceContext(input: { propertyContext: JourneyPropertyContext; result?: ValuationResult; askingPriceWan?: number; valuationStatus?: PriceJourneyDisplayStatus }): JourneyPriceContext {
  const actionable = actionAvailable(input.result);
  const result = input.result;
  const askingPriceWan = finitePositive(input.askingPriceWan) ? input.askingPriceWan : input.propertyContext.askingPriceWan;
  return {
    propertyContext: input.propertyContext,
    ...(finitePositive(askingPriceWan) ? { askingPriceWan } : {}),
    ...(finitePositive(input.propertyContext.areaPing) ? { propertyAreaPing: input.propertyContext.areaPing } : {}),
    officialValuationStatus: result ? valuationStatus(result) : input.valuationStatus ?? "not_started",
    ...(actionable && result && finitePositive(result.estimate_total_price) ? { officialEstimateWan: result.estimate_total_price } : {}),
    ...(actionable && result && finitePositive(result.price_range.low) ? { estimateLowWan: result.price_range.low } : {}),
    ...(actionable && result && finitePositive(result.price_range.high) ? { estimateHighWan: result.price_range.high } : {}),
    ...(actionable && result && Number.isInteger(result.official_same_road_count) ? { officialComparableCount: result.official_same_road_count } : {}),
    loanTransferAvailable: actionable,
    caseTransferAvailable: actionable,
  };
}

export function buildPriceTrustStatusItems(context: JourneyPriceContext, result?: ValuationResult): PriceTrustStatusItem[] {
  const actionable = actionAvailable(result);
  const propertyStatus: PriceJourneyDisplayStatus = context.propertyContext.selectionStatus === "not_selected" ? "not_started" : context.propertyContext.selectionStatus === "partial" ? "partial" : "available";
  const comparableText = context.officialComparableCount && context.officialComparableCount > 0 ? `官方可比成交 ${context.officialComparableCount} 筆` : result ? "官方可比成交資料不足" : "尚未取得官方可比成交";
  return [
    { id: "property", label: "物件條件", status: propertyStatus, text: propertyStatus === "not_started" ? "未提供" : propertyStatus === "partial" ? "部分提供" : "已輸入" },
    { id: "valuation", label: "估價資料狀態", status: context.officialValuationStatus, text: context.officialValuationStatus === "available" ? "官方資料可用" : context.officialValuationStatus === "partial" ? "可比成交可查閱，估價信心不足" : context.officialValuationStatus === "demo" ? "展示資料" : context.officialValuationStatus === "no_data" ? "資料不足" : context.officialValuationStatus === "unavailable" ? "資料暫時無法取得" : "尚未估價" },
    { id: "comparables", label: "官方可比成交", status: context.officialValuationStatus, text: comparableText },
    { id: "actions", label: "後續操作狀態", status: actionable ? "available" : "not_started", text: actionable ? "可手動帶入貸款或儲存案件" : "尚不可帶入" },
  ];
}

export function buildPriceDecisionSnapshot(context: JourneyPriceContext, result?: ValuationResult) {
  const actionable = actionAvailable(result);
  return {
    title: "價格資料概況",
    description: "只整理目前已知價格與資料狀態，不構成出價或購買建議。",
    askingPriceWan: context.askingPriceWan,
    officialValuationStatus: context.officialValuationStatus,
    officialEstimateWan: actionable ? context.officialEstimateWan : undefined,
    estimateLowWan: actionable ? context.estimateLowWan : undefined,
    estimateHighWan: actionable ? context.estimateHighWan : undefined,
    officialComparableCount: actionable ? context.officialComparableCount : undefined,
    actionsAvailable: actionable,
  };
}

function resultStatus(result: LoanCalculationResult | HoldingCostResult | undefined): AffordabilityDisplayStatus {
  return result ? "available" : "not_started";
}

export function buildAffordabilityStatusItems(context: JourneyAffordabilityContext): AffordabilityStatusItem[] {
  return [
    { id: "price", label: "房屋價格", status: context.propertyPriceWan ? "available" : "not_started", text: context.propertyPriceWan ? "已提供價格" : "未提供" },
    { id: "loan", label: "貸款試算", status: context.loanStatus, text: context.loanStatus === "available" ? "試算可用" : context.loanStatus === "unavailable" ? "試算暫時無法完成" : "尚未試算" },
    { id: "holding", label: "持有成本", status: context.holdingCostStatus, text: context.holdingCostStatus === "available" ? "試算可用" : context.holdingCostStatus === "partial" ? "部分資料" : context.holdingCostStatus === "unavailable" ? "試算暫時無法完成" : "尚未試算" },
    { id: "tax", label: "稅務快篩", status: context.taxOracleStatus, text: context.taxOracleStatus === "eligible" ? "eligible" : context.taxOracleStatus === "manual_review" ? "需人工複核" : context.taxOracleStatus === "not_eligible" ? "有阻擋項目" : context.taxOracleStatus === "unavailable" ? "暫時無法取得" : "尚未執行" },
  ];
}

export function buildAffordabilityDecisionSnapshot(context: JourneyAffordabilityContext) {
  return {
    title: "資金與稅務資料概況",
    description: "各項試算與快篩彼此獨立，只整理目前已知數據，不代表核貸、稅務或購買結論。",
    propertyPriceWan: context.propertyPriceWan,
    downPaymentWan: context.downPaymentWan,
    loanAmountWan: context.loanAmountWan,
    monthlyPayment: context.monthlyPayment,
    monthlyHoldingCost: context.monthlyHoldingCost,
    incomeBurdenRatio: context.incomeBurdenRatio,
    taxOracleStatus: context.taxOracleStatus,
    missingDataLabels: context.missingDataLabels,
  };
}

export function buildJourneyAffordabilityContext(input: { propertyPriceWan?: number; loanResult?: LoanCalculationResult; holdingResult?: HoldingCostResult; taxResult?: TaxResult }): JourneyAffordabilityContext {
  const missingDataLabels: string[] = [];
  if (!finitePositive(input.propertyPriceWan)) missingDataLabels.push("尚未提供房屋總價");
  if (!input.loanResult) missingDataLabels.push("尚未試算貸款");
  if (input.loanResult?.monthly_income_wan === null) missingDataLabels.push("未輸入收入");
  if (!input.holdingResult) missingDataLabels.push("尚未試算持有成本");
  if (!input.taxResult) missingDataLabels.push("尚未執行 TaxOracle");
  return {
    ...(finitePositive(input.propertyPriceWan) ? { propertyPriceWan: input.propertyPriceWan } : {}),
    loanStatus: resultStatus(input.loanResult),
    ...(input.loanResult && finitePositive(input.loanResult.down_payment_wan) ? { downPaymentWan: input.loanResult.down_payment_wan } : {}),
    ...(input.loanResult && finitePositive(input.loanResult.loan_amount_wan) ? { loanAmountWan: input.loanResult.loan_amount_wan } : {}),
    ...(input.loanResult && finitePositive(input.loanResult.monthly_payment) ? { monthlyPayment: input.loanResult.monthly_payment } : {}),
    ...(input.loanResult && input.loanResult.income_burden_ratio !== null && Number.isFinite(input.loanResult.income_burden_ratio) ? { incomeBurdenRatio: input.loanResult.income_burden_ratio } : {}),
    holdingCostStatus: input.holdingResult ? (finitePositive(input.holdingResult.monthly_total_holding_cost) ? "available" : "partial") : "not_started",
    ...(input.holdingResult && finitePositive(input.holdingResult.monthly_total_holding_cost) ? { monthlyHoldingCost: input.holdingResult.monthly_total_holding_cost } : {}),
    ...(input.holdingResult && finitePositive(input.holdingResult.annual_total_holding_cost) ? { annualHoldingCost: input.holdingResult.annual_total_holding_cost } : {}),
    taxOracleStatus: input.taxResult?.eligibility_status ?? "not_started",
    missingDataLabels,
  };
}

export function addVisitedAffordabilityTool(visited: readonly AffordabilityToolId[], tool: AffordabilityToolId): AffordabilityToolId[] {
  return visited.includes(tool) ? [...visited] : [...visited, tool];
}
