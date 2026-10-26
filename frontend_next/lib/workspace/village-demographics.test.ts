import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Native TS runner extension.
import { captureVillageDemographics, demographicsFreshness, demographicsViewState, formatBoundaryVintage, formatDemographicsCount, formatDemographicsMonth, formatDemographicsRatio, formatDemographicsSignedCount, formatDemographicsSignedRatio, formatHouseholdSizeValue, hasSufficientTrend, normalizeVillageDemographics, shareVillageDemographicsAcquisition, villageDemographicsMatches } from "./village-demographics.ts";
// @ts-expect-error Native TS runner extension.
import { villageDemographicsCopy } from "./village-demographics-copy.ts";

const POINT = { latitude: 25.026, longitude: 121.534 };
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

function village(overrides: Record<string, unknown> = {}) {
  return { status: "resolved", county: "臺北市", town: "大安區", village: "龍泉里", village_code: "63000020001", district_code: "63000020001", source: "nlsc_village_boundary", source_vintage: "ROC-1150817", reason: "unique_intersection", ...overrides };
}

function available(overrides: Record<string, unknown> = {}) {
  return { status: "available", reason: null, statistic_yyymm: "11507", statistic_month: "2026-07-01", total_population: 12345, household_count: 4567, average_household_size: 2.7, child_ratio: 0.121, working_age_ratio: 0.702, elderly_ratio: 0.177, first_month: "11406", last_month: "11507", observed_month_count: 13, population_change: 120, population_change_ratio: 0.0098, household_change: 45, has_month_gaps: false, trend_status: "increasing", source_provider: "RIS", source_dataset: "ODRP014", ...overrides };
}

function response(overrides: Record<string, unknown> = {}) {
  return { ...POINT, checked_at: "2026-10-26T01:00:00+00:00", village_resolution: village(), demographics: available(), ...overrides };
}

test("an available response is captured for the confirmed coordinate only", () => {
  const evidence = captureVillageDemographics(response(), POINT);
  assert.deepEqual(evidence.origin, { lat: POINT.latitude, lng: POINT.longitude });
  assert.equal(evidence.demographics.status, "available");
  assert.equal(demographicsViewState(evidence.village, evidence.demographics), "available");
  // Address B's response can never be captured for Address A's request.
  assert.throws(() => captureVillageDemographics(response({ latitude: 25.1 }), POINT));
  assert.throws(() => captureVillageDemographics(response(), { latitude: 25.026, longitude: 121.6 }));
});

test("figures for a non-unique village and malformed counts are refused, never coerced", () => {
  assert.throws(() => captureVillageDemographics(response({ village_resolution: village({ status: "ambiguous" }) }), POINT));
  assert.throws(() => captureVillageDemographics(response({ demographics: available({ total_population: -1 }) }), POINT));
  assert.throws(() => captureVillageDemographics(response({ demographics: available({ child_ratio: "0.1" }) }), POINT));
  assert.throws(() => captureVillageDemographics(response({ demographics: available({ statistic_yyymm: "11513" }) }), POINT));
});

test("zero population stays a real zero and null ratios stay insufficient", () => {
  const evidence = captureVillageDemographics(response({ demographics: available({ total_population: 0, household_count: 0, child_ratio: null, working_age_ratio: 0, elderly_ratio: null, average_household_size: null, population_change_ratio: null }) }), POINT);
  assert.equal(evidence.demographics.status, "available");
  if (evidence.demographics.status !== "available") return;
  assert.equal(evidence.demographics.total_population, 0);
  assert.equal(formatDemographicsCount(0, "en"), "0");
  assert.equal(evidence.demographics.child_ratio, null);
  assert.equal(formatDemographicsRatio(null), null);
  assert.equal(formatDemographicsRatio(0), "0.0%");
  assert.equal(formatDemographicsRatio(0.187), "18.7%");
  assert.equal(formatHouseholdSizeValue(null), null);
  assert.equal(formatHouseholdSizeValue(2.7), "2.70");
  assert.equal(formatDemographicsSignedRatio(null), null);
});

test("every outcome maps to one explicit state", () => {
  assert.equal(demographicsViewState(village({ status: "unresolved" }) as never, { status: "no_data", reason: "village_identity_not_resolved" }), "unresolved");
  assert.equal(demographicsViewState(village({ status: "ambiguous", candidate_count: 3 }) as never, { status: "no_data", reason: "village_identity_not_resolved" }), "ambiguous");
  assert.equal(demographicsViewState(village() as never, { status: "no_data", reason: "demographics_not_available_for_village_code" }), "no_data");
  assert.equal(demographicsViewState(village() as never, { status: "no_data", reason: "demographics_unavailable" }), "unavailable");
  assert.equal(demographicsViewState({ status: "unavailable", reason: "village_resolver_unavailable" } as never, { status: "no_data", reason: "demographics_unavailable" }), "unavailable");
  // A legacy payload without demographics is unavailable, never a hidden section.
  assert.equal(demographicsViewState(undefined, undefined), "unavailable");
});

test("unresolved and ambiguous captures keep only the bounded village state", () => {
  const evidence = captureVillageDemographics(response({ village_resolution: village({ status: "ambiguous", county: "x", candidate_count: 2 }), demographics: { status: "no_data", reason: "village_identity_not_resolved" } }), POINT);
  assert.equal(evidence.village.status, "ambiguous");
  assert.equal(evidence.village.county, null);
  assert.equal(evidence.village.village_code, null);
  assert.equal(evidence.village.candidate_count, 2);
});

test("trend needs two observed months; month gaps are flagged and never filled", () => {
  const trend = captureVillageDemographics(response(), POINT).demographics;
  const single = captureVillageDemographics(response({ demographics: available({ observed_month_count: 1, first_month: "11507", last_month: "11507", population_change: 0, household_change: 0, population_change_ratio: null }) }), POINT).demographics;
  const gapped = captureVillageDemographics(response({ demographics: available({ has_month_gaps: true }) }), POINT).demographics;
  assert.ok(trend.status === "available" && hasSufficientTrend(trend));
  assert.ok(single.status === "available" && !hasSufficientTrend(single));
  assert.ok(gapped.status === "available" && gapped.has_month_gaps && gapped.observed_month_count === 13);
  assert.equal(formatDemographicsSignedCount(120, "en"), "+120");
  assert.equal(formatDemographicsSignedCount(-45, "en"), "-45");
  assert.equal(formatDemographicsSignedRatio(0.0098), "+1.0%");
});

test("freshness is recomputed against today and never invents a date", () => {
  const insight = captureVillageDemographics(response(), POINT).demographics;
  assert.ok(insight.status === "available");
  assert.deepEqual(demographicsFreshness(insight, new Date(Date.UTC(2026, 8, 1))), { kind: "current", months: 2 });
  assert.deepEqual(demographicsFreshness(insight, new Date(Date.UTC(2026, 9, 26))), { kind: "stale", months: 3 });
  assert.deepEqual(demographicsFreshness(insight, new Date(Date.UTC(2026, 5, 1))), { kind: "unknown", months: null });
});

test("months, vintages and counts are localized; raw codes are not echoed", () => {
  assert.equal(formatDemographicsMonth("11507", "zh-TW"), "民國115年07月");
  assert.equal(formatDemographicsMonth("11406", "zh-TW"), "民國114年06月");
  assert.equal(formatDemographicsMonth("11507", "en"), "Jul 2026");
  assert.equal(formatDemographicsMonth("11507", "ja"), "2026年7月");
  assert.equal(formatDemographicsMonth("11507", "ko"), "2026년 7월");
  assert.equal(formatDemographicsMonth(null, "en"), null);
  assert.equal(formatDemographicsCount(12345, "en"), "12,345");
  assert.match(formatBoundaryVintage("ROC-1150817", "en") ?? "", /2026/);
  assert.equal(formatBoundaryVintage("nlsc-raw-key", "en"), null);
});

test("stored evidence revalidates on read and binds to coordinates", () => {
  const evidence = captureVillageDemographics(response(), POINT);
  const restored = normalizeVillageDemographics(JSON.parse(JSON.stringify(evidence)));
  assert.deepEqual(restored, evidence);
  assert.ok(villageDemographicsMatches(restored, POINT));
  assert.ok(!villageDemographicsMatches(restored, { latitude: POINT.latitude + 0.001, longitude: POINT.longitude }));
  assert.equal(normalizeVillageDemographics({ ...evidence, version: 2 }), undefined);
  assert.equal(normalizeVillageDemographics({ ...evidence, demographics: { status: "available" } }), undefined);
});

test("rapid repeated acquisitions for one identity share a single request", async () => {
  let calls = 0;
  const run = () => shareVillageDemographicsAcquisition("case:anchor:point", async () => { calls++; await new Promise((resolve) => setTimeout(resolve, 5)); return calls; });
  const [a, b] = await Promise.all([run(), run()]);
  assert.equal(calls, 1);
  assert.equal(a, b);
  await run();
  assert.equal(calls, 2);
});

test("all four locales carry every key, and en/ja/ko never fall back to Chinese product copy", () => {
  const keys = Object.keys(villageDemographicsCopy["zh-TW"]) as Array<keyof typeof villageDemographicsCopy["zh-TW"]>;
  for (const locale of LOCALES) {
    assert.deepEqual(Object.keys(villageDemographicsCopy[locale]).sort(), [...keys].sort(), locale);
    for (const key of keys) assert.ok(villageDemographicsCopy[locale][key].trim(), `${locale}.${key}`);
  }
  for (const key of keys) {
    assert.doesNotMatch(villageDemographicsCopy.en[key], /[㐀-鿿]/, `en.${key}`);
    // Japanese legitimately shares these Han terms with Traditional Chinese; anything else must be translated.
    if (!["village", "populationUnit", "trendDecreasing"].includes(key)) assert.notEqual(villageDemographicsCopy.ja[key], villageDemographicsCopy["zh-TW"][key], `ja.${key}`);
    assert.notEqual(villageDemographicsCopy.ko[key], villageDemographicsCopy["zh-TW"][key], `ko.${key}`);
    assert.doesNotMatch(villageDemographicsCopy.ko[key], /[㐀-鿿]/, `ko.${key}`);
    // Placeholders must survive translation.
    const placeholders = (text: string) => (text.match(/\{\{\w+\}\}/g) ?? []).sort();
    for (const locale of LOCALES) assert.deepEqual(placeholders(villageDemographicsCopy[locale][key]), placeholders(villageDemographicsCopy["zh-TW"][key]), `${locale}.${key}`);
  }
  // No locale shows raw backend identifiers.
  for (const locale of LOCALES) for (const text of Object.values(villageDemographicsCopy[locale]) as string[]) assert.doesNotMatch(text, /ODRP|VILLCODE|village_code|no_data|_unavailable|unique_intersection/);
});
