"use client";

import { MAX_SAVED_CASES, writeReservedCases } from "@/lib/case-storage";
import { CHANGE_EVENT, decisionRoomKey, validateRoom } from "@/lib/decision-room-reader";
import type { ExperienceLocale } from "@/lib/experience-i18n";
import { buildDemoCases, buildDemoRooms, planDemoInstall, type DemoInstallBlocked, type DemoInstallMode } from "./demo-cases";
import { DEMO_CASE_A_ID } from "./demo-case-ids";

export type DemoInstallFailure = DemoInstallBlocked | "lock_unavailable" | "write_failed";
export type DemoInstallResult = { status: "ready"; caseId: string; installed: string[] } | { status: "blocked"; reason: DemoInstallFailure };

/**
 * Local only; never runs a provider. Installs missing demo snapshots ("ensure") or resets both
 * ("restore"). A reinstalled demo gets its seeded Decision Room; an existing demo keeps its room.
 */
export async function installDemoCases(mode: DemoInstallMode, locale: ExperienceLocale): Promise<DemoInstallResult> {
  const result = await writeReservedCases((read) => planDemoInstall(read, mode, buildDemoCases(locale), MAX_SAVED_CASES));
  if (result.kind === "blocked") return { status: "blocked", reason: result.reason as DemoInstallFailure };
  const installed = result.kind === "write" ? result.installed : [];
  for (const room of buildDemoRooms(locale).filter((row) => installed.includes(row.caseId))) {
    if (validateRoom(room, room.caseId)) continue;
    try {
      await navigator.locks.request(decisionRoomKey(room.caseId), () => window.localStorage.setItem(decisionRoomKey(room.caseId), JSON.stringify(room)));
      window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: room.caseId }));
    } catch { /* The case is installed; its room opens empty rather than failing the example. */ }
  }
  return { status: "ready", caseId: DEMO_CASE_A_ID, installed };
}
