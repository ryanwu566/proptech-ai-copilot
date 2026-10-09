import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case, E9_NOW } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { parseSavedCasesDiagnostic } from "./saved-case-diagnostics.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportModel, assessReportSnapshot } from "./compare-report-model.ts";
import type { ChecklistId } from "./checklist-persistence";
// @ts-expect-error Native TS runner extension.
import { buildSavedCaseSnapshotUpdate } from "./case-snapshot-save.ts";
// @ts-expect-error Native TS runner extension.
const feature = await import("./evidence-checklist.ts").catch(() => null);
// @ts-expect-error Native TS runner extension.
const persistence = await import("./checklist-persistence.ts").catch(() => null);

function model(saved = e9Case()) { return projectCaseEvidence(adaptSavedCaseToWorkspace(saved)); }
function review(saved = e9Case(), id: ChecklistId = "risk-active_fault") {
  const workspace = adaptSavedCaseToWorkspace(saved);
  return feature?.setChecklistReview(workspace, id, "reviewed", E9_NOW);
}

test("missing evidence becomes compact domain actions without duplicate IDs", () => {
  assert.ok(feature, "checklist projection must exist");
  const items = feature.buildEvidenceChecklist(model());
  assert.ok(items.some((item) => item.id === "risk-active_fault"));
  assert.ok(items.some((item) => item.domain === "identity"));
  assert.equal(new Set(items.map((item) => item.id)).size, items.length);
  assert.ok(items.length <= 24);
  assert.ok(items.length < model().gaps.length);
  assert.ok(items.every((item) => item.nextAction && item.impact && item.href));
  assert.ok(items.slice(0, 3).some((item) => item.domain === "risk"), "overview prioritizes material missing risk evidence");
});

test("snapshot save preserves checklist, other-case data and optimistic concurrency", () => {
  const a = e9Case(); const b = e9Case("case-b"); const anchor = a.data.propertyIdentityAnchor!;
  const expectation = { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates! };
  const manual = review(a); assert.ok(manual);
  const compact = (data: typeof a.data) => ({ ...data, checklistReview: persistence!.normalizeChecklistReview(data.checklistReview) ?? undefined });
  const update = buildSavedCaseSnapshotUpdate([a, b], a.id, expectation, "confirmed", a.updatedAt, () => "2026-10-09T03:00:00Z", compact, manual);
  assert.equal(update.result.status, "saved"); assert.deepEqual(update.rows[1], b);
  assert.equal(feature!.buildEvidenceChecklist(model(JSON.parse(JSON.stringify(update.rows[0])))).find((item) => item.id === "risk-active_fault")?.reviewState, "reviewed");
  assert.equal(buildSavedCaseSnapshotUpdate(update.rows, a.id, expectation, "confirmed", a.updatedAt, () => E9_NOW, compact, manual).result.status, "blocked");
  assert.equal(buildSavedCaseSnapshotUpdate([a, b], b.id, expectation, "confirmed", b.updatedAt, () => E9_NOW, compact, manual).result.status, "blocked");
});

test("write-time invalidation survives switching away and back without changing the old review date", () => {
  const original = e9Case(); original.data.checklistReview = review(original); assert.ok(original.data.checklistReview);
  const switched = structuredClone(original); switched.data.propertyIdentityAnchor!.coordinates!.latitude += 0.01;
  switched.data.checklistReview = persistence!.invalidateChangedChecklist(original, switched);
  const restored = structuredClone(original); restored.data.checklistReview = switched.data.checklistReview;
  restored.data.checklistReview = persistence!.invalidateChangedChecklist(switched, restored);
  assert.equal(restored.data.checklistReview?.entries[0].state, "recheck");
  assert.equal(restored.data.checklistReview?.entries[0].reviewedAt, E9_NOW);
  assert.equal(feature!.buildEvidenceChecklist(model(restored)).find((item) => item.id === "risk-active_fault")?.reviewState, "recheck");
});

test("new usable source removes a gap while retaining the historical manual action", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved, "risk-geological_sensitivity");
  assert.ok(saved.data.checklistReview);
  const evidence = model(saved); const row = evidence.risk.find((row) => row.key === "geological_sensitivity")!;
  row.evidence = { ...row.evidence, status: "available", value: "來源有效結果", missingReason: null };
  evidence.gaps = evidence.gaps.filter((gap) => gap.id !== row.evidence.id);
  const item = feature!.buildEvidenceChecklist(evidence).find((item) => item.id === row.evidence.id)!;
  assert.equal(item.outstanding, false); assert.equal(item.reviewState, "recheck"); assert.equal(item.reviewedAt, E9_NOW);
});

test("usable matched hazards still require a material source verification action", () => {
  const saved = e9Case(); saved.data.terrainReference!.layers[1].evidence_metadata = { version: 1, usability: "usable", matched: true, source_url: null, query_condition: "radius 500m" };
  const evidence = model(saved);
  assert.equal(evidence.risk.find((item) => item.key === "landslide")?.matched, true);
  assert.equal(evidence.risk.find((item) => item.key === "landslide")?.evidence.status, "available");
  assert.ok(feature!.buildEvidenceChecklist(evidence).some((item) => item.id === "risk-landslide" && item.outstanding));
});

test("source match metadata changes invalidate a reviewed action even with the same display text", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved, "risk-flood"); assert.ok(saved.data.checklistReview);
  const evidence = model(saved); const row = evidence.risk.find((item) => item.key === "flood")!;
  row.matched = true;
  assert.equal(feature!.buildEvidenceChecklist(evidence).find((item) => item.id === "risk-flood")?.reviewState, "recheck");
});

test("unsupported and no-match retain source states; manual review never upgrades evidence", () => {
  const saved = e9Case(); const before = model(saved);
  saved.data.checklistReview = review(saved);
  const after = model(saved);
  assert.ok(saved.data.checklistReview, "manual review must be produced");
  assert.deepEqual(after.risk, before.risk);
  assert.deepEqual(after.gaps, before.gaps);
  const items = feature!.buildEvidenceChecklist(after);
  assert.equal(items.find((item) => item.id === "risk-active_fault")?.fields[0].status, "unsupported");
  assert.equal(items.find((item) => item.id === "risk-active_fault")?.reviewState, "reviewed");
  assert.equal(items.find((item) => item.id === "risk-flood")?.fields[0].status, "no_match");
  assert.match(items.find((item) => item.id === "risk-flood")?.impact ?? "", /不代表安全/);
});

test("verified zero stays numeric and unknown stays missing", () => {
  const evidence = model();
  assert.equal(evidence.finance.annualInsurance.value, 0);
  assert.equal(evidence.finance.monthlyIncome.value, null);
  assert.ok(feature?.buildEvidenceChecklist(evidence).some((item) => item.id === "finance-affordability"));
});

test("versioned allowlist survives serialization and reopening; legacy stays compatible", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved);
  assert.ok(saved.data.checklistReview);
  const parsed = parseSavedCasesDiagnostic(JSON.stringify([saved]), (row) => row);
  assert.equal(parsed.status, "ready");
  assert.equal(feature!.buildEvidenceChecklist(model(parsed.cases[0])).find((item) => item.id === "risk-active_fault")?.reviewState, "reviewed");
  assert.equal(parseSavedCasesDiagnostic(JSON.stringify([e9Case()]), (row) => row).status, "ready");
  assert.ok(feature!.buildEvidenceChecklist(model()).every((item) => item.reviewState === "not_checked"));
});

test("A/B isolation rejects copied case envelopes and does not show another case's review", () => {
  const a = e9Case(); const b = e9Case("case-b"); a.data.checklistReview = review(a);
  assert.ok(a.data.checklistReview);
  assert.ok(feature!.buildEvidenceChecklist(model(b)).every((item) => item.reviewState === "not_checked"));
  b.data.checklistReview = a.data.checklistReview;
  assert.equal(parseSavedCasesDiagnostic(JSON.stringify([b]), (row) => row).status, "partial");
});

test("identity change and revalidation preserve history but require checking again", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved);
  assert.ok(saved.data.checklistReview);
  saved.data.propertyIdentityAnchor!.coordinates!.latitude += 0.001;
  let item = feature!.buildEvidenceChecklist(model(saved)).find((item) => item.id === "risk-active_fault")!;
  assert.equal(item.reviewState, "recheck"); assert.equal(item.reviewedAt, E9_NOW);
  saved.data.propertyIdentityAnchor!.revalidation.status = "needs_revalidation";
  item = feature!.buildEvidenceChecklist(model(saved)).find((item) => item.id === "risk-active_fault")!;
  assert.equal(item.reviewState, "recheck");
});

test("source version and freshness changes invalidate only relevant review", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved, "risk-flood");
  assert.ok(saved.data.checklistReview);
  saved.data.terrainReference!.layers[0].data_version = "new-version";
  assert.equal(feature!.buildEvidenceChecklist(model(saved)).find((item) => item.id === "risk-flood")?.reviewState, "recheck");
  const unchanged = e9Case(); unchanged.data.checklistReview = review(unchanged, "risk-flood");
  unchanged.title = "rename only"; unchanged.updatedAt = "2026-10-09T00:00:00Z";
  assert.equal(feature!.buildEvidenceChecklist(model(unchanged)).find((item) => item.id === "risk-flood")?.reviewState, "reviewed");
  unchanged.data.riskEvidenceCheckedAt = "2026-10-09T00:00:00Z";
  assert.equal(feature!.buildEvidenceChecklist(model(unchanged)).find((item) => item.id === "risk-flood")?.reviewState, "recheck");
});

test("invalidation is sticky across save and identity restoration", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved);
  const workspace = adaptSavedCaseToWorkspace(saved);
  workspace.identity.state = "revalidation_required";
  const invalidated = feature?.reconcileChecklistReview(workspace);
  assert.ok(invalidated);
  saved.data.checklistReview = invalidated;
  assert.equal(feature!.buildEvidenceChecklist(model(saved)).find((item) => item.id === "risk-active_fault")?.reviewState, "recheck");
});

test("uncheck and pending preserve prior review date without claiming source verification", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved);
  assert.ok(saved.data.checklistReview);
  saved.data.checklistReview = feature!.setChecklistReview(adaptSavedCaseToWorkspace(saved), "risk-active_fault", "pending", E9_NOW);
  const item = feature!.buildEvidenceChecklist(model(saved)).find((item) => item.id === "risk-active_fault")!;
  assert.equal(item.reviewState, "pending"); assert.equal(item.reviewedAt, E9_NOW);
});

test("malformed and oversized review records fail closed, unknown properties are stripped", () => {
  const valid = review(); assert.ok(valid);
  for (const bad of [{ ...valid, version: 99 }, { ...valid, entries: [...valid.entries, valid.entries[0]] }, { ...valid, entries: Array(25).fill(valid.entries[0]) }, { ...valid, entries: [{ ...valid.entries[0], id: "invented-official-safe" }] }, { ...valid, entries: [{ ...valid.entries[0], evidenceToken: "x".repeat(20000) }] }]) {
    assert.equal(persistence?.normalizeChecklistReview(bad), null);
    const saved = e9Case(); saved.data.checklistReview = bad as never;
    assert.equal(parseSavedCasesDiagnostic(JSON.stringify([saved]), (row) => row).status, "partial");
  }
  const clean = persistence!.normalizeChecklistReview({ ...valid, credentials: "secret", raw: { provider: "payload" }, entries: valid.entries.map((entry) => ({ ...entry, notes: "private" })) });
  assert.ok(clean); assert.doesNotMatch(JSON.stringify(clean), /secret|payload|private|notes|credentials/);
});

test("report projects frozen manual actions read-only with zero fetches", () => {
  const saved = e9Case(); saved.data.checklistReview = review(saved);
  assert.ok(saved.data.checklistReview);
  const frozen = model(saved); const raw = JSON.stringify(saved);
  const oldFetch = globalThis.fetch; let calls = 0;
  globalThis.fetch = (() => { calls++; throw new Error("provider call"); }) as typeof fetch;
  try {
    const report = buildReportModel(frozen, E9_NOW);
    assert.ok(report.evidence?.checklistReview?.entries.length);
    feature!.buildEvidenceChecklist(frozen);
    assert.equal(JSON.stringify(saved), raw);
    saved.data.checklistReview = feature!.setChecklistReview(adaptSavedCaseToWorkspace(saved), "risk-active_fault", "pending", E9_NOW);
    assert.equal(assessReportSnapshot(frozen, model(saved), false), "snapshot_changed");
    assert.equal(feature!.buildEvidenceChecklist(frozen).find((item) => item.id === "risk-active_fault")?.reviewState, "reviewed");
    assert.equal(calls, 0);
  } finally { globalThis.fetch = oldFetch; }
});
