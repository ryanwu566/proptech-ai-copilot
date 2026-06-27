"use client";
import { useViewMode } from "@/lib/view-mode";

export function ViewModeToggle({ compact = false }: { compact?: boolean }) {
  const [viewMode, setViewMode] = useViewMode();
  return <div className="flex min-w-0 items-center gap-1 rounded-xl border border-stone-200 bg-white p-1" aria-label="顯示模式切換">
    <button type="button" aria-pressed={viewMode === "beginner"} onClick={() => setViewMode("beginner")} className={`rounded-lg px-2.5 py-1.5 text-[10px] font-bold ${viewMode === "beginner" ? "bg-cyan-700 text-white" : "text-slate-500"}`}>{compact ? "新手" : "新手模式：我只想知道值不值得看"}</button>
    <button type="button" aria-pressed={viewMode === "pro"} onClick={() => setViewMode("pro")} className={`rounded-lg px-2.5 py-1.5 text-[10px] font-bold ${viewMode === "pro" ? "bg-slate-900 text-white" : "text-slate-500"}`}>{compact ? "專業" : "專業模式：我要看完整分析細節"}</button>
  </div>;
}
