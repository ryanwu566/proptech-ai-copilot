"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AsyncState } from "@/components/design-system/async-state";
import { Panel, Section } from "@/components/design-system/section";
import { StatusLabel } from "@/components/design-system/status-label";
import { formatExactDate, formatWan } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { RepositoryNotice, storageBlocked } from "@/components/evidence/evidence-view";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { buildWorkspaceOverview } from "@/lib/workspace/overview-model";
import styles from "./saved-cases-entry.module.css";

export function SavedCasesEntry() {
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const [cases, setCases] = useState<PropertyCaseWorkspace[] | null>(null);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  useEffect(() => {
    const load = () => { const next = repository.readDiagnostic(); setRead(next); setCases(next.cases); };
    load();
    return repository.subscribe(load);
  }, [repository]);

  return <main className={styles.page} id="main-content">
    <header className={styles.heading}>
      <p className="text-meta">瀏覽器本機案件</p>
      <h1 className="text-page">已儲存案件</h1>
      <p className="text-body">從這個瀏覽器恢復物件脈絡與符合保存邊界的摘要。</p>
      <Link className="ds-button ds-button--secondary" href="/compare">比較案件</Link>
    </header>
    {read && <RepositoryNotice read={read} />}
    <Section title="最近案件">
      {cases === null
        ? <AsyncState kind="loading" title="正在讀取已儲存案件" />
        : read && storageBlocked(read) ? null : cases.length === 0 && read?.issues.length ? <p>儲存紀錄需要修復，目前無可開啟的有效案件。</p> : cases.length === 0
          ? <AsyncState kind="not_started" title="尚無已儲存案件" detail="先從首頁完成物件選擇並儲存案件。" action={<Link className="ds-button ds-button--primary" href="/">回到首頁</Link>} />
          : <div className={styles.grid}>{cases.map((workspace) => <SavedCaseRow key={workspace.caseId} workspace={workspace} />)}</div>}
    </Section>
  </main>;
}

function SavedCaseRow({ workspace }: { workspace: PropertyCaseWorkspace }) {
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const overview = buildWorkspaceOverview(workspace);
  return <article aria-label={workspace.title} className={styles.caseArticle}><Panel>
    <div className={styles.rowHeading}>
      <div><h2 className="text-subsection">{workspace.title}</h2><p className="text-dense">{workspace.displayAddress}</p></div>
      <StatusLabel semanticRole={identity.role}>{identity.label["zh-TW"]}</StatusLabel>
    </div>
    <p className="text-meta">{workspace.assumptions.activePriceWan ? formatWan(workspace.assumptions.activePriceWan) : "價格未提供"} · 已儲存快照 {formatExactDate(workspace.updatedAt)}</p>
    <p className="text-dense">{overview.unresolvedCount > 0 ? `${overview.unresolvedCount} 項待確認或限制` : "目前沒有額外待確認摘要"}</p>
    <Link className="ds-button ds-button--primary" href={`/cases/${encodeURIComponent(workspace.caseId)}/overview`}>開啟{workspace.title}</Link>
    <Link className="ds-button ds-button--secondary" href={`/cases/${encodeURIComponent(workspace.caseId)}/report`}>產生報告</Link>
  </Panel></article>;
}
