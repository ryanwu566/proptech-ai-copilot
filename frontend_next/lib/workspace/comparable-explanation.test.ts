import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
// @ts-expect-error Native TS runner extension.
import { compactActionableValuationSummary } from "./market-price-persistence.ts";
import type { SavedCase } from "../case-storage";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportModel, assessReportSnapshot } from "./compare-report-model.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
import type { ValuationResult } from "../api";
// @ts-expect-error Native TS runner extension.
const copyModule = await import("../comparable-explanation-copy.ts").catch(() => null);

const fixture = JSON.parse(readFileSync(new URL("../../../tests/fixtures/comparable-explanation-result.json", import.meta.url), "utf8")) as ValuationResult;

test("trace survives repeated summary compaction without retaining provider payloads", () => {
  const value = structuredClone(fixture);
  Object.assign(value.comparable_decision_trace!, { provider_secret: "SECRET" });
  Object.assign(value.comparable_decision_trace!.selected[0], { raw_note: "SECRET" });
  const compact = compactActionableValuationSummary(value)!;
  assert.ok(compact.comparable_decision_trace, "saved valuation must retain the bounded trace");
  assert.deepEqual(compact.comparable_decision_trace, fixture.comparable_decision_trace);
  assert.equal(JSON.stringify(compact).includes("SECRET"), false);
  assert.deepEqual(compact.comparables, []);
  assert.deepEqual(compactActionableValuationSummary(compact), compact);
});

test("saving, normalization and frozen report preserve trace with its own snapshot token", () => {
  const saved = e9Case(); saved.data.valuation = fixture;
  const reopened = JSON.parse(JSON.stringify(saved)) as SavedCase;
  reopened.data.valuation = compactActionableValuationSummary(reopened.data.valuation);
  const frozen = projectCaseEvidence(adaptSavedCaseToWorkspace(reopened)!);
  assert.deepEqual(frozen.comparableExplanation, fixture.comparable_decision_trace);
  const report = buildReportModel(frozen, "2026-10-10T03:00:00Z");
  const newer = structuredClone(reopened) as SavedCase;
  newer.data.valuation!.comparable_decision_trace!.reference_period = "2026-11";
  const current = projectCaseEvidence(adaptSavedCaseToWorkspace(newer)!);
  assert.equal(assessReportSnapshot(frozen, current, false), "snapshot_changed");
  assert.equal(report.evidence!.comparableExplanation!.reference_period, "2026-10");
});

test("legacy snapshots and malformed traces remain unavailable instead of reconstructed", () => {
  const value = structuredClone(fixture);
  delete value.comparable_decision_trace;
  assert.equal(compactActionableValuationSummary(value)!.comparable_decision_trace, undefined);
  Object.assign(value, { comparable_decision_trace: { version: "comparable-explanation-v1", selected: [] } });
  assert.equal(compactActionableValuationSummary(value)!.comparable_decision_trace, undefined);
});

test("all supported locales translate explanations and preserve unknown versus real zero", () => {
  assert.ok(copyModule, "locale resources must exist");
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    assert.ok(copyModule.comparableCopy(locale).included);
    assert.ok(Object.values(copyModule.comparableCopy(locale)).every((text) => typeof text === "string" && text.length > 0));
    assert.notEqual(copyModule.comparableCopy(locale).included, copyModule.comparableCopy(locale).excluded);
    assert.equal(copyModule.formatComparableValue(null, "area", locale), copyModule.comparableCopy(locale).unknown);
    assert.match(copyModule.formatComparableValue(0, "area", locale), /0/);
  }
  assert.equal(copyModule.comparableCopy("en").title, "Why these comparables?");
  assert.equal(copyModule.formatComparableValue(30, "area", "en"), "30.0 ping");
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    assert.ok(copyModule.formatComparableValue(600, "community_distance", locale).endsWith(copyModule.comparableCopy(locale).metres));
  }
});

test("a trace inconsistent with the valuation sample count is not promoted", () => {
  const value = structuredClone(fixture);
  value.valuation_explanation.sample_count = 9;
  assert.equal(compactActionableValuationSummary(value)!.comparable_decision_trace, undefined);
});

test("missing or contradictory exclusion counters cannot cross the save boundary", () => {
  for (const reason_counts of [{}, { rank_limit: 3 }, { scope: 3 }, { scope: 1, rank_limit: 1 }]) {
    const value = structuredClone(fixture);
    value.comparable_decision_trace!.reason_counts = reason_counts;
    assert.equal(compactActionableValuationSummary(value)!.comparable_decision_trace, undefined);
  }
});
