import assert from "node:assert/strict";
import test from "node:test";
import type { DecisionRoom, WorkItem } from "./decision-room-store";
// @ts-expect-error Native TS runner extension.
import { addEvidenceAction, createDecisionRoomRepository, decisionRoomGaps, emptyDecisionRoom, findEvidenceAction, decisionRoomKey } from "./decision-room-store.ts";
// @ts-expect-error Native TS runner extension.
import { actionPriority, actionsForSource, projectDecisionRoomReport, ROOM_REPORT_LIMITS } from "./decision-room-report.ts";
// @ts-expect-error Native TS runner extension.
import { decisionRoomReportCopy } from "./decision-room-report-copy.ts";
// @ts-expect-error Native TS runner extension.
import { decisionRoomCopy } from "./decision-room-copy.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./workspace/e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./workspace/legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { createDecisionRoomCaseAdapter } from "./decision-room-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { checklistIdForEvidence } from "./workspace/evidence-checklist.ts";

let clock = 0;
function setup() {
  clock = 0;
  const values = new Map<string, string>();
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); } };
  let n = 0;
  const repository = createDecisionRoomRepository(storage, () => new Date(Date.UTC(2026, 9, 20, 0, 0, clock++)).toISOString(), () => `event-${n++}`);
  return { values, repository };
}
const item = (over: Partial<WorkItem> & Pick<WorkItem, "id">): WorkItem => ({ kind: "task", title: over.id, owner: "", dueDate: "", status: "open", resolution: "", ...over });
function saved(repository: ReturnType<typeof setup>["repository"], room: DecisionRoom): DecisionRoom {
  const result = repository.save(room, room.revision);
  assert.equal(result.status, "saved");
  return (result as { room: DecisionRoom }).room;
}

test("manual verification action saves with owner, defaults to manual origin and stamps created/updated", () => {
  const { repository } = setup();
  const room = emptyDecisionRoom("case-a");
  room.items.push(item({ id: "v1", kind: "verification", title: "Ask management about basement flooding", owner: "Buyer" }));
  const next = saved(repository, room);
  const row = next.items[0]!;
  assert.equal(row.kind, "verification");
  assert.equal(row.owner, "Buyer");
  assert.equal(row.origin, "manual");
  assert.equal(row.sourceKey, "");
  assert.ok(row.createdAt && row.createdAt === row.updatedAt);
  assert.equal(next.history.at(-1)?.kind, "verification_added");
});

test("status changes persist across reopen; DONE stops counting, BLOCKED stays outstanding", () => {
  const { repository } = setup();
  let room = emptyDecisionRoom("case-a");
  room.items.push(item({ id: "v1", kind: "verification" }), item({ id: "q1", kind: "question" }), item({ id: "t1" }));
  room = saved(repository, room);
  const created = room.items[0]!.createdAt;
  room = { ...room, items: room.items.map((row) => row.id === "v1" ? { ...row, status: "done", resolution: "Committee confirmed no record", owner: "Partner" } : row.id === "t1" ? { ...row, status: "blocked" } : row.id === "q1" ? { ...row, status: "in_progress" } : row) };
  saved(repository, room);
  const reopened = repository.read("case-a");
  assert.equal(reopened.status, "ready");
  const report = projectDecisionRoomReport(reopened);
  assert.deepEqual(report.counts, { total: 3, outstanding: 2, open: 0, inProgress: 1, blocked: 1, done: 1, verification: 0 });
  assert.equal(report.readiness, "outstanding");
  assert.deepEqual(report.outstanding.map((row: WorkItem) => row.id), ["t1", "q1"]);
  assert.equal(report.completed[0]?.owner, "Partner");
  const done = (reopened as { room: DecisionRoom }).room.items.find((row) => row.id === "v1")!;
  assert.equal(done.createdAt, created);
  assert.notEqual(done.updatedAt, created);
  assert.ok(!decisionRoomGaps((reopened as { room: DecisionRoom }).room, []).some((gap: { id: string }) => gap.id === "open-v1"));
  assert.ok(decisionRoomGaps((reopened as { room: DecisionRoom }).room, []).some((gap: { id: string }) => gap.id === "open-t1"));
});

test("projection orders verification, blocked, questions, other; due date then creation", () => {
  const room = emptyDecisionRoom("case-a");
  room.items.push(
    item({ id: "task", kind: "task" }), item({ id: "q", kind: "question" }), item({ id: "blockedQ", kind: "question", status: "blocked" }),
    item({ id: "v-late", kind: "verification", dueDate: "2026-12-01" }), item({ id: "v-soon", kind: "verification", dueDate: "2026-11-01" }), item({ id: "check", kind: "checklist", status: "done" }),
  );
  const report = projectDecisionRoomReport({ status: "ready", room });
  assert.deepEqual(report.outstanding.map((row: WorkItem) => row.id), ["v-soon", "v-late", "blockedQ", "q", "task"]);
  assert.equal(report.counts.verification, 2);
  assert.equal(actionPriority({ kind: "verification", status: "blocked" }), 1);
  assert.equal(report.completed.length, 1);
});

test("empty, cleared and unreadable rooms never manufacture readiness", () => {
  assert.equal(projectDecisionRoomReport({ status: "empty", room: emptyDecisionRoom("a") }).readiness, "none");
  assert.equal(projectDecisionRoomReport({ status: "corrupt" }).readiness, "unreadable");
  assert.equal(projectDecisionRoomReport(null).status, "unreadable");
  const room = emptyDecisionRoom("a");
  room.items.push(item({ id: "t", status: "done", resolution: "ok" }));
  const report = projectDecisionRoomReport({ status: "ready", room });
  assert.equal(report.readiness, "clear");
  assert.equal(report.counts.outstanding, 0);
  assert.ok(!Object.keys(report).some((key) => /score|recommend|confidence/i.test(key)));
});

test("evidence-linked action is idempotent, keeps its source section and is rejected as a duplicate", () => {
  const { repository, values } = setup();
  const input = { origin: "risk" as const, sourceKey: "risk-flood", title: "淹水潛勢", note: "向管委會確認地下室歷史淹水紀錄" };
  let room = emptyDecisionRoom("case-a");
  const first = addEvidenceAction(room, input, () => "a1");
  assert.equal(first.added, true);
  room = saved(repository, first.room);
  const second = addEvidenceAction(room, input, () => "a2");
  assert.equal(second.added, false);
  assert.equal(second.room, room);
  assert.equal(room.items.length, 1);
  assert.equal(findEvidenceAction(room, "risk-flood")?.origin, "risk");
  assert.equal(findEvidenceAction(room, "risk-flood")?.note, input.note);
  // A forced duplicate key or a manual action claiming an evidence key never persists.
  const before = values.get(decisionRoomKey("case-a"));
  assert.equal(repository.save({ ...room, items: [...room.items, { ...room.items[0]!, id: "dup" }] }, room.revision).status, "invalid");
  assert.equal(repository.save({ ...room, items: [...room.items, item({ id: "m", origin: "manual", sourceKey: "risk-flood" })] }, room.revision).status, "invalid");
  assert.equal(repository.save({ ...room, items: [...room.items, item({ id: "m", origin: "risk", sourceKey: "" })] }, room.revision).status, "invalid");
  assert.equal(values.get(decisionRoomKey("case-a")), before);
  // Manual actions with identical titles stay distinct.
  room = saved(repository, { ...room, items: [...room.items, item({ id: "m1", title: "Same" }), item({ id: "m2", title: "Same" })] });
  assert.equal(room.items.filter((row) => row.origin === "manual").length, 2);
  const report = projectDecisionRoomReport({ status: "ready", room });
  assert.equal(actionsForSource(report, "risk-flood").length, 1);
  assert.equal(actionsForSource(report, "").length, 0);
});

test("rooms saved before this change still read, normalize and accept new statuses", () => {
  const { repository, values } = setup();
  const legacy = { ...emptyDecisionRoom("case-a"), revision: 1, updatedAt: "2026-10-12T03:00:00.000Z", items: [{ id: "t1", kind: "task", title: "Get deed", owner: "", dueDate: "", status: "open", resolution: "" }], history: [] };
  values.set(decisionRoomKey("case-a"), JSON.stringify(legacy));
  const read = repository.read("case-a");
  assert.equal(read.status, "ready");
  const room = (read as { room: DecisionRoom }).room;
  assert.deepEqual({ origin: room.items[0]!.origin, sourceKey: room.items[0]!.sourceKey, note: room.items[0]!.note }, { origin: "manual", sourceKey: "", note: "" });
  const next = saved(repository, { ...room, items: [{ ...room.items[0]!, status: "in_progress" }] });
  assert.equal(next.items[0]!.status, "in_progress");
  assert.ok(next.items[0]!.createdAt);
  // Unknown statuses or origins are rejected rather than coerced.
  // @ts-expect-error hostile runtime payload
  assert.equal(repository.save({ ...next, items: [{ ...next.items[0]!, status: "approved" }] }, next.revision).status, "invalid");
  // @ts-expect-error hostile runtime payload
  assert.equal(repository.save({ ...next, items: [{ ...next.items[0]!, origin: "ai", sourceKey: "x" }] }, next.revision).status, "invalid");
});

test("case adapter offers outstanding saved-evidence checks with stable keys and section origins", () => {
  const workspace = adaptSavedCaseToWorkspace(e9Case());
  const adapter = createDecisionRoomCaseAdapter({ readDiagnostic: () => ({ status: "ready" as const, cases: [workspace], issues: [] }), subscribe: () => () => {} });
  const read = adapter.read("case-a");
  assert.equal(read.status, "ready");
  const actions = (read as { context: { evidenceActions: Array<{ origin: string; sourceKey: string; title: string }> } }).context.evidenceActions;
  assert.ok(actions.length > 0);
  assert.equal(new Set(actions.map((row) => row.sourceKey)).size, actions.length);
  for (const row of actions) assert.ok(["identity", "market", "location", "risk", "finance"].includes(row.origin), row.origin);
  assert.ok(actions.some((row) => row.origin === "risk" && row.sourceKey.startsWith("risk-")));
  // Report rows map back to the same keys.
  assert.equal(checklistIdForEvidence("risk-flood"), "risk-flood");
  assert.equal(checklistIdForEvidence("market-median"), "market-summary");
});

test("new copy covers all four locales with identical keys and no English fallback", () => {
  const keys = Object.keys(decisionRoomReportCopy.en).sort() as Array<keyof typeof decisionRoomReportCopy.en>;
  for (const locale of ["zh-TW", "ja", "ko"] as const) {
    assert.deepEqual(Object.keys(decisionRoomReportCopy[locale]).sort(), keys);
    for (const key of keys) {
      if (key === "sep") continue;
      assert.notEqual(decisionRoomReportCopy[locale][key], decisionRoomReportCopy.en[key], `${locale}.${key}`);
    }
  }
  const room = { en: decisionRoomCopy("en"), "zh-TW": decisionRoomCopy("zh-TW"), ja: decisionRoomCopy("ja"), ko: decisionRoomCopy("ko") };
  for (const key of ["verifications", "in_progress", "blocked", "note", "evidenceActions", "verification_added", "open_verification", "actionSummary"] as const) {
    for (const locale of ["zh-TW", "ja", "ko"] as const) assert.notEqual(room[locale][key], room.en[key], `${locale}.${key}`);
  }
  assert.ok(ROOM_REPORT_LIMITS.page3Rows <= 4);
});
