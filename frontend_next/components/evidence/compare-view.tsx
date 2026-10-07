"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Section, ActionSection } from "@/components/design-system/section";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { AsyncState } from "@/components/design-system/async-state";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { projectCaseEvidence } from "@/lib/workspace/case-evidence";
import { buildComparisonModel, parseCompareSelection, compareHref, type ComparisonStatus } from "@/lib/workspace/compare-report-model";
import { EvidenceValue, EvidenceGaps, EvidenceSources, RepositoryNotice, storageBlocked, date } from "./evidence-view";
import styles from "./evidence.module.css";
const blockedMessages: { [K in Exclude<ComparisonStatus, "ready">]: string } = { too_few: "請選擇 2–4 個已儲存案件以開始比較。", too_many: "最多選擇 4 個案件；請移除第五個案件。", duplicate: "選取案件識別重複；請移除重複選取。", invalid_selection: "案件識別格式無效；請重新選取本機案件。", case_not_found: "找不到選取案件，或儲存紀錄無效；不會替換成其他案件。", identity_requires_revalidation: "選取案件的身分需要重新確認；正式比較已停止，請回到物件工作區。" };
export function CompareView() {
  const repository = useMemo(createBrowserCaseRepository, []);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  const [feedback, setFeedback] = useState("");
  const search = useSearchParams();
  const query = search.get("cases");
  const [ids, setIds] = useState(() => parseCompareSelection(query));
  const [leftId, setLeftId] = useState<string | null>(null); const [rightId, setRightId] = useState<string | null>(null);
  const [domain, setDomain] = useState("overview");
  useEffect(() => { const load = () => setRead(repository.readDiagnostic()); load(); return repository.subscribe(load); }, [repository]);
  useEffect(() => { setIds(parseCompareSelection(query)); }, [query]);
  const allCases = read?.cases.map(projectCaseEvidence) ?? [];
  const model = buildComparisonModel(allCases, ids);
  const left = ids.includes(leftId ?? "") ? leftId! : ids[0];
  const right = ids.includes(rightId ?? "") && rightId !== left ? rightId! : ids.find((id) => id !== left);
  const pair = model.cases.filter((item) => item.caseId === left || item.caseId === right);
  const orderedPair = [pair.find((item) => item.caseId === left), pair.find((item) => item.caseId === right)].filter((item) => item !== undefined);
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
          {read.status === "empty" && <p>尚無已儲存案件，請先回到工作區保存案件。</p>}
        </Section>
        {model.status !== "ready" ? <Message variant={model.status === "too_few" ? "information" : "error"}>{blockedMessages[model.status]}{model.status === "identity_requires_revalidation" && <div>{ids.map((id) => <Link key={id} href={`/cases/${encodeURIComponent(id)}/overview`}>開啟選取案件工作區 </Link>)}</div>}</Message> : <>
          <Section title="重要比較限制"><div data-testid="comparability-warnings"><Message variant="warning"><ul>{model.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></Message></div></Section>
          <div className={styles.desktop} data-testid="compare-desktop"><table className={styles.table}><caption className="sr-only">已儲存案件的分領域證據比較</caption>
            <thead><tr><th scope="col">證據欄位</th>{model.cases.map((item, index) => <th scope="col" key={item.caseId}><p>{"ABCD"[index]} · {item.title}</p><p>{item.displayAddress}</p><p className="text-meta">瀏覽器案件關聯已確認 · 保存 {date(item.savedAt)}</p><CommercialButton variant="secondary" aria-label={`移除 ${item.title}`} onClick={() => toggle(item.caseId)}>移除</CommercialButton></th>)}</tr></thead>
            {model.sections.map((section) => <tbody key={section.id}><tr className={styles.domainRow}><th colSpan={model.cases.length + 1} scope="colgroup">{section.title}<p>{section.description}</p></th></tr>{section.rows.map((row) => <tr key={row.id}><th scope="row">{row.label}</th>{row.cells.map((cell, index) => <td key={model.cases[index].caseId}><EvidenceValue field={cell} /></td>)}</tr>)}</tbody>)}
          </table></div>
          <div className={styles.mobile} data-testid="compare-mobile">
            <ActionSection className={styles.pairControls}>
              <label>左側比較案件<select aria-label="左側比較案件" value={left} onChange={(event) => setLeftId(event.target.value)}>{model.cases.filter((item) => item.caseId !== right).map((item) => <option key={item.caseId} value={item.caseId}>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</option>)}</select></label>
              <label>右側比較案件<select aria-label="右側比較案件" value={right} onChange={(event) => setRightId(event.target.value)}>{model.cases.filter((item) => item.caseId !== left).map((item) => <option key={item.caseId} value={item.caseId}>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</option>)}</select></label>
              <label>比較領域<select aria-label="比較領域" value={domain} onChange={(event) => setDomain(event.target.value)}>{model.sections.map((section) => <option key={section.id} value={section.id}>{section.title}</option>)}</select></label>
            </ActionSection>
            {orderedPair.map((item) => <div key={item.caseId} className={styles.mobileHeader}><strong>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</strong><p>{item.displayAddress}</p><p>瀏覽器關聯已確認 · 保存 {date(item.savedAt)}</p><CommercialButton variant="secondary" onClick={() => toggle(item.caseId)} aria-label={`移除 ${item.title}`}>移除</CommercialButton></div>)}
            {model.sections.filter((section) => section.id === domain).map((section) => <Section key={section.id} title={section.title} description={section.description}>{section.rows.map((row) => <article key={row.id} className={styles.mobileRow} data-testid={`mobile-row-${row.id}`}><h3 className="text-subsection">{row.label}</h3>{orderedPair.map((item) => <div key={item.caseId}><p className={styles.caseName}>{"ABCD"[ids.indexOf(item.caseId)]} · {item.title}</p><EvidenceValue field={row.cells[model.cases.indexOf(item)]} /></div>)}</article>)}</Section>)}
          </div>
          <Section title="未知與待查證缺口"><EvidenceGaps cases={model.cases} /></Section>
          <Section title="來源、日期與方法"><EvidenceSources cases={model.cases} /></Section>
        </>}
      </>}
    </>}
  </main>;
}
