import type { RoomActivity, RoomRead, WorkItem } from "./decision-room-store";
// @ts-expect-error Native TS runner extension.
import { isOutstanding, normalizeWorkItem } from "./decision-room-store.ts";

/**
 * Read-only projection of one saved Decision Room into the client report.
 * Inputs are the saved room only: no provider, case writer or clock reads. It counts and
 * orders the buyer's own actions; it never scores, ranks the property or recommends a decision.
 */
export type RoomAction = Required<WorkItem>;
export type RoomReadiness = "unreadable" | "none" | "outstanding" | "clear";
export type DecisionRoomReport = {
  status: "ready" | "empty" | "unreadable";
  readiness: RoomReadiness;
  /** Ordered for the pre-offer list: verification, blocked, open questions, other open work. */
  outstanding: RoomAction[];
  completed: RoomAction[];
  counts: { total: number; outstanding: number; open: number; inProgress: number; blocked: number; done: number; verification: number };
  history: RoomActivity[];
};

export const ROOM_REPORT_LIMITS = { page3Rows: 4, completedTitles: 3, history: 50 } as const;

/** 0 open verification · 1 blocked · 2 open question · 3 other open work · 4 done. */
export function actionPriority(item: Pick<WorkItem, "kind" | "status">): number {
  if (item.status === "done") return 4;
  if (item.status === "blocked") return 1;
  return item.kind === "verification" ? 0 : item.kind === "question" ? 2 : 3;
}
const byPriority = (a: RoomAction, b: RoomAction) => actionPriority(a) - actionPriority(b)
  // Dated work first (earliest due), then the order the buyer created it.
  || (a.dueDate || "9999").localeCompare(b.dueDate || "9999")
  || (a.createdAt || "").localeCompare(b.createdAt || "");

export function projectDecisionRoomReport(read: RoomRead | null): DecisionRoomReport {
  const empty = { outstanding: [], completed: [], counts: { total: 0, outstanding: 0, open: 0, inProgress: 0, blocked: 0, done: 0, verification: 0 }, history: [] };
  if (!read || (read.status !== "ready" && read.status !== "empty")) return { status: "unreadable", readiness: "unreadable", ...empty };
  const items = (read.room.items as WorkItem[]).map(normalizeWorkItem) as RoomAction[];
  const outstanding = items.filter(isOutstanding).sort(byPriority);
  const completed = items.filter((item) => !isOutstanding(item)).sort((a, b) => (b.updatedAt || "").localeCompare(a.updatedAt || ""));
  const count = (status: WorkItem["status"]) => items.filter((item) => item.status === status).length;
  const counts = { total: items.length, outstanding: outstanding.length, open: count("open"), inProgress: count("in_progress"), blocked: count("blocked"), done: count("done"), verification: outstanding.filter((item) => item.kind === "verification").length };
  const readiness: RoomReadiness = !items.length ? "none" : outstanding.length ? "outstanding" : "clear";
  return { status: read.status, readiness, outstanding, completed, counts, history: read.room.history.slice(-ROOM_REPORT_LIMITS.history).reverse() };
}

/** Actions linked to one saved-evidence key, outstanding first. Manual actions never match. */
export function actionsForSource(report: DecisionRoomReport, sourceKey: string): RoomAction[] {
  if (!sourceKey) return [];
  return [...report.outstanding, ...report.completed].filter((item) => item.sourceKey === sourceKey);
}
