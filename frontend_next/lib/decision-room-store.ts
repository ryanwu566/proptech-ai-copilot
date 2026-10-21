// @ts-expect-error Native TypeScript runner extension.
import { CHANGE_EVENT, MAX_DOCUMENT, ROOM_LIMITS, decisionRoomKey, createDecisionRoomReader, createBrowserDecisionRoomReader, validateRoom, roomData } from "./decision-room-reader.ts";
// @ts-expect-error Native TypeScript runner extension.
export { ROOM_LIMITS, decisionRoomKey, emptyDecisionRoom, validRoomDate, safeRoomUrl } from "./decision-room-reader.ts";
/** Independent browser-local aggregate. No saved-case writer or provider dependency. */
export type WorkKind = "checklist" | "question" | "task";
export type ViewingNote = { id: string; date: string; text: string };
export type WorkItem = { id: string; kind: WorkKind; title: string; owner: string; dueDate: string; status: "open" | "done"; resolution: string };
export type ManualCheck = { id: string; topic: string; outcome: "user_checked" | "needs_follow_up"; sourceUrl: string; sourceNote: string; checkedDate: string; checkedBy: string };
export type AskingPrice = { priceWan: number | null; sourceUrl: string; sourceNote: string; checkedDate: string };
export type ActivityKind = `${"note" | WorkKind | "manual_check"}_${"added" | "updated" | "removed"}` | "asking_price_updated";
export type RoomActivity = { id: string; at: string; kind: ActivityKind; subject: string };
export type DecisionRoom = { version: 1; caseId: string; revision: number; updatedAt: string; notes: ViewingNote[]; items: WorkItem[]; verifications: ManualCheck[]; askingPrice: AskingPrice; history: RoomActivity[] };
export type RoomError = "corrupt" | "unsupported" | "unavailable" | "full" | "invalid" | "limit" | "conflict";
export type RoomRead = { status: "ready"; room: DecisionRoom } | { status: "empty"; room: DecisionRoom } | { status: RoomError };
export type RoomSave = { status: "saved"; room: DecisionRoom } | { status: RoomError };
export type DecisionRoomRepository = { read(caseId: string): RoomRead; save(room: DecisionRoom, expectedRevision: number): RoomSave; subscribe(caseId: string, listener: () => void): () => void };
type RoomStorage = { getItem(key: string): string | null; setItem(key: string, value: string): void };
/** Apply only intentionally edited fields to the latest record after an explicit reload. */
export function mergeRoomRecord<T extends object>(base: T, draft: T, latest: T | undefined): T | null {
  if (!latest) return null;
  const merged = { ...latest };
  for (const key of Object.keys(draft) as (keyof T)[]) {
    if (key !== "id" && draft[key] !== base[key]) merged[key] = draft[key];
  }
  return merged;
}
function changes(before: DecisionRoom, after: DecisionRoom, at: string, makeId: () => string): RoomActivity[] {
  const events: RoomActivity[] = [];
  const add = (kind: ActivityKind, subject: string) => events.push({ id: makeId(), at, kind, subject: subject.slice(0, 300) });
  for (const name of ["notes", "items", "verifications"] as const) {
    type Row = ViewingNote | WorkItem | ManualCheck;
    const old = before[name] as Row[];
    const next = after[name] as Row[];
    const kind = (row: Row) => "kind" in row ? row.kind : "topic" in row ? "manual_check" : "note";
    const title = (row: Row) => "title" in row ? row.title : "topic" in row ? row.topic : row.text;
    for (const row of next) {
      const previous = old.find((r) => r.id === row.id);
      if (!previous) add(`${kind(row)}_added`, title(row));
      else if (JSON.stringify(previous) !== JSON.stringify(row)) add(`${kind(row)}_updated`, title(row));
    }
    for (const row of old) if (!next.some((r) => r.id === row.id)) add(`${kind(row)}_removed`, title(row));
  }
  if (JSON.stringify(before.askingPrice) !== JSON.stringify(after.askingPrice)) add("asking_price_updated", "");
  return events;
}
export function createDecisionRoomRepository(storage: RoomStorage, now = () => new Date().toISOString(), makeId: () => string = () => crypto.randomUUID()): DecisionRoomRepository {
  const { read } = createDecisionRoomReader(storage);
  return {
    read,
    save(room, expectedRevision) {
      try {
        const error = validateRoom(room, room.caseId);
        if (error) return { status: error };
        const stored = read(room.caseId);
        if (stored.status !== "ready" && stored.status !== "empty") return stored;
        if (!Number.isSafeInteger(expectedRevision) || expectedRevision !== room.revision || stored.room.revision !== expectedRevision) return { status: "conflict" };
        const previous = stored.room;
        const next = { ...room, ...roomData(room) };
        const at = now();
        const events = changes(previous, next, at, makeId);
        if (!events.length) return { status: "saved", room: previous };
        const updated: DecisionRoom = { version: 1, caseId: room.caseId, revision: previous.revision + 1, updatedAt: at, ...roomData(next), history: [...previous.history, ...events].slice(-ROOM_LIMITS.history) };
        const updatedError = validateRoom(updated, room.caseId);
        if (updatedError) return { status: updatedError };
        const serialized = JSON.stringify(updated);
        if (serialized.length > MAX_DOCUMENT) return { status: "limit" };
        storage.setItem(decisionRoomKey(room.caseId), serialized);
        return { status: "saved", room: updated };
      } catch (error) { return { status: error instanceof DOMException && error.name === "QuotaExceededError" ? "full" : "unavailable" }; }
    },
    subscribe: () => () => {},
  };
}
export type BrowserRoomSave = RoomSave | { status: "case_unreadable" };
export type BrowserDecisionRoomRepository = Omit<DecisionRoomRepository, "save"> & { save(room: DecisionRoom, expectedRevision: number, canSave?: () => boolean): Promise<BrowserRoomSave> };
export function createBrowserDecisionRoomRepository(): BrowserDecisionRoomRepository {
  const repository = createDecisionRoomRepository({ getItem: (key) => window.localStorage.getItem(key), setItem: (key, value) => window.localStorage.setItem(key, value) });
  return {
    ...repository,
    async save(room, revision, canSave = () => true) {
      try {
        // Serialize read/check/write across tabs. Fail closed without Web Locks.
        if (!navigator.locks) return { status: "unavailable" };
        return await navigator.locks.request(decisionRoomKey(room.caseId), (): BrowserRoomSave => {
          if (!canSave()) return { status: "case_unreadable" };
          const result = repository.save(room, revision);
          if (result.status === "saved") window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: room.caseId }));
          return result;
        });
      } catch { return { status: "unavailable" }; }
    },
    subscribe: createBrowserDecisionRoomReader().subscribe,
  };
}
export type RoomEvidence = { key: string; query: string; usability?: string; completeness: string };
export type RoomGapReason = "asking_price" | "asking_source" | "asking_date" | "viewing_notes" | "open_question" | "open_task" | "unchecked_item" | "task_owner" | "task_due" | "manual_followup" | "saved_evidence";
export type RoomGap = { id: string; reason: RoomGapReason; subject?: string; state?: string; target: string };
/** Task progress never promotes saved evidence or a manual record into an official fact. */
export function decisionRoomGaps(room: DecisionRoom, evidence: RoomEvidence[]): RoomGap[] {
  const gaps: RoomGap[] = [];
  const add = (id: string, reason: RoomGapReason, target: string, subject?: string, state?: string) => gaps.push({ id, reason, target, subject, state });
  if (room.askingPrice.priceWan === null) add("asking-price", "asking_price", "asking-price");
  if (!room.askingPrice.sourceUrl.trim() && !room.askingPrice.sourceNote.trim()) add("asking-source", "asking_source", "asking-price");
  if (!room.askingPrice.checkedDate) add("asking-date", "asking_date", "asking-price");
  if (!room.notes.length) add("viewing-notes", "viewing_notes", "viewing-notes");
  for (const item of room.items.filter((r) => r.status === "open")) {
    add(`open-${item.id}`, item.kind === "question" ? "open_question" : item.kind === "task" ? "open_task" : "unchecked_item", `${item.kind}-items`, item.title);
    if (item.kind === "task" && !item.owner.trim()) add(`owner-${item.id}`, "task_owner", "task-items", item.title);
    if (item.kind === "task" && !item.dueDate) add(`due-${item.id}`, "task_due", "task-items", item.title);
  }
  for (const check of room.verifications.filter((r) => r.outcome === "needs_follow_up")) add(`manual-${check.id}`, "manual_followup", "manual-checks", check.topic);
  for (const row of evidence) {
    if (row.query !== "succeeded" || row.usability !== "usable" || row.completeness !== "sufficient_for_task") add(`evidence-${row.key}`, "saved_evidence", "saved-evidence", row.key, row.usability ?? row.query);
  }
  return gaps;
}
