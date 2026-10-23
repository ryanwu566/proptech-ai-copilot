"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
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
// The Decision Room store and copy load only when an outstanding item offers the action.
const AddToDecisionRoom = dynamic(() => import("@/components/decision-room/add-to-decision-room").then((module) => module.AddToDecisionRoom), { ssr: false });

import { useExperienceLocale } from "@/components/experience-locale-provider";
import { checklistCopy, checklistDomainLabel, checklistItemName, checklistReviewLabel, checklistEvidenceStatus, checklistGapLabel, presentChecklistAction } from "@/lib/workspace/overview-presentation";

export function ChecklistView({ workspace }: { workspace: PropertyCaseWorkspace }) {
  const { locale, copyFrom } = useExperienceLocale();
  const c = (key: keyof typeof checklistCopy.en, values?: Record<string, string>) => copyFrom(checklistCopy, key, values);
  const domainName = (domain: keyof typeof CHECKLIST_DOMAINS) => checklistDomainLabel(domain, locale, CHECKLIST_DOMAINS[domain]);
  const itemName = (item: { id: string; name: string }) => checklistItemName(item.id, locale, item.name);
  const reviewLabel = (state: ManualReviewState) => checklistReviewLabel(state, locale, MANUAL_REVIEW_LABELS[state]);
  const repository = useMemo(createBrowserCaseRepository, []);
  const [draft, setDraft] = useState<{ base: string; review: StoredChecklistReviewV1 } | null>(null);
  const [notice, setNotice] = useState<{ error: boolean; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const evidence = projectCaseEvidence({ ...workspace, checklistReview: draft?.review ?? workspace.checklistReview });
  const items = buildEvidenceChecklist(evidence);
  const staleDraft = Boolean(draft && draft.base !== workspace.updatedAt);
  const canReview = workspace.identity.state === "confirmed" && !staleDraft && !saving;
  function change(id: ChecklistId, state: ManualReviewState) {
    if (savingRef.current || !canReview) return;
    const review = setChecklistReview({ ...workspace, checklistReview: draft?.review ?? workspace.checklistReview }, id, state, new Date().toISOString());
    if (review) { setDraft({ base: draft?.base ?? workspace.updatedAt, review }); setNotice(null); }
  }
  async function save() {
    if (savingRef.current || !draft || !canReview) return;
    const submittedDraft = draft;
    savingRef.current = true;
    setSaving(true);
    try {
      const result = await repository.saveChecklist(workspace, submittedDraft.review);
      if (result.status === "blocked") { setNotice({ error: true, text: `${c("notSaved")}${result.message}` }); return; }
      setDraft((current) => current === submittedDraft ? null : current); setNotice({ error: false, text: c("saved") });
    } catch { setNotice({ error: true, text: c("notSavedStorage") }); }
    finally { savingRef.current = false; setSaving(false); }
  }
  return <Section title={c("title")} description={c("description")}>
    <div id="evidence-checklist" className={styles.checklist}>
      <ul className={styles.preview}>{items.filter((item) => item.reviewState !== "reviewed").slice(0, 3).map((item) => <li key={item.id}><strong>{itemName(item)}</strong> · {reviewLabel(item.reviewState)}<p>{presentChecklistAction(item.nextAction, locale)}</p>
        {item.outstanding && <AddToDecisionRoom caseId={workspace.caseId} candidate={{ origin: (item.domain as string) === "overview" ? "identity" : item.domain, sourceKey: item.id, title: item.name, note: item.nextAction }} />}</li>)}</ul>
      {workspace.identity.state !== "confirmed" && <Message variant="warning">{c("identityStale")}</Message>}
      {staleDraft && <Message variant="warning">{c("staleDraft")}</Message>}
      {notice && <div role={notice.error ? undefined : "status"}><Message variant={notice.error ? "error" : "information"}>{notice.text}</Message></div>}
      {draft && <div role="status"><Message>{c("unsaved")}</Message></div>}
      <DetailsDisclosure summary={c("openFull")}>
        {Object.keys(CHECKLIST_DOMAINS).map((domain) => <section key={domain} className={styles.domain} aria-label={c("domainItems", { domain: domainName(domain as keyof typeof CHECKLIST_DOMAINS) })}>
          <h3 className="text-subsection">{domainName(domain as keyof typeof CHECKLIST_DOMAINS)}</h3>
          <ul>{items.filter((item) => item.domain === domain).map((item) => <li key={item.id} data-testid={`checklist-${item.id}`} className={styles.item}>
            <h4>{itemName(item)}</h4>
            <p>{c("evidenceStatus")}{[...new Set(item.fields.map((field) => checklistEvidenceStatus(field.status, locale, EVIDENCE_STATUS_LABELS[field.status])))].join("；") || c("unsupportedAuto")}</p>
            <p>{c("gapReason")}{[...new Set(item.gaps.map((gap) => checklistGapLabel(gap.reason, locale, GAP_LABELS[gap.reason])))].join("；") || c("gapDefault")}</p>
            <p>{c("whyMatters")}<span lang="zh-TW">{item.impact}</span></p>
            <p>{c("sources")}{[...new Set(item.fields.map((field) => field.source).concat(item.sources.map((source) => source.name)))].join("；") || c("noSources")}</p>
            {item.sources.filter((source) => source.url).map((source) => <p key={source.id}><a href={source.url!} target="_blank" rel="noopener noreferrer">{c("viewSource")}{source.name}</a></p>)}
            <p>{c("next")}{presentChecklistAction(item.nextAction, locale)}</p><Link href={item.href}>{c("goTo", { domain: domainName(item.domain) })}</Link>
            <div className={styles.controls}>
              <label><input type="checkbox" checked={item.reviewState === "reviewed"} disabled={!canReview} onChange={(event) => change(item.id, event.target.checked ? "reviewed" : "not_checked")} />{c("reviewedBy")}{itemName(item)}</label>
              <label>{c("reviewState")}{itemName(item)}<select value={item.reviewState} disabled={!canReview} onChange={(event) => change(item.id, event.target.value as ManualReviewState)}>{Object.keys(MANUAL_REVIEW_LABELS).map((state) => <option key={state} value={state}>{reviewLabel(state as ManualReviewState)}</option>)}</select></label>
            </div>
            {item.reviewedAt && <p className="text-meta">{c("previousReview")}{reviewDate(item.reviewedAt)}{item.reviewState === "recheck" ? c("recheck") : c("userRecord")}</p>}
            {!item.outstanding && <p>{c("resolved")}</p>}
          </li>)}</ul>
        </section>)}
      </DetailsDisclosure>
      <ActionSection>
        <CommercialButton onClick={save} disabled={!draft || !canReview}>{c("save")}</CommercialButton>
        {draft && <CommercialButton variant="secondary" disabled={saving} onClick={() => { if (!savingRef.current) { setDraft(null); setNotice(null); } }}>{c("loadSaved")}</CommercialButton>}
      </ActionSection>
    </div>
  </Section>;
}
