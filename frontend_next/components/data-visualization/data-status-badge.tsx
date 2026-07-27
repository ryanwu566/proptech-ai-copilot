"use client";

type Status = "available" | "no_data" | "unavailable" | "fresh" | "aging" | "stale" | "unknown" | "partial" | "covered" | "not_covered";

const labels: Record<Status, string> = {
  available: "資料可用",
  no_data: "查無資料",
  unavailable: "資料暫不可用",
  fresh: "資料新鮮度：新近",
  aging: "資料新鮮度：需留意",
  stale: "資料新鮮度：過期",
  unknown: "資料新鮮度：未知",
  partial: "涵蓋狀態：部分",
  covered: "涵蓋狀態：已涵蓋",
  not_covered: "涵蓋狀態：未涵蓋",
};

export function DataStatusBadge({ status }: { status: Status }) {
  return <span role="status" aria-label={labels[status]} className="inline-flex rounded-full border border-slate-300 bg-slate-50 px-2 py-1 text-[11px] font-bold text-slate-700">{labels[status]}</span>;
}
