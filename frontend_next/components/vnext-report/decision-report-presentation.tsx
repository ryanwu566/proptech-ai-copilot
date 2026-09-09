"use client";

import type { DecisionReportModel } from "@/lib/vnext-report";
import { BeforeViewingChecklist } from "./before-viewing-checklist";
import { EvidenceRegister } from "./evidence-register";
import { ReportSectionCard } from "./report-section-card";
import styles from "./decision-report-presentation.module.css";

export function DecisionReportPresentation({ report }: { report: DecisionReportModel }) {
  return <div className={styles.reportFrame}>
    <div className={styles.toolbar}>
      <div>
        <strong>決策報告預覽</strong>
        <span>瀏覽器原生列印會保留警示、來源與限制。</span>
      </div>
      <button type="button" onClick={() => window.print()} data-testid="print-report">列印／另存 PDF</button>
    </div>

    <article className={styles.report} data-testid="decision-report" data-synthetic={report.syntheticPreview ? "true" : "false"}>
      <header className={styles.reportHeader}>
        <div className={styles.headerTopline}>
          <span>PROPERTY VIEWING BRIEF</span>
          <span>報告格式 v1</span>
        </div>
        {report.syntheticPreview && <div className={styles.syntheticNotice} data-testid="synthetic-notice">合成案例預覽／非真實物件／非官方來源</div>}
        <div className={styles.headerGrid}>
          <div>
            <p className={styles.caseLabel}>{report.caseLabel}</p>
            <h1>{report.propertyLabel}</h1>
            <p className={styles.generatedTime}>報告產生時間：<time dateTime={report.generatedAt}>{formatTime(report.generatedAt)}</time></p>
          </div>
          <div className={styles.identityCard} data-testid="identity-status" data-identity-status={report.identity.status}>
            <span>物件身分狀態</span>
            <strong>{report.identity.label}</strong>
            {report.identity.detail && <p>{report.identity.detail}</p>}
            <p>{report.identity.boundary}</p>
          </div>
        </div>
      </header>

      <main>
        <section className={`${styles.decisionOverview} ${styles[`decision_${report.decision.displayStatus}`]}`} aria-labelledby="decision-overview-title" data-testid="decision-overview" data-engine-status={report.decision.sourceStatus}>
          <div className={styles.decisionLead}>
            <p className={styles.eyebrow}>EXISTING RULE OUTPUT</p>
            <h2 id="decision-overview-title">{report.decision.label}</h2>
            <p>{report.decision.summary}</p>
          </div>
          <div className={styles.decisionColumns}>
            <DecisionList title="支持這項呈現的理由" items={report.decision.reasons} empty="既有規則未提供可顯示理由。" />
            <DecisionList title="已知風險" items={report.decision.knownRisks} empty="目前沒有由既有規則辨識的已知高風險；不等於安全。" risk />
            <DecisionList title="缺漏與不確定資訊" items={report.decision.missingInformation} empty="核心缺漏清單目前為空；仍須閱讀各證據限制。" warning />
          </div>
        </section>

        <section className={styles.analysisSection} aria-labelledby="analysis-title">
          <div className={styles.sectionHeading}>
            <div><p className={styles.eyebrow}>ANALYSIS</p><h2 id="analysis-title">分析摘要</h2></div>
            <p>不使用新的綜合分數</p>
          </div>
          <div className={styles.analysisGrid}>{report.sections.map((section) => <ReportSectionCard key={section.id} section={section} />)}</div>
        </section>

        <section className={styles.reportSection} aria-labelledby="other-observations-title">
          <div className={styles.sectionHeading}>
            <div><p className={styles.eyebrow}>OTHER NOTES</p><h2 id="other-observations-title">其他可用觀察</h2></div>
          </div>
          <ul className={styles.observationList}>
            {(report.otherObservations.length ? report.otherObservations : ["目前未提供其他觀察；未提供不等於沒有其他風險。"])
              .map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>

        <EvidenceRegister evidence={report.evidence} />
        <BeforeViewingChecklist items={report.checklist} />

        <section className={`${styles.reportSection} ${styles.limitations}`} aria-labelledby="report-limitations-title">
          <div className={styles.sectionHeading}>
            <div><p className={styles.eyebrow}>BOUNDARIES</p><h2 id="report-limitations-title">報告限制</h2></div>
          </div>
          <ul>{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      </main>

      <footer className={styles.reportFooter}>
        <p>{report.syntheticPreview ? "合成預覽資料，不得作為真實交易或正式來源證明。" : "請連同證據來源、時間、涵蓋範圍與限制使用本報告。"}</p>
        <p>報告產生時間：{formatTime(report.generatedAt)}</p>
      </footer>
    </article>
  </div>;
}

function DecisionList({ title, items, empty, risk = false, warning = false }: { title: string; items: string[]; empty: string; risk?: boolean; warning?: boolean }) {
  return <div className={`${styles.decisionList} ${risk ? styles.riskList : ""} ${warning ? styles.warningList : ""}`}>
    <h3>{title}</h3>
    <ul>{(items.length ? items : [empty]).map((item) => <li key={item}>{item}</li>)}</ul>
  </div>;
}

function formatTime(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Intl.DateTimeFormat("zh-TW", { dateStyle: "long", timeStyle: "short", timeZone: "Asia/Taipei" }).format(new Date(timestamp));
}
