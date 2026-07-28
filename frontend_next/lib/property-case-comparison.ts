import type { SavedCase } from "@/lib/case-storage";

export type PropertyCaseComparisonRow = {
  caseId: string;
  caseName: string;
  addressSummary: string;
  decisionStatus: string;
  listingPrice: number | null;
  userEstimatedValue: number | null;
  initialCashNeeded: number | null;
  monthlyPayment: number | null;
  monthlyHoldingCost: number | null;
  financialStatus: string;
  dueDiligenceReadiness: string;
  viewingOfferReadiness: string;
  timelineReadiness: string;
  missingDataCount: number;
};

export type PropertyCaseComparisonModel = {
  rows: PropertyCaseComparisonRow[];
  canCompare: boolean;
  message: string;
};

export function buildPropertyCaseComparisonModel(savedCases: SavedCase[], selectedIds: string[]): PropertyCaseComparisonModel {
  const rows = savedCases.filter((item) => selectedIds.includes(item.id)).slice(0, 3).map(toRow);
  return {
    rows,
    canCompare: rows.length >= 2 && rows.length <= 3,
    message: rows.length < 2 ? "請明確勾選 2–3 個已儲存案件後比較。" : "資料不足，僅比較已知欄位；比較不產生排名或購買建議。",
  };
}

function toRow(saved: SavedCase): PropertyCaseComparisonRow {
  const propertyPrice = positive(saved.inputSummary.propertyPrice);
  const userEstimatedValue = null;
  const initialCashNeeded = positive(saved.data.loan?.down_payment_wan);
  const monthlyPayment = positive(saved.data.loan?.monthly_payment);
  const monthlyHoldingCost = positive(saved.data.holdingCost?.monthly_total_holding_cost);
  const values = [propertyPrice, userEstimatedValue, initialCashNeeded, monthlyPayment, monthlyHoldingCost];
  return {
    caseId: saved.id,
    caseName: saved.title.trim() || "未命名案件",
    addressSummary: [saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].filter((value) => value?.trim()).join("") || "未提供地址／識別",
    decisionStatus: "未提供",
    listingPrice: propertyPrice,
    userEstimatedValue,
    initialCashNeeded,
    monthlyPayment,
    monthlyHoldingCost,
    financialStatus: monthlyPayment !== null || monthlyHoldingCost !== null ? "部分提供" : "尚未評估",
    dueDiligenceReadiness: "目前儲存資料未提供",
    viewingOfferReadiness: "目前儲存資料未提供",
    timelineReadiness: "目前儲存資料未提供",
    missingDataCount: values.filter((value) => value === null).length + 3,
  };
}

function positive(value: number | null | undefined): number | null { return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null; }
