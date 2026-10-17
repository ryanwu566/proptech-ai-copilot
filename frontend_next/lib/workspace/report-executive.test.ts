import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { reportEvidenceReferences } from "./document-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportExecutiveSummary, EXECUTIVE_LIMITS } from "./report-executive.ts";
// @ts-expect-error Native TS runner extension.
import { reportExecutiveCopy } from "./report-executive-copy.ts";

import type { ExecutiveAttention, ExecutiveKeyNumber, ReportExecutiveSummary } from "./report-executive";

const GENERATED = "2026-10-07T04:00:00Z";
type Mutate = (row: ReturnType<typeof e9Case>) => void;
function build(mutate: Mutate = () => {}, id = "case-a") {
  const row = e9Case(id); mutate(row);
  const evidence = projectCaseEvidence(adaptSavedCaseToWorkspace(row));
  const citations = reportEvidenceReferences(evidence);
  return { evidence, citations, summary: buildReportExecutiveSummary(evidence, citations, GENERATED) };
}
const key = (summary: ReportExecutiveSummary, id: ExecutiveKeyNumber["id"]) => summary.keyNumbers.find((item) => item.id === id);
function attention<I extends ExecutiveAttention["id"]>(summary: ReportExecutiveSummary, id: I) { return summary.attention.find((item): item is Extract<ExecutiveAttention, { id: I }> => item.id === id); }

test("known evidence produces cited key numbers that resolve to existing report citations", () => {
  const { summary, citations } = build();
  assert.equal(summary.contract, "report-executive-v1");
  assert.deepEqual(summary.keyNumbers.map((item: { id: string }) => item.id), ["asking", "asking_unit", "market", "housing", "commute"]);
  assert.equal(key(summary, "asking")?.value, 2480);
  assert.equal(key(summary, "asking")?.trust, "user_entered");
  assert.equal(key(summary, "housing")?.value, 55111);
  assert.equal(key(summary, "housing")?.trust, "saved_calculation");
  assert.equal(key(summary, "commute")?.value, 24);
  const ids = new Set(citations.map((citation: { id: string }) => citation.id));
  for (const item of [...summary.keyNumbers, ...summary.attention]) for (const ref of item.refs) {
    assert.ok(ids.has(ref.citationId), `${item.id} cites ${ref.citationId}`);
    assert.equal(citations.find((citation: { id: string }) => citation.id === ref.citationId)!.observationId, ref.fieldId);
  }
  assert.ok(summary.keyNumbers.length <= EXECUTIVE_LIMITS.keyNumbers && summary.attention.length <= EXECUTIVE_LIMITS.attention && summary.open.areas.length <= EXECUTIVE_LIMITS.openAreas);
  assert.equal(summary.snapshot.origin, "saved_snapshot");
  assert.equal(summary.snapshot.autoRefresh, false);
  assert.equal(summary.snapshot.generatedAt, GENERATED);
});

test("derived asking unit price cites every input and is never labelled as a source value", () => {
  const { summary } = build();
  const derived = key(summary, "asking_unit")!;
  assert.equal(derived.trust, "derived");
  assert.equal(derived.value, 82.67);
  assert.deepEqual(derived.refs.map((ref) => ref.fieldId), ["price-asking", "property-area", "market-p25", "market-p75"]);
  assert.equal(derived.position, "above");
  // Without a saved band the derivation keeps only its own two inputs and makes no comparison.
  const { summary: noMarket } = build((row) => { delete row.data.marketInsight; });
  assert.deepEqual(key(noMarket, "asking_unit")!.refs.map((ref) => ref.fieldId), ["price-asking", "property-area"]);
  assert.equal(key(noMarket, "asking_unit")!.position, null);
  assert.equal(key(noMarket, "market"), undefined);
});

test("missing evidence never produces a fake number and remains an open item", () => {
  const { summary } = build((row) => { delete row.data.financeEvidence; delete row.data.commuteRoute; delete row.inputSummary.areaPing; row.data.inputs.area_ping = 0; });
  assert.equal(key(summary, "housing"), undefined);
  assert.equal(key(summary, "commute"), undefined);
  assert.equal(key(summary, "asking_unit"), undefined);
  assert.ok(summary.keyNumbers.every((item: { value: number }) => Number.isFinite(item.value) && item.value !== 0));
  const finance = summary.open.areas.find((area: { domain: string }) => area.domain === "finance");
  assert.ok(finance && finance.count > 0);
  assert.ok(summary.open.areas.find((area: { domain: string }) => area.domain === "overview")!.items.some((item: { gapId: string }) => item.gapId === "identity-legal"));
  assert.equal(summary.open.total, build((row) => { delete row.data.financeEvidence; delete row.data.commuteRoute; delete row.inputSummary.areaPing; row.data.inputs.area_ping = 0; }).evidence.gaps.length);
});

test("unknown, unavailable and no-match risk stay unresolved and never read as safe", () => {
  const { summary } = build();
  const unresolved = attention(summary, "risk_unresolved")!;
  assert.equal(unresolved.count, 6);
  assert.ok(unresolved.labels!.includes("淹水"));
  // The no-match row is cited; not-run/unavailable/unsupported rows are gap-backed, not invented citations.
  assert.deepEqual(unresolved.refs.map((ref) => ref.fieldId), ["risk-flood"]);
  assert.ok(unresolved.gapIds.includes("risk-geological_sensitivity") && unresolved.gapIds.includes("risk-active_fault"));
  assert.deepEqual(attention(summary, "risk_match")!.refs.map((ref) => ref.fieldId), ["risk-landslide"]);
  for (const locale of ["en", "zh-TW", "ja", "ko"] as const) {
    const copy = reportExecutiveCopy[locale];
    assert.match(copy.risk_unresolved, /safe|安全|안전/);
    assert.doesNotMatch(Object.values(copy).join("\n"), /recommend(ed)? (to )?buy|best (property|case)|winner|最佳物件|推薦購買/i);
  }
  const { summary: unavailable } = build((row) => { row.data.terrainReference!.layers = []; });
  assert.equal(attention(unavailable, "risk_match"), undefined);
  assert.equal(attention(unavailable, "risk_unresolved")!.count, 7);
});

test("stale evidence stays stale: no current key number and a cited historical signal", () => {
  const { summary, evidence } = build((row) => { row.data.marketInsight!.freshness_status = "stale"; });
  assert.equal(evidence.price.marketMedianUnit.value, null);
  assert.equal(key(summary, "market"), undefined);
  assert.equal(key(summary, "asking_unit")!.position, null);
  const stale = attention(summary, "stale")!;
  assert.ok(stale.refs.some((ref) => ref.fieldId === "market-unit"));
  assert.ok(stale.refs.every((ref) => ref.state === "stale"));
  assert.ok(stale.count! >= stale.labels!.length);
});

test("conflicting saved prices are surfaced with both inputs and not resolved", () => {
  // Persistence rejects inconsistent finance records, so model the conflict in the projected snapshot.
  const { evidence } = build(); evidence.finance.price.value = 2300;
  const summary = buildReportExecutiveSummary(evidence, reportEvidenceReferences(evidence), GENERATED);
  const conflict = attention(summary, "conflicting_price");
  assert.ok(conflict);
  assert.deepEqual(conflict.refs.map((ref: { fieldId: string }) => ref.fieldId), ["finance-price", "price-active"]);
  assert.equal(conflict.finance, 2300); assert.equal(conflict.selected, 2480);
  assert.equal(key(summary, "asking")?.value, 2480);
  assert.equal(summary.attention[0].id, "conflicting_price");
});

test("affordability without income stays not assessed and carries no conclusion", () => {
  const { summary } = build();
  const item = attention(summary, "affordability_not_assessed")!;
  assert.deepEqual(item.refs.map((ref) => ref.fieldId), ["finance-affordability"]);
  assert.ok(item.gapIds.includes("finance-income"));
  assert.deepEqual(Object.keys(item).sort(), ["gapIds", "id", "refs"]);
  assert.ok(summary.keyNumbers.every((entry: { refs: Array<{ fieldId: string }> }) => entry.refs.every((ref) => !["finance-burden", "finance-affordability"].includes(ref.fieldId))));
});

test("another case's citations cannot support this report", () => {
  const { evidence } = build();
  const other = build(() => {}, "case-b");
  const leaked = buildReportExecutiveSummary(evidence, other.citations, GENERATED);
  assert.deepEqual(leaked.keyNumbers, []);
  assert.ok(leaked.attention.every((item: { refs: unknown[] }) => item.refs.length === 0));
  assert.equal(JSON.stringify(leaked).includes("case-b"), false);
  assert.equal(leaked.caseId, "case-a");
  // Mixed lists keep only this case's references.
  const mixed = buildReportExecutiveSummary(evidence, [...other.citations, ...reportEvidenceReferences(evidence)], GENERATED);
  assert.ok(mixed.keyNumbers.flatMap((item: { refs: Array<{ citationId: string }> }) => item.refs).every((ref: { citationId: string }) => ref.citationId.startsWith("ec1.case-a.")));
});

test("missing citation drops the executive item instead of showing it uncited", () => {
  const { evidence, citations } = build();
  const withoutArea = citations.filter((citation: { observationId: string }) => citation.observationId !== "property-area");
  const summary = buildReportExecutiveSummary(evidence, withoutArea, GENERATED);
  assert.equal(key(summary, "asking_unit"), undefined);
  assert.equal(key(summary, "asking")?.value, 2480);
});

test("identical input gives identical output and does not mutate inputs or depend on providers", async () => {
  const { evidence, citations } = build();
  const before = JSON.stringify({ evidence, citations });
  const original = globalThis.fetch;
  globalThis.fetch = (() => { throw new Error("provider call"); }) as typeof fetch;
  try {
    const first = buildReportExecutiveSummary(evidence, citations, GENERATED);
    const second = buildReportExecutiveSummary(structuredClone(evidence), structuredClone(citations), GENERATED);
    assert.deepEqual(first, second);
    assert.equal(JSON.stringify(first), JSON.stringify(second));
  } finally { globalThis.fetch = original; }
  assert.equal(JSON.stringify({ evidence, citations }), before);
  const source = readFileSync(new URL("./report-executive.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /fetch\(|localStorage|sessionStorage|Date\.now|new Date\(|XMLHttpRequest|api\//);
});

test("copy catalogue covers all four locales with identical keys", () => {
  const keys = Object.keys(reportExecutiveCopy.en).sort();
  for (const locale of ["zh-TW", "ja", "ko"] as const) assert.deepEqual(Object.keys(reportExecutiveCopy[locale]).sort(), keys);
});

test("a stale risk match is not shown as a current match and stays unresolved", () => {
  const { evidence } = build();
  const landslide = evidence.risk.find((row: { key: string }) => row.key === "landslide")!;
  landslide.evidence.historicalValue = landslide.evidence.value; landslide.evidence.value = null; landslide.evidence.status = "stale";
  const summary = buildReportExecutiveSummary(evidence, reportEvidenceReferences(evidence), GENERATED);
  assert.equal(attention(summary, "risk_match"), undefined);
  assert.equal(attention(summary, "risk_unresolved")!.count, 7);
  assert.ok(attention(summary, "stale")!.labels.includes("山崩"));
  assert.match(reportExecutiveCopy.en.risk_unresolved, /stale/);
});

test("an estimate-based selected price is never labelled user-entered", () => {
  const { evidence } = build();
  evidence.price.basis.value = "成交資料推估"; evidence.price.active.value = 2300;
  const summary = buildReportExecutiveSummary(evidence, reportEvidenceReferences(evidence), GENERATED);
  const selected = key(summary, "selected")!;
  assert.equal(selected.trust, "saved_estimate");
  assert.deepEqual(selected.refs.map((ref) => ref.fieldId), ["price-active", "price-basis"]);
  for (const locale of ["en", "zh-TW", "ja", "ko"] as const) assert.ok(reportExecutiveCopy[locale].saved_estimate);
});

test("band position uses the unrounded unit price", () => {
  const { evidence } = build();
  evidence.price.asking.value = 2999.88; evidence.price.area.value = 30; evidence.price.marketP25.value = 100; evidence.price.marketP75.value = 120;
  const summary = buildReportExecutiveSummary(evidence, reportEvidenceReferences(evidence), GENERATED);
  assert.equal(key(summary, "asking_unit")!.value, 100);
  assert.equal(key(summary, "asking_unit")!.position, "below");
});

test("a saved assessed affordability state is not contradicted, and an uncited not-assessed state stays visible", () => {
  const { evidence } = build();
  evidence.finance.affordability.value = "依保存假設已評估";
  assert.equal(attention(buildReportExecutiveSummary(evidence, reportEvidenceReferences(evidence), GENERATED), "affordability_not_assessed"), undefined);
  const fresh = build();
  const withoutState = fresh.citations.filter((citation: { observationId: string }) => citation.observationId !== "finance-affordability");
  const item = attention(buildReportExecutiveSummary(fresh.evidence, withoutState, GENERATED), "affordability_not_assessed")!;
  assert.deepEqual(item.refs, []);
  assert.ok(item.gapIds.includes("finance-income"));
});
