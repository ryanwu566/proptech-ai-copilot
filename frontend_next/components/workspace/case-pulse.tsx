"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { RoomRead } from "@/lib/decision-room-store";
import { createBrowserDecisionRoomReader } from "@/lib/decision-room-reader";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import { buildCasePulse, presentCasePulse } from "@/lib/workspace/case-pulse";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import styles from "./case-pulse.module.css";

export function CasePulse({ workspace }: { workspace: PropertyCaseWorkspace }) {
  const { locale } = useExperienceLocale();
  const repository = useMemo(createBrowserDecisionRoomReader, []);
  const [roomState, setRoomState] = useState<{ caseId: string; read: RoomRead } | null>(null);
  useEffect(() => {
    const load = () => setRoomState({ caseId: workspace.caseId, read: repository.read(workspace.caseId) });
    load();
    return repository.subscribe(workspace.caseId, load);
  }, [repository, workspace.caseId]);
  const model = buildCasePulse(workspace, roomState?.caseId === workspace.caseId ? roomState.read : { status: "unavailable" });
  const view = presentCasePulse(model, locale);
  return <section className={styles.pulse} aria-label={view.title} data-testid="case-pulse">
    <div className={styles.heading}><span>{view.title}</span></div>
    <ul className={styles.items}>
      {view.items.map((item) => <li key={item.section}>
        <Link className={styles.item} href={item.href} prefetch={false} data-pulse-section={item.section} data-pulse-state={item.state}>
          <span className={styles.label}><span className={styles.dot} aria-hidden="true" />{item.label}</span>
          <span className={styles.value} key={`${item.state}:${item.text}`}>{item.text}</span>
        </Link>
      </li>)}
    </ul>
    <p className={styles.activity} role="status" aria-live="polite" aria-atomic="true">
      {view.activity && model.activity && <>{view.activity}<span aria-hidden="true"> · </span><time dateTime={model.activity.at}>{new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(model.activity.at))}</time></>}
    </p>
  </section>;
}

/** Standalone routes keep their own diagnostic reads; this subscription is read-only. */
export function SavedCasePulse({ caseId }: { caseId: string }) {
  const repository = useMemo(createBrowserCaseRepository, []);
  const [workspace, setWorkspace] = useState<PropertyCaseWorkspace | null>(null);
  useEffect(() => {
    const load = () => setWorkspace(repository.getCase(caseId));
    load();
    return repository.subscribe(load);
  }, [caseId, repository]);
  return workspace?.caseId === caseId ? <CasePulse key={caseId} workspace={workspace} /> : null;
}
