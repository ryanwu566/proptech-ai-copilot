import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TypeScript runner requires source extension.
const feature = await import("./decision-room-store.ts").catch(() => null);

const NOW = "2026-10-12T03:00:00.000Z";
function setup() {
  assert.ok(feature, "Decision Room repository must exist");
  const values = new Map<string, string>([["proptech.savedCases.v1", "CORE-SNAPSHOT"]]);
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); } };
  const repository = feature.createDecisionRoomRepository(storage, () => NOW, () => `event-${Math.random()}`);
  return { values, storage, repository, room: feature.emptyDecisionRoom("case/a") };
}
test("saves and reopens room data without changing core cases or another case", () => {
  const { repository, room, values } = setup();
  room.notes.push({ id: "n1", date: "2026-10-12", text: "Check window noise in person" });
  const result = repository.save(room, 0);
  assert.equal(result.status, "saved");
  const reopened = repository.read("case/a");
  assert.equal(reopened.status, "ready");
  if (reopened.status === "ready") { assert.equal(reopened.room.notes[0]?.text, room.notes[0]?.text); assert.equal(reopened.room.revision, 1); assert.equal(reopened.room.history[0]?.kind, "note_added"); }
  assert.equal(values.get("proptech.savedCases.v1"), "CORE-SNAPSHOT");
  assert.equal(repository.read("case-b").status, "empty");
  assert.equal(values.size, 2);
});
test("rejects a stale revision and preserves the newer room", () => {
  const { repository, room } = setup();
  room.notes.push({ id: "n1", date: "", text: "Initial viewing" });
  repository.save(room, 0);
  room.askingPrice.priceWan = 2400;
  assert.equal(repository.save(room, 0).status, "conflict");
  const read = repository.read(room.caseId);
  assert.equal(read.status === "ready" && read.room.askingPrice.priceWan, null);
});
test("corrupt and unsupported storage cannot be overwritten by an empty room", () => {
  const { repository, room, values } = setup();
  const key = feature!.decisionRoomKey(room.caseId);
  for (const [raw, status] of [["{bad", "corrupt"], [JSON.stringify({ ...room, version: 2 }), "unsupported"], [JSON.stringify({ ...room, caseId: "other" }), "corrupt"]]) {
    values.set(key, raw);
    assert.equal(repository.read(room.caseId).status, status);
    assert.equal(repository.save(room, 0).status, status);
    assert.equal(values.get(key), raw);
  }
});
test("blocked reads and quota failures return errors instead of claiming saved", () => {
  setup();
  const blocked = feature!.createDecisionRoomRepository({ getItem() { throw Error("blocked"); }, setItem() { throw Error("blocked"); } });
  assert.equal(blocked.read("case-a").status, "unavailable");
  const full = feature!.createDecisionRoomRepository({ getItem() { return null; }, setItem() { throw Error("quota"); } });
  const draft = feature!.emptyDecisionRoom("case-a");
  draft.askingPrice.priceWan = 2000;
  assert.equal(full.save(draft, 0).status, "unavailable");
  const quota = feature!.createDecisionRoomRepository({ getItem() { return null; }, setItem() { throw new DOMException("quota", "QuotaExceededError"); } });
  assert.equal(quota.save(draft, 0).status, "full");
});
test("manual checks require actual user notes, checker and valid date; unsafe URLs fail", () => {
  const { repository, room } = setup();
  room.verifications.push({ id: "v1", topic: "Ownership", outcome: "user_checked", sourceUrl: "javascript:alert(1)", sourceNote: "", checkedDate: "2026-02-30", checkedBy: "" });
  assert.equal(repository.save(room, 0).status, "invalid");
  Object.assign(room.verifications[0]!, { sourceUrl: "https://example.com/source", sourceNote: "Read document with seller; still need current copy", checkedDate: "2026-10-12", checkedBy: "Buyer" });
  const result = repository.save(room, 0);
  assert.equal(result.status, "saved");
  assert.equal(result.status === "saved" && result.room.verifications[0]?.outcome, "user_checked");
  assert.equal(result.status === "saved" && result.room.items.length, 0);
});
test("resolved questions and tasks require resolution; checklist completion is not verification", () => {
  const { repository, room } = setup();
  room.items.push({ id: "q1", kind: "question", title: "Management fee?", owner: "Buyer", dueDate: "2026-10-15", status: "done", resolution: "" });
  assert.equal(repository.save(room, 0).status, "invalid");
  room.items[0]!.resolution = "Agent will send current fee statement";
  room.items.push({ id: "c1", kind: "checklist", title: "Inspect windows", owner: "", dueDate: "", status: "done", resolution: "" });
  const result = repository.save(room, 0);
  assert.equal(result.status, "saved");
  assert.equal(result.status === "saved" && result.room.verifications.length, 0);
});
test("validation bounds records and strings; rejects duplicates, impossible dates and fake outcomes", () => {
  const { repository, room } = setup();
  room.notes = Array.from({ length: 51 }, (_, i) => ({ id: `n${i}`, date: "", text: "note" }));
  assert.equal(repository.save(room, 0).status, "limit");
  room.notes = [{ id: "n", date: "", text: "x".repeat(4001) }];
  assert.equal(repository.save(room, 0).status, "invalid");
  room.notes = [{ id: "n", date: "", text: "a" }, { id: "n", date: "", text: "b" }];
  assert.equal(repository.save(room, 0).status, "invalid");
  room.notes = [{ id: "n", date: "2026-13-01", text: "a" }];
  assert.equal(repository.save(room, 0).status, "invalid");
  room.notes = [];
  room.askingPrice.priceWan = -1;
  assert.equal(repository.save(room, 0).status, "invalid");
  room.askingPrice.priceWan = null;
  // @ts-expect-error Exercise a hostile runtime payload outside the public type.
  room.verifications = [{ id: "v", topic: "Title", outcome: "officially_verified", sourceNote: "claim", sourceUrl: "", checkedBy: "Buyer", checkedDate: "2026-10-12" }];
  assert.equal(repository.save(room, 0).status, "invalid");
});
test("history is derived from actual edits, no-op save stays unchanged, retains latest 200", () => {
  const { repository, room } = setup();
  let current = room;
  for (let i = 0; i < 205; i++) {
    current.askingPrice.priceWan = 2000 + i;
    const result = repository.save(current, current.revision);
    assert.equal(result.status, "saved");
    if (result.status === "saved") current = result.room;
  }
  assert.equal(current.history.length, 200);
  assert.equal(current.history.at(-1)?.kind, "asking_price_updated");
  const unchanged = repository.save(current, current.revision);
  assert.equal(unchanged.status === "saved" && unchanged.room.revision, current.revision);
  assert.equal(unchanged.status === "saved" && unchanged.room.history.length, 200);
});
test("gap summary keeps missing provenance and saved evidence states after manual work", () => {
  const { room } = setup();
  room.askingPrice.priceWan = 2400;
  room.items.push({ id: "t1", kind: "task", title: "Get deed", owner: "", dueDate: "", status: "open", resolution: "" });
  room.verifications.push({ id: "v1", topic: "Ownership", outcome: "user_checked", sourceUrl: "", sourceNote: "Saw an old copy", checkedDate: "2026-10-12", checkedBy: "Buyer" });
  const gaps = feature!.decisionRoomGaps(room, [{ key: "risk", query: "succeeded", usability: "no_match", completeness: "partial" }, { key: "valuation", query: "failed", usability: "unavailable", completeness: "insufficient" }]);
  assert.ok(gaps.some((gap: { reason: string }) => gap.reason === "asking_source"));
  assert.ok(gaps.some((gap: { reason: string }) => gap.reason === "task_owner"));
  assert.ok(gaps.some((gap: { reason: string }) => gap.reason === "task_due"));
  assert.ok(gaps.some((gap: { reason: string; state?: string }) => gap.reason === "saved_evidence" && gap.state === "no_match"));
  assert.ok(gaps.some((gap: { reason: string; state?: string }) => gap.reason === "saved_evidence" && gap.state === "unavailable"));
});
test("editing one field after reload preserves newer untouched fields and does not resurrect deleted records", () => {
  setup();
  const base = { id: "t1", title: "Get deed", owner: "Buyer", status: "open" };
  const draft = { ...base, owner: "Partner" };
  const latest = { ...base, status: "done", title: "Get current deed" };
  assert.ok(feature!.mergeRoomRecord, "record merge boundary must exist");
  assert.deepEqual(feature!.mergeRoomRecord(base, draft, latest), { id: "t1", title: "Get current deed", owner: "Partner", status: "done" });
  assert.equal(feature!.mergeRoomRecord(base, draft, undefined), null);
});
test("case IDs accepted by the saved-case boundary remain usable in the sidecar store", () => {
  const { repository } = setup();
  const room = feature!.emptyDecisionRoom("a".repeat(128));
  room.notes.push({ id: "n", date: "", text: "Long ID property" });
  assert.equal(repository.save(room, 0).status, "saved");
});
