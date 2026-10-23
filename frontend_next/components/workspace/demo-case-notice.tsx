"use client";

import Link from "next/link";
import { useState } from "react";
import { Message } from "@/components/design-system/message";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { DEMO_CASE_IDS, DEMO_SNAPSHOT_DATE, isDemoCaseId } from "@/lib/workspace/demo-case-ids";
import { demoCaseCopy, type DemoCaseCopyKey } from "@/lib/workspace/demo-case-copy";
import { compareHref } from "@/lib/workspace/compare-selection";
import styles from "./demo-case-notice.module.css";

/** Disclosure for the reserved demo snapshots only; real cases render nothing. Restore never touches other cases. */
export function DemoCaseNotice({ caseIds, showCompare = true }: { caseIds: string[]; showCompare?: boolean }) {
  const { copyFrom, locale } = useExperienceLocale();
  const [status, setStatus] = useState<"idle" | "restoring" | "restored" | "failed">("idle");
  if (!caseIds.some(isDemoCaseId)) return null;
  const text = (key: DemoCaseCopyKey) => copyFrom(demoCaseCopy, key, { date: DEMO_SNAPSHOT_DATE });
  async function restore() {
    setStatus("restoring");
    try {
      const { installDemoCases } = await import("@/lib/workspace/demo-cases-install");
      setStatus((await installDemoCases("restore", locale)).status === "ready" ? "restored" : "failed");
    } catch { setStatus("failed"); }
  }
  return <div className={styles.notice} data-testid="demo-case-notice">
    <Message variant="information" title={text("title")} action={<>
      {showCompare && <Link prefetch={false} className="ds-button ds-button--secondary ds-button--compact" data-testid="demo-compare" href={compareHref([...DEMO_CASE_IDS])}>{text("compare")}</Link>}
      <button type="button" className="ds-button ds-button--tertiary ds-button--compact" data-testid="demo-restore" disabled={status === "restoring"} onClick={restore}>{status === "restoring" ? text("restoring") : text("restore")}</button>
    </>}>
      <p data-testid="demo-snapshot-disclosure">{text("body")}</p>
      <p>{text("boundary")}</p>
      <p aria-live="polite" data-testid="demo-restore-status">{status === "restored" ? text("restored") : status === "failed" ? text("restoreFailed") : ""}</p>
    </Message>
  </div>;
}
