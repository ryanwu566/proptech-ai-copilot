import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { createDecisionRoomRepository, emptyDecisionRoom, decisionRoomKey } from "./decision-room-store.ts";
// @ts-expect-error Native TS runner extension.
const reader = await import("./decision-room-reader.ts").catch(() => null);

test("read-only room adapter preserves repository validation and never writes", () => {
  assert.ok(reader, "read-only room adapter must exist");
  const room = emptyDecisionRoom("case/a");
  room.items.push({ id: "inspect", kind: "checklist", title: "Inspect", owner: "", dueDate: "", status: "open", resolution: "" });
  const rawValues = [null, JSON.stringify(room), "corrupt", JSON.stringify({ ...room, version: 2 }), JSON.stringify({ ...room, caseId: "other" }), JSON.stringify({ ...room, items: [{ ...room.items[0], status: "unknown" }] }), JSON.stringify({ ...room, notes: [{ id: "invalid", text: "", date: "2026-02-30" }] }), "x".repeat(1_500_001)];
  let writes = 0;
  for (const raw of rawValues) {
    const storage = { getItem(key: string) { assert.equal(key, decisionRoomKey(room.caseId)); return raw; }, setItem() { writes++; } };
    assert.deepEqual(reader.createDecisionRoomReader(storage).read(room.caseId), createDecisionRoomRepository(storage).read(room.caseId));
    assert.equal("save" in reader.createDecisionRoomReader(storage), false);
  }
  assert.equal(writes, 0);
});

test("read-only room adapter preserves DONE, follow-up, empty and blocked state", () => {
  assert.ok(reader, "read-only room adapter must exist");
  const room = emptyDecisionRoom("case-a");
  room.items.push({ id: "inspect", kind: "checklist", title: "Inspect", owner: "", dueDate: "", status: "done", resolution: "" });
  room.verifications.push({ id: "check", topic: "Inspect", outcome: "needs_follow_up", sourceUrl: "", sourceNote: "Ask seller", checkedDate: "2026-10-21", checkedBy: "Buyer" });
  const read = reader.createDecisionRoomReader({ getItem: () => JSON.stringify(room) }).read(room.caseId);
  assert.equal(read.status, "ready");
  if (read.status === "ready") {
    assert.equal(read.room.items[0].status, "done");
    assert.equal(read.room.verifications[0].outcome, "needs_follow_up");
  }
  assert.deepEqual(reader.createDecisionRoomReader({ getItem() { throw Error("blocked"); } }).read(room.caseId), { status: "unavailable" });
  assert.equal(reader.createDecisionRoomReader({ getItem: () => null }).read(room.caseId).status, "empty");
});

test("browser read-only room adapter filters same-tab and cross-tab events and unsubscribes", () => {
  assert.ok(reader, "read-only room adapter must exist");
  const original = Object.getOwnPropertyDescriptor(globalThis, "window");
  const browser = Object.assign(new EventTarget(), { localStorage: { getItem: () => null } });
  Object.defineProperty(globalThis, "window", { configurable: true, value: browser });
  try {
    const repository = reader.createBrowserDecisionRoomReader();
    assert.equal(repository.read("case/a").status, "empty");
    assert.equal("save" in repository, false);
    let calls = 0;
    const stop = repository.subscribe("case/a", () => calls++);
    browser.dispatchEvent(new CustomEvent("proptech:decision-room-changed", { detail: "other" }));
    browser.dispatchEvent(Object.assign(new Event("storage"), { key: decisionRoomKey("other") }));
    assert.equal(calls, 0);
    browser.dispatchEvent(new CustomEvent("proptech:decision-room-changed", { detail: "case/a" }));
    browser.dispatchEvent(Object.assign(new Event("storage"), { key: decisionRoomKey("case/a") }));
    browser.dispatchEvent(Object.assign(new Event("storage"), { key: null }));
    assert.equal(calls, 3);
    stop();
    browser.dispatchEvent(new CustomEvent("proptech:decision-room-changed", { detail: "case/a" }));
    browser.dispatchEvent(Object.assign(new Event("storage"), { key: null }));
    assert.equal(calls, 3);
  } finally {
    if (original) Object.defineProperty(globalThis, "window", original);
    else Reflect.deleteProperty(globalThis, "window");
  }
});
