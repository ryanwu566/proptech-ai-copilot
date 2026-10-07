import type { EvidenceStatus, GapReason } from "./case-evidence";
export const PRICE_BASIS_LABELS = { asking: "開價", estimate: "成交資料推估", manual: "使用者設定基準" } as const;
export const EVIDENCE_STATUS_LABELS: { [S in EvidenceStatus]: string } = {
  available: "已儲存證據", limited: "已儲存摘要／受限", not_run: "尚未查詢", unavailable: "已嘗試，目前無法取得", unsupported: "目前不支援／需人工確認", no_coverage: "無資料覆蓋", no_match: "未命中，不代表安全", stale: "已過期，需重新確認", insufficient: "資料不足",
};
export const GAP_LABELS: { [S in GapReason]: string } = { missing_input: "缺少輸入", not_run: "尚未查詢", unavailable: "目前無法取得", unsupported: "目前不支援", no_coverage: "無資料覆蓋", stale: "已過期", insufficient: "證據不足", not_preserved: "快照未保存" };
