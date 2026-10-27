"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { autoBriefModeFor, isActiveRun, precheckAutoBrief } from "@/lib/workspace/auto-brief";
import { autoBriefCopy } from "@/lib/workspace/auto-brief-copy";
import { getAutoBriefController } from "@/lib/workspace/auto-brief-runtime";
import { AutoBriefStage, type Translate } from "./auto-brief-stage";
import styles from "./auto-brief-panel.module.css";

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReduced(listener: () => void) {
  const query = window.matchMedia(REDUCED_QUERY);
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
}

/**
 * Auto Brief entry and cinematic presentation. The stage only visualises the A1-1 run:
 * skipping or pausing changes the presentation, never which evidence is acquired.
 */
export function AutoBriefPanel() {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const c: Translate = (key, values) => copyFrom(autoBriefCopy, key, values);
  const controller = getAutoBriefController();
  const caseId = workspace.caseId;
  const getSnapshot = useCallback(() => controller.getRun(caseId), [controller, caseId]);
  const run = useSyncExternalStore(controller.subscribe, getSnapshot, () => null);
  const reduced = useSyncExternalStore(subscribeReduced, () => window.matchMedia(REDUCED_QUERY).matches, () => true);
  const [skip, setSkip] = useState(false);
  const [paused, setPaused] = useState(false);
  const motion = !reduced && !skip;
  const precheck = precheckAutoBrief(workspace);
  const active = Boolean(run && isActiveRun(run.status));
  const base = `/cases/${encodeURIComponent(caseId)}`;
  const panel = useRef<HTMLElement>(null);
  const wasActive = useRef(active);

  // Keep keyboard focus on a live control as the start button gives way to cancel and back; scenes never move focus.
  useEffect(() => {
    const focus = (selector: string) => panel.current?.querySelector<HTMLElement>(selector)?.focus({ preventScroll: true });
    const focusLost = document.activeElement === document.body || document.activeElement === null;
    if (active && !wasActive.current) {
      if (focusLost || panel.current?.contains(document.activeElement)) focus("[data-auto-brief-cancel]");
      panel.current?.scrollIntoView({ block: "start", behavior: motion ? "smooth" : "auto" });
    } else if (!active && wasActive.current && focusLost) focus("[data-auto-brief-primary]");
    wasActive.current = active;
  }, [active, motion]);

  function skipAnimation() {
    setSkip(true);
    setPaused(false);
  }

  function start() {
    // Skipping applies to one run; a new run is a fresh choice to watch it, unless reduced motion applies.
    setSkip(false);
    setPaused(false);
    void controller.start(caseId);
  }

  return <section ref={panel} className={styles.panel} aria-labelledby="auto-brief-title" data-testid="auto-brief-panel" data-run-status={run?.status ?? "idle"}>
    <div className={styles.heading}>
      <h2 id="auto-brief-title" className="text-section">{run ? c("stageTitle") : c("title")}</h2>
      <p className="text-dense">{c("intro")}</p>
      {autoBriefModeFor(caseId) === "demo_fixture" && <p className="text-helper" data-testid="auto-brief-demo-note">{c("demoNote")}</p>}
    </div>

    {!precheck.ok && !active && <div data-testid="auto-brief-needs-location">
      <Message variant="warning" title={c("run_needs_location")}>{c(`reason_${precheck.reason}`)}</Message>
    </div>}

    {!run && <div className={styles.actions}>
      <CommercialButton data-auto-brief-primary size="touch" disabled={!precheck.ok} onClick={start} data-testid="auto-brief-start">{c("start")}</CommercialButton>
      <Link prefetch={false} className="ds-button ds-button--secondary ds-button--touch" href={`${base}/market`} data-testid="auto-brief-manual">{c("manual")}</Link>
    </div>}

    {run && <AutoBriefStage c={c} run={run} workspace={workspace} motion={motion} paused={paused} onPause={() => setPaused((value) => !value)} onSkip={skipAnimation}
      manualHref={`${base}/market`} briefHref={`${base}/overview`} moneyHref={`${base}/finance`}
      actions={{ cancel: () => controller.cancel(caseId), start, continueRun: () => void controller.continue(caseId), retry: (id) => void controller.retryStep(caseId, id), canRestart: precheck.ok }} />}
  </section>;
}
