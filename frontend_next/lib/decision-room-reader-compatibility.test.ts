import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { createDecisionRoomReader, emptyDecisionRoom } from "./decision-room-reader.ts";
import type { DecisionRoom, WorkItem } from "./decision-room-store";

const at = "2026-10-21T03:00:00.000Z";
const legacyItem = (): WorkItem => ({ id: "inspect", kind: "checklist", title: "Inspect", owner: "", dueDate: "", status: "open", resolution: "" });
const read = (room: DecisionRoom) => createDecisionRoomReader({ getItem: () => JSON.stringify(room) }).read(room.caseId);

test("pre-action v1 items normalize every missing field without changing saved storage", () => {
  const room = emptyDecisionRoom("case-a");
  room.items = [legacyItem()];
  const before = JSON.stringify(room);
  const result = read(room);
  assert.equal(result.status, "ready");
  if (result.status === "ready") assert.deepEqual(result.room.items[0], { ...legacyItem(), origin: "manual", sourceKey: "", note: "", createdAt: "", updatedAt: "" });
  assert.equal(JSON.stringify(room), before);
});

test("verification actions retain all current statuses, origins, source keys, notes and timestamps", () => {
  for (const status of ["open", "in_progress", "blocked", "done"] as const) {
    for (const origin of ["manual", "identity", "market", "location", "risk", "finance"] as const) {
      const room = emptyDecisionRoom("case-a");
      const item: WorkItem = { ...legacyItem(), kind: "verification", status, origin, sourceKey: origin === "manual" ? "" : `${origin}:saved-source`, note: "Verify saved evidence", createdAt: at, updatedAt: at, resolution: status === "done" ? "Checked with seller" : "" };
      room.items = [item];
      const result = read(room);
      assert.equal(result.status, "ready", `${status}/${origin}`);
      if (result.status === "ready") assert.deepEqual(result.room.items[0], item);
    }
  }
});

test("reader rejects invalid evidence provenance, duplicate source keys and invalid action timestamps", () => {
  const item: WorkItem = { ...legacyItem(), origin: "risk", sourceKey: "risk:saved-source", note: "Verify", createdAt: at, updatedAt: at };
  const invalid = [
    [{ ...item, sourceKey: "" }],
    [{ ...item, origin: "manual" as const }],
    [item, { ...item, id: "duplicate" }],
    [{ ...item, createdAt: "invalid" }],
    [{ ...item, updatedAt: "invalid" }],
    [{ ...item, note: "x".repeat(2001) }],
  ];
  for (const items of invalid) {
    const room = emptyDecisionRoom("case-a");
    room.items = items;
    assert.deepEqual(read(room), { status: "corrupt" });
  }
});

test("verification activity is retained and DONE non-checklist work requires a resolution", () => {
  const room = emptyDecisionRoom("case-a");
  room.items = [{ ...legacyItem(), kind: "verification", status: "done", resolution: "Checked" }];
  room.history = (["added", "updated", "removed"] as const).map((change) => ({ id: change, at, kind: `verification_${change}`, subject: "Inspect" }));
  const result = read(room);
  assert.equal(result.status, "ready");
  if (result.status === "ready") assert.deepEqual(result.room.history, room.history);
  for (const kind of ["question", "task", "verification"] as const) {
    room.items = [{ ...legacyItem(), kind, status: "done", resolution: "" }];
    assert.deepEqual(read(room), { status: "corrupt" });
  }
});
