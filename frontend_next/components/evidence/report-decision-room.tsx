"use client";
import Link from "next/link";
import { Section } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserDecisionRoomRepository } from "@/lib/decision-room-store";
import { decisionRoomCopy } from "@/lib/decision-room-copy";
import { projectDecisionRoomReport, ROOM_REPORT_LIMITS, type DecisionRoomReport, type RoomAction } from "@/lib/decision-room-report";
import { decisionRoomReportCopy, type DecisionRoomReportCopyKey } from "@/lib/decision-room-report-copy";
import styles from "./evidence.module.css";

/** Reads the saved Decision Room sidecar only; opening or printing the report never writes or calls a provider. */
export function watchDecisionRoomReport(caseId: string, onReport: (report: DecisionRoomReport) => void): () => void {
  const repository = createBrowserDecisionRoomRepository();
  const load = () => onReport(projectDecisionRoomReport(repository.read(caseId)));
  load();
  return repository.subscribe(caseId, load);
}

/** Core pages keep a bounded line budget; the appendix always prints the full user text. */
const brief = (text: string, max: number) => text.length > max ? `${text.slice(0, max - 1)}…` : text;

function useRoomCopy() {
  const { copyFrom, formatDate } = useExperienceLocale();
  const t = (key: DecisionRoomReportCopyKey, values?: Record<string, string | number>) => copyFrom(decisionRoomReportCopy, key, values);
  const due = (value: string) => value ? formatDate(`${value}T12:00:00`) : "";
  /** Owner · status · due · origin, in that order; user text stays as entered. */
  const meta = (action: RoomAction) => [
    `${t("owner")}: ${action.owner || t("unassigned")}`,
    `${t("status")}: ${t(`status_${action.status}`)}`,
    action.dueDate && `${t("due")}: ${due(action.dueDate)}`,
    `${t("origin")}: ${t(`origin_${action.origin}`)}`,
  ].filter(Boolean).join(" · ");
  return { t, meta, formatDate };
}

/** Report → Decision Room, screen only (the controls bar never prints). */
export function OpenRoomLink({ caseId }: { caseId: string }) {
  const { t } = useRoomCopy();
  return <Link href={`/cases/${encodeURIComponent(caseId)}/decision-room`} className="ds-button ds-button--secondary" data-testid="report-open-room">{t("openRoom")}</Link>;
}

/** Page one: a count/status statement of the buyer's own actions. Not a score. */
export function RoomReadiness({ report }: { report: DecisionRoomReport }) {
  const { t } = useRoomCopy();
  const { counts } = report;
  const sentence = { unreadable: t("readinessUnreadable"), none: t("readinessNone"), clear: t("readinessClear", { done: counts.done }), outstanding: t("readinessOutstanding", { count: counts.outstanding, verification: counts.verification }) }[report.readiness];
  return <section aria-labelledby="executive-room" data-testid="executive-room-readiness" data-readiness={report.readiness} data-outstanding={counts.outstanding}>
    <h3 id="executive-room" className="text-subsection">{t("readinessTitle")}</h3>
    <p><strong>{sentence}</strong>{report.readiness === "outstanding" && <> {t("readinessBreakdown", { open: counts.open, inProgress: counts.inProgress, blocked: counts.blocked, done: counts.done })}</>} <span className={`text-meta ${styles.screenOnly}`}>{t("readinessCaveat")}</span>
      {/* Page one's limitation already rules out a purchase recommendation; print keeps the short caveat, and only when there are counts to qualify. */}
      {report.counts.total > 0 && <span className={`text-meta ${styles.printInline}`}>{t("readinessCaveatPrint")}</span>}</p>
  </section>;
}

/** Page two: one concise reference from an evidence row to its linked Decision Room action. */
export function RoomActionRef({ action }: { action: RoomAction }) {
  const { t } = useRoomCopy();
  return <p className={styles.roomRef} data-testid="core-room-ref" data-source-key={action.sourceKey} data-status={action.status}>
    {t("nextStep")}: <span className={styles.userText} title={action.title}>{brief(action.title, 60)}</span> · {action.owner || t("unassigned")} · {t(`status_${action.status}`)}
  </p>;
}

/** Page three: the operational close. Outstanding actions first, completed work stays compact. */
export function RoomNextActions({ report, caseId }: { report: DecisionRoomReport; caseId: string }) {
  const { t, meta } = useRoomCopy();
  const rows = report.outstanding.slice(0, ROOM_REPORT_LIMITS.page3Rows);
  const more = report.outstanding.length - rows.length;
  const done = report.completed.slice(0, ROOM_REPORT_LIMITS.completedTitles);
  // An empty room prints nothing here: page one already states that no actions were recorded.
  const printEmpty = report.status !== "unreadable" && !report.counts.total;
  return <section aria-labelledby="core-room-actions" className={`${styles.coreGroup} ${styles.roomClose} ${printEmpty ? styles.screenOnly : ""}`} data-testid="core-room-actions">
    <h3 id="core-room-actions" className="text-subsection">{t("page3Title")}</h3>
    {report.status === "unreadable" ? <p>{t("readinessUnreadable")}</p> : <>
      <p className={`text-meta ${styles.screenOnly}`}>{t("page3Intro")}</p>
      {rows.length ? <ol className={styles.roomActions}>{rows.map((action) => <li key={action.id} data-testid="core-room-action" data-status={action.status} data-kind={action.kind} data-origin={action.origin}>
        <p><strong className={styles.userText} title={action.title}>{brief(action.title, 80)}</strong> <span className={styles.roomKind}>{t(`kind_${action.kind}`)}</span></p>
        <p className="text-meta">{meta(action)}</p>
      </li>)}</ol> : <p>{t("page3Empty")}</p>}
      {(more > 0 || report.completed.length > 0) && <p className="text-meta">
        {more > 0 && <span data-testid="core-room-more">{t("page3More", { count: more })}</span>}
        {more > 0 && report.completed.length > 0 && " · "}
        {report.completed.length > 0 && <span data-testid="core-room-completed"><strong>{t("completed", { count: report.completed.length })}</strong>: <span className={styles.userText}>{done.map((action) => brief(action.title, 30)).join(t("sep"))}</span>{report.completed.length > done.length && ` · ${t("completedMore", { count: report.completed.length - done.length })}`}</span>}
      </p>}
    </>}
    <p className={styles.screenOnly}><Link href={`/cases/${encodeURIComponent(caseId)}/decision-room`}>{t("openRoom")}</Link></p>
  </section>;
}

/** Appendix: every action with its note, resolution and timestamps, plus recent room activity. */
export function RoomAppendix({ report, index }: { report: DecisionRoomReport; index: number }) {
  const { t, meta, formatDate } = useRoomCopy();
  const { locale } = useExperienceLocale();
  const c = decisionRoomCopy(locale);
  const all = [...report.outstanding, ...report.completed];
  return <Section headingLevel={3} title={`A${index}. ${t("appendixTitle")}`} description={t("appendixIntro")}>
    <div data-testid="report-room-appendix">
      {report.status === "unreadable" ? <p>{t("readinessUnreadable")}</p> : !all.length ? <p>{t("appendixEmpty")}</p> : <ul className={styles.roomLedger}>{all.map((action) => <li key={action.id} data-testid="appendix-room-action" data-status={action.status}>
        <p><strong className={styles.userText}>{action.title}</strong> · {t(`kind_${action.kind}`)}{action.sourceKey && ` · ${t("linked")}`}</p>
        <p className="text-meta">{meta(action)}{action.createdAt && ` · ${t("created")}: ${formatDate(action.createdAt)}`}{action.updatedAt && ` · ${t("updated")}: ${formatDate(action.updatedAt)}`}</p>
        {action.note && <p className={styles.userText}>{t("note")}: {action.note}</p>}
        {action.resolution && <p className={styles.userText}>{t("resolution")}: {action.resolution}</p>}
      </li>)}</ul>}
      {report.history.length > 0 && <>
        <h4>{t("history", { count: report.history.length })}</h4>
        <ol className={styles.roomLedger}>{report.history.map((event) => <li key={event.id}><span>{c[event.kind]}</span>{event.subject && <span className={styles.userText}> · {event.subject}</span>} <span className="text-meta">{formatDate(event.at)}</span></li>)}</ol>
      </>}
    </div>
  </Section>;
}
