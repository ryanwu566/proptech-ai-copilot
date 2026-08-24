"use client";

import { LOCALE_LABELS, SUPPORTED_LOCALES } from "@/lib/experience-i18n";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function LocaleSwitcher() {
  const { locale, setLocale, t } = useExperienceLocale();
  return <label className="flex items-center gap-1.5 text-[10px] text-slate-600">
    <span className="sr-only">{t("locale.switcherLabel")}</span>
    <select data-testid="locale-switcher" value={locale} onChange={(event) => setLocale(event.target.value)} aria-label={t("locale.switcherLabel")} className="rounded-md border border-stone-200 bg-white px-2 py-1.5 font-bold focus:outline-none focus:ring-2 focus:ring-cyan-500">
      {SUPPORTED_LOCALES.map((item) => <option key={item} value={item}>{LOCALE_LABELS[item]}</option>)}
    </select>
  </label>;
}
