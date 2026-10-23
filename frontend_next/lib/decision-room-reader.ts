/** Shared current-schema reader; no writer, history generation or Web Locks. */
import type { DecisionRoom, RoomError, RoomRead, WorkItem } from "./decision-room-store";

export const WORK_STATUSES = ["open", "in_progress", "blocked", "done"] as const;
export const WORK_ORIGINS = ["manual", "identity", "market", "location", "risk", "finance"] as const;
const PREFIX = "proptech.decisionRoom.v1.";
export const CHANGE_EVENT = "proptech:decision-room-changed";
export const MAX_DOCUMENT = 1_500_000;
export const ROOM_LIMITS = { notes: 50, items: 100, verifications: 100, history: 200 } as const;
export const decisionRoomKey = (caseId: string) => `${PREFIX}${encodeURIComponent(caseId)}`;
export function emptyDecisionRoom(caseId: string): DecisionRoom {
  return { version: 1, caseId, revision: 0, updatedAt: "", notes: [], items: [], verifications: [], askingPrice: { priceWan: null, sourceUrl: "", sourceNote: "", checkedDate: "" }, history: [] };
}
export function validRoomDate(value: unknown, optional = true): value is string {
  if (typeof value !== "string") return false;
  if (optional && value === "") return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number(value.slice(0, 4)) < 1900 || Number(value.slice(0, 4)) > 9999) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
export function safeRoomUrl(value: unknown): value is string {
  if (value === "") return true;
  if (typeof value !== "string" || value.length > 2048) return false;
  try { const url = new URL(value); return (url.protocol === "https:" || url.protocol === "http:") && !url.username && !url.password; } catch { return false; }
}
const record = (v: unknown): v is Record<string, unknown> => Boolean(v && typeof v === "object" && !Array.isArray(v));
const text = (v: unknown, max: number, required = false): v is string => typeof v === "string" && v.length <= max && (!required || v.trim().length > 0);
const id = (v: unknown) => text(v, 100, true);
const timestamp = (v: unknown) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v) && Number.isFinite(Date.parse(v));
const unique = (rows: unknown[]) => new Set(rows.map((row) => record(row) ? row.id : undefined)).size === rows.length;

export function validateRoom(value: unknown, caseId: string): RoomError | null {
  if (!record(value)) return "invalid";
  if (value.version !== 1) return "unsupported";
  if (!text(caseId, 128, true) || value.caseId !== caseId || !Number.isSafeInteger(value.revision) || Number(value.revision) < 0 || (value.updatedAt !== "" && !timestamp(value.updatedAt))) return "invalid";
  const lists = ["notes", "items", "verifications", "history"] as const;
  for (const name of lists) {
    if (!Array.isArray(value[name])) return "invalid";
    if (value[name].length > ROOM_LIMITS[name]) return "limit";
    if (!unique(value[name])) return "invalid";
  }
  for (const row of value.notes as unknown[]) {
    if (!record(row) || !id(row.id) || !validRoomDate(row.date) || !text(row.text, 4000, true)) return "invalid";
  }
  const sourceKeys = new Set<string>();
  for (const row of value.items as unknown[]) {
    if (!record(row) || !id(row.id) || !["checklist", "question", "task", "verification"].includes(String(row.kind)) || !text(row.title, 300, true) || !text(row.owner, 100) || !validRoomDate(row.dueDate) || !(WORK_STATUSES as readonly string[]).includes(String(row.status)) || !text(row.resolution, 2000) || (row.status === "done" && row.kind !== "checklist" && !text(row.resolution, 2000, true))) return "invalid";
    const origin = row.origin ?? "manual"; const sourceKey = row.sourceKey ?? "";
    if (!(WORK_ORIGINS as readonly string[]).includes(String(origin)) || !text(sourceKey, 100) || !text(row.note ?? "", 2000) || ![row.createdAt ?? "", row.updatedAt ?? ""].every((at) => at === "" || timestamp(at))) return "invalid";
    // Evidence-linked actions need a key; manual actions never claim one. One action per evidence key.
    if ((origin === "manual") !== (sourceKey === "") || (sourceKey && sourceKeys.has(sourceKey as string))) return "invalid";
    if (sourceKey) sourceKeys.add(sourceKey as string);
  }
  for (const row of value.verifications as unknown[]) {
    if (!record(row) || !id(row.id) || !text(row.topic, 300, true) || !["user_checked", "needs_follow_up"].includes(String(row.outcome)) || !safeRoomUrl(row.sourceUrl) || !text(row.sourceNote, 2000, true) || !text(row.checkedBy, 100, true) || !validRoomDate(row.checkedDate, false)) return "invalid";
  }
  const asking = value.askingPrice;
  if (!record(asking) || !(asking.priceWan === null || (typeof asking.priceWan === "number" && Number.isFinite(asking.priceWan) && asking.priceWan > 0 && asking.priceWan <= 1_000_000_000)) || !safeRoomUrl(asking.sourceUrl) || !text(asking.sourceNote, 2000) || !validRoomDate(asking.checkedDate)) return "invalid";
  for (const event of value.history as unknown[]) {
    if (!record(event) || !id(event.id) || !timestamp(event.at) || !text(event.subject, 300) || !/^(asking_price_updated|(note|checklist|question|task|verification|manual_check)_(added|updated|removed))$/.test(String(event.kind))) return "invalid";
  }
  return null;
}
/** Whitelist persisted fields; callers cannot inject provider payloads or arbitrary properties. */
export function roomData(room: DecisionRoom) {
  return {
    notes: room.notes.map(({ id, date, text }) => ({ id, date, text })),
    items: room.items.map(normalizeWorkItem),
    verifications: room.verifications.map(({ id, topic, outcome, sourceUrl, sourceNote, checkedDate, checkedBy }) => ({ id, topic, outcome, sourceUrl, sourceNote, checkedDate, checkedBy })),
    askingPrice: { priceWan: room.askingPrice.priceWan, sourceUrl: room.askingPrice.sourceUrl, sourceNote: room.askingPrice.sourceNote, checkedDate: room.askingPrice.checkedDate },
  };
}
export function normalizeWorkItem({ id, kind, title, owner, dueDate, status, resolution, origin, sourceKey, note, createdAt, updatedAt }: WorkItem): Required<WorkItem> {
  return { id, kind, title, owner, dueDate, status, resolution, origin: origin ?? "manual", sourceKey: sourceKey ?? "", note: note ?? "", createdAt: createdAt ?? "", updatedAt: updatedAt ?? "" };
}
export function createDecisionRoomReader(storage: { getItem(key: string): string | null }) {
  const read = (caseId: string): RoomRead => {
    if (!text(caseId, 128, true)) return { status: "invalid" };
    try {
      const raw = storage.getItem(decisionRoomKey(caseId));
      if (raw === null) return { status: "empty", room: emptyDecisionRoom(caseId) };
      if (raw.length > MAX_DOCUMENT) return { status: "limit" };
      let parsed: unknown;
      try { parsed = JSON.parse(raw); } catch { return { status: "corrupt" }; }
      const error = validateRoom(parsed, caseId);
      if (error) return { status: error === "invalid" ? "corrupt" : error };
      const room = parsed as DecisionRoom;
      return { status: "ready", room: { version: 1, caseId, revision: room.revision, updatedAt: room.updatedAt, ...roomData(room), history: room.history.map(({ id, at, kind, subject }) => ({ id, at, kind, subject })) } };
    } catch { return { status: "unavailable" }; }
  };
  return { read };
}

export function createBrowserDecisionRoomReader() {
  const repository = createDecisionRoomReader({ getItem: (key) => window.localStorage.getItem(key) });
  return {
    ...repository,
    subscribe(caseId: string, listener: () => void) {
      const onStorage = (event: StorageEvent) => { if (event.key === decisionRoomKey(caseId) || event.key === null) listener(); };
      const onChange = (event: Event) => { if ((event as CustomEvent).detail === caseId) listener(); };
      window.addEventListener("storage", onStorage);
      window.addEventListener(CHANGE_EVENT, onChange);
      return () => { window.removeEventListener("storage", onStorage); window.removeEventListener(CHANGE_EVENT, onChange); };
    },
  };
}
