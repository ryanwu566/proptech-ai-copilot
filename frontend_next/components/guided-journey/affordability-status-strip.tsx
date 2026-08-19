"use client";

import type { AffordabilityStatusItem } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function AffordabilityStatusStrip({ items }: { items: readonly AffordabilityStatusItem[] }) {
  const { copy } = useExperienceLocale();
  return <section aria-labelledby="affordability-status-heading" className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex items-baseline justify-between gap-3"><h3 id="affordability-status-heading" className="text-sm font-black text-slate-950">{copy("journey.affordStatusTitle")}</h3><span className="text-[10px] text-slate-500">{copy("journey.affordStatusNote")}</span></div>
    <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{items.map((item) => <div key={item.id} className="rounded-lg border border-stone-100 bg-stone-50 p-3"><p className="text-[10px] font-bold text-slate-500">{item.label}</p><p className="mt-1 text-sm font-bold text-slate-900">{item.text}</p><p className="mt-1 text-[10px] text-slate-500">{item.status}</p></div>)}</div>
  </section>;
}
