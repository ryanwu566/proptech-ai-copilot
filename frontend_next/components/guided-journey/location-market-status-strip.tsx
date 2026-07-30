import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { TranslationKey } from "@/lib/experience-i18n";
import type { LocationMarketStatusItem } from "@/lib/location-market-journey";

export function LocationMarketStatusStrip({ items, onOpen }: { items: readonly LocationMarketStatusItem[]; onOpen: (id: LocationMarketStatusItem["id"]) => void }) {
  const { t, copy } = useExperienceLocale();
  return <section aria-labelledby="location-market-status-heading" className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex items-baseline justify-between gap-3"><h3 id="location-market-status-heading" className="text-sm font-black text-slate-950">{t("journey.location.title")}</h3><span className="text-[10px] text-slate-500">{t("evidence.summaryDescription")}</span></div>
    <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{items.map((item) => <article key={item.id} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
      <div className="flex items-start justify-between gap-2"><div><p className="text-xs font-bold text-slate-900">{toolLabel(item.id, t, copy)}</p><p className="mt-1 text-[11px] font-bold text-slate-700">{statusLabel(item.status, t)}</p></div><span aria-hidden="true" className="mt-1 h-2 w-2 shrink-0 rounded-full bg-slate-400" /></div>
      <p className="mt-2 text-[10px] leading-5 text-slate-500">{summaryLabel(item.id, copy, t)}</p>
      <button type="button" onClick={() => onOpen(item.id)} className="mt-3 w-full rounded-md border border-stone-300 bg-white px-2 py-1.5 text-[11px] font-bold text-slate-700 transition hover:border-cyan-300 hover:text-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">{t("journey.openTool")}</button>
    </article>)}</div>
  </section>;
}

function toolLabel(id: LocationMarketStatusItem["id"], t: (key: TranslationKey) => string, copy: ReturnType<typeof useExperienceLocale>["copy"]) {
  if (id === "location") return copy("location.title");
  if (id === "commute") return copy("commute.title");
  if (id === "terrain") return copy("location.risk");
  return t("page.market");
}

function statusLabel(status: LocationMarketStatusItem["status"], t: (key: TranslationKey) => string) {
  const key: TranslationKey = status === "not_started" ? "state.not_assessed.heading" : status === "loading" ? "state.loading.heading" : status === "available" ? "state.ready.heading" : status === "no_data" ? "state.no_official_data.heading" : status === "unavailable" ? "state.unavailable.heading" : status === "partial" ? "state.partial.heading" : status === "stale" ? "state.limited.heading" : "state.unknown.heading";
  return t(key);
}

function summaryLabel(id: LocationMarketStatusItem["id"], copy: ReturnType<typeof useExperienceLocale>["copy"], t: (key: TranslationKey) => string) {
  if (id === "terrain") return t("trust.referenceOnly");
  if (id === "market") return t("trust.noPurchase");
  if (id === "commute") return copy("commute.description");
  return copy("location.description");
}
