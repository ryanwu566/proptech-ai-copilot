export type VisualDataState =
  | "available"
  | "official_available"
  | "no_data"
  | "unavailable"
  | "partial"
  | "stale"
  | "unknown"
  | "missing"
  | "blocked"
  | "demo";

export const VISUAL_STATE_LABELS: Record<VisualDataState, string> = {
  available: "資料可用",
  official_available: "官方資料可用",
  no_data: "目前資料不足",
  unavailable: "資料暫時無法取得",
  partial: "部分資料可用",
  stale: "資料更新時間較早",
  unknown: "尚未評估",
  missing: "未提供",
  blocked: "有阻擋項目",
  demo: "展示資料，不可作為正式決策依據",
};

export const EVIDENCE_DISCLOSURE_LABELS = {
  market: "查看資料依據",
  calculation: "查看完整計算依據",
  rules: "查看完整規則追蹤",
  transactions: "查看完整成交明細",
  knownFields: "查看已知欄位與證據狀態",
} as const;

export const VISUAL_FAILURE_COPY = {
  noData: "目前資料不足，請調整條件或稍後再試。",
  unavailable: "資料暫時無法取得，請稍後再試；不以缺少資料推論低風險或零值。",
  unknown: "尚未評估，不能解讀為低風險或已完成。",
  missing: "未提供；不以 0 或其他假值補入。",
  demo: "目前為展示資料，不可作為正式決策依據。",
} as const;

export const PRODUCTION_ACCEPTANCE_PENDING_NOTICE = "正式站仍需由人工完成部署、瀏覽器、鍵盤、手機、隱私與失敗復原驗收。";

export function visualStateLabel(state: VisualDataState): string {
  return VISUAL_STATE_LABELS[state];
}

export function visualFailureCopy(state: keyof typeof VISUAL_FAILURE_COPY): string {
  return VISUAL_FAILURE_COPY[state];
}
