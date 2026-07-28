import type { JourneyPropertyContext } from "@/lib/location-market-journey";
import type { JourneyAffordabilityContext, JourneyPriceContext } from "@/lib/price-affordability-journey";

export type JourneyDecisionContext = {
  propertyContext: JourneyPropertyContext;
  priceStatus: JourneyPriceContext["officialValuationStatus"];
  officialValuationAvailable: boolean;
  affordabilityStatus: "not_started" | "partial" | "available";
  loanKnown: boolean;
  holdingKnown: boolean;
  taxStatus: JourneyAffordabilityContext["taxOracleStatus"];
  candidateCaseId?: string;
  selectedSavedCaseIds: readonly string[];
  missingDataLabels: readonly string[];
};

export function buildJourneyDecisionContext(input: {
  propertyContext: JourneyPropertyContext;
  priceContext: JourneyPriceContext;
  affordabilityContext: JourneyAffordabilityContext;
  candidateCaseId?: string;
  selectedSavedCaseIds?: readonly string[];
}): JourneyDecisionContext {
  const affordabilityStatus = input.affordabilityContext.loanStatus === "available" || input.affordabilityContext.holdingCostStatus === "available"
    ? input.affordabilityContext.loanStatus === "available" && input.affordabilityContext.holdingCostStatus === "available" && input.affordabilityContext.taxOracleStatus !== "not_started" ? "available" : "partial"
    : "not_started";
  return {
    propertyContext: input.propertyContext,
    priceStatus: input.priceContext.officialValuationStatus,
    officialValuationAvailable: input.priceContext.loanTransferAvailable,
    affordabilityStatus,
    loanKnown: input.affordabilityContext.loanStatus === "available",
    holdingKnown: input.affordabilityContext.holdingCostStatus === "available",
    taxStatus: input.affordabilityContext.taxOracleStatus,
    ...(input.candidateCaseId ? { candidateCaseId: input.candidateCaseId } : {}),
    selectedSavedCaseIds: [...(input.selectedSavedCaseIds ?? [])],
    missingDataLabels: [...input.affordabilityContext.missingDataLabels],
  };
}

export type DecisionAttentionCategory = "blocked" | "missing" | "unknown" | "partial" | "pending";

export type DecisionAttentionItem = {
  id: string;
  category: DecisionAttentionCategory;
  label: string;
  status: string;
  action: "property" | "price" | "affordability" | "case";
};

export function buildDecisionAttentionItems(context: JourneyDecisionContext): DecisionAttentionItem[] {
  const items: DecisionAttentionItem[] = [];
  if (context.taxStatus === "not_eligible") items.push({ id: "tax-blocked", category: "blocked", label: "TaxOracle 有待人工複核項目", status: "有阻擋項目", action: "affordability" });
  if (context.propertyContext.selectionStatus === "not_selected") items.push({ id: "property-missing", category: "missing", label: "物件脈絡", status: "尚未提供", action: "property" });
  if (!context.officialValuationAvailable) items.push({ id: "valuation-unknown", category: context.priceStatus === "unavailable" ? "unknown" : "missing", label: "官方估價證據", status: context.priceStatus === "unavailable" ? "資料暫時無法取得" : "尚無可採取行動的官方估價", action: "price" });
  if (!context.loanKnown) items.push({ id: "loan-pending", category: "pending", label: "貸款試算", status: "尚未完成貸款試算", action: "affordability" });
  if (!context.holdingKnown) items.push({ id: "holding-pending", category: "pending", label: "持有成本", status: "尚未完成持有成本試算", action: "affordability" });
  if (context.taxStatus === "not_started") items.push({ id: "tax-pending", category: "pending", label: "TaxOracle", status: "尚未執行", action: "affordability" });
  if (!context.candidateCaseId) items.push({ id: "case-missing", category: "missing", label: "案件工作區", status: "尚未建立案件", action: "case" });
  if (context.affordabilityStatus === "partial") items.push({ id: "affordability-partial", category: "partial", label: "資金與稅務", status: "部分資料", action: "affordability" });
  return items;
}

export function attentionCategoryLabel(category: DecisionAttentionCategory): string {
  return { blocked: "有阻擋項目", missing: "尚未提供", unknown: "尚未評估", partial: "部分資料", pending: "等待處理" }[category];
}
