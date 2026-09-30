import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { formatAreaPing, formatDistance, formatDuration, formatExactDate, formatMissing, formatMonthlyTwd, formatPercent, formatPriceRangeWan, formatTwd, formatTwdAsWan, formatValuationConfidence, formatWan, formatWanPerPing, formatYearMonthPeriod } from "./formatters.ts";

test("money formatters keep canonical TWD separate from explicit wan presentation", () => {
  assert.equal(formatTwd(18_500_000), "NT$18,500,000");
  assert.equal(formatTwdAsWan(18_500_000), "1,850 萬元");
  assert.equal(formatWan(1_850), "1,850 萬元");
  assert.equal(formatWanPerPing(52.4), "52.4 萬元／坪");
  assert.equal(formatPriceRangeWan(1_720, 1_980), "1,720–1,980 萬元");
  assert.equal(formatMonthlyTwd(60_752), "NT$60,752／月");
});

test("missing financial data stays distinct from a legitimate zero", () => {
  assert.equal(formatTwd(null), "尚未估算");
  assert.equal(formatMonthlyTwd(undefined, "not_provided"), "未提供");
  assert.equal(formatTwd(0), "NT$0");
  assert.equal(formatMonthlyTwd(0), "NT$0／月");
  assert.equal(formatMissing("not_included"), "未納入");
});

test("distance and duration follow commercial presentation thresholds", () => {
  assert.equal(formatDistance(999), "999 公尺");
  assert.equal(formatDistance(1_000), "1.0 公里");
  assert.equal(formatDistance(1_499), "1.5 公里");
  assert.equal(formatDistance(10_000), "10 公里");
  assert.equal(formatDuration(59), "約 59 分鐘");
  assert.equal(formatDuration(60), "1 小時");
  assert.equal(formatDuration(75), "1 小時 15 分鐘");
});

test("percent, area, exact date, and effective period keep their units and time meaning", () => {
  assert.equal(formatPercent(0.187), "18.7%");
  assert.equal(formatAreaPing(26), "26.0 坪");
  assert.equal(formatExactDate("2026-09-27T14:30:00+08:00"), "2026-09-27");
  assert.equal(formatYearMonthPeriod("2025-01", "2026-07"), "2025/01–2026/07");
});

test("valuation confidence is categorical customer language rather than a raw enum", () => {
  assert.equal(formatValuationConfidence("high"), "高");
  assert.equal(formatValuationConfidence("medium"), "中等");
  assert.equal(formatValuationConfidence("low"), "有限");
  assert.equal(formatValuationConfidence("RAW_CONFIDENCE"), "尚無法判定");
});
