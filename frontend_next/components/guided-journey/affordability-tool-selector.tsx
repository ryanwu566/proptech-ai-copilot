"use client";

import type { AffordabilityToolId } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function AffordabilityToolSelector({ activeTool, onSelect }: { activeTool: AffordabilityToolId | null; onSelect: (tool: AffordabilityToolId) => void }) {
  const { copy } = useExperienceLocale();
  return <section aria-labelledby="affordability-tool-selector-heading" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4">
    <h3 id="affordability-tool-selector-heading" className="text-sm font-black text-slate-950">{copy("journey.affordToolTitle")}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{copy("journey.affordToolDesc")}</p>
    <div className="mt-3 grid gap-2 sm:grid-cols-2"><ToolButton active={activeTool === "holding"} onClick={() => onSelect("holding")} label={copy("journey.affordToolHolding")} showing={copy("journey.affordToolShowing")} click={copy("journey.affordToolClick")} /><ToolButton active={activeTool === "tax"} onClick={() => onSelect("tax")} label={copy("journey.affordToolTax")} showing={copy("journey.affordToolShowing")} click={copy("journey.affordToolClick")} /></div>
  </section>;
}

function ToolButton({ active, onClick, label, showing, click }: { active: boolean; onClick: () => void; label: string; showing: string; click: string }) {
  return <button type="button" aria-pressed={active} onClick={onClick} className="w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-left text-sm font-bold text-slate-800 transition hover:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">{label}<span className="mt-1 block text-[10px] font-normal text-slate-500">{active ? showing : click}</span></button>;
}
