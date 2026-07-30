"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";

export function JourneyToolCard({ title, productLabel, description, onOpen, primary = false }: { title: string; productLabel: string; description: string; onOpen: () => void; primary?: boolean }) {
  const { t } = useExperienceLocale();
  return <article className={"min-w-0 rounded-2xl border p-4 " + (primary ? "border-cyan-300 bg-cyan-50/70" : "border-stone-200 bg-white")}>
    <p className="break-words text-[10px] font-bold tracking-wider text-cyan-700">{productLabel}</p>
    <h3 className="mt-1 break-words text-base font-bold text-slate-950">{title}</h3>
    <p className="mt-2 break-words text-xs leading-5 text-slate-600">{description}</p>
    <button type="button" data-action-kind={primary ? "primary" : "secondary"} data-primary-action-id={primary ? "property-finder" : undefined} onClick={onOpen} className={"mt-4 w-full rounded-lg px-3 py-2.5 text-sm font-bold transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 " + (primary ? "bg-cyan-700 text-white hover:bg-cyan-800" : "border border-stone-300 bg-white text-slate-800 hover:border-cyan-300")}>{primary ? t("hero.primary") : t("journey.openTool")}</button>
  </article>;
}
