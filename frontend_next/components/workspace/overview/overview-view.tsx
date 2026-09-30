"use client";

import Link from "next/link";
import { Message } from "@/components/design-system/message";
import { MetricItem, SummaryStrip } from "@/components/design-system/summary-strip";
import { Panel, Section } from "@/components/design-system/section";
import { StatusLabel } from "@/components/design-system/status-label";
import { resolveCommercialState } from "@/lib/commercial/state";
import { buildWorkspaceOverview } from "@/lib/workspace/overview-model";
import { useWorkspace } from "@/components/workspace/workspace-provider";

export function OverviewView() {
  const workspace = useWorkspace();
  const overview = buildWorkspaceOverview(workspace);
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const evidenceReady = (overview.evidenceCounts.usable ?? 0) + (overview.evidenceCounts.limited ?? 0);

  return <div className="workspace-view">
    <header className="workspace-view__heading">
      <p className="text-meta">目前案件</p>
      <h1 className="text-page">物件總覽</h1>
      <p className="text-body">掌握目前可安全使用的資訊、待確認事項與下一步，不以分數或推薦取代判讀。</p>
    </header>

    <SummaryStrip label="目前案件狀態">
      <MetricItem label="物件身分" value={<StatusLabel semanticRole={identity.role}>{identity.label["zh-TW"]}</StatusLabel>} />
      <MetricItem label="已恢復的證據區段" value={evidenceReady} unit="／6" note="舊案件摘要僅標示為有限證據" />
      <MetricItem label="看屋前準備" value={<StatusLabel semanticRole={overview.readiness.role}>{overview.readiness.label["zh-TW"]}</StatusLabel>} />
    </SummaryStrip>

    <Section title="主要發現" description="只呈現可追溯到目前案件版本的證據。">
      {overview.findings.length === 0
        ? <Message variant="inline" title="目前沒有可安全綜合的重大發現">完成需要的區段分析後，已確認的發現會出現在這裡。</Message>
        : <OverviewList items={overview.findings} />}
    </Section>

    <Section title="待確認事項" description="未查詢不代表沒有問題，也不會以零或安全狀態呈現。">
      <OverviewList items={overview.unknowns} />
    </Section>

    {overview.blockers.length > 0 && <Section title="需先處理">
      <Message variant="warning" title={overview.blockers[0].label}>{overview.blockers[0].reason}</Message>
    </Section>}

    <Section title="下一步" description="每個動作只前往一個工作區段。">
      <div className="workspace-action-grid">
        {overview.actions.map((item) => <Panel key={item.id}>
          <h2 className="text-subsection">{item.label}</h2>
          <p className="text-dense">{item.reason}</p>
          <a className="ds-button ds-button--secondary ds-button--compact" href={item.href}>前往{item.label.replace("確認", "")}</a>
        </Panel>)}
      </div>
      <Panel>
        <h2 className="text-subsection">既有案件規劃工具</h2>
        <p className="text-dense">手動筆記、財務情境、看屋與出價規劃、時間軸及列印仍保留在原有工具。</p>
        <Link className="ds-button ds-button--secondary ds-button--compact" href={`/cases/${encodeURIComponent(workspace.caseId)}/planning`}>開啟既有案件規劃工具</Link>
      </Panel>
    </Section>

    <Section title="證據準備摘要">
      <dl className="workspace-evidence-summary text-dense">
        <div><dt>有限證據</dt><dd>{overview.evidenceCounts.limited ?? 0}</dd></div>
        <div><dt>需重新確認</dt><dd>{overview.evidenceCounts.stale ?? 0}</dd></div>
        <div><dt>尚未查詢</dt><dd>{overview.evidenceCounts.not_started ?? 0}</dd></div>
      </dl>
    </Section>
  </div>;
}

function OverviewList({ items }: { items: Array<{ id: string; label: string; reason: string; href: string }> }) {
  return <ul className="workspace-overview-list">
    {items.map((item) => <li key={item.id}>
      <div><strong>{item.label}</strong><p className="text-dense">{item.reason}</p></div>
      <a href={item.href}>查看區段</a>
    </li>)}
  </ul>;
}
