import type { ExperienceLocale } from "@/lib/experience-i18n";
import { ROAD_PHONETICS } from "@/lib/road-phonetics";

export type RoadDisplayLabels = Record<ExperienceLocale, string>;
export type RoadScope = { county?: string; district?: string };

/** Generated offline from the checked-in Taiwan road directory. */
export const ROAD_LABEL_PIPELINE_VERSION = "road-display-v2";
export const ROAD_FALLBACK_STRATEGY = "offline deterministic transliteration";

const NUMBER_VALUES: Record<string, number> = { "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10 };
const DIRECTIONS: Record<string, string> = { "東": "East", "西": "West", "南": "South", "北": "North" };
const ROAD_SUFFIXES = [
  ["高速公路", "Expressway", "高速道路 ハイウェイ", "고속도로"],
  ["公路", "Highway", "幹線道路 ハイウェイ", "간선도로"],
  ["大道", "Boulevard", "大通り メインストリート", "대로"],
  ["路", "Road", "道路 ロード", "로"],
  ["街", "Street", "通り ストリート", "길"],
  ["巷", "Lane", "路地 レーン", "골목"],
  ["弄", "Alley", "路地 アレイ", "골목"],
] as const;

const missingCharacters = new Set<string>();

function numberValue(value: string): number | undefined {
  if (!value || [...value].some((char) => NUMBER_VALUES[char] === undefined)) return undefined;
  if (value === "十") return 10;
  if (value.includes("十")) {
    const [left, right] = value.split("十");
    return (left ? NUMBER_VALUES[left] * 10 : 10) + (right ? NUMBER_VALUES[right] : 0);
  }
  return [...value].reduce((total, char) => total * 10 + NUMBER_VALUES[char], 0);
}

function phonetic(char: string, locale: "en" | "ja" | "ko"): string {
  const record = ROAD_PHONETICS[char];
  if (record) return record[locale];
  if (/[\u4e00-\u9fff]/u.test(char)) {
    missingCharacters.add(char);
    if (process.env.NODE_ENV !== "production" && missingCharacters.size <= 20) {
      console.warn(`[road-display] missing offline phonetic character: ${char}`);
    }
  }
  return char;
}

function romanizedBase(value: string): string {
  const words: string[] = [];
  let current = "";
  for (const char of value) {
    const direction = DIRECTIONS[char];
    if (direction) {
      if (current) words.push(current);
      current = "";
      words.push(direction);
    } else {
      current += phonetic(char, "en").toLowerCase();
    }
  }
  if (current) words.push(current);
  return words.filter(Boolean).map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function localizedBase(value: string, locale: "ja" | "ko"): string {
  return [...value].map((char) => phonetic(char, locale)).join("");
}

function ordinal(value: number): string {
  if (value % 100 >= 11 && value % 100 <= 13) return `${value}th`;
  return `${value}${value % 10 === 1 ? "st" : value % 10 === 2 ? "nd" : value % 10 === 3 ? "rd" : "th"}`;
}

function splitRoad(value: string): { base: string; section?: number; suffix?: readonly [string, string, string, string] } {
  if (value.endsWith("段")) {
    const beforeSection = value.slice(0, -1);
    const match = beforeSection.match(/([零一二兩三四五六七八九十]+)$/u);
    const section = match ? numberValue(match[1]) : undefined;
    if (section !== undefined && match) return { base: beforeSection.slice(0, match.index ?? 0), section };
  }
  const suffix = ROAD_SUFFIXES.find(([raw]) => value.endsWith(raw));
  return suffix ? { base: value.slice(0, -suffix[0].length), suffix } : { base: value };
}

function getRoadDisplayLabelsInternal(value: string): RoadDisplayLabels {
  const canonical = value.trim().replace(/\s+/gu, " ");
  const parts = splitRoad(canonical);
  let base = parts.base;
  let trailingNumber: number | undefined;
  const trailing = base.match(/([零一二兩三四五六七八九十]+)$/u);
  if (trailing && trailing.index && trailing.index > 0) {
    trailingNumber = numberValue(trailing[1]);
    if (trailingNumber !== undefined) base = base.slice(0, trailing.index);
  }
  const englishBase = romanizedBase(base);
  const jaBase = localizedBase(base, "ja");
  const koBase = localizedBase(base, "ko");
  const englishNumber = trailingNumber === undefined ? "" : ` ${ordinal(trailingNumber)}`;
  const localNumber = trailingNumber === undefined ? "" : String(trailingNumber);
  const suffix = parts.suffix;
  const en = parts.section !== undefined
    ? `${romanizedBase(base)} Road, Section ${parts.section}`
    : `${englishBase}${englishNumber}${suffix ? ` ${suffix[1]}` : ""}`;
  const ja = parts.section !== undefined
    ? `${jaBase}道路 第${parts.section}区間`
    : `${jaBase}${localNumber}${suffix ? suffix[2] : "道路"}`;
  const ko = parts.section !== undefined
    ? `${koBase}로 제${parts.section}구간`
    : `${koBase}${localNumber}${suffix ? suffix[3] : "도로"}`;
  return { "zh-TW": canonical, en, ja, ko };
}

export function getRoadDisplayLabels(value: string, _scope?: RoadScope): RoadDisplayLabels {
  return getRoadDisplayLabelsInternal(value);
}

export function getLocalizedRoadDisplayLabel(value: string, locale: ExperienceLocale, scope?: RoadScope): string {
  return getRoadDisplayLabels(value, scope)[locale];
}

export function getRoadDisplayCoverageStatus(value: string, scope?: RoadScope): { canonical: string; labels: RoadDisplayLabels; unresolved: boolean } {
  const labels = getRoadDisplayLabels(value, scope);
  return { canonical: value.trim(), labels, unresolved: Object.values(labels).some((label) => !label.trim()) };
}
