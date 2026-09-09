import {
  PROPERTY_COMPARISON_MAX_CASES,
  PROPERTY_COMPARISON_MIN_CASES,
} from "@/lib/property-comparison";
import type {
  CompareDataState,
  CompareMetric,
  NormalizedCompareDataset,
  PropertyCompareCase,
} from "@/lib/vnext-compare/types";

export const COMPARE_MIN_CASES = PROPERTY_COMPARISON_MIN_CASES;
export const COMPARE_MAX_CASES = PROPERTY_COMPARISON_MAX_CASES;

export type CompareFieldKey =
  | "identity"
  | "askingPrice"
  | "area"
  | "buildingType"
  | "valuation"
  | "downPayment"
  | "monthlyMortgage"
  | "monthlyHoldingCost"
  | "location"
  | "terrain"
  | "tax"
  | "warnings"
  | "freshness"
  | "sources"
  | "nextChecks";

export const COMPARE_FIELD_GROUPS: Array<{ label: string; fields: CompareFieldKey[] }> = [
  { label: "物件與身分", fields: ["identity", "askingPrice", "area", "buildingType"] },
  { label: "估價與資金", fields: ["valuation", "downPayment", "monthlyMortgage", "monthlyHoldingCost"] },
  { label: "位置與風險", fields: ["location", "terrain", "tax", "warnings"] },
  { label: "證據與後續", fields: ["freshness", "sources", "nextChecks"] },
];

const STATE_LABELS: Record<CompareDataState, string> = {
  known: "已知",
  unknown: "未知",
  unavailable: "暫時無法取得",
  partial: "部分資料",
  limited: "涵蓋有限",
  stale: "資料可能過期",
  conflicting: "資料衝突",
  no_match: "未命中（不代表沒有風險）",
  not_assessed: "尚未評估",
  unverified: "尚未驗證",
  malformed: "格式不正確",
};

const NO_VALUE_STATES = new Set<CompareDataState>([
  "unknown",
  "unavailable",
  "no_match",
  "not_assessed",
  "malformed",
]);

export function stateLabel(state: CompareDataState): string {
  return STATE_LABELS[state];
}

export function normalizeComparisonDataset(input: readonly PropertyCompareCase[]): NormalizedCompareDataset {
  const seen = new Set<string>();
  const cases: PropertyCompareCase[] = [];
  const issues: NormalizedCompareDataset["issues"] = [];

  input.forEach((item, itemIndex) => {
    const caseId = item.caseId.trim();
    if (!caseId) {
      issues.push({ code: "empty_case_id", itemIndex, message: `第 ${itemIndex + 1} 筆資料缺少案件 ID，已排除。` });
      return;
    }
    if (seen.has(caseId)) {
      issues.push({ code: "duplicate_case_id", itemIndex, message: `案件 ID「${caseId}」重複；為避免錯置或合併，重複資料已排除。` });
      return;
    }
    seen.add(caseId);
    cases.push(normalizeCase({ ...item, caseId }));
  });

  return { cases, issues };
}

function normalizeCase(item: PropertyCompareCase): PropertyCompareCase {
  const valuationTransferable = item.valuation.transferable === true && item.valuation.state === "known";
  const valuationLimitation = valuationTransferable
    ? item.valuation.limitation
    : item.valuation.limitation || "估價未通過既有移轉與可信度門檻。";
  const unavailableValuation = (metric: CompareMetric): CompareMetric => ({
    ...metric,
    value: null,
    state: item.valuation.state === "malformed" ? "malformed" : "unavailable",
    limitation: valuationLimitation,
  });

  return {
    ...item,
    title: boundedText(item.title, "未命名案件"),
    locationSummary: boundedText(item.locationSummary, "未提供位置摘要"),
    caseUpdatedAt: validDate(item.caseUpdatedAt),
    askingPrice: normalizeMetric(item.askingPrice),
    area: normalizeMetric(item.area),
    buildingType: {
      ...item.buildingType,
      value: item.buildingType.value?.trim() || null,
      state: item.buildingType.value?.trim() ? item.buildingType.state : "unknown",
    },
    valuation: {
      ...item.valuation,
      transferable: valuationTransferable,
      limitation: valuationLimitation,
      low: valuationTransferable ? normalizeMetric(item.valuation.low) : unavailableValuation(item.valuation.low),
      midpoint: valuationTransferable ? normalizeMetric(item.valuation.midpoint) : unavailableValuation(item.valuation.midpoint),
      high: valuationTransferable ? normalizeMetric(item.valuation.high) : unavailableValuation(item.valuation.high),
    },
    downPayment: normalizeMetric(item.downPayment),
    monthlyMortgage: normalizeMetric(item.monthlyMortgage),
    monthlyHoldingCost: normalizeMetric(item.monthlyHoldingCost),
    sources: item.sources.map((source) => ({
      ...source,
      retrievedAt: validDate(source.retrievedAt),
      effectiveAt: validDate(source.effectiveAt),
    })),
  };
}

function boundedText(value: string, fallback: string): string {
  const trimmed = value.trim();
  if (!trimmed) return fallback;
  return trimmed.length > 240 ? `${trimmed.slice(0, 237)}…` : trimmed;
}

function validDate(value: string | null): string | null {
  return value && !Number.isNaN(Date.parse(value)) ? value : null;
}

function normalizeMetric(metric: CompareMetric): CompareMetric {
  if (metric.value === null || NO_VALUE_STATES.has(metric.state)) return { ...metric, value: null };
  const moneyUnit = metric.unit === "currency" || metric.unit === "currency_10k";
  const malformedShape = (moneyUnit && metric.currency === null) || (!moneyUnit && metric.currency !== null);
  if (malformedShape || !Number.isFinite(metric.value) || metric.value < 0 || (metric.value === 0 && metric.basis !== "down_payment")) {
    return {
      ...metric,
      value: null,
      state: "malformed",
      limitation: "數值不是此欄位可接受的有限值，未以 0 代替。",
    };
  }
  return metric;
}

export type MetricDelta =
  | { kind: "reference"; label: string }
  | { kind: "comparable"; difference: number; label: string }
  | { kind: "unavailable"; reason: string; label: string };

export function compareMetricDelta(metric: CompareMetric, reference: CompareMetric, isReference: boolean): MetricDelta {
  if (isReference) return { kind: "reference", label: "參考基準" };
  if (metric.value === null) return unavailableDelta(`此案為${stateLabel(metric.state)}`);
  if (reference.value === null) return unavailableDelta(`參考案為${stateLabel(reference.state)}`);
  if (metric.state !== "known") return unavailableDelta(`此案為${stateLabel(metric.state)}`);
  if (reference.state !== "known") return unavailableDelta(`參考案為${stateLabel(reference.state)}`);
  if (metric.basis !== reference.basis) return unavailableDelta("價格或數值基礎不同");
  if (metric.unit !== reference.unit) return unavailableDelta("單位不同");
  if (metric.currency !== reference.currency) return unavailableDelta("幣別不同");
  if (metric.period !== reference.period) return unavailableDelta("計算期間不同");
  const difference = metric.value - reference.value;
  return { kind: "comparable", difference, label: formatDelta(difference, metric) };
}

function unavailableDelta(reason: string): MetricDelta {
  return { kind: "unavailable", reason, label: `無法比較：${reason}` };
}

export function formatMetric(metric: CompareMetric): string {
  if (metric.value === null) return stateLabel(metric.state);
  const formatted = formatNumber(metric.value);
  const unit = {
    currency_10k: metric.currency === "USD" ? "萬美元" : "萬元",
    currency: metric.currency === "USD" ? "美元" : "元",
    ping: "坪",
    sqm: "平方公尺",
  }[metric.unit];
  const period = metric.period === "monthly" ? "／月" : metric.period === "annual" ? "／年" : "";
  return `${formatted} ${unit}${period}`;
}

function formatDelta(difference: number, metric: CompareMetric): string {
  const sign = difference > 0 ? "+" : difference < 0 ? "−" : "±";
  const absolute = Math.abs(difference);
  const unit = { currency_10k: metric.currency === "USD" ? "萬美元" : "萬元", currency: metric.currency === "USD" ? "美元" : "元", ping: "坪", sqm: "平方公尺" }[metric.unit];
  const period = metric.period === "monthly" ? "／月" : metric.period === "annual" ? "／年" : "";
  return `相較基準 ${sign}${formatNumber(absolute)} ${unit}${period}`;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 2 }).format(value);
}

export function visibleCompareFields(cases: readonly PropertyCompareCase[], differencesOnly: boolean): Set<CompareFieldKey> {
  const all = new Set(COMPARE_FIELD_GROUPS.flatMap((group) => group.fields));
  if (!differencesOnly || cases.length < COMPARE_MIN_CASES) return all;
  return new Set([...all].filter((field) => fieldAlwaysVisible(field) || hasDifference(cases, field) || mustPreserve(cases, field)));
}

function fieldAlwaysVisible(field: CompareFieldKey): boolean {
  return ["warnings", "freshness", "sources", "nextChecks"].includes(field);
}

function hasDifference(cases: readonly PropertyCompareCase[], field: CompareFieldKey): boolean {
  return new Set(cases.map((item) => fieldSignature(item, field))).size > 1;
}

function mustPreserve(cases: readonly PropertyCompareCase[], field: CompareFieldKey): boolean {
  return cases.some((item) => {
    if (field === "identity") return item.identity.status !== "confirmed";
    if (field === "askingPrice") return item.askingPrice.state !== "known";
    if (field === "area") return item.area.state !== "known";
    if (field === "buildingType") return item.buildingType.state !== "known";
    if (field === "valuation") return !item.valuation.transferable || item.valuation.state !== "known";
    if (field === "downPayment") return item.downPayment.state !== "known";
    if (field === "monthlyMortgage") return item.monthlyMortgage.state !== "known";
    if (field === "monthlyHoldingCost") return item.monthlyHoldingCost.state !== "known";
    if (field === "location") return item.location.state !== "known";
    if (field === "terrain") return item.terrain.state !== "available" || item.terrain.riskLevel === "high";
    if (field === "tax") return item.tax.state !== "known";
    return false;
  });
}

function fieldSignature(item: PropertyCompareCase, field: CompareFieldKey): string {
  if (field === "identity") return JSON.stringify(item.identity);
  if (field === "askingPrice") return metricSignature(item.askingPrice);
  if (field === "area") return metricSignature(item.area);
  if (field === "buildingType") return JSON.stringify(item.buildingType);
  if (field === "valuation") return JSON.stringify(item.valuation);
  if (field === "downPayment") return metricSignature(item.downPayment);
  if (field === "monthlyMortgage") return metricSignature(item.monthlyMortgage);
  if (field === "monthlyHoldingCost") return metricSignature(item.monthlyHoldingCost);
  if (field === "location") return JSON.stringify(item.location);
  if (field === "terrain") return JSON.stringify(item.terrain);
  if (field === "tax") return JSON.stringify(item.tax);
  if (field === "warnings") return JSON.stringify(item.warnings);
  if (field === "freshness") return JSON.stringify([item.caseUpdatedAt, ...item.sources.map((source) => [source.retrievedAt, source.effectiveAt, source.state])]);
  if (field === "sources") return JSON.stringify(item.sources);
  return JSON.stringify(item.nextChecks);
}

function metricSignature(metric: CompareMetric): string {
  return JSON.stringify([metric.value, metric.state, metric.unit, metric.currency, metric.period, metric.basis]);
}
