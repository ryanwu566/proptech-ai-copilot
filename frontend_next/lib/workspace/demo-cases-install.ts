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
 * ("restore"). A reinstalled demo gets its seeded Decision Room; an existing demo keeps any
 * present room. Missing rooms can be seeded on retry after a partially completed install.
 */
export async function installDemoCases(mode: DemoInstallMode, locale: ExperienceLocale): Promise<DemoInstallResult> {
  const result = await writeReservedCases((read) => planDemoInstall(read, mode, buildDemoCases(locale), MAX_SAVED_CASES));
  if (result.kind === "blocked") return { status: "blocked", reason: result.reason as DemoInstallFailure };
  const installed = result.kind === "write" ? result.installed : [];
  for (const room of buildDemoRooms(locale)) {
    if (validateRoom(room, room.caseId)) return { status: "blocked", reason: "write_failed" };
    try {
      const changed = await navigator.locks.request(decisionRoomKey(room.caseId), () => {
        const key = decisionRoomKey(room.caseId);
        if (!installed.includes(room.caseId) && window.localStorage.getItem(key) !== null) return false;
        window.localStorage.setItem(key, JSON.stringify(room));
        return true;
      });
      if (changed) window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: room.caseId }));
    } catch { return { status: "blocked", reason: "write_failed" }; }
  }
  return { status: "ready", caseId: DEMO_CASE_A_ID, installed };
}
