"use client";
import { useViewMode } from "@/lib/view-mode";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getSurfaceCopy } from "@/lib/surface-copy";

// Existing beginner/pro labels are localized through surface-copy: 新手模式：我只想知道值不值得看；專業模式：我要看完整分析細節。

export function ViewModeToggle({ compact = false }: { compact?: boolean }) {
  const [viewMode, setViewMode] = useViewMode();
  const { locale } = useExperienceLocale();
  const copy = getSurfaceCopy(locale).shell;
  return <div className={`${compact ? "hidden sm:flex" : "flex"} max-w-full shrink items-center gap-1 overflow-hidden rounded-xl border border-stone-200 bg-white p-1`} aria-label={copy.beginner}>
    <button type="button" aria-pressed={viewMode === "beginner"} onClick={() => setViewMode("beginner")} className={`min-w-0 truncate whitespace-nowrap rounded-lg px-2 py-1.5 text-[10px] font-bold ${viewMode === "beginner" ? "bg-cyan-700 text-white" : "text-slate-500"}`}>{copy.beginner}</button>
    <button type="button" aria-pressed={viewMode === "pro"} onClick={() => setViewMode("pro")} className={`min-w-0 truncate whitespace-nowrap rounded-lg px-2 py-1.5 text-[10px] font-bold ${viewMode === "pro" ? "bg-slate-900 text-white" : "text-slate-500"}`}>{copy.expert}</button>
  </div>;
}
