import { getDraftSaveMissingFields, type SaveCaseInput } from "./case-storage";
import type { ExperienceLocale } from "./experience-i18n";
import { translateRuntimeCopy } from "./runtime-copy";

export function getCaseSaveFailureFeedback(input: SaveCaseInput, locale: ExperienceLocale): string {
  const missing = getDraftSaveMissingFields(input);
  if (missing.length) return translateRuntimeCopy(locale, "case.missing", {
    items: missing.map(field => translateRuntimeCopy(locale, field === "case_name" ? "case.title" : "case.address")).join(" / "),
  });
  return {
    "zh-TW": "案件未保存；瀏覽器儲存無法寫入、容量不足或案件已變更。請檢查已儲存案件後再試。",
    en: "Case was not saved. Browser storage is unavailable, full, or cases changed. Check saved cases and try again.",
    ja: "案件を保存できませんでした。保存領域を利用できない、容量が不足している、または案件が更新されています。保存済み案件を確認して再試行してください。",
    ko: "사례가 저장되지 않았습니다. 브라우저 저장소를 사용할 수 없거나 공간이 부족하거나 사례가 변경되었습니다. 저장된 사례를 확인하고 다시 시도하세요.",
  }[locale];
}
