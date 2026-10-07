import Link from "next/link";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { StatusLabel } from "@/components/design-system/status-label";
import { Message } from "@/components/design-system/message";
import { formatExactDate } from "@/lib/commercial/formatters";
import type { EvidenceField, CaseEvidenceModel } from "@/lib/workspace/case-evidence";
import { EVIDENCE_STATUS_LABELS, GAP_LABELS } from "@/lib/workspace/evidence-labels";
import type { WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import styles from "./evidence.module.css";

export function date(value: string | null): string { return value ? formatExactDate(value) : "未保存／未知"; }
function valueText(value: string | number, unit: string): string { return `${typeof value === "number" ? value.toLocaleString("zh-TW", { maximumFractionDigits: 2 }) : value}${unit ? ` ${unit}` : ""}`; }
function Provenance({ field }: { field: EvidenceField<string | number> }) {
  return <div className={styles.provenance}>
    <p>來源：{field.source}</p><p>檢查／計算時間：{date(field.freshness.checkedAt)}</p><p>來源更新時間：{date(field.freshness.sourceUpdatedAt)}</p>
    <p>保存快照 · 輸入關聯：{{ matches: "符合保存條件", stale: "已失效", unknown: "未知" }[field.freshness.inputRelation]} · 時間：{{ within_source_policy: "依來源政策有效", stale: "來源已標示過期", unknown: "未保存有效期政策" }[field.freshness.timeRelation]}</p>
    <p>限制：{field.limitation}</p><p>下一步：{field.nextAction}</p>
  </div>;
}
export function EvidenceValue({ field }: { field: EvidenceField<string | number> }) {
  return <div className={styles.value} data-evidence-status={field.status}>
    <strong className={typeof field.value === "number" ? styles.numeric : undefined} data-numeric={typeof field.value === "number" || undefined}>{field.value === null ? field.missingReason ? GAP_LABELS[field.missingReason] : "未保存" : valueText(field.value, field.unit)}</strong>
    <StatusLabel semanticRole="neutral">{EVIDENCE_STATUS_LABELS[field.status]}</StatusLabel>
    {field.historicalValue !== null && <p className="text-meta">先前保存值（不能視為目前）：{valueText(field.historicalValue, field.unit)}</p>}
    <div className={styles.screenOnly}><DetailsDisclosure summary={`${field.label}：來源與限制`} variant="compact"><Provenance field={field} /></DetailsDisclosure></div>
    <div className={styles.printOnly}><Provenance field={field} /></div>
  </div>;
}
export function EvidenceGaps({ cases, actionsOnly = false }: { cases: CaseEvidenceModel[]; actionsOnly?: boolean }) {
  return <div className={styles.gaps}>{cases.map((item) => <div key={item.caseId}>
    <h3 className="text-subsection">{item.title}</h3>
    {item.gaps.length === 0 ? <p>沒有列出的證據缺口；仍適用各來源限制。</p> : <ul>{item.gaps.map((gap) => <li key={gap.id}>
      <strong>{gap.item}</strong>{!actionsOnly && <><span> · {GAP_LABELS[gap.reason]}</span><p>{gap.impact}</p></>}
      <p>{gap.nextAction}</p><Link href={gap.href}>前往查證工作區</Link>
    </li>)}</ul>}
  </div>)}</div>;
}
const coverageLabels: { [key: string]: string } = { covered: "來源範圍內", not_covered: "未覆蓋", coverage_unknown: "覆蓋未知", unknown: "未知", nationwide: "全國範圍", partial: "部分範圍" };
export function EvidenceSources({ cases }: { cases: CaseEvidenceModel[] }) {
  return <div className={styles.sources}><p>由本機案件保存摘要產生。沒有執行新查詢、財務重算或 AI 撰文。儲存時間、報告產生時間、來源檢查時間與來源更新時間各自獨立。</p>
    {cases.map((item) => <div key={item.caseId}><h3 className="text-subsection">{item.title}</h3>{item.sources.map((source) => <article key={source.id}>
      <h4>{source.name}</h4>
      <p>檢查／計算：{date(source.checkedAt)} · 更新：{date(source.updatedAt)}</p>
      <p>資料期間：{source.period ?? "未保存"} · 版本：{source.version ?? "未保存"}</p>
      <p>覆蓋：{coverageLabels[source.coverage] ?? source.coverage} · 查詢條件：{source.queryCondition}</p>
      <p>限制：{source.limitation}</p>
      {source.url && <a href={source.url} target="_blank" rel="noopener noreferrer">{source.url}</a>}
    </article>)}</div>)}
  </div>;
}
export const STORAGE_MESSAGES = { parse_error: "儲存資料無法解析；請回到已儲存案件檢查本機資料。", invalid_storage: "儲存資料格式不正確；不能產生正式比較或報告。", storage_unavailable: "瀏覽器儲存目前無法讀取；請恢復本機儲存存取後重試。" } as const;
export function storageBlocked(read: WorkspaceReadDiagnostic): boolean { return read.status in STORAGE_MESSAGES; }
export function RepositoryNotice({ read }: { read: WorkspaceReadDiagnostic }) {
  if (storageBlocked(read)) return <Message variant="error">{STORAGE_MESSAGES[read.status as keyof typeof STORAGE_MESSAGES]}</Message>;
  if (read.issues.length) return <Message variant="warning">部分儲存案件無效或識別重複，已停止使用這些紀錄；不會以其他案件替代。請回到案件清單處理。</Message>;
  return null;
}
