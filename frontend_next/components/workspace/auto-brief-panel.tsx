"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { StatusLabel } from "@/components/design-system/status-label";
import type { VisualRole } from "@/components/design-system/types";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { autoBriefModeFor, isActiveRun, precheckAutoBrief, type AutoBriefStep, type AutoBriefStepStatus } from "@/lib/workspace/auto-brief";
import { autoBriefCopy } from "@/lib/workspace/auto-brief-copy";
import { getAutoBriefController } from "@/lib/workspace/auto-brief-runtime";
import styles from "./auto-brief-panel.module.css";

const ROLE: Record<AutoBriefStepStatus, VisualRole> = {
  pending: "neutral", running: "information", available: "success", partial: "warning", no_data: "warning", unavailable: "error", needs_input: "warning", skipped: "disabled",
};

/** Minimal Auto Brief control: start, progress, cancel, retry and View Brief. Manual navigation stays available. */
export function AutoBriefPanel() {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const c: Translate = (key, values) => copyFrom(autoBriefCopy, key, values);
  const controller = getAutoBriefController();
  const caseId = workspace.caseId;
  const getSnapshot = useCallback(() => controller.getRun(caseId), [controller, caseId]);
  const run = useSyncExternalStore(controller.subscribe, getSnapshot, () => null);
  const precheck = precheckAutoBrief(workspace);
  const active = Boolean(run && isActiveRun(run.status));
  const base = `/cases/${encodeURIComponent(caseId)}`;
  const panel = useRef<HTMLElement>(null);
  const wasActive = useRef(active);

  // Keep keyboard focus on a live control as the start button gives way to cancel and back.
  useEffect(() => {
    const focus = (selector: string) => panel.current?.querySelector<HTMLElement>(selector)?.focus();
    const focusLost = document.activeElement === document.body || document.activeElement === null;
    if (active && !wasActive.current && (focusLost || panel.current?.contains(document.activeElement))) focus("[data-auto-brief-cancel]");
    else if (!active && wasActive.current && focusLost) focus("[data-auto-brief-primary]");
    wasActive.current = active;
  }, [active]);

  const terminal = run && !active;
  const finished = run?.status === "completed" || run?.status === "completed_with_gaps";
  const resumable = run?.status === "interrupted" || run?.status === "cancelled";
  const money = run?.steps.find((step) => step.id === "money");

  return <section ref={panel} className={styles.panel} aria-labelledby="auto-brief-title" data-testid="auto-brief-panel" data-run-status={run?.status ?? "idle"}>
    <div className={styles.heading}>
      <h2 id="auto-brief-title" className="text-section">{c("title")}</h2>
      <p className="text-dense">{c("intro")}</p>
      {autoBriefModeFor(caseId) === "demo_fixture" && <p className="text-helper" data-testid="auto-brief-demo-note">{c("demoNote")}</p>}
    </div>

    {!precheck.ok && !active && <div data-testid="auto-brief-needs-location">
      <Message variant="warning" title={c("run_needs_location")}>{c(`reason_${precheck.reason}`)}</Message>
    </div>}

    <div className={styles.actions}>
      {active
        ? <CommercialButton data-auto-brief-cancel variant="secondary" size="touch" onClick={() => controller.cancel(caseId)} data-testid="auto-brief-cancel">{c("cancel")}</CommercialButton>
        : !finished && !resumable && <CommercialButton data-auto-brief-primary size="touch" disabled={!precheck.ok} onClick={() => void controller.start(caseId)} data-testid="auto-brief-start">{c("start")}</CommercialButton>}
      {finished && <Link data-auto-brief-primary prefetch={false} className="ds-button ds-button--primary ds-button--touch" href={`${base}/overview`} data-testid="auto-brief-view-brief">{c("viewBrief")}</Link>}
      {resumable && precheck.ok && <CommercialButton data-auto-brief-primary size="touch" onClick={() => void controller.continue(caseId)} data-testid="auto-brief-continue">{c("continue")}</CommercialButton>}
      {terminal && precheck.ok && <CommercialButton variant="secondary" size="touch" onClick={() => void controller.start(caseId)} data-testid="auto-brief-restart">{c("restart")}</CommercialButton>}
      {!active && <Link prefetch={false} className="ds-button ds-button--tertiary ds-button--touch" href={`${base}/market`} data-testid="auto-brief-manual">{c("manual")}</Link>}
    </div>

    {run && <div className={styles.progress}>
      <div role="status" aria-live="polite" data-testid="auto-brief-status" className={styles.summary}>
        <strong>{c(`run_${run.status}`)}</strong>
        {active && run.currentStep && <span> · {c(`step_${run.currentStep}`)}</span>}
        {run.reason && run.reason !== "cancelled" && !active && <p className="text-helper">{c(`reason_${run.reason}`)}</p>}
        {finished && run.gapCount !== null && <p className="text-helper" data-testid="auto-brief-gaps">{run.gapCount ? c("gaps", { count: run.gapCount }) : c("noGaps")}</p>}
      </div>
      <ol className={styles.steps} aria-label={c("progress")}>
        {run.steps.map((step) => <StepRow key={step.id} c={c} step={step} retry={terminal && precheck.ok && step.retryable ? () => void controller.retryStep(caseId, step.id) : undefined} />)}
      </ol>
      {terminal && money?.status === "needs_input" && <Link prefetch={false} className="ds-button ds-button--secondary ds-button--compact" href={`${base}/finance`} data-testid="auto-brief-go-money">{c("goMoney")}</Link>}
    </div>}
  </section>;

}

type Translate = (key: keyof typeof autoBriefCopy.en, values?: Record<string, string | number>) => string;

function StepRow({ c, step, retry }: { c: Translate; step: AutoBriefStep; retry?: () => void }) {
  const label = c(`step_${step.id}`);
  return <li className={styles.step} data-testid={`auto-brief-step-${step.id}`} data-status={step.status} aria-current={step.status === "running" ? "step" : undefined}>
    <div className={styles.stepLine}>
      <span className={styles.stepLabel}>{label}</span>
      <StatusLabel semanticRole={ROLE[step.status]}>{c(`status_${step.status}`)}</StatusLabel>
    </div>
    {step.parts && <p className="text-helper">{c("part_nearby")}: {c(`status_${step.parts.nearby}`)} · {c("part_demographics")}: {c(`status_${step.parts.demographics}`)}{step.reused ? ` · ${c("reused")}` : ""}</p>}
    {step.reason && step.status !== "available" && step.reason !== "cancelled" && <p className="text-helper">{c(`reason_${step.reason}`)}</p>}
    {retry && <CommercialButton variant="tertiary" size="compact" onClick={retry} aria-label={c("retryStep", { step: label })} data-testid={`auto-brief-retry-${step.id}`}>{c("retry")}</CommercialButton>}
  </li>;
}
