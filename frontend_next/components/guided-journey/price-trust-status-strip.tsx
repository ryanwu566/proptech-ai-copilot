"use client";

import type { PriceTrustStatusItem } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PriceTrustStatusStrip({ items }: { items: readonly PriceTrustStatusItem[] }) {
  const { copy } = useExperienceLocale();
  return <section aria-labelledby="price-trust-status-heading" className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex items-baseline justify-between gap-3"><h3 id="price-trust-status-heading" className="text-sm font-black text-slate-950">{copy("journey.priceStatusTitle")}</h3><span className="text-[10px] text-slate-500">{copy("journey.priceStatusNote")}</span></div>
    <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{items.map((item) => <div key={item.id} className="rounded-lg border border-stone-100 bg-stone-50 p-3"><p className="text-[10px] font-bold text-slate-500">{item.label}</p><p className="mt-1 text-sm font-bold text-slate-900">{item.text}</p><p className="mt-1 text-[10px] text-slate-500">{item.status}</p></div>)}</div>
  </section>;
}
