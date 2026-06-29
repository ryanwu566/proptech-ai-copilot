import type { PropertyCaseDraft, PropertyCaseStatus } from "@/lib/property-case";

export type PropertyCaseReadinessState = "ready" | "needs_data" | "unavailable";

export type PropertyCaseReadiness = {
  state: PropertyCaseReadinessState;
  label: string;
  primaryMessage: string;
  nextSteps: string[];
  safeWarnings: string[];
  statusLabels: Record<PropertyCaseStatus, string>;
};

export function buildPropertyCaseReadiness(draft: PropertyCaseDraft): PropertyCaseReadiness {
  const safeWarnings = [
    ...draft.readiness.unavailable_or_incomplete.map((key) => `${moduleLabel(key)} 資料不足或暫時不可用，不代表沒有風險。`),
  ];
  if (draft.readiness.missing_required.length > 0) {
    return {
      state: "needs_data",
      label: "補資料後再判斷",
      primaryMessage: "目前案件可建立草稿，但還不適合直接比較或輸出完整報告。",
      nextSteps: draft.readiness.missing_required.slice(0, 4).map((key) => `補齊 ${moduleLabel(key)}`),
      safeWarnings,
      statusLabels,
    };
  }
  if (draft.readiness.unavailable_or_incomplete.length > 0) {
    return {
      state: "unavailable",
      label: "先確認資料可用性",
      primaryMessage: "部分分析資料不足或暫時不可用，請先確認再用於比較。",
      nextSteps: draft.readiness.unavailable_or_incomplete.slice(0, 4).map((key) => `重新檢查 ${moduleLabel(key)}`),
      safeWarnings,
      statusLabels,
    };
  }
  return {
    state: "ready",
    label: "可保存並比較",
    primaryMessage: "案件已具備基本物件、位置、資金與風險摘要，可進一步保存、比較或列印報告。",
    nextSteps: ["保存目前案件", "選擇 2 到 3 個案件比較", "列印或另存決策報告"],
    safeWarnings,
    statusLabels,
  };
}

export function moduleLabel(key: string): string {
  return {
    case_name: "案件名稱",
    address: "物件地址",
    listing_price: "價格資訊",
    property: "Property Finder",
    location: "Location Insight",
    terrain: "Terrain Risk",
    commute: "通勤資訊",
    valuation: "估價",
    loan: "貸款試算",
    holding: "持有成本",
    tax: "TaxOracle",
    decision: "風險摘要",
  }[key] ?? key;
}

const statusLabels: Record<PropertyCaseStatus, string> = {
  completed: "已完成",
  missing: "尚未完成",
  incomplete: "資料不足",
  unavailable: "暫時不可用",
};
