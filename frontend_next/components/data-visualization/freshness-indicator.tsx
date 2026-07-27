import { DataStatusBadge } from "./data-status-badge";
import type { VisualFreshnessStatus } from "@/lib/market-insight-visualization";

export function FreshnessIndicator({ status }: { status: VisualFreshnessStatus }) {
  return <div aria-label="資料新鮮度" className="flex items-center gap-2"><DataStatusBadge status={status} /><span className="text-xs text-slate-500">若無法判定更新狀態，會明確標示未知。</span></div>;
}
