import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { buildCasePulse, presentCasePulse } from "./case-pulse.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { emptyDecisionRoom } from "../decision-room-store.ts";
import type { RoomRead } from "../decision-room-store";

const workspace = () => adaptSavedCaseToWorkspace(e9Case());
const empty = (): RoomRead => ({ status: "empty", room: emptyDecisionRoom("case-a") });

test("never-located case does not acquire a confirmed location or fabricated activity", () => {
  const saved = e9Case();
  saved.data = { inputs: saved.data.inputs };
  const pulse = buildCasePulse(adaptSavedCaseToWorkspace(saved), empty());
  assert.equal(pulse.items[0].state, "not_queried");
  assert.equal(pulse.items[0].message, "unconfirmed");
  assert.equal(pulse.activity, null);
});

test("confirmed location means address/coordinate association only", () => {
  const pulse = buildCasePulse(workspace(), empty());
  assert.equal(pulse.items[0].state, "known");
  assert.equal(pulse.items[0].message, "located");
});

test("Market saved state preserves its limited summary semantics", () => {
  const item = buildCasePulse(workspace(), empty()).items[1];
  assert.equal(item.state, "available");
  assert.equal(item.message, "limited");
});

for (const [status, state, message] of [
  ["unavailable", "unavailable", "unavailable"],
  ["stale", "needs_attention", "stale"],
  ["insufficient", "needs_attention", "insufficient"],
  ["not_started", "not_queried", "notQueried"],
] as const) test(`Market ${status} is never promoted to available`, () => {
  const w = workspace();
  w.marketPrice.market.status = status;
  assert.deepEqual(buildCasePulse(w, empty()).items[1], { section: "market", state, message, href: "/cases/case-a/market" });
});

test("Risk unknown remains unknown when saved legacy results lack layer evidence", () => {
  const w = workspace();
  w.risk = null;
  assert.equal(buildCasePulse(w, empty()).items[2].message, "unknown");
});

test("Risk matched evidence retains unresolved verification and unknown layer counts", () => {
  const item = buildCasePulse(workspace(), empty()).items[2];
  assert.equal(item.state, "needs_attention");
  assert.equal(item.message, "riskReview");
  assert.deepEqual(item.counts, { matched: 1, verification: 2, unknown: 1 });
});

test("Risk with no matches describes the saved query, never safety", () => {
  const w = workspace();
  w.risk!.rows = w.risk!.rows.filter((row) => row.usability === "no_match");
  w.risk!.materialEvidenceCount = 0;
  w.risk!.unknownEvidenceCount = 0;
  w.risk!.verificationActions = [];
  assert.equal(buildCasePulse(w, empty()).items[2].message, "noMatch");
});

test("Money reports saved assumptions without inventing completeness", () => {
  const item = buildCasePulse(workspace(), empty()).items[3];
  assert.equal(item.state, "available");
  assert.equal(item.message, "moneySaved");
});

test("Money with unavailable saved evidence is not reported as available", () => {
  const w = workspace();
  w.finance!.calculation.usability = "unavailable";
  const item = buildCasePulse(w, empty()).items[3];
  assert.equal(item.state, "unavailable");
});

test("Money with insufficient saved assumptions requires attention", () => {
  const w = workspace();
  w.finance!.calculation.completeness = "insufficient";
  const item = buildCasePulse(w, empty()).items[3];
  assert.equal(item.state, "needs_attention");
  assert.equal(item.message, "insufficient");
});

test("stale Money and revalidated identity remain attention states", () => {
  const w = workspace();
  w.identity.state = "revalidation_required";
  w.finance!.freshness.status = "stale";
  const pulse = buildCasePulse(w, empty());
  assert.equal(pulse.items[0].message, "reconfirm");
  assert.equal(pulse.items[3].message, "stale");
});

test("Decision outstanding counts open work and manual follow-ups once each", () => {
  const room = emptyDecisionRoom("case-a");
  room.items = ["checklist", "task", "question"].map((kind, i) => ({ id: `${i}`, kind: kind as "task", title: "Work", owner: "", dueDate: "", status: "open", resolution: "" }));
  room.verifications = [{ id: "check", topic: "Visit", outcome: "needs_follow_up", sourceUrl: "", sourceNote: "Observed", checkedDate: "2026-10-21", checkedBy: "Buyer" }];
  assert.equal(buildCasePulse(workspace(), { status: "ready", room }).items[4].counts?.outstanding, 4);
  room.items[1].status = "done";
  assert.equal(buildCasePulse(workspace(), { status: "ready", room }).items[4].counts?.outstanding, 3);
});

test("unreadable room never claims zero outstanding actions", () => {
  const item = buildCasePulse(workspace(), { status: "corrupt" }).items[4];
  assert.equal(item.state, "unavailable");
  assert.equal(item.counts, undefined);
});

test("empty room says no recorded actions without claiming the case is complete", () => {
  assert.equal(buildCasePulse(workspace(), empty()).items[4].message, "noActions");
});

test("latest activity selects actual evidence timestamp and ignores dataset publication date", () => {
  const w = workspace();
  w.marketPrice.source.updatedAt = "2099-01-01";
  w.risk!.freshness.checkedAt = "2026-10-20T08:00:00Z";
  assert.deepEqual(buildCasePulse(w, empty()).activity, { section: "risk", at: "2026-10-20T08:00:00Z" });
});

test("nearby saved evidence changes Location and provides reliable activity", () => {
  const w = workspace();
  w.location.nearbyFacilities = { version: 1, source: "google_places", origin: { lat: 24.16525, lng: 120.64555 }, radiusM: 800, checkedAt: "2026-10-21T01:00:00Z", partial: false, successfulCategories: ["food", "school", "park", "medical", "shopping", "transport"], places: [] };
  const pulse = buildCasePulse(w, empty());
  assert.equal(pulse.items[0].message, "nearbySaved");
  assert.deepEqual(pulse.activity, { section: "nearby", at: "2026-10-21T01:00:00Z" });
});

test("invalid timestamps are omitted without falling back to snapshot time", () => {
  const w = workspace();
  w.location.property.checkedAt = "bad";
  w.risk!.freshness.checkedAt = "";
  w.finance!.freshness.calculatedAt = null;
  assert.equal(buildCasePulse(w, empty()).activity, null);
});

test("impossible calendar timestamps cannot fabricate recent activity", () => {
  const w = workspace();
  w.location.property.checkedAt = "2026-02-30T10:00:00Z";
  w.risk!.freshness.checkedAt = "2026-02-31T10:00:00Z";
  w.finance!.freshness.calculatedAt = "2026-04-31T24:00:00Z";
  assert.equal(buildCasePulse(w, empty()).activity, null);
});

test("activity requires a timezone and compares offset timestamps as instants", () => {
  const w = workspace();
  w.location.property.checkedAt = "2026-10-21T10:00:00";
  w.risk!.freshness.checkedAt = "2026-10-21T09:00:00+08:00";
  w.finance!.freshness.calculatedAt = "2026-10-21T02:00:00Z";
  assert.deepEqual(buildCasePulse(w, empty()).activity, { section: "money", at: "2026-10-21T02:00:00Z" });
});

test("navigation targets the encoded current case and the five requested pages", () => {
  const w = workspace();
  w.caseId = "a/b ?";
  assert.deepEqual(buildCasePulse(w, empty()).items.map((item) => item.href), ["location", "market", "risk", "finance", "decision-room"].map((path) => `/cases/a%2Fb%20%3F/${path}`));
});

for (const [locale, labels, activity] of [
  ["zh-TW", ["位置", "市場", "風險", "資金", "決策室"], "最近證據"],
  ["en", ["Location", "Market", "Risk", "Money", "Decision"], "Latest evidence"],
  ["ja", ["所在地", "市場", "リスク", "資金", "意思決定"], "最新の根拠"],
  ["ko", ["위치", "시장", "위험", "자금", "의사결정"], "최근 근거"],
] as const) test(`${locale} localizes every Pulse label and factual status without score language`, () => {
  const view = presentCasePulse(buildCasePulse(workspace(), empty()), locale);
  assert.deepEqual(view.items.map((item) => item.label), [...labels]);
  assert.ok(view.activity?.startsWith(activity));
  const text = JSON.stringify(view);
  assert.doesNotMatch(text, /%|％|score|confidence|readiness|complete|完成率|分數|スコア|점수/i);
  if (locale !== "en") assert.doesNotMatch(view.items.map((item) => `${item.label} ${item.text}`).join(" "), /Location|Market|Risk|Money|Decision|saved|unknown|available/i);
});
