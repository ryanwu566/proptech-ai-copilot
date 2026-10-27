import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { AUTO_BRIEF_STEP_IDS, classifyDemographics, classifyMarketResult, classifyMoney, classifyNearby, classifyRiskModel, combineLocationParts, createAutoBriefController, finalRunStatus, normalizeAutoBriefRun, precheckAutoBrief, restoreAutoBriefRun } from "./auto-brief.ts";
// @ts-expect-error Native TS runner extension.
import { autoBriefCopy } from "./auto-brief-copy.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { buildDemoCases } from "./demo-cases.ts";
// @ts-expect-error Native TS runner extension.
import { DEMO_CASE_A_ID } from "./demo-case-ids.ts";
// @ts-expect-error Native TS runner extension.
import { buildRiskEvidenceModel } from "./risk-evidence-model.ts";
import type { AutoBriefPortInput, AutoBriefPorts, AutoBriefRun, AutoBriefStepOutcome, AutoBriefStore } from "./auto-brief";
import type { SavedCase } from "../case-storage";
import type { PropertyCaseWorkspace } from "./workspace-model";

const NEARBY = { version: 1, source: "google_places", origin: { lat: 24.16525, lng: 120.64555 }, radiusM: 800, checkedAt: "2026-10-07T03:00:00.000Z", partial: false, successfulCategories: ["transport", "shopping", "food", "school", "medical", "park"],
  places: [{ id: "p1", name: "Station", category: "transport", kind: "rail", lat: 24.166, lng: 120.646, distanceM: 120 }] };
const DEMOGRAPHICS = { version: 1, origin: { lat: 24.16525, lng: 120.64555 }, checkedAt: "2026-10-07T03:00:00.000Z",
  village: { status: "resolved", county: "臺中市", town: "西屯區", village: "潮洋里", village_code: "66000060-020", district_code: "66000060", source: "nlsc_village_boundary", source_vintage: "11409", reason: "" },
  demographics: { status: "no_data", reason: "no_rows" } };

function confirmedCase(id = "case-a", patch: (row: SavedCase) => void = () => undefined): SavedCase {
  const row = e9Case(id);
  row.data.nearbyFacilities = structuredClone(NEARBY) as SavedCase["data"]["nearbyFacilities"];
  row.data.villageDemographics = structuredClone(DEMOGRAPHICS) as SavedCase["data"]["villageDemographics"];
  if (id !== "case-a") {
    row.data.nearbyFacilities!.origin = { ...NEARBY.origin };
    row.data.villageDemographics!.origin = { ...DEMOGRAPHICS.origin };
  }
  patch(row);
  return row;
}

type Calls = Record<"market" | "location" | "risk" | "geocode", number>;

function harness(rows: SavedCase[], overrides: Partial<Record<keyof AutoBriefPorts, (input: AutoBriefPortInput) => Promise<AutoBriefStepOutcome>>> = {}) {
  const db = new Map(rows.map((row) => [row.id, row]));
  const calls: Calls = { market: 0, location: 0, risk: 0, geocode: 0 };
  const writes: string[] = [];
  const stored = new Map<string, AutoBriefRun>();
  const store: AutoBriefStore = { read: (id) => stored.get(id) ?? null, write: (run) => { stored.set(run.caseId, JSON.parse(JSON.stringify(run))); } };
  const readWorkspace = (id: string): PropertyCaseWorkspace | null => { const row = db.get(id); return row ? adaptSavedCaseToWorkspace(row) : null; };
  const port = (key: keyof AutoBriefPorts, fallback: AutoBriefStepOutcome) => async (input: AutoBriefPortInput) => {
    calls[key] += 1;
    const outcome = await (overrides[key]?.(input) ?? Promise.resolve(fallback));
    if (input.canCommit()) writes.push(`${input.binding.caseId}:${key}`);
    return outcome;
  };
  const realPorts: AutoBriefPorts = {
    market: port("market", { status: "available", reason: null }),
    location: port("location", { status: "available", reason: "reused_saved", parts: { nearby: "available", demographics: "available" }, reused: true }),
    risk: port("risk", { status: "available", reason: null }),
  };
  let tick = 0;
  const controller = createAutoBriefController({ readWorkspace, realPorts, store, now: () => `2026-10-27T00:00:${String(tick++ % 60).padStart(2, "0")}.000Z` });
  return { controller, calls, writes, db, stored, store, readWorkspace, realPorts };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

async function waitFor(predicate: () => boolean) {
  for (let tick = 0; tick < 200 && !predicate(); tick += 1) await new Promise((done) => setTimeout(done, 1));
  assert.ok(predicate(), "condition not reached");
}

const statuses = (run: AutoBriefRun) => Object.fromEntries(run.steps.map((step) => [step.id, step.status]));

test("confirmed case starts and runs Market, Location, Risk once each in canonical order", async () => {
  const order: string[] = [];
  const h = harness([confirmedCase()], {
    market: async () => { order.push("market"); return { status: "available", reason: null }; },
    location: async () => { order.push("location"); return { status: "available", reason: null, parts: { nearby: "available", demographics: "available" } }; },
    risk: async () => { order.push("risk"); return { status: "available", reason: null }; },
  });
  const run = await h.controller.start("case-a");
  assert.deepEqual(order, ["market", "location", "risk"]);
  assert.deepEqual({ market: h.calls.market, location: h.calls.location, risk: h.calls.risk, geocode: h.calls.geocode }, { market: 1, location: 1, risk: 1, geocode: 0 });
  assert.equal(run.mode, "real_case");
  assert.equal(run.steps.every((step) => step.startedAt && step.completedAt), true);
  assert.equal(typeof run.gapCount, "number");
});

test("unconfirmed location blocks start with needs_location and zero acquisitions", async () => {
  const h = harness([confirmedCase("case-a", (row) => { delete row.data.propertyIdentityAnchor; })]);
  const run = await h.controller.start("case-a");
  assert.equal(run.status, "needs_location");
  assert.equal(run.reason, "location_unconfirmed");
  assert.deepEqual(h.calls, { market: 0, location: 0, risk: 0, geocode: 0 });
  assert.equal(run.steps.every((step) => step.status === "pending"), true);
});

test("revalidation, pending wrong-district candidate and incomplete administrative area all block", () => {
  const stale = adaptSavedCaseToWorkspace(confirmedCase("case-a", (row) => { row.data.propertyIdentityAnchor!.revalidation = { status: "needs_revalidation", conflicts: [] }; }));
  assert.deepEqual(precheckAutoBrief(stale), { ok: false, reason: "location_revalidation" });
  const pending = { ...adaptSavedCaseToWorkspace(confirmedCase()), pendingLocationCandidate: { kind: "blocked" } } as unknown as PropertyCaseWorkspace;
  assert.deepEqual(precheckAutoBrief(pending), { ok: false, reason: "location_pending_candidate" });
  const incomplete = adaptSavedCaseToWorkspace(confirmedCase("case-a", (row) => { row.data.propertyIdentityAnchor!.administrative_location.district = ""; }));
  assert.deepEqual(precheckAutoBrief(incomplete), { ok: false, reason: "location_admin_incomplete" });
  assert.deepEqual(precheckAutoBrief(null), { ok: false, reason: "case_missing" });
});

test("blocked candidate case cannot start", async () => {
  const h = harness([confirmedCase("case-a", (row) => { row.data.propertyIdentityAnchor!.revalidation = { status: "needs_revalidation", conflicts: [] }; })]);
  const run = await h.controller.start("case-a");
  assert.equal(run.status, "needs_location");
  assert.equal(h.calls.market + h.calls.location + h.calls.risk, 0);
});

test("saved Nearby and demographics are classified for reuse; missing stays unavailable, never safe", () => {
  const workspace = adaptSavedCaseToWorkspace(confirmedCase());
  assert.equal(classifyNearby(workspace.location.nearbyFacilities), "available");
  assert.equal(classifyDemographics(workspace.location.villageDemographics), "no_data");
  assert.equal(classifyNearby(undefined), "unavailable");
  assert.equal(classifyNearby({ ...NEARBY, partial: true } as never), "partial");
  assert.deepEqual(combineLocationParts("available", "available", true), { status: "available", reason: "reused_saved", parts: { nearby: "available", demographics: "available" }, reused: true });
  assert.equal(combineLocationParts("available", "no_data", true).status, "partial");
  assert.equal(combineLocationParts("unavailable", "unavailable", false).status, "unavailable");
});

test("market no_data / unavailable / partial map to their own statuses", () => {
  const base = e9Case().data.marketInsight!;
  assert.equal(classifyMarketResult(base).status, "available");
  assert.equal(classifyMarketResult({ ...base, data_status: "no_data" }).status, "no_data");
  assert.equal(classifyMarketResult({ ...base, data_status: "unavailable" }).status, "unavailable");
  assert.equal(classifyMarketResult(undefined).status, "unavailable");
  assert.equal(classifyMarketResult({ ...base, transaction_count: 4, transaction_volume: 4 }).status, "partial");
});

test("risk keeps each layer independent: partial stays partial, all-unknown is unavailable", () => {
  const workspace = adaptSavedCaseToWorkspace(confirmedCase());
  assert.equal(classifyRiskModel(workspace.risk).status, "partial");
  assert.equal(classifyRiskModel(null).status, "unavailable");
  const allUnknown = { rows: [{}, {}], unknownEvidenceCount: 2 } as never;
  assert.equal(classifyRiskModel(allUnknown).status, "unavailable");
  const none = { rows: [{}], unknownEvidenceCount: 0 } as never;
  assert.equal(classifyRiskModel(none).status, "available");
  assert.equal(typeof buildRiskEvidenceModel, "function");
});

test("Money with saved inputs is reviewed; affordability without income stays partial", () => {
  const workspace = adaptSavedCaseToWorkspace(confirmedCase());
  assert.equal(workspace.finance?.freshness.status, "current");
  assert.deepEqual(classifyMoney(workspace), { status: "partial", reason: "money_partial" });
});

test("Money without inputs is needs_input and the workflow still continues to the Brief", async () => {
  const h = harness([confirmedCase("case-a", (row) => { delete row.data.financeEvidence; })]);
  const run = await h.controller.start("case-a");
  assert.equal(statuses(run).money, "needs_input");
  assert.equal(run.steps.find((step) => step.id === "money")?.reason, "money_inputs_missing");
  assert.equal(statuses(run).brief, "available");
  assert.equal(run.status, "completed_with_gaps");
});

test("provider no_data, unavailable and partial Risk complete with gaps, never as success", async () => {
  const h = harness([confirmedCase()], {
    market: async () => ({ status: "no_data", reason: "no_data" }),
    location: async () => ({ status: "unavailable", reason: "provider_unavailable", parts: { nearby: "unavailable", demographics: "unavailable" } }),
    risk: async () => ({ status: "partial", reason: "partial_evidence" }),
  });
  const run = await h.controller.start("case-a");
  assert.deepEqual(statuses(run), { market: "no_data", location: "unavailable", risk: "partial", money: "partial", brief: "available" });
  assert.equal(run.status, "completed_with_gaps");
  assert.equal(run.steps.find((step) => step.id === "location")?.retryable, true);
  assert.equal(run.steps.find((step) => step.id === "market")?.retryable, false);
});

test("a throwing provider port becomes unavailable without a raw error", async () => {
  const h = harness([confirmedCase()], { risk: async () => { throw new Error("upstream 503 secret=abc"); } });
  const run = await h.controller.start("case-a");
  assert.equal(statuses(run).risk, "unavailable");
  assert.doesNotMatch(JSON.stringify(run), /503|secret/);
});

test("all steps available completes; any gap is completed_with_gaps", async () => {
  const full = harness([confirmedCase()]);
  const fullRun = await full.controller.start("case-a");
  // e9 Money lacks income, so a real case with complete evidence still truthfully has a Money gap.
  assert.equal(fullRun.status, "completed_with_gaps");
  assert.equal(finalRunStatus(fullRun.steps.map((step) => ({ ...step, status: "available" as const }))), "completed");
});

test("cancel stops future steps, ignores the late result and keeps earlier evidence", async () => {
  const gate = deferred<AutoBriefStepOutcome>();
  const h = harness([confirmedCase()], { location: () => gate.promise });
  const pending = h.controller.start("case-a");
  await waitFor(() => h.controller.getRun("case-a")?.currentStep === "location");
  const cancelled = h.controller.cancel("case-a");
  assert.equal(cancelled?.status, "cancelled");
  gate.resolve({ status: "available", reason: null });
  await pending;
  const run = h.controller.getRun("case-a")!;
  assert.equal(run.status, "cancelled");
  assert.deepEqual(statuses(run), { market: "available", location: "skipped", risk: "skipped", money: "skipped", brief: "skipped" });
  assert.equal(h.calls.risk, 0);
  assert.deepEqual(h.writes, ["case-a:market"]);
});

test("a second run invalidates the first; its late response cannot overwrite the newer run", async () => {
  const first = deferred<AutoBriefStepOutcome>();
  let marketCall = 0;
  const h = harness([confirmedCase()], { market: () => ++marketCall === 1 ? first.promise : Promise.resolve({ status: "available", reason: null }) });
  const one = h.controller.start("case-a");
  await waitFor(() => marketCall === 1);
  const firstRunId = h.controller.getRun("case-a")!.runId;
  const two = await h.controller.start("case-a");
  first.resolve({ status: "no_data", reason: "no_data" });
  await one;
  const run = h.controller.getRun("case-a")!;
  assert.notEqual(run.runId, firstRunId);
  assert.equal(run.runId, two.runId);
  assert.equal(statuses(run).market, "available");
  assert.equal(h.writes.filter((row) => row === "case-a:market").length, 1);
});

test("Address A → B: a late A response never commits after the case moves to B", async () => {
  const gate = deferred<AutoBriefStepOutcome>();
  let committed: boolean | null = null;
  const h = harness([confirmedCase()], { risk: async (input) => { const outcome = await gate.promise; committed = input.canCommit(); return outcome; } });
  const pending = h.controller.start("case-a");
  await waitFor(() => h.controller.getRun("case-a")?.currentStep === "risk");
  // The user re-confirms case-a at Address B while the A risk request is in flight.
  const moved = h.db.get("case-a")!;
  moved.data.propertyIdentityAnchor = { ...moved.data.propertyIdentityAnchor!, journey_anchor_id: "journey-browser-11111111-2222-4333-8444-999999999999", coordinates: { latitude: 25.03, longitude: 121.56 } };
  gate.resolve({ status: "available", reason: null });
  const run = await pending;
  assert.equal(committed, false);
  assert.equal(run.status, "needs_location");
  assert.equal(run.reason, "location_changed");
  assert.equal(statuses(run).risk, "skipped");
  assert.equal(h.writes.includes("case-a:risk"), false);
});

test("starting case B supersedes a running case A; A's late response is dropped", async () => {
  const gate = deferred<AutoBriefStepOutcome>();
  const h = harness([confirmedCase(), confirmedCase("case-b")], { market: (input) => input.binding.caseId === "case-a" ? gate.promise : Promise.resolve({ status: "available", reason: null }) });
  const a = h.controller.start("case-a");
  await waitFor(() => h.calls.market === 1);
  const b = await h.controller.start("case-b");
  gate.resolve({ status: "available", reason: null });
  await a;
  assert.equal(h.controller.getRun("case-a")?.status, "cancelled");
  assert.equal(b.caseId, "case-b");
  assert.equal(h.writes.includes("case-a:market"), false);
});

test("refresh: a persisted running run restores as interrupted and never resumes by itself", async () => {
  const gate = deferred<AutoBriefStepOutcome>();
  let locationCalls = 0;
  const h = harness([confirmedCase()], { location: () => ++locationCalls === 1 ? gate.promise : Promise.resolve({ status: "available", reason: null }) });
  void h.controller.start("case-a");
  await waitFor(() => locationCalls === 1);
  // A fresh controller is what a page reload creates.
  const reloaded = createAutoBriefController({ readWorkspace: h.readWorkspace, realPorts: h.realPorts, store: h.store });
  const before = { ...h.calls };
  const restored = reloaded.getRun("case-a")!;
  assert.equal(restored.status, "interrupted");
  assert.equal(statuses(restored).market, "available");
  assert.equal(statuses(restored).location, "pending");
  assert.deepEqual(h.calls, before);
  // Continue is an explicit decision that runs only what never finished.
  const next = await reloaded.continue("case-a")!;
  assert.equal(h.calls.market, before.market);
  assert.equal(h.calls.location, before.location + 1);
  assert.equal(next.status, "completed_with_gaps");
  gate.resolve({ status: "available", reason: null });
});

test("reopening a completed run, opening the Brief, Compare or Report triggers zero acquisitions", async () => {
  const h = harness([confirmedCase()]);
  await h.controller.start("case-a");
  const after = { ...h.calls };
  const reopened = createAutoBriefController({ readWorkspace: h.readWorkspace, realPorts: h.realPorts, store: h.store });
  for (let index = 0; index < 3; index += 1) assert.equal(reopened.getRun("case-a")?.status, "completed_with_gaps");
  assert.equal(reopened.continue("case-a"), null);
  assert.deepEqual(h.calls, after);
});

test("a saved run for a previous location anchor is not shown", async () => {
  const h = harness([confirmedCase()]);
  await h.controller.start("case-a");
  h.db.get("case-a")!.data.propertyIdentityAnchor!.journey_anchor_id = "journey-browser-11111111-2222-4333-8444-999999999999";
  assert.equal(restoreAutoBriefRun(h.stored.get("case-a")!, h.readWorkspace("case-a")), null);
  assert.equal(h.controller.getRun("case-a"), null);
});

test("explicit single-domain retry is bounded and reruns only that domain plus Money/Brief", async () => {
  let riskCalls = 0;
  const h = harness([confirmedCase()], { risk: async () => (++riskCalls === 1 ? { status: "unavailable", reason: "provider_unavailable" } : { status: "available", reason: null }) });
  const first = await h.controller.start("case-a");
  assert.equal(statuses(first).risk, "unavailable");
  assert.equal(h.controller.retryStep("case-a", "market"), null);
  const retried = await h.controller.retryStep("case-a", "risk")!;
  assert.equal(statuses(retried).risk, "available");
  assert.deepEqual({ market: h.calls.market, location: h.calls.location, risk: h.calls.risk }, { market: 1, location: 1, risk: 2 });
  assert.equal(retried.runId, first.runId);
});

test("DEMO_FIXTURE uses saved snapshots only: zero provider calls, same step model", async () => {
  const demo = buildDemoCases("en")[0];
  const h = harness([demo], {
    market: async () => { throw new Error("live market called"); },
    location: async () => { throw new Error("live location called"); },
    risk: async () => { throw new Error("live risk called"); },
  });
  const run = await h.controller.start(DEMO_CASE_A_ID);
  assert.equal(run.mode, "demo_fixture");
  assert.deepEqual(h.calls, { market: 0, location: 0, risk: 0, geocode: 0 });
  assert.deepEqual(run.steps.map((step) => step.id), ["market", "location", "risk", "money", "brief"]);
  assert.equal(run.steps.every((step) => step.status !== "pending" && step.status !== "running"), true);
  // The showcase story is truthful: complete market and location snapshots, partial risk and money.
  assert.deepEqual(statuses(run), { market: "available", location: "available", risk: "partial", money: "partial", brief: "available" });
  assert.equal(run.status, "completed_with_gaps");
  const again = await h.controller.start(DEMO_CASE_A_ID);
  assert.deepEqual(statuses(again), statuses(run));
});

test("stored runs are shape-checked; malformed storage is discarded", () => {
  assert.equal(normalizeAutoBriefRun(null), null);
  assert.equal(normalizeAutoBriefRun({ runId: "x", caseId: "a", mode: "evil", status: "running", steps: [] }), null);
  const ok = normalizeAutoBriefRun({ runId: "x", caseId: "a", mode: "real_case", status: "completed", anchorId: "j", startedAt: "t", updatedAt: "t", currentStep: null, reason: null, gapCount: 2,
    steps: ["market", "location", "risk", "money", "brief"].map((id) => ({ id, status: "available", startedAt: "t", completedAt: "t", reason: null, retryable: true, providerError: "secret" })) });
  assert.equal(ok?.steps.length, 5);
  assert.doesNotMatch(JSON.stringify(ok), /secret/);
});

test("four locales carry the same complete Auto Brief copy without raw step ids or reason codes", () => {
  const locales = ["zh-TW", "en", "ja", "ko"] as const;
  const keys = Object.keys(autoBriefCopy.en).sort();
  for (const id of AUTO_BRIEF_STEP_IDS) assert.ok(keys.includes(`step_${id}`));
  for (const locale of locales) {
    assert.deepEqual(Object.keys(autoBriefCopy[locale]).sort(), keys, locale);
    for (const [key, value] of Object.entries(autoBriefCopy[locale]) as Array<[string, string]>) {
      assert.ok(value.trim(), `${locale}.${key}`);
      assert.doesNotMatch(value, /(needs_input|no_data|completed_with_gaps|provider_unavailable|location_[a-z_]+|money_[a-z_]+)/, `${locale}.${key}`);
    }
  }
  assert.equal(autoBriefCopy.en.start, "One-click analysis");
  assert.equal(autoBriefCopy.en.run_completed_with_gaps, "Completed with gaps");
  assert.equal(autoBriefCopy.en.run_needs_location, "Location must be confirmed first");
  for (const locale of ["zh-TW", "ja", "ko"] as const) assert.doesNotMatch(autoBriefCopy[locale].start + autoBriefCopy[locale].cancel + autoBriefCopy[locale].viewBrief, /[A-Za-z]/, locale);
});

test("page unload suspends silently: an aborted request is not recorded and the run restores as interrupted", async () => {
  const gate = deferred<AutoBriefStepOutcome>();
  const h = harness([confirmedCase()], { risk: (input) => new Promise((resolve) => { input.signal.addEventListener("abort", () => resolve({ status: "unavailable", reason: "provider_unavailable" })); void gate.promise; }) });
  const pending = h.controller.start("case-a");
  await waitFor(() => h.calls.risk === 1);
  h.controller.suspend();
  await pending;
  assert.equal(h.stored.get("case-a")?.status, "running");
  assert.equal(h.controller.getRun("case-a")?.status, "interrupted");
  assert.equal(h.calls.risk, 1);
});
