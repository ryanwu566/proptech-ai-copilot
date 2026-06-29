import type { PropertyCaseDraft, PropertyCaseStatus } from "@/lib/property-case";
import { PARTIAL_CASE_PRINT_NOTICE } from "@/lib/property-case";

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
    ...draft.readiness.unavailable_or_incomplete.map(
      (key) => `${moduleLabel(key)} 資料暫時不可用或不完整，不能推論為低風險或已完成。`,
    ),
  ];

  if (!draft.readiness.draft_ready) {
    return {
      state: "needs_data",
      label: "待補案件基本資料",
      primaryMessage: "請先補齊案件名稱與物件地址／識別，才可儲存草稿案件。",
      nextSteps: draft.readiness.missing_required
        .filter((key) => key === "case_name" || key === "address")
        .map((key) => `補齊 ${moduleLabel(key)}`),
      safeWarnings,
      statusLabels,
    };
  }

  if (!draft.readiness.compare_ready) {
    return {
      state: "needs_data",
      label: "待補比較資料",
      primaryMessage: "此案件可保留目前摘要，但仍需可比較價格資料才會進入比較候選。",
      nextSteps: draft.readiness.missing_required.map((key) => `補齊 ${moduleLabel(key)}`),
      safeWarnings: [...safeWarnings, "缺少價格資料時，不會顯示為低價、0 元或比較完成。"],
      statusLabels,
    };
  }

  if (draft.readiness.unavailable_or_incomplete.length > 0) {
    return {
      state: "unavailable",
      label: "部分資料待確認",
      primaryMessage: "此案件已有比較基礎，但部分分析仍需補齊或重新確認。",
      nextSteps: [
        "可先列印目前摘要",
        ...draft.readiness.unavailable_or_incomplete.slice(0, 3).map((key) => `確認 ${moduleLabel(key)}`),
      ],
      safeWarnings: [PARTIAL_CASE_PRINT_NOTICE, ...safeWarnings],
      statusLabels,
    };
  }

  return {
    state: "ready",
    label: "可比較與列印",
    primaryMessage: "案件具備名稱、物件地址與可比較價格，可進入最多三件案件比較；完整度不是投資評分或買賣建議。",
    nextSteps: ["列印目前摘要", "與 2 至 3 件案件比較", "繼續補齊缺少的分析"],
    safeWarnings: [PARTIAL_CASE_PRINT_NOTICE, ...safeWarnings],
    statusLabels,
  };
}

export function moduleLabel(key: string): string {
  return {
    case_name: "案件名稱",
    address: "物件地址／識別",
    listing_price: "可比較價格資料",
    property: "Property Finder",
    location: "Location Insight",
    terrain: "Terrain Risk",
    commute: "通勤資訊",
    valuation: "估價",
    loan: "貸款試算",
    holding: "持有成本",
    tax: "TaxOracle",
    decision: "看房決策摘要",
  }[key] ?? key;
}

const statusLabels: Record<PropertyCaseStatus, string> = {
  completed: "已完成",
  missing: "尚未分析",
  incomplete: "資料不完整",
  unavailable: "暫不可用",
};
