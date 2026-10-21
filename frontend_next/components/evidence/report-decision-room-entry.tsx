"use client";
import { useEffect, useState } from "react";
import type { DecisionRoomReport } from "@/lib/decision-room-report";

/**
 * Report-only boundary: the Decision Room store, projection and copy load when a report
 * opens, never with the shared case/compare client entry. Data and UI arrive together, so
 * the report renders (and prints) only once the room section is settled.
 */
export type ReportRoomUi = typeof import("./report-decision-room");
export type ReportRoom = { report: DecisionRoomReport | null; ui: ReportRoomUi | null };

/** `undefined` while loading; a failed chunk load leaves the report without the room section. */
export function useReportRoom(caseId: string): ReportRoom | undefined {
  const [room, setRoom] = useState<ReportRoom | undefined>(undefined);
  useEffect(() => {
    let live = true;
    let stop: (() => void) | undefined;
    setRoom(undefined);
    import("./report-decision-room").then((ui) => {
      if (!live) return;
      stop = ui.watchDecisionRoomReport(caseId, (report) => setRoom({ report, ui }));
    }, () => { if (live) setRoom({ report: null, ui: null }); });
    return () => { live = false; stop?.(); };
  }, [caseId]);
  return room;
}
