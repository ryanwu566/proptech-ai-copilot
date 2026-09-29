// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { TWD_PER_WAN } from "../monetary-units.ts";

export type MissingValueReason = "not_provided" | "not_estimated" | "not_included" | "not_applicable" | "unavailable" | "outside_coverage";

export const PRICE_CONCEPT_LABELS = {
  asking_price: "開價",
  user_entered_price: "比較基準價格（依輸入條件）",
  system_estimate: "成交資料推估",
  market_median: "市場成交中位數",
  comparable_transaction: "歷史成交總價",
  price_range: "成交資料推估區間",
  unit_price: "歷史成交單價",
} as const;

const missingLabels: Record<MissingValueReason, string> = {
  not_provided: "未提供",
  not_estimated: "尚未估算",
  not_included: "未納入",
  not_applicable: "不適用",
  unavailable: "目前無法取得",
  outside_coverage: "不在涵蓋範圍",
};

const numberFormat = new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 0 });
const oneDecimalFormat = new Intl.NumberFormat("zh-TW", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function finiteNonNegative(value: unknown): value is number {
  return finite(value) && value >= 0;
}

export function formatMissing(reason: MissingValueReason = "not_estimated"): string {
  return missingLabels[reason];
}

export function formatTwd(value: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  return finiteNonNegative(value) ? `NT$${numberFormat.format(value)}` : formatMissing(missing);
}

export function formatTwdAsWan(valueTwd: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  return finiteNonNegative(valueTwd) ? formatWan(valueTwd / TWD_PER_WAN, missing) : formatMissing(missing);
}

/** Format a value whose explicit input/storage contract is already ten-thousand TWD. */
export function formatWan(valueWan: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  if (!finiteNonNegative(valueWan)) return formatMissing(missing);
  const formatted = Number.isInteger(valueWan) ? numberFormat.format(valueWan) : oneDecimalFormat.format(valueWan);
  return `${formatted} 萬元`;
}

export function formatWanPerPing(valueWan: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  if (!finiteNonNegative(valueWan)) return formatMissing(missing);
  return `${oneDecimalFormat.format(valueWan)} 萬元／坪`;
}

export function formatPriceRangeWan(lowWan: number | null | undefined, highWan: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  if (!finiteNonNegative(lowWan) || !finiteNonNegative(highWan) || lowWan > highWan) return formatMissing(missing);
  const low = Number.isInteger(lowWan) ? numberFormat.format(lowWan) : oneDecimalFormat.format(lowWan);
  const high = Number.isInteger(highWan) ? numberFormat.format(highWan) : oneDecimalFormat.format(highWan);
  return `${low}–${high} 萬元`;
}

export function formatMonthlyTwd(value: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  return finiteNonNegative(value) ? `${formatTwd(value)}／月` : formatMissing(missing);
}

export function formatAnnualTwd(value: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  return finiteNonNegative(value) ? `${formatTwd(value)}／年` : formatMissing(missing);
}

export function formatPercent(ratio: number | null | undefined, missing: MissingValueReason = "not_estimated"): string {
  return finite(ratio) ? `${oneDecimalFormat.format(ratio * 100)}%` : formatMissing(missing);
}

export function formatValuationConfidence(value: unknown): string {
  return { high: "高", medium: "中等", low: "有限" }[typeof value === "string" ? value : ""] ?? "尚無法判定";
}

export function formatAreaPing(value: number | null | undefined, missing: MissingValueReason = "not_provided"): string {
  return finiteNonNegative(value) ? `${oneDecimalFormat.format(value)} 坪` : formatMissing(missing);
}

export function formatSquareMetres(value: number | null | undefined, missing: MissingValueReason = "not_provided"): string {
  return finiteNonNegative(value) ? `${oneDecimalFormat.format(value)} 平方公尺` : formatMissing(missing);
}

export function formatDistance(metres: number | null | undefined, missing: MissingValueReason = "not_provided"): string {
  if (!finiteNonNegative(metres)) return formatMissing(missing);
  if (metres < 1_000) return `${numberFormat.format(Math.round(metres))} 公尺`;
  const kilometres = metres / 1_000;
  return `${kilometres < 10 ? oneDecimalFormat.format(kilometres) : numberFormat.format(Math.round(kilometres))} 公里`;
}

export function formatDuration(minutes: number | null | undefined, missing: MissingValueReason = "not_provided"): string {
  if (!finiteNonNegative(minutes)) return formatMissing(missing);
  const rounded = Math.round(minutes);
  if (rounded < 60) return `約 ${rounded} 分鐘`;
  const hours = Math.floor(rounded / 60);
  const remainder = rounded % 60;
  return remainder ? `${hours} 小時 ${remainder} 分鐘` : `${hours} 小時`;
}

export function formatExactDate(value: string | null | undefined, missing: MissingValueReason = "not_provided"): string {
  if (typeof value !== "string") return formatMissing(missing);
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : formatMissing(missing);
}

export function formatYearMonthPeriod(start: string | null | undefined, end: string | null | undefined, missing: MissingValueReason = "not_provided"): string {
  const normalize = (value: string | null | undefined) => typeof value === "string" && /^(\d{4})-(\d{2})$/.test(value) ? value.replace("-", "/") : null;
  const normalizedStart = normalize(start);
  const normalizedEnd = normalize(end);
  return normalizedStart && normalizedEnd ? `${normalizedStart}–${normalizedEnd}` : formatMissing(missing);
}
