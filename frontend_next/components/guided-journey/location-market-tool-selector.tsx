"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { LocationMarketToolId } from "@/lib/location-market-journey";

const TOOLS: Array<{ id: LocationMarketToolId; labelKey: "journey.location.title" | "journey.location.next" | "page.market"; descriptionKey: "journey.location.description" | "trust.referenceOnly" | "evidence.summaryDescription" }> = [
  { id: "commute", labelKey: "journey.location.next", descriptionKey: "journey.location.description" },
  { id: "terrain", labelKey: "journey.location.title", descriptionKey: "trust.referenceOnly" },
  { id: "market", labelKey: "page.market", descriptionKey: "evidence.summaryDescription" },
];

export function LocationMarketToolSelector({ activeTool, onSelect }: { activeTool: LocationMarketToolId | null; onSelect: (tool: LocationMarketToolId) => void }) {
  const { t } = useExperienceLocale();
  return <section aria-labelledby="location-market-tools-heading" className="rounded-xl border border-stone-200 bg-white p-4"><h3 id="location-market-tools-heading" className="text-sm font-black text-slate-950">{t("journey.location.title")}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{t("journey.location.description")}</p><div className="mt-3 grid gap-2 sm:grid-cols-3">{TOOLS.map((tool) => <button type="button" key={tool.id} aria-pressed={activeTool === tool.id} onClick={() => onSelect(tool.id)} className={`rounded-lg border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 ${activeTool === tool.id ? "border-cyan-400 bg-cyan-50" : "border-stone-200 bg-stone-50 hover:border-cyan-200"}`}><span className="block text-xs font-bold text-slate-900">{t(tool.labelKey)}</span><span className="mt-1 block text-[10px] leading-5 text-slate-500">{t(tool.descriptionKey)}</span></button>)}</div></section>;
}
