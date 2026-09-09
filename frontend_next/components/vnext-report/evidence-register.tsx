import type { ReportEvidenceModel } from "@/lib/vnext-report";
import { ReportStatusBadge } from "./report-status-badge";
import styles from "./decision-report-presentation.module.css";

export function EvidenceRegister({ evidence }: { evidence: ReportEvidenceModel[] }) {
  return <section className={styles.reportSection} aria-labelledby="report-evidence-title" data-testid="evidence-register">
    <div className={styles.sectionHeading}>
      <div>
        <p className={styles.eyebrow}>TRACEABILITY</p>
        <h2 id="report-evidence-title">證據、來源與限制</h2>
      </div>
      <p>{evidence.length} 項證據紀錄</p>
    </div>
    <p className={styles.sectionIntro}>取得時間與資料生效時間分開呈現；未提供的來源、時間或涵蓋範圍會保留為缺漏。</p>
    {evidence.length === 0
      ? <div className={styles.emptyEvidence} role="note">
        <strong>證據來源與溯源資料未提供</strong>
        <p>目前不能確認來源、取得時間、生效時間或涵蓋範圍；這不表示分析已通過。</p>
      </div>
      : <ol className={styles.evidenceList}>
        {evidence.map((item, index) => <li key={`${item.id ?? "missing"}-${index}`}>
          <details className={styles.evidenceDetails} data-testid={`evidence-detail-${index}`}>
            <summary>
              <span><b>{item.label}</b><small>{sectionLabel(item.section)}</small></span>
              <ReportStatusBadge status={item.status} />
            </summary>
            <EvidenceMeta item={item} />
          </details>
          <div className={styles.printEvidenceRecord} aria-hidden="true" data-testid={`print-evidence-detail-${index}`}>
            <div className={styles.printEvidenceHeading}><b>{item.label}</b><ReportStatusBadge status={item.status} /></div>
            <EvidenceMeta item={item} />
          </div>
        </li>)}
      </ol>}
  </section>;
}

function EvidenceMeta({ item }: { item: ReportEvidenceModel }) {
  return <dl className={styles.evidenceMeta}>
    <Meta label="證據識別碼" value={item.id} missing="未提供" />
    <Meta label="來源標籤" value={item.sourceLabel} missing="未提供（來源資訊缺漏）" />
    <Meta label="來源取得時間" value={formatTime(item.retrievedAt)} missing="未提供" />
    <Meta label="資料生效時間" value={formatTime(item.effectiveAt)} missing="未提供（不可用取得時間代替）" />
    <Meta label="涵蓋範圍" value={item.coverage} missing="未提供" />
    <Meta label="限制" value={item.limitation} missing="未提供（限制資訊缺漏）" />
  </dl>;
}

function Meta({ label, value, missing }: { label: string; value?: string | null; missing: string }) {
  return <div><dt>{label}</dt><dd className={!value ? styles.missingMeta : undefined}>{value || missing}</dd></div>;
}

function sectionLabel(section: ReportEvidenceModel["section"]): string {
  return {
    valuation: "估價／市場",
    affordability: "負擔／持有成本",
    terrain: "地勢／空間",
    tax: "稅務／其他",
    identity: "物件身分",
    other: "其他觀察",
  }[section];
}

function formatTime(value?: string | null): string | null {
  if (!value) return null;
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value.slice(0, 160);
  return new Intl.DateTimeFormat("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Taipei",
  }).format(new Date(timestamp));
}
