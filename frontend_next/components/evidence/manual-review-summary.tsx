import type { CaseEvidenceModel } from "@/lib/workspace/case-evidence";
import { buildEvidenceChecklist, CHECKLIST_DOMAINS, MANUAL_REVIEW_LABELS } from "@/lib/workspace/evidence-checklist";
import styles from "./checklist.module.css";

export function reviewDate(value: string): string { return new Date(value).toLocaleString("zh-TW", { timeZone: "Asia/Taipei" }); }

export function ManualReviewSummary({ evidence }: { evidence: CaseEvidenceModel }) {
  const records = buildEvidenceChecklist(evidence).filter((item) => item.reviewState !== "not_checked" || item.reviewedAt !== null);
  return <div data-testid="report-manual-review" className={styles.checklist}>
    <h3 className="text-subsection">使用者人工核對紀錄</h3>
    <p>這是報告快照中的使用者紀錄，不代表官方查證，不會將未知或未命中改為安全。</p>
    {!records.length ? <p>尚未保存人工核對紀錄；來源證據與待查證缺口仍依上列狀態判讀。</p> : <ul>{records.map((item) => <li key={item.id}>{CHECKLIST_DOMAINS[item.domain]} · {item.name}：{MANUAL_REVIEW_LABELS[item.reviewState]}{item.reviewedAt && `；先前人工核對 ${reviewDate(item.reviewedAt)}`}{!item.outstanding && "；保存來源已補齊原缺口"}。</li>)}</ul>}
  </div>;
}
