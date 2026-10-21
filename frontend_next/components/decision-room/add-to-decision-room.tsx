"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { addEvidenceAction, createBrowserDecisionRoomRepository, findEvidenceAction, type EvidenceActionInput, type WorkItem } from "@/lib/decision-room-store";
import { decisionRoomReportCopy, type DecisionRoomReportCopyKey } from "@/lib/decision-room-report-copy";

/**
 * Turns one saved-evidence check into a Decision Room verification action. Browser-local
 * sidecar write only: no provider or saved-case write. A key already in the room is shown,
 * never added twice.
 */
export function AddToDecisionRoom({ caseId, candidate }: { caseId: string; candidate: EvidenceActionInput }) {
  const { copyFrom } = useExperienceLocale();
  const t = (key: DecisionRoomReportCopyKey, values?: Record<string, string | number>) => copyFrom(decisionRoomReportCopy, key, values);
  const repository = useMemo(createBrowserDecisionRoomRepository, []);
  const [existing, setExisting] = useState<WorkItem | null>(null);
  const [state, setState] = useState<"idle" | "saving" | "failed">("idle");
  useEffect(() => {
    const load = () => { const read = repository.read(caseId); setExisting(read.status === "ready" ? findEvidenceAction(read.room, candidate.sourceKey) ?? null : null); };
    load();
    return repository.subscribe(caseId, load);
  }, [repository, caseId, candidate.sourceKey]);
  async function add() {
    setState("saving");
    // One retry covers a concurrent save in another tab; the latest room decides idempotency.
    for (let attempt = 0; attempt < 2; attempt++) {
      const read = repository.read(caseId);
      if (read.status !== "ready" && read.status !== "empty") break;
      const { room, added } = addEvidenceAction(read.room, candidate);
      if (!added) { setExisting(findEvidenceAction(read.room, candidate.sourceKey) ?? null); setState("idle"); return; }
      const result = await repository.save(room, read.room.revision);
      if (result.status === "saved") { setExisting(findEvidenceAction(result.room, candidate.sourceKey) ?? null); setState("idle"); return; }
      if (result.status !== "conflict") break;
    }
    setState("failed");
  }
  const href = `/cases/${encodeURIComponent(caseId)}/decision-room#verification-items`;
  if (existing) return <Link href={href} data-testid="add-to-room-existing" data-source-key={candidate.sourceKey}>{t("inRoom", { status: t(`status_${existing.status}`) })}</Link>;
  return <span data-testid="add-to-room" data-source-key={candidate.sourceKey}>
    <button type="button" className="ds-button ds-button--secondary ds-button--compact" disabled={state === "saving"} onClick={add}>{t("addToRoom")}</button>
    {state === "failed" && <span role="alert"> {t("addFailed")}</span>}
  </span>;
}
