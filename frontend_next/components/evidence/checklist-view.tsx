"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Section, ActionSection } from "@/components/design-system/section";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import { projectCaseEvidence } from "@/lib/workspace/case-evidence";
import { buildEvidenceChecklist, setChecklistReview, CHECKLIST_DOMAINS, MANUAL_REVIEW_LABELS } from "@/lib/workspace/evidence-checklist";
import type { StoredChecklistReviewV1, ChecklistId, ManualReviewState } from "@/lib/workspace/checklist-persistence";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { EVIDENCE_STATUS_LABELS, GAP_LABELS } from "@/lib/workspace/evidence-labels";
import styles from "./checklist.module.css";
import { reviewDate } from "./manual-review-summary";

export function ChecklistView({ workspace }: { workspace: PropertyCaseWorkspace }) {
  const repository = useMemo(createBrowserCaseRepository, []);
  const [draft, setDraft] = useState<{ base: string; review: StoredChecklistReviewV1 } | null>(null);
  const [notice, setNotice] = useState<{ error: boolean; text: string } | null>(null);
  const evidence = projectCaseEvidence({ ...workspace, checklistReview: draft?.review ?? workspace.checklistReview });
  const items = buildEvidenceChecklist(evidence);
  const staleDraft = Boolean(draft && draft.base !== workspace.updatedAt);
  const canReview = workspace.identity.state === "confirmed" && !staleDraft;
  function change(id: ChecklistId, state: ManualReviewState) {
    const review = setChecklistReview({ ...workspace, checklistReview: draft?.review ?? workspace.checklistReview }, id, state, new Date().toISOString());
    if (review) { setDraft({ base: draft?.base ?? workspace.updatedAt, review }); setNotice(null); }
  }
  function save() {
    if (!draft || !canReview) return;
    try {
      const result = repository.saveChecklist(workspace, draft.review);
      if (result.status === "blocked") { setNotice({ error: true, text: `人工核對狀態未保存。${result.message}` }); return; }
      setDraft(null); setNotice({ error: false, text: "人工核對狀態已保存於此瀏覽器案件。" });
    } catch { setNotice({ error: true, text: "人工核對狀態未保存。瀏覽器儲存失敗；請恢復儲存空間或存取後重試。" }); }
  }
  return <Section title="證據查證清單" description="人工核對是使用者提供的紀錄，不代表官方查證；未知、未命中與無法取得仍保留原狀。">
    <div id="evidence-checklist" className={styles.checklist}>
      <ul className={styles.preview}>{items.filter((item) => item.reviewState !== "reviewed").slice(0, 3).map((item) => <li key={item.id}><strong>{item.name}</strong> · {MANUAL_REVIEW_LABELS[item.reviewState]}<p>{item.nextAction}</p></li>)}</ul>
      {workspace.identity.state !== "confirmed" && <Message variant="warning">物件身分需重新確認；先前人工核對僅保留為歷史紀錄，目前不能新增核對。</Message>}
      {staleDraft && <Message variant="warning">案件已有較新快照；草稿不能覆蓋新證據。請載入已保存核對狀態後再核對。</Message>}
      {notice && <div role={notice.error ? undefined : "status"}><Message variant={notice.error ? "error" : "information"}>{notice.text}</Message></div>}
      {draft && <div role="status"><Message>尚未保存人工核對變更。</Message></div>}
      <DetailsDisclosure summary="開啟完整查證清單">
        {Object.entries(CHECKLIST_DOMAINS).map(([domain, label]) => <section key={domain} className={styles.domain} aria-label={`${label}查證項目`}>
          <h3 className="text-subsection">{label}</h3>
          <ul>{items.filter((item) => item.domain === domain).map((item) => <li key={item.id} data-testid={`checklist-${item.id}`} className={styles.item}>
            <h4>{item.name}</h4>
            <p>來源證據狀態：{[...new Set(item.fields.map((field) => EVIDENCE_STATUS_LABELS[field.status]))].join("；") || "自動查證未支援"}</p>
            <p>缺少或受限原因：{[...new Set(item.gaps.map((gap) => GAP_LABELS[gap.reason]))].join("；") || "保存摘要仍有來源與適用範圍限制"}</p>
            <p>為何重要：{item.impact}</p>
            <p>來源：{[...new Set(item.fields.map((field) => field.source).concat(item.sources.map((source) => source.name)))].join("；") || "來源未保存"}</p>
            {item.sources.filter((source) => source.url).map((source) => <p key={source.id}><a href={source.url!} target="_blank" rel="noopener noreferrer">查看保存的來源：{source.name}</a></p>)}
            <p>下一步：{item.nextAction}</p><Link href={item.href}>前往{CHECKLIST_DOMAINS[item.domain]}工作區</Link>
            <div className={styles.controls}>
              <label><input type="checkbox" checked={item.reviewState === "reviewed"} disabled={!canReview} onChange={(event) => change(item.id, event.target.checked ? "reviewed" : "not_checked")} />已由使用者核對：{item.name}</label>
              <label>人工核對狀態：{item.name}<select value={item.reviewState} disabled={!canReview} onChange={(event) => change(item.id, event.target.value as ManualReviewState)}>{Object.entries(MANUAL_REVIEW_LABELS).map(([state, label]) => <option key={state} value={state}>{label}</option>)}</select></label>
            </div>
            {item.reviewedAt && <p className="text-meta">先前人工核對：{reviewDate(item.reviewedAt)}{item.reviewState === "recheck" ? "；證據或物件已變更，需再次核對。" : "；僅為使用者紀錄。"}</p>}
            {!item.outstanding && <p>原缺口已由保存的來源證據補齊；人工核對紀錄仍保留。</p>}
          </li>)}</ul>
        </section>)}
      </DetailsDisclosure>
      <ActionSection>
        <CommercialButton onClick={save} disabled={!draft || !canReview}>保存人工核對</CommercialButton>
        {draft && <CommercialButton variant="secondary" onClick={() => { setDraft(null); setNotice(null); }}>載入已保存核對狀態</CommercialButton>}
      </ActionSection>
    </div>
  </Section>;
}
