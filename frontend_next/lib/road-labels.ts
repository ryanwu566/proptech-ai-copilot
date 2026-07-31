import type { ExperienceLocale } from "@/lib/experience-i18n";

export type RoadDisplayLabels = Record<ExperienceLocale, string>;

/** Stable, checked-in display labels are a presentation layer; the CSV value remains canonical. */
export const ROAD_LABEL_PIPELINE_VERSION = "road-display-v1";
export const ROAD_FALLBACK_STRATEGY = "localized official-name fallback";

const ROAD_LABELS: Record<string, RoadDisplayLabels> = {
  "\u548c\u5e73\u6771\u8def\u4e8c\u6bb5": { "zh-TW": "\u548c\u5e73\u6771\u8def\u4e8c\u6bb5", en: "Heping East Road, Section 2", ja: "和平東路2段", ko: "허핑동로 2단" },
  "\u5e02\u5e9c\u8def": { "zh-TW": "\u5e02\u5e9c\u8def", en: "City Hall Road", ja: "市府路", ko: "스푸로" },
  "\u5fe0\u4fe1\u8def": { "zh-TW": "\u5fe0\u4fe1\u8def", en: "Zhongxin Road", ja: "忠信路", ko: "중신로" },
  "\u4ec1\u611b\u8def": { "zh-TW": "\u4ec1\u611b\u8def", en: "Renai Road", ja: "仁愛路", ko: "런아이로" },
  "\u4fe1\u7fa9\u8def": { "zh-TW": "\u4fe1\u7fa9\u8def", en: "Xinyi Road", ja: "信義路", ko: "신이로" },
  "\u5fe0\u5b5d\u8def": { "zh-TW": "\u5fe0\u5b5d\u8def", en: "Zhongxiao Road", ja: "忠孝路", ko: "중샤오로" },
  "\u6566\u5316\u5357\u8def": { "zh-TW": "\u6566\u5316\u5357\u8def", en: "Dunhua South Road", ja: "敦化南路", ko: "둔화남로" },
  "\u5fa9\u8208\u5357\u8def": { "zh-TW": "\u5fa9\u8208\u5357\u8def", en: "Fuxing South Road", ja: "復興南路", ko: "푸싱남로" },
  "\u57fa\u9686\u8def": { "zh-TW": "\u57fa\u9686\u8def", en: "Keelung Road", ja: "基隆路", ko: "지룽로" },
  "\u7f85\u65af\u798f\u8def": { "zh-TW": "\u7f85\u65af\u798f\u8def", en: "Roosevelt Road", ja: "羅斯福路", ko: "뤄스푸로" },
  "\u6c11\u751f\u6771\u8def": { "zh-TW": "\u6c11\u751f\u6771\u8def", en: "Minsheng East Road", ja: "民生東路", ko: "민성동로" },
  "\u4e2d\u5c71\u5317\u8def": { "zh-TW": "\u4e2d\u5c71\u5317\u8def", en: "Zhongshan North Road", ja: "中山北路", ko: "중산베이로" },
};

const SECTION_NAMES: Record<string, { en: string; ja: string; ko: string }> = {
  "\u4e00": { en: "1", ja: "1", ko: "1" },
  "\u4e8c": { en: "2", ja: "2", ko: "2" },
  "\u4e09": { en: "3", ja: "3", ko: "3" },
  "\u56db": { en: "4", ja: "4", ko: "4" },
  "\u4e94": { en: "5", ja: "5", ko: "5" },
  "\u516d": { en: "6", ja: "6", ko: "6" },
};

function canonicalRoadName(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function sectionFallback(value: string): RoadDisplayLabels | undefined {
  const match = value.match(/^(.*?)([\u4e00-\u4e5d\u5341]+)\u6bb5$/u);
  if (!match) return undefined;
  const section = SECTION_NAMES[match[2]];
  if (!section) return undefined;
  const base = match[1].replace(/\u8def$/u, "");
  return {
    "zh-TW": value,
    en: `${base} Road, Section ${section.en}`,
    ja: `${base}路${section.ja}段`,
    ko: `${base}로 ${section.ko}단`,
  };
}

export function getRoadDisplayLabels(value: string): RoadDisplayLabels {
  const canonical = canonicalRoadName(value);
  return ROAD_LABELS[canonical] ?? sectionFallback(canonical) ?? {
    "zh-TW": canonical,
    en: `Official road name (${canonical})`,
    ja: `公式道路名（${canonical}）`,
    ko: `공식 도로명 (${canonical})`,
  };
}

export function getLocalizedRoadDisplayLabel(value: string, locale: ExperienceLocale): string {
  return getRoadDisplayLabels(value)[locale];
}
