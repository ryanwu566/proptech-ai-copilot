import type { ExperienceLocale } from "./experience-i18n";
export const LOCALE_SETTING_KEY = "proptech.locale.v1";
export function readLocaleSetting(storage: Pick<Storage, "getItem">): ExperienceLocale | null {
  try { const data = JSON.parse(storage.getItem(LOCALE_SETTING_KEY) ?? "null"); return data?.version === 1 && ["zh-TW", "en", "ja", "ko"].includes(data.locale) ? data.locale : null; } catch { return null; }
}
export function saveLocaleSetting(storage: Pick<Storage, "setItem">, locale: ExperienceLocale): void {
  try { storage.setItem(LOCALE_SETTING_KEY, JSON.stringify({ version: 1, locale })); } catch { /* Locale switching still works without persistent storage. */ }
}
