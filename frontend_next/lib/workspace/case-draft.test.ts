import assert from "node:assert/strict";
import test from "node:test";
import type { SavedCase } from "../case-storage";
import type { SavedCaseReadDiagnostic } from "./saved-case-diagnostics";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildAddressDraftCase, isPristineAddressDraft, MAX_DRAFT_ADDRESS_LENGTH, normalizeDraftAddress, planAddressDraft } from "./case-draft.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { parseSavedCasesDiagnostic } from "./saved-case-diagnostics.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { capturePendingLocation } from "./pending-location.ts";

const NOW = "2026-10-18T08:00:00.000Z";
const ADDRESS = "臺中市西屯區臺灣大道三段100號";
const options = { id: "draft-1", now: NOW, maxCases: 10 };
const ready = (cases: SavedCase[] = []): SavedCaseReadDiagnostic => ({ status: cases.length ? "ready" : "empty", cases, issues: [] });
const draftCase = (id = "draft-1"): SavedCase => buildAddressDraftCase(ADDRESS, { id, now: NOW })!;

test("address normalization collapses whitespace, strips control characters and bounds length", () => {
  assert.equal(normalizeDraftAddress(`  ${ADDRESS}\n\t `), ADDRESS);
  assert.equal(normalizeDraftAddress("臺北市\u0000信義區   市府路1號"), "臺北市 信義區 市府路1號");
  assert.equal(normalizeDraftAddress("   "), null);
  assert.equal(normalizeDraftAddress(42), null);
  assert.equal(normalizeDraftAddress("a".repeat(MAX_DRAFT_ADDRESS_LENGTH)), "a".repeat(MAX_DRAFT_ADDRESS_LENGTH));
  assert.equal(normalizeDraftAddress("a".repeat(MAX_DRAFT_ADDRESS_LENGTH + 1)), null);
});

test("draft is deterministic for injected id and time and records only the typed address", () => {
  const draft = draftCase();
  assert.deepEqual(draft, draftCase());
  assert.equal(draft.title, ADDRESS);
  assert.equal(draft.createdAt, NOW);
  assert.equal(draft.updatedAt, NOW);
  assert.deepEqual(draft.inputSummary, {});
  assert.equal(draft.progress, 0);
  assert.deepEqual(Object.keys(draft.data).sort(), ["inputs", "journeyContext"]);
  assert.equal(draft.data.propertyIdentityAnchor, undefined);
  assert.deepEqual(draft.data.journeyContext?.propertyContext, { addressSummary: ADDRESS, sourceLabel: "使用者輸入", selectionStatus: "partial" });
  assert.equal(buildAddressDraftCase("  ", { id: "draft-1", now: NOW }), null);
});

test("draft passes the saved-case read contract without weakening it", () => {
  const draft = draftCase();
  const read = parseSavedCasesDiagnostic(JSON.stringify([draft]), (row: SavedCase) => row);
  assert.equal(read.status, "ready");
  assert.equal(read.cases.length, 1);
});

test("workspace for a draft keeps identity unconfirmed and every evidence domain not started", () => {
  const workspace = adaptSavedCaseToWorkspace(draftCase());
  assert.equal(workspace.displayAddress, ADDRESS);
  assert.deepEqual(workspace.identity, { state: "unconfirmed", scope: "unconfirmed", anchor: null });
  for (const state of Object.values(workspace.evidence) as Array<{ query: string; completeness: string }>) {
    assert.equal(state.query, "not_started");
    assert.equal(state.completeness, "not_started");
  }
  assert.deepEqual(workspace.assumptions, { activePriceBasis: "asking" });
  assert.equal(workspace.risk, null);
  assert.equal(workspace.location.property.coordinates, null);
});

test("existing saved cases keep their stored building inputs", () => {
  const workspace = adaptSavedCaseToWorkspace(e9Case());
  assert.equal(workspace.assumptions.ageYears, 8);
  assert.equal(workspace.assumptions.floor, 12);
});

test("plan refuses unsafe storage instead of overwriting it", () => {
  assert.deepEqual(planAddressDraft(ready(), " ", options), { kind: "blocked", reason: "invalid_address" });
  assert.deepEqual(planAddressDraft({ status: "storage_unavailable", cases: [], issues: [] }, ADDRESS, options), { kind: "blocked", reason: "storage_unavailable" });
  assert.deepEqual(planAddressDraft({ status: "parse_error", cases: [], issues: [] }, ADDRESS, options), { kind: "blocked", reason: "storage_invalid" });
  assert.deepEqual(planAddressDraft({ status: "invalid_storage", cases: [], issues: [] }, ADDRESS, options), { kind: "blocked", reason: "storage_invalid" });
});

test("plan respects the saved-case limit and never evicts an existing case", () => {
  const full = Array.from({ length: 10 }, (_, index) => e9Case(`case-${index}`));
  assert.deepEqual(planAddressDraft(ready(full), ADDRESS, options), { kind: "blocked", reason: "limit_reached" });
  const plan = planAddressDraft(ready(full.slice(0, 9)), ADDRESS, options);
  assert.equal(plan.kind, "create");
});

test("plan keeps quarantined partial storage and creates alongside valid cases", () => {
  const plan = planAddressDraft({ status: "partial", cases: [e9Case()], issues: [{ caseId: null, reason: "invalid_record" }] }, ADDRESS, options);
  assert.equal(plan.kind, "create");
  assert.equal(plan.kind === "create" && plan.saved.id, "draft-1");
});

test("an untouched draft for the same address is reopened, never duplicated", () => {
  const draft = draftCase("draft-0");
  assert.deepEqual(planAddressDraft(ready([draft]), `  ${ADDRESS} `, options), { kind: "reopen", saved: draft });
  assert.equal(planAddressDraft(ready([draft]), "臺北市信義區市府路1號", options).kind, "create");
  const full = [draft, ...Array.from({ length: 9 }, (_, index) => e9Case(`case-${index}`))];
  assert.equal(planAddressDraft(ready(full), ADDRESS, options).kind, "reopen");
});

test("a pending-only draft reopens on repeated Home Start without another acquisition", () => {
  const draft = draftCase("draft-0");
  draft.data.pendingLocationCandidate = capturePendingLocation(draft, { addressInput: ADDRESS, interpretedAddress: ADDRESS, county: null, district: null, latitude: 24.16, longitude: 120.64, source: "google" });
  draft.updatedAt = "2026-10-21T01:00:00Z";
  assert.equal(planAddressDraft(ready([draft]), ADDRESS, options).kind, "reopen");
  draft.data.pendingLocationCandidate!.caseId = "foreign-case";
  assert.equal(planAddressDraft(ready([draft]), ADDRESS, options).kind, "create");
});

test("a draft with saved evidence or assumptions is no longer pristine", () => {
  const draft = draftCase("draft-0");
  assert.equal(isPristineAddressDraft(draft, ADDRESS), true);
  assert.equal(isPristineAddressDraft({ ...draft, data: { ...draft.data, marketInsight: { data_status: "available" } as unknown as SavedCase["data"]["marketInsight"] } }, ADDRESS), false);
  assert.equal(isPristineAddressDraft({ ...draft, data: { ...draft.data, journeyContext: { ...draft.data.journeyContext!, activePriceWan: 2000 } } }, ADDRESS), false);
  assert.equal(isPristineAddressDraft({ ...draft, inputSummary: { road: ADDRESS } }, ADDRESS), false);
  assert.equal(isPristineAddressDraft(e9Case(), ADDRESS), false);
});

test("the compacted stored shape of a draft stays pristine and still adapts as not started", () => {
  // compactCaseData materialises explicit undefined fields and a not-assessed valuation summary.
  const draft = draftCase();
  const compacted: SavedCase = { ...draft, data: { ...draft.data, propertyIdentityAnchor: undefined, propertySearch: undefined, valuation: undefined, trend: undefined, marketInsight: undefined, terrainReference: undefined, terrainRisk: undefined, financeEvidence: undefined, checklistReview: undefined, valuationEvidence: { status: "not_assessed", source: "none", label: "成交資料推估", value: null, range: null, confidence: null, reason: "", transferable: false } as unknown as SavedCase["data"]["valuationEvidence"] } };
  assert.equal(isPristineAddressDraft(compacted, ADDRESS), true);
  const workspace = adaptSavedCaseToWorkspace(compacted);
  for (const state of Object.values(workspace.evidence) as Array<{ query: string }>) assert.equal(state.query, "not_started");
});

test("a draft that was later updated, renamed or given building facts is not reopened", () => {
  const draft = draftCase();
  assert.equal(isPristineAddressDraft({ ...draft, updatedAt: "2026-10-18T09:00:00.000Z" }, ADDRESS), false);
  assert.equal(isPristineAddressDraft({ ...draft, title: "我的案件" }, ADDRESS), false);
  assert.equal(isPristineAddressDraft({ ...draft, data: { ...draft.data, journeyContext: { ...draft.data.journeyContext!, propertyContext: { ...draft.data.journeyContext!.propertyContext, floor: 3 } } } }, ADDRESS), false);
});
