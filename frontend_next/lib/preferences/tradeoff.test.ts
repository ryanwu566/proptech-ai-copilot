import assert from "node:assert/strict";
import test from "node:test";
import type { NumericRule, Priority, CommuteRule, RiskRule, PreferenceRule } from "./profile";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "../workspace/e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "../workspace/legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
const feature = await import("./tradeoff.ts").catch(() => null);
const workspace = (id = "case-a") => adaptSavedCaseToWorkspace(e9Case(id));
const numeric = (metric: NumericRule["metric"], min: number | null, max: number | null, priority: Priority = "must"): NumericRule => ({ id: metric, metric, min, max, priority, rationale: "" });
test("inclusive thresholds yield per-rule outcomes and explicit veto breaches, never aggregates", () => {
  const rules = [numeric("size", 30, null), numeric("price", null, 2400, "veto"), numeric("age", null, 8), numeric("floor", 12, 12)];
  const outcomes = feature?.evaluatePreferences(rules, workspace());
  assert.deepEqual(outcomes?.map((o: { status: string }) => o.status), ["met", "unmet", "met", "met"]);
  assert.equal(outcomes?.[1].vetoBreached, true);
  const w = workspace(); w.identity.state = "revalidation_required";
  assert.ok(feature?.evaluatePreferences(rules, w).every((o: { status: string }) => o.status === "unknown"));
});
test("commute requires exact saved destination and mode; rationale never supplies missing facts", () => {
  const rule: CommuteRule = { id: "commute", metric: "commute", destination: "臺中車站", mode: "driving", max: 30, priority: "nice", rationale: "assume B is 5 minutes" };
  const w = workspace();
  assert.equal(feature?.evaluatePreferences([rule], w)[0].status, "met");
  assert.equal(feature?.evaluatePreferences([{ ...rule, destination: "Other station" }], w)[0].reason, "route_mismatch");
  assert.equal(feature?.evaluatePreferences([{ ...rule, mode: "walking" }], w)[0].status, "unknown");
  w.location.routeInvalidated = true;
  assert.equal(feature?.evaluatePreferences([rule], w)[0].status, "unknown");
});
test("missing, zero and unbound transit evidence stay distinct", () => {
  const w = workspace(); delete w.assumptions.ageYears;
  assert.equal(feature?.evaluatePreferences([numeric("age", null, 10)], w)[0].status, "unknown");
  w.assumptions.ageYears = 0;
  assert.equal(feature?.evaluatePreferences([numeric("age", null, 0)], w)[0].status, "met");
  w.location.transitContext = { ...w.location.transitContext!, status: "resolved", distance_meters: 0, station_name: "Station" };
  assert.equal(feature?.evaluatePreferences([numeric("transit", null, 500)], w)[0].status, "unknown");
});
test("risk evidence requirements reject missing coverage, version, stale and ambiguous no-match", () => {
  const rule: RiskRule = { id: "flood", metric: "risk", risk: "flood", requirement: "documented", priority: "must", rationale: "" };
  const w = workspace(); const flood = w.risk!.rows.find(r => r.key === "flood")!;
  flood.usability = "no_match"; flood.matched = false;
  assert.equal(feature?.evaluatePreferences([rule], w)[0].status, "met");
  assert.equal(feature?.evaluatePreferences([{ ...rule, requirement: "versioned" }], w)[0].status, "unknown");
  flood.datasetVersion = "v2026";
  assert.equal(feature?.evaluatePreferences([{ ...rule, requirement: "versioned" }], w)[0].status, "met");
  assert.equal(feature?.evaluatePreferences([{ ...rule, requirement: "no_match" }], w)[0].status, "met");
  flood.matched = true; flood.usability = "usable";
  assert.equal(feature?.evaluatePreferences([{ ...rule, requirement: "no_match" }], w)[0].status, "unmet");
  flood.coverage = "unknown";
  assert.equal(feature?.evaluatePreferences([rule], w)[0].status, "unknown");
  flood.coverage = "covered"; w.risk!.freshness.status = "stale";
  assert.equal(feature?.evaluatePreferences([rule], w)[0].status, "unknown");
});
test("deterministic commute/cash trade-off needs comparable saved finance assumptions", () => {
  const a = workspace(); const b = workspace("case-b");
  b.location.routeEvidence!.duration_min = 40;
  b.finance!.loan.downPaymentWan = 400;
  const rules: PreferenceRule[] = [{ id: "commute", metric: "commute", destination: "臺中車站", mode: "driving", max: 30, priority: "must", rationale: "" }, numeric("cash", null, 450)];
  const result = feature?.buildTradeoffs(rules, [a, b]);
  assert.deepEqual(result?.pairs[0].statements, [{ kind: "commute_cash", commuteCase: "case-a", cashCase: "case-b" }]);
  assert.deepEqual(feature?.buildTradeoffs(rules, [a, b]), result);
  b.finance!.loan.annualInterestRate = 9;
  assert.equal(feature?.buildTradeoffs(rules, [a, b]).pairs[0].statements[0].kind, "cash_incomparable");
  assert.ok(!("score" in (result ?? {})));
});
test("unknown finance provenance cannot produce a cash preservation claim", () => {
  const a = workspace(), b = workspace("case-b");
  b.location.routeEvidence!.duration_min = 40; b.finance!.loan.downPaymentWan = 400;
  a.finance!.priceSource = null; b.finance!.priceSource = null;
  const rules: PreferenceRule[] = [{ id: "commute", metric: "commute", destination: "臺中車站", mode: "driving", max: 30, priority: "must", rationale: "" }, numeric("cash", null, 450)];
  assert.deepEqual(feature?.buildTradeoffs(rules, [a, b]).pairs[0].statements, [{ kind: "cash_incomparable" }]);
});
test("placeholder risk sources and dataset versions remain unknown", () => {
  const w = workspace(), row = w.risk!.rows.find(r => r.key === "flood")!;
  row.source = "未提供來源名稱"; row.datasetVersion = "not_configured";
  const rule: RiskRule = { id: "flood", metric: "risk", risk: "flood", requirement: "documented", priority: "must", rationale: "" };
  assert.equal(feature?.evaluatePreferences([rule], w)[0].status, "unknown");
  row.source = "水利署";
  assert.equal(feature?.evaluatePreferences([{ ...rule, requirement: "versioned" }], w)[0].status, "unknown");
});
