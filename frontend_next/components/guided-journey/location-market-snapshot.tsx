import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { TranslationKey } from "@/lib/experience-i18n";
import type { LocationMarketStatusItem } from "@/lib/location-market-journey";

export function LocationMarketSnapshot({ items, evidenceAvailable }: { items: readonly LocationMarketStatusItem[]; evidenceAvailable?: boolean }) {
  const { t, copy } = useExperienceLocale();
  return <section aria-labelledby="location-market-snapshot-heading" data-evidence-available={evidenceAvailable ? "yes" : "no"} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
    <h3 id="location-market-snapshot-heading" className="text-sm font-black text-slate-950">{t("evidence.summaryTitle")}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{t("evidence.summaryDescription")}</p>
    <ul className="mt-3 grid gap-2 text-xs sm:grid-cols-2">{items.map((item) => <li key={item.id} className="flex items-start justify-between gap-3 rounded-lg border border-stone-200 bg-white px-3 py-2"><span className="font-bold text-slate-700">{toolLabel(item.id, t, copy)}</span><span className="text-right text-slate-600">{statusLabel(item.status, t)}</span></li>)}</ul>
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
