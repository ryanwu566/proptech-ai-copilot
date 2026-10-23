"use client";
import Link from "next/link";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { identityConfirmationCopy, identityConfirmationKind } from "@/lib/workspace/identity-confirmation-copy";
import { useEffect, useMemo, useRef, useState } from "react";
import { Section, ActionSection } from "@/components/design-system/section";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { AsyncState } from "@/components/design-system/async-state";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { projectCaseEvidence, type CaseEvidenceModel } from "@/lib/workspace/case-evidence";
import { assessReportSnapshot, buildReportModel } from "@/lib/workspace/compare-report-model";
import { EvidenceValue, EvidenceGaps, EvidenceSources, RepositoryNotice, storageBlocked, date } from "./evidence-view";
import styles from "./evidence.module.css";
import { ManualReviewSummary } from "./manual-review-summary";
import { ComparableExplanation } from "../workspace/market/comparable-explanation";
import { CopilotLink } from "../workspace/copilot/copilot-link";
import { EvidenceCitation, ReportCitationReferences } from "./citation";
import { buildReportExecutiveSummary } from "@/lib/workspace/report-executive";
import { ReportExecutive } from "./report-executive";
import { buildReportCore } from "@/lib/workspace/report-core";
import { EMPTY_REPORT_BRANDING, ReportAppendixHeading, ReportCorePages, ReportPreparedBy } from "./report-core";
import { useReportRoom } from "./report-decision-room-entry";
function currentEvidence(read: WorkspaceReadDiagnostic, caseId: string): CaseEvidenceModel | null { const workspace = read.cases.find((item) => item.caseId === caseId); return workspace ? projectCaseEvidence(workspace) : null; }
function invalid(read: WorkspaceReadDiagnostic, caseId: string): boolean { return storageBlocked(read) || read.issues.some((issue) => issue.caseId === caseId); }
export function ReportView({ caseId }: { caseId: string }) {
  const { copyFrom } = useExperienceLocale();
  const repository = useMemo(createBrowserCaseRepository, []);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  const [frozen, setFrozen] = useState<{ evidence: CaseEvidenceModel; generatedAt: string } | null>(null);
  const frozenRef = useRef<typeof frozen>(null);
  const root = useRef<HTMLElement>(null);
  const roomRead = useReportRoom(caseId);
  const room = roomRead?.report ?? null; const roomUi = roomRead?.ui ?? null;
  useEffect(() => {
    const load = () => {
      const next = repository.readDiagnostic(); setRead(next);
      const evidence = currentEvidence(next, caseId);
      if (!frozenRef.current && evidence?.identity.state === "confirmed" && !invalid(next, caseId)) {
        const snapshot = { evidence, generatedAt: new Date().toISOString() }; frozenRef.current = snapshot; setFrozen(snapshot);
      }
    };
    const beforePrint = () => {
      root.current?.setAttribute("data-print-blocked", "true");
      const next = repository.readDiagnostic();
      const current = currentEvidence(next, caseId);
      const blocked = invalid(next, caseId) || current?.identity.state !== "confirmed" || !frozenRef.current;
      // Synchronous DOM guard covers browser-menu printing before React can commit.
      root.current?.setAttribute("data-print-blocked", String(blocked));
      setRead(next);
    };
    load(); const unsubscribe = repository.subscribe(load);
    window.addEventListener("beforeprint", beforePrint);
    return () => { unsubscribe(); window.removeEventListener("beforeprint", beforePrint); };
  }, [caseId, repository]);
  const current = read ? currentEvidence(read, caseId) : null;
  const currentIdentity = read?.cases.find((item) => item.caseId === caseId)?.identity;
  const reconfirmation = currentIdentity && identityConfirmationKind(currentIdentity) === "reconfirmation";
  const assessment = read && frozen ? assessReportSnapshot(frozen.evidence, current, invalid(read, caseId)) : null;
  const blocked = read && (invalid(read, caseId) || current?.identity.state !== "confirmed");
  const report = frozen ? buildReportModel(frozen.evidence, frozen.generatedAt) : null;
  const executive = report?.evidence ? buildReportExecutiveSummary(report.evidence, report.citations, report.generatedAt) : null;
  const core = report?.evidence ? buildReportCore(report.evidence) : null;
  function loadNewer() {
    const next = repository.readDiagnostic(); const evidence = currentEvidence(next, caseId); setRead(next);
    if (!evidence || evidence.identity.state !== "confirmed" || invalid(next, caseId)) return;
    const snapshot = { evidence, generatedAt: new Date().toISOString() }; frozenRef.current = snapshot; setFrozen(snapshot);
  }
  function print() {
    const next = repository.readDiagnostic(); const evidence = currentEvidence(next, caseId); setRead(next);
    if (!evidence || evidence.identity.state !== "confirmed" || invalid(next, caseId) || !frozenRef.current) { root.current?.setAttribute("data-print-blocked", "true"); return; }
    root.current?.setAttribute("data-print-blocked", "false"); window.print();
  }
  return <main id="main-content" ref={root} className={`${styles.page} ${styles.report}`} data-print-blocked={Boolean(blocked)}>
    {(!report || blocked) && <header className={styles.screenOnly}><h1 className="text-page">案件證據報告</h1></header>}
    {!read || !roomRead ? <AsyncState kind="loading" title="正在讀取案件快照" /> : <>
      <div className={styles.screenOnly}><RepositoryNotice read={read} /></div>
      {blocked || !report ? <div className={styles.screenOnly} data-testid="report-identity-gate"><Message variant="error">
        {invalid(read, caseId) ? "案件儲存紀錄無效或識別衝突；正式報告與列印已停止。" : !current ? "找不到已儲存案件，或案件已被移除；正式列印已停止。" : copyFrom(identityConfirmationCopy, reconfirmation ? "reconfirmationReport" : "pendingReport")}
        <ActionSection><Link href="/cases" className="ds-button ds-button--secondary">回到已儲存案件</Link>{current && <Link href={`/cases/${encodeURIComponent(caseId)}/${reconfirmation ? "overview" : "location"}`} className="ds-button ds-button--secondary">{copyFrom(identityConfirmationCopy, reconfirmation ? "reconfirmationAction" : "pendingAction")}</Link>}</ActionSection>
      </Message></div> : <>
        <div className={styles.screenOnly} data-testid="report-controls">
          <CopilotLink caseId={caseId} />
          <ActionSection><CommercialButton onClick={print}>列印／另存 PDF</CommercialButton><Link href={`/cases/${encodeURIComponent(caseId)}/overview`} className="ds-button ds-button--secondary">返回案件工作區</Link>{roomUi && <roomUi.OpenRoomLink caseId={caseId} />}<Link href="/cases" className="ds-button ds-button--secondary">已儲存案件</Link></ActionSection>
          <p className="text-meta">開啟瀏覽器列印對話框，可選擇另存為 PDF。</p>
          {assessment === "snapshot_changed" && <div data-testid="snapshot-change"><Message variant="warning" action={<CommercialButton variant="secondary" onClick={loadNewer}>載入較新快照</CommercialButton>}>案件已有較新快照；目前畫面與列印仍使用你正在檢視的保存快照。</Message></div>}
        </div>
        <article data-testid="report-evidence" className={styles.reportEvidence}>
          <header className={styles.reportCover}><h1 className="text-page">案件證據報告 · {report.evidence!.title}</h1><p>{report.evidence!.displayAddress}</p><ReportPreparedBy branding={EMPTY_REPORT_BRANDING} /><div className={styles.screenOnly}><p>案件保存：{date(report.evidence!.savedAt)} · 報告產生：{date(report.generatedAt)}</p><p>{report.status === "ready_with_limits" ? "可閱讀的證據摘要，含待查證限制" : "可閱讀的保存證據摘要"}</p><Message>本報告依已儲存證據快照製作；不是即時重新查詢。{report.evidence!.identity.limitation}</Message></div></header>
          {executive && <ReportExecutive summary={executive} citations={report.citations} room={room && roomUi && <roomUi.RoomReadiness report={room} />} />}
          {core && <ReportCorePages core={core} citations={report.citations} askingUnit={executive?.keyNumbers.find((item) => item.id === "asking_unit")} room={room} roomUi={roomUi} />}
          {/* Detailed evidence is kept whole: every section, full provenance and the reference ledger. */}
          <section aria-labelledby="report-appendix" className={styles.appendix} data-testid="report-appendix" data-report-page="appendix">
          <ReportAppendixHeading />
          {report.sections.map((section, index) => <Section key={section.id} headingLevel={3} title={`A${index + 1}. ${section.title}`} description={section.evidenceSection?.description}>
            {section.id === "context" && <p>{report.evidence!.title} · {report.evidence!.displayAddress}。{report.evidence!.identity.limitation}</p>}
            {section.evidenceSection && <table className={styles.reportTable}><caption className="sr-only">{section.title}</caption>{/* Fixed layout honours <col> widths; cell widths alone left a 50/50 split. */}<colgroup><col className={styles.reportLabelColumn} /><col /></colgroup><tbody>{section.evidenceSection.rows.map((row) => <tr key={row.id}><th scope="row">{row.label}</th><td><EvidenceValue field={row.cells[0]} />{report.citations.filter(citation => citation.observationId === row.id).map(citation => <EvidenceCitation key={citation.id} citation={citation} number={report.citations.indexOf(citation) + 1} report />)}</td></tr>)}</tbody></table>}
            {section.id === "summary" && <ul>{report.summary.map((sentence) => <li key={sentence}>{sentence}</li>)}</ul>}
            {section.id === "market" && <ComparableExplanation report value={report.evidence!.comparableExplanation} stale={report.evidence!.price.valuationEstimate.status === "stale"} />}
            {section.id === "limits" && <div id="report-limits" tabIndex={-1}><EvidenceGaps cases={[report.evidence!]} /></div>}
            {section.id === "actions" && <><EvidenceGaps cases={[report.evidence!]} actionsOnly /><ManualReviewSummary evidence={report.evidence!} /></>}
            {section.id === "sources" && <EvidenceSources cases={[report.evidence!]} />}
          </Section>)}
          {room && roomUi && <roomUi.RoomAppendix report={room} index={report.sections.length + 1} />}
          </section>
          <ReportCitationReferences citations={report.citations} />
        </article>
      </>}
    </>}
    <p className={styles.printBlocked}>{current ? copyFrom(identityConfirmationCopy, reconfirmation ? "reconfirmationReport" : "pendingReport") : "本機案件已移除或無效；正式報告列印已停止。請返回已儲存案件。"}</p>
  </main>;
}
