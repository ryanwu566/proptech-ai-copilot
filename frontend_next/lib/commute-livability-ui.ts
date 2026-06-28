import type { CommuteAddressLookupResult } from "@/lib/api";

export type CommuteLivabilityStatus = "idle" | "loading" | "resolved" | "unresolved" | "unavailable" | "error";

export const COMMUTE_LIVABILITY_NOTICE = "僅供通勤與生活機能參考，不影響地勢災害、貸款、法律或看房結論。";

export function isBlankAddress(address: string): boolean {
  return address.trim().length === 0;
}

export function commuteStatusMessage(status: CommuteLivabilityStatus): string {
  if (status === "idle") return "尚未查詢通勤資訊。";
  if (status === "loading") return "正在查詢通勤資訊⋯";
  if (status === "unresolved") return "目前無法從此地址取得可信的通勤參考結果。";
  if (status === "unavailable") return "通勤資料目前無法使用，請稍後再試。";
  if (status === "error") return "通勤資料目前無法使用，請稍後再試。";
  return "";
}

export function normalizeCommuteResult(result: CommuteAddressLookupResult): CommuteAddressLookupResult {
  return {
    status: result.status,
    source: result.source,
    station_name: result.station_name ?? null,
    line_ids: Array.isArray(result.line_ids) ? result.line_ids.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim()) : [],
    distance_meters: typeof result.distance_meters === "number" && Number.isFinite(result.distance_meters) ? result.distance_meters : null,
    source_updated_at: result.source_updated_at ?? null,
    snapshot_generated_at: result.snapshot_generated_at ?? null,
    message: result.status === "resolved" ? COMMUTE_LIVABILITY_NOTICE : result.message,
  };
}
