"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_LOCALE, formatExperienceDate, formatExperienceNumber, formatExperiencePercent, normalizeExperienceLocale, translateExperience, type ExperienceLocale, type TranslationKey } from "@/lib/experience-i18n";

type ExperienceLocaleContextValue = {
  locale: ExperienceLocale;
  setLocale: (value: string) => void;
  t: (key: TranslationKey) => string;
  formatNumber: (value: number) => string;
  formatPercent: (value: number) => string;
  formatDate: (value: string | number | Date) => string;
};

const ExperienceLocaleContext = createContext<ExperienceLocaleContextValue | null>(null);

export function ExperienceLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<ExperienceLocale>(DEFAULT_LOCALE);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<ExperienceLocaleContextValue>(() => ({
    locale,
    setLocale: (next) => setLocale(normalizeExperienceLocale(next)),
    t: (key) => translateExperience(locale, key),
    formatNumber: (number) => formatExperienceNumber(number, locale),
    formatPercent: (percent) => formatExperiencePercent(percent, locale),
    formatDate: (date) => formatExperienceDate(date, locale),
  }), [locale]);

  return <ExperienceLocaleContext.Provider value={value}>{children}</ExperienceLocaleContext.Provider>;
}

export function useExperienceLocale(): ExperienceLocaleContextValue {
  const value = useContext(ExperienceLocaleContext);
  if (!value) throw new Error("ExperienceLocaleProvider is required");
  return value;
}
