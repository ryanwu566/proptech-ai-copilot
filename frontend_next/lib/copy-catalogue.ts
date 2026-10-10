import type { ExperienceLocale } from "@/lib/experience-i18n";

export type CopyCatalogue<K extends string> = Record<ExperienceLocale, Record<K, string>>;
export function translateCopyCatalogue<K extends string>(locale: ExperienceLocale, catalogue: CopyCatalogue<K>, key: K, values: Record<string, string | number> = {}): string {
  return Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{{${name}}}`, String(value)), catalogue[locale][key]);
}
