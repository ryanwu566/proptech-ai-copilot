import type { ExperienceLocale } from "../experience-i18n";
/** Keep entry routes independent of the conversation, evidence graph and full catalogue. */
export function copilotEntryLabel(locale: ExperienceLocale): string {
  return { "zh-TW": "物件決策 Copilot", en: "Property decision Copilot", ja: "物件判断 Copilot", ko: "부동산 의사결정 Copilot" }[locale];
}
