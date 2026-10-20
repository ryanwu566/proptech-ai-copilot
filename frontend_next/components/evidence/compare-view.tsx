"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Section, ActionSection } from "@/components/design-system/section";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { AsyncState } from "@/components/design-system/async-state";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { projectCaseEvidence } from "@/lib/workspace/case-evidence";
import { buildComparisonModel, parseCompareSelection, compareHref, type ComparisonStatus } from "@/lib/workspace/compare-report-model";
import { buildCompareDiff, compareFieldsHref, isVisibleInDifferences, parseFieldsView, type CompareDiffModel, type CompareFieldsView } from "@/lib/workspace/compare-diff";
import { compareCopy, type CompareCopyKey } from "@/lib/workspace/compare-copy";
import { EvidenceValue, EvidenceGaps, EvidenceSources, RepositoryNotice, storageBlocked, date } from "./evidence-view";
import { CompareDifferenceBrief } from "./compare-difference-brief";
import styles from "./evidence.module.css";
import { TradeoffPanel } from "@/components/preferences/tradeoff-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { navigationCopy } from "@/lib/navigation/copy";
import { CopilotLink } from "../workspace/copilot/copilot-link";
const blockedMessages: { [K in Exclude<ComparisonStatus, "ready">]: string } = { too_few: "請選擇 2–4 個已儲存案件以開始比較。", too_many: "最多選擇 4 個案件；請移除第五個案件。", duplicate: "選取案件識別重複；請移除重複選取。", invalid_selection: "案件識別格式無效；請重新選取本機案件。", case_not_found: "找不到選取案件，或儲存紀錄無效；不會替換成其他案件。", identity_requires_revalidation: "選取案件的身分需要重新確認；正式比較已停止，請回到物件工作區。" };
export function CompareView() {
  const { copyFrom } = useExperienceLocale();
  const repository = useMemo(createBrowserCaseRepository, []);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  const [feedback, setFeedback] = useState("");
  const search = useSearchParams();
  const query = search.get("cases");
  const [ids, setIds] = useState(() => parseCompareSelection(query));
  const [leftId, setLeftId] = useState<string | null>(null); const [rightId, setRightId] = useState<string | null>(null);
  const [chosenDomain, setDomain] = useState<string | null>(null);
  const c: CompareCopy = (key, values) => copyFrom(compareCopy, key, values);
  // Field display lives in the URL (`fields=all`), so Back/Forward restore it; a new case selection starts from differences only.
  const view = parseFieldsView(search.get("fields"));
  useEffect(() => { const load = () => setRead(repository.readDiagnostic()); load(); return repository.subscribe(load); }, [repository]);
  useEffect(() => { setIds(parseCompareSelection(query)); }, [query]);
  const allCases = read?.cases.map(projectCaseEvidence) ?? [];
  const model = buildComparisonModel(allCases, ids);
  const left = ids.includes(leftId ?? "") ? leftId! : ids[0];
  const right = ids.includes(rightId ?? "") && rightId !== left ? rightId! : ids.find((id) => id !== left);
  const pair = model.cases.filter((item) => item.caseId === left || item.caseId === right);
  const orderedPair = [pair.find((item) => item.caseId === left), pair.find((item) => item.caseId === right)].filter((item) => item !== undefined);
  const diff = buildCompareDiff(model.sections);
  const pairDiff = buildCompareDiff(model.sections, orderedPair.map((item) => model.cases.indexOf(item)));
  // Until the user picks an area, open the first one with differences for this pair (overview otherwise).
  const domain = chosenDomain ?? (view === "all" ? undefined : pairDiff.sections.find((section) => section.rows.some(isVisibleInDifferences))?.id) ?? "overview";
  const totalGaps = model.cases.reduce((sum, item) => sum + item.gaps.length, 0);
  function setView(next: CompareFieldsView) { window.history.pushState(null, "", compareFieldsHref(compareHref(ids), next)); }
  function toggle(id: string) {
    if (!ids.includes(id) && ids.length >= 4) { setFeedback("最多選擇 4 個案件；請先移除一個案件。"); return; }
    const next = ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
    setFeedback(""); setIds(next);
    // Local selection only: update the URL synchronously without a server navigation.
    window.history.replaceState(null, "", compareHref(next));
  }
  return <main id="main-content" className={styles.page}>
    <header><p className="text-meta">已儲存快照 · 本機案件</p><h1 className="text-page">案件證據比較</h1><p>比較各案件的保存證據、假設與未知項目；不提供物件排名、評分或購買建議。</p><Link className="ds-button ds-button--secondary" href="/cases">已儲存案件</Link></header>
    {!read ? <AsyncState kind="loading" title="正在讀取本機案件" /> : <>
      <RepositoryNotice read={read} />
      {!storageBlocked(read) && <>
        <Section title="選取案件" description="選取 2–4 案，保留你的選取順序。A／B／C／D 只表示位置。">
          <div className={styles.selection}>{allCases.map((item) => <label key={item.caseId}><input type="checkbox" aria-label={`選擇 ${item.title}`} checked={ids.includes(item.caseId)} onChange={() => toggle(item.caseId)} /><span><strong>{item.title}</strong><span>{item.displayAddress}</span><span>保存：{date(item.savedAt)}</span>{item.identity.state !== "confirmed" && <span>需先確認物件身分</span>}</span></label>)}</div>
          <p role="status" aria-live="polite">{feedback || `已選取 ${ids.length} 個案件`}</p>
          {read.status === "empty" && <div><p>{copyFrom(navigationCopy, "emptyHint")}</p><Link prefetch={false} className="commercial-text-action" href="/">{copyFrom(navigationCopy, "property")}</Link></div>}
        </Section>
        {model.status !== "ready" ? <Message variant={model.status === "too_few" ? "information" : "error"}>{blockedMessages[model.status]}{model.status === "identity_requires_revalidation" && <div>{ids.map((id) => <Link key={id} href={`/cases/${encodeURIComponent(id)}/overview`}>開啟選取案件工作區 </Link>)}</div>}</Message> : <>
          <div className={styles.selection}>{model.cases.map(item => <div key={item.caseId}><p>{item.title}</p><CopilotLink caseId={item.caseId} /></div>)}</div>
          <CompareDifferenceBrief cases={model.cases} />
          <p><a href="#compare-limitations">{c("limitsLink", { count: model.warnings.length })}</a></p>
          <FieldsToolbar view={view} diff={diff} onChange={setView} c={c} />
          <div className={styles.desktop} data-testid="compare-desktop" data-fields-view={view}><table className={styles.table}><caption className="sr-only">已儲存案件的分領域證據比較</caption>
            <thead><tr><th scope="col">證據欄位</th>{model.cases.map((item, index) => <th scope="col" key={item.caseId}><p>{"ABCD"[index]} · {item.title}</p><p>{item.displayAddress}</p><p className="text-meta">瀏覽器案件關聯已確認 · 保存 {date(item.savedAt)}</p><CommercialButton variant="secondary" aria-label={`移除 ${item.title}`} onClick={() => toggle(item.caseId)}>移除</CommercialButton></th>)}</tr></thead>
            {diff.sections.map((section) => <tbody key={section.id}><tr className={styles.domainRow}><th colSpan={model.cases.length + 1} scope="colgroup">{section.title}<p>{section.description}</p>{view !== "all" && !section.rows.some(isVisibleInDifferences) && <p>{c("domainNoneAll")}</p>}</th></tr>{section.rows.map((row) => <tr key={row.id} hidden={view !== "all" && !isVisibleInDifferences(row)} data-testid={`compare-row-${row.id}`} data-row-relation={row.relation}><th scope="row">{row.label}</th>{row.cells.map((cell, index) => <td key={model.cases[index].caseId}><EvidenceValue field={cell} density="compact" sourceSummary={c("sourceDetails")} /></td>)}</tr>)}</tbody>)}
          </table></div>
          <div className={styles.mobile} data-testid="compare-mobile" data-fields-view={view}>
            <ActionSection className={styles.pairControls}>
              <label>左側比較案件<select aria-label="左側比較案件" value={left} onChange={(event) => setLeftId(event.target.value)}>{model.cases.filter((item) => item.caseId !== right).map((item) => <option key={item.caseId} value={item.caseId}>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</option>)}</select></label>
              <label>右側比較案件<select aria-label="右側比較案件" value={right} onChange={(event) => setRightId(event.target.value)}>{model.cases.filter((item) => item.caseId !== left).map((item) => <option key={item.caseId} value={item.caseId}>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</option>)}</select></label>
              <label>比較領域<select aria-label="比較領域" value={domain} onChange={(event) => setDomain(event.target.value)}>{pairDiff.sections.map((section) => <option key={section.id} value={section.id}>{view === "all" ? section.title : c("domainOption", { title: section.title, count: section.rows.filter(isVisibleInDifferences).length })}</option>)}</select></label>
            </ActionSection>
            {orderedPair.map((item) => <div key={item.caseId} className={styles.mobileHeader}><strong>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</strong><p>{item.displayAddress}</p><p>瀏覽器關聯已確認 · 保存 {date(item.savedAt)}</p><CommercialButton variant="secondary" onClick={() => toggle(item.caseId)} aria-label={`移除 ${item.title}`}>移除</CommercialButton></div>)}
            {pairDiff.sections.filter((section) => section.id === domain).map((section) => <Section key={section.id} title={section.title} description={section.description}>
              {view !== "all" && !section.rows.some(isVisibleInDifferences) && <p>{c("domainNone")}</p>}
              {view !== "all" && <HiddenNotes rows={section.rows} c={c} />}
              {section.rows.map((row) => <article key={row.id} hidden={view !== "all" && !isVisibleInDifferences(row)} className={styles.mobileRow} data-testid={`mobile-row-${row.id}`} data-row-relation={row.relation}><h3 className="text-subsection">{row.label}</h3>{orderedPair.map((item, index) => <div key={item.caseId}><p className={styles.caseName}>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</p><EvidenceValue field={row.cells[index]} density="compact" sourceSummary={c("sourceDetails")} /></div>)}</article>)}
            </Section>)}
          </div>
          <TradeoffPanel cases={ids.map(id => read.cases.find(item => item.caseId === id)!)} />
          <div id="compare-limitations" data-testid="compare-limitations"><Section title={c("limitsTitle")} description={c("limitsDescription")}><div className={styles.limits}>
            <div data-testid="comparability-warnings"><Message variant="warning"><ul>{model.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></Message></div>
            <ul data-testid="compare-gap-counts">{model.cases.map((item, index) => <li key={item.caseId}>{c("gapsSummary", { title: `${"ABCD"[index]} · ${item.title}`, count: item.gaps.length })}</li>)}</ul>
            <DetailsDisclosure summary={c("gapsDisclosure", { count: totalGaps })} data-testid="compare-gaps"><EvidenceGaps cases={model.cases} /></DetailsDisclosure>
            <DetailsDisclosure summary={c("sourcesDisclosure")} data-testid="compare-sources"><EvidenceSources cases={model.cases} /></DetailsDisclosure>
          </div></Section></div>
          <nav className="case-workflow-handoff" data-testid="compare-report-handoff" aria-label={copyFrom(navigationCopy, "report")}>
            <div><strong>{copyFrom(navigationCopy, "next")}</strong><p>{copyFrom(navigationCopy, "reportHint")}</p></div>
            {model.cases.map((item) => <Link prefetch={false} className="ds-button ds-button--secondary" key={item.caseId} href={`/cases/${encodeURIComponent(item.caseId)}/report`}>{copyFrom(navigationCopy, "report")} · {item.title}</Link>)}
          </nav>
        </>}
      </>}
    </>}
  </main>;
}
type CompareCopy = (key: CompareCopyKey, values?: Record<string, string | number>) => string;
/** Collapsed rows are always summarized; unresolved rows are named so unknowns never disappear silently. */
function HiddenNotes({ rows, c }: { rows: CompareDiffModel["sections"][number]["rows"]; c: CompareCopy }) {
  const identical = rows.filter((row) => row.relation === "identical").length;
  const unresolved = rows.filter((row) => row.relation === "same_unresolved").map((row) => row.label);
  return <>
    {identical > 0 && <p className={styles.hiddenNote}>{c("hiddenIdentical", { count: identical })}</p>}
    {unresolved.length > 0 && <p className={styles.hiddenNote} data-testid="hidden-unresolved">{c("hiddenUnresolved", { count: unresolved.length, labels: unresolved.join(" · ") })}</p>}
  </>;
}
function FieldsToolbar({ view, diff, onChange, c }: { view: CompareFieldsView; diff: CompareDiffModel; onChange: (view: CompareFieldsView) => void; c: CompareCopy }) {
  // Counts cover every selected case; the mobile pair view shows its own per-area notes instead.
  return <div data-testid="compare-fields-toolbar">
    <div className={styles.fieldsToolbar} role="group" aria-label={c("fieldsLabel")}>
      <CommercialButton variant="secondary" aria-pressed={view === "all"} onClick={() => onChange(view === "all" ? "differences" : "all")}>{c("showAll")}</CommercialButton>
      <p className={styles.desktop}>{view === "all" ? c("summaryAll", { total: diff.counts.total }) : c("summaryDifferences", { visible: diff.counts.visible, total: diff.counts.total })}</p>
    </div>
    {view !== "all" && <div className={styles.desktop}><HiddenNotes rows={diff.sections.flatMap((section) => section.rows)} c={c} /></div>}
  </div>;
}
