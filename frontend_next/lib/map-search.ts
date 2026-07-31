import type { ExperienceLocale } from "@/lib/experience-i18n";
import { getAdministrativeDistrictOptions, getAdministrativeOptions, getLocalizedRoadLabel } from "@/lib/structured-options";

type SearchAlias = {
  pattern: RegExp;
  replacement: string;
};

const SEARCH_ALIASES: SearchAlias[] = [
  { pattern: /new\s+taipei(?:\s+city)?/gi, replacement: "新北市" },
  { pattern: /taipei(?:\s+city)?/gi, replacement: "台北市" },
  { pattern: /taichung(?:\s+city)?/gi, replacement: "台中市" },
  { pattern: /tainan(?:\s+city)?/gi, replacement: "台南市" },
  { pattern: /kaohsiung(?:\s+city)?/gi, replacement: "高雄市" },
  { pattern: /banqiao(?:\s+district)?/gi, replacement: "板橋區" },
  { pattern: /(?:daan|da'an)(?:\s+district)?/gi, replacement: "大安區" },
  { pattern: /xinyi(?:\s+district)?/gi, replacement: "信義區" },
  { pattern: /zhongzheng(?:\s+district)?/gi, replacement: "中正區" },
  { pattern: /heping\s+east\s+road(?:\s+section)?\s*2/gi, replacement: "和平東路二段" },
  { pattern: /台北市|taipei|台北|臺北|타이베이|타이페이|タイペイ/gi, replacement: "台北市" },
  { pattern: /new\s*taipei|新北|신베이|신베이시|シンベイ/gi, replacement: "新北市" },
  { pattern: /大安区|다안구|ダアン区/gi, replacement: "大安區" },
  { pattern: /板橋区|반차오|반차오구|バンチャオ/gi, replacement: "板橋區" },
  { pattern: /信義区|신이구/gi, replacement: "信義區" },
  { pattern: /中正区|중정구/gi, replacement: "中正區" },
  { pattern: /和平東路二段|和平東路2段/gi, replacement: "和平東路二段" },
];

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^\${}()|[\]\\]/g, "\\$&");
}

function localeAliases(locale: ExperienceLocale): SearchAlias[] {
  const aliases: SearchAlias[] = [];
  for (const option of getAdministrativeOptions(locale)) {
    if (option.labels[locale] !== option.value) aliases.push({ pattern: new RegExp(escapeRegExp(option.labels[locale]), "gi"), replacement: option.value });
  }
  for (const area of getAdministrativeOptions("zh-TW")) {
    for (const option of getAdministrativeDistrictOptions(area.value, locale)) {
      if (option.labels[locale] !== option.value) aliases.push({ pattern: new RegExp(escapeRegExp(option.labels[locale]), "gi"), replacement: option.value });
    }
  }
  for (const road of ["和平東路二段", "市府路", "忠信路"]) {
    const label = getLocalizedRoadLabel(road, locale);
    if (label !== road) aliases.push({ pattern: new RegExp(escapeRegExp(label), "gi"), replacement: road });
  }
  return aliases;
}

export function normalizeTaiwanPlaceQuery(query: string, locale: ExperienceLocale): string {
  let normalized = query.trim().replace(/\s+/g, " ");
  for (const alias of [...localeAliases(locale), ...SEARCH_ALIASES]) normalized = normalized.replace(alias.pattern, alias.replacement);
  return normalized.replace(/\s+/g, " ").trim();
}

export function hasSearchablePlaceQuery(query: string): boolean {
  return normalizeTaiwanPlaceQuery(query, "zh-TW").length > 0;
}
