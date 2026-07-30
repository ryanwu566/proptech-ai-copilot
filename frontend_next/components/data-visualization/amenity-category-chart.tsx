import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { TranslationKey } from "@/lib/experience-i18n";
import type { AmenityCategoryModel } from "@/lib/location-market-journey";

export function AmenityCategoryChart({ categories }: { categories: readonly AmenityCategoryModel[] }) {
  const { t, copy } = useExperienceLocale();
  const categoryLabel = (id: string) => id === "transit" ? copy("location.transit") : id === "school" ? copy("location.education") : id === "park" ? copy("location.green") : id === "medical" ? copy("location.medical") : copy("location.convenience");
  const statusLabel = (status: AmenityCategoryModel["status"]) => {
    const key: TranslationKey = status === "unavailable" ? "state.unavailable.heading" : status === "not_started" ? "state.not_assessed.heading" : status === "partial" ? "state.partial.heading" : status === "unknown" ? "state.unknown.heading" : "state.no_official_data.heading";
    return t(key);
  };
  const hasData = categories.some((item) => item.count !== null);
  if (!hasData) {
    const unavailable = categories.some((item) => item.status === "unavailable");
    return <section aria-label={copy("location.convenience")} className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-4"><h3 className="text-sm font-bold text-slate-900">{copy("location.convenience")}</h3><p className="mt-2 text-xs leading-5 text-slate-600">{unavailable ? t("state.unavailable.explanation") : t("state.empty.explanation")}</p></section>;
  }
  const maxCount = Math.max(1, ...categories.flatMap((item) => item.count === null ? [] : [item.count]));
  return <section aria-label={copy("location.convenience")} className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between"><h3 className="text-sm font-black text-slate-950">{copy("location.convenience")}</h3><span className="text-[10px] text-slate-500">{t("evidence.summaryDescription")}</span></div>
    <div role="img" aria-label={copy("location.convenience")} className="mt-4 space-y-3">{categories.map((item) => <div key={item.id} className="grid grid-cols-[72px_minmax(0,1fr)_auto] items-center gap-2 text-xs">
      <span className="font-bold text-slate-700">{categoryLabel(item.id)}</span><div className="h-3 rounded-full bg-stone-100"><div className="h-3 rounded-full bg-cyan-600" style={{ width: item.count === null ? "0%" : `${(item.count / maxCount) * 100}%` }} /></div><span className="whitespace-nowrap font-bold text-slate-800">{item.count === null ? statusLabel(item.status) : `${item.count} ${copy("common.records")}`}</span>
    </div>)}</div>
    <p className="mt-3 text-[11px] leading-5 text-slate-500">{t("state.no_official_data.source")}</p>
  </section>;
}
