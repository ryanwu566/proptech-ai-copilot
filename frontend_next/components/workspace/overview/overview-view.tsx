"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
import { ActionSection, Section } from "@/components/design-system/section";
import { MetricItem, MetricRow, SummaryStrip } from "@/components/design-system/summary-strip";
import { StatusLabel } from "@/components/design-system/status-label";
import { formatDistance, formatDuration, formatExactDate, formatMonthlyTwd } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import { buildWorkspaceOverview, type OverviewItem, type WorkspaceOverviewModel } from "@/lib/workspace/overview-model";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { OverviewSection } from "./overview-section";
import styles from "./overview-view.module.css";

const freshnessLabels: Record<string, string> = {
  current: "本次工作階段證據",
  saved_snapshot: "已儲存的摘要快照",
  partial: "部分證據已保存，仍有項目待確認",
  stale: "資料可能已過期",
  unavailable: "目前無法取得證據",
  not_started: "尚未查詢",
};

const priceBasisLabels = { asking: "開價", estimate: "成交資料推估", manual: "比較基準價格" } as const;
const routeModeLabels: Record<string, string> = { driving: "開車", transit: "大眾運輸", walking: "步行", bicycling: "自行車" };

export function OverviewView() {
  const workspace = useWorkspace();
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const overview = buildWorkspaceOverview(workspace);
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const [saveStatus, setSaveStatus] = useState("這份總覽顯示已儲存的案件快照；保存不代表分析已完成。");

  function saveSnapshot() {
    const result = repository.saveSnapshot(workspace);
    setSaveStatus(result.status === "saved"
      ? "已保存目前已知狀態；未知、無法取得與尚未完成的項目仍保持原狀。"
      : result.message);
  }

  return <div className={styles.page} data-testid="commercial-overview-workspace">
    <header className="workspace-view__heading">
      <p className="text-meta">案件版本 {workspace.revision} · 瀏覽器本機快照</p>
      <h1 className="text-page">物件總覽</h1>
      <p className="text-body">目前掌握什麼、哪些仍未知，以及下一步該查證什麼。總覽不評分、不排名，也不提供購買建議。</p>
    </header>

    <SummaryStrip label="目前案件狀態">
      <MetricItem label="物件脈絡" value={<StatusLabel semanticRole={identity.role}>{identity.label["zh-TW"]}</StatusLabel>} note="瀏覽器案件關聯，不是地籍或法律身分" />
      <MetricItem label="案件快照" value="已儲存" note={`保存於 ${formatExactDate(overview.snapshot.savedAt)}`} />
      <MetricItem label="看屋前準備" value={<StatusLabel semanticRole={overview.readiness.role}>{overview.readiness.label["zh-TW"]}</StatusLabel>} note={`${overview.unresolvedCount} 項待確認或限制`} />
    </SummaryStrip>

    <Section title="決策摘要" description="只綜合目前案件版本中的有界證據；未查詢、無法取得與過期各自保留。">
      <div className={styles.decisionGrid}>
        <DecisionGroup title="已掌握" items={overview.known} empty="目前沒有可在證據邊界內綜合的已知項目。" />
        <DecisionGroup title="尚未確認" items={overview.unknown} empty="目前沒有額外尚未確認項目。" />
        <DecisionGroup title="需要特別留意" items={[...overview.blockers, ...overview.attention]} empty="目前沒有額外需優先留意的狀態；仍應依證據限制查證。" />
        <DecisionGroup title="下一步" items={overview.actions} empty="目前沒有系統指定的下一步。" links />
      </div>
    </Section>

    <MarketSummary model={overview} />
    <LocationSummary model={overview} />
    <RiskSummary model={overview} />
    <FinanceSummary model={overview} />

    <Section title="保存、鮮度與來源" description="保存只代表保留目前已知狀態，不代表所有分析已完成。">
      <div className={styles.savePanel}>
        <Message variant="information" title="已儲存的案件快照，不是即時重新查詢">
          開啟或重新開啟總覽不會自動執行市場、估價、路線、風險、衛星、稅務、貸款或持有成本分析。
        </Message>
        <ActionSection>
          <CommercialButton size="touch" onClick={saveSnapshot}>保存目前案件快照</CommercialButton>
          <Link className="ds-button ds-button--secondary" href="/cases">返回已儲存案件</Link>
        </ActionSection>
        <p className="text-dense" data-testid="overview-save-status" aria-live="polite">{saveStatus}</p>
        <DetailsDisclosure summary="查看快照與證據鮮度">
          <dl className={styles.provenance}>
            <div><dt>案件保存時間</dt><dd>{formatExactDate(overview.snapshot.savedAt)}</dd></div>
            <div><dt>市場／估價</dt><dd>{freshnessLabels[overview.domains.market.freshness]}</dd></div>
            <div><dt>區位／通勤</dt><dd>{freshnessLabels[overview.domains.location.freshness]}</dd></div>
            <div><dt>風險／環境</dt><dd>{freshnessLabels[overview.domains.risk.freshness]}</dd></div>
            <div><dt>資金／成本</dt><dd>{freshnessLabels[overview.domains.finance.freshness]}</dd></div>
            <div><dt>身分邊界</dt><dd>瀏覽器案件關聯錨點只用於連結這次案件，不代表地號、建物、所有權、界址、權利或分區確認。</dd></div>
          </dl>
        </DetailsDisclosure>
      </div>
    </Section>

    <Section title="既有案件規劃工具" description="手動筆記、看屋與出價規劃仍保留在既有工作台。">
      <Link className="ds-button ds-button--secondary ds-button--compact" href={`/cases/${encodeURIComponent(workspace.caseId)}/planning`}>開啟既有案件規劃工具</Link>
    </Section>
  </div>;
}

function DecisionGroup({ title, items, empty, links = false }: { title: string; items: OverviewItem[]; empty: string; links?: boolean }) {
  return <section className={styles.decisionGroup}>
    <h3 className="text-subsection">{title}</h3>
    {items.length ? <ul className={styles.list}>{items.map((entry) => <li key={entry.id}>
      <strong>{entry.label}</strong><p className="text-dense">{entry.reason}</p>
      {links && <a href={entry.href}>前往{sectionLabel(entry.section)}</a>}
    </li>)}</ul> : <p className="text-dense">{empty}</p>}
  </section>;
}

function MarketSummary({ model }: { model: WorkspaceOverviewModel }) {
  const market = model.domains.market;
  return <OverviewSection title="價格與市場" description="開價、採用中的價格基準、市場證據與價格推估維持不同概念。" href={market.href} linkLabel="查看價格與市場" testId="overview-market-summary">
    <div className={styles.metricRows}>
      <MetricRow label="開價" value={market.askingPrice?.formatted ?? "未提供"} />
      <MetricRow label={`目前採用價格（${market.activePrice.label}）`} value={market.activePrice.formatted} />
      <MetricRow label="市場成交中位數" value={market.marketMedianUnit?.formatted ?? "尚未取得"} />
      <MetricRow label="價格推估區間" value={market.estimateRange ?? (market.valuationStatus === "unavailable" ? "目前無法取得價格推估" : "尚未取得")} />
    </div>
    <StatusLabel semanticRole={market.freshness === "stale" || market.freshness === "unavailable" || market.freshness === "partial" ? "warning" : "information"}>{freshnessLabels[market.freshness]}</StatusLabel>
  </OverviewSection>;
}

function LocationSummary({ model }: { model: WorkspaceOverviewModel }) {
  const location = model.domains.location;
  return <OverviewSection title="區位與通勤" description="保存的 Google 路線與次要大眾運輸證據各自呈現，互不覆蓋。" href={location.href} linkLabel="查看區位與通勤" testId="overview-location-summary">
    {location.route ? <div className={styles.routeSummary}>
      <strong>已保存前往{location.route.destination}的路線</strong>
      <p>{formatDuration(location.route.durationMinutes)} · {formatDistance(location.route.distanceM)} · {routeModeLabels[location.route.mode] ?? "其他方式"}</p>
    </div> : <p className="text-body">尚未保存可用的目的地路線。</p>}
    {location.secondaryTransitStatus === "unavailable" && <Message variant="warning">次要大眾運輸證據目前無法取得；已保存的 Google 路線仍可使用。</Message>}
    <StatusLabel semanticRole={location.freshness === "stale" ? "warning" : "information"}>{freshnessLabels[location.freshness]}</StatusLabel>
  </OverviewSection>;
}

function RiskSummary({ model }: { model: WorkspaceOverviewModel }) {
  const risk = model.domains.risk;
  return <OverviewSection title="風險與環境" description="逐項保存符合、未命中與未知狀態；沒有任何整體安全分數。" href={risk.href} linkLabel="查看風險與環境" testId="overview-risk-summary">
    {risk.materialMatchedEvidence.map((row) => <Message key={row.key} variant="warning" title={row.label}>{row.result}</Message>)}
    {risk.noMatchEvidence.map((row) => <Message key={row.key} title={`${row.label}：保存摘要未命中`}>{row.result} 未命中不代表安全，仍需核對來源範圍與現場。</Message>)}
    {risk.unknownOrUnavailableEvidence.map((row) => <Message key={row.key} variant="warning" title={`${row.label}仍無法判定`}>{row.result}</Message>)}
    {!risk.materialMatchedEvidence.length && !risk.noMatchEvidence.length && !risk.unknownOrUnavailableEvidence.length && <p className="text-body">尚未保存風險與環境證據。</p>}
    <StatusLabel semanticRole={risk.freshness === "stale" || risk.freshness === "unavailable" ? "warning" : "information"}>{freshnessLabels[risk.freshness]}</StatusLabel>
  </OverviewSection>;
}

function FinanceSummary({ model }: { model: WorkspaceOverviewModel }) {
  const finance = model.domains.finance;
  return <OverviewSection title="資金與持有成本" description="計算狀態、已知成本與負擔能力分開呈現；缺少收入不會變成零。" href={finance.href} linkLabel="查看資金與持有成本" testId="overview-finance-summary">
    <div className={styles.metricRows}>
      <MetricRow label="採用價格基準" value={priceBasisLabels[finance.activePriceBasis]} />
      <MetricRow label="每月房貸試算" value={finance.freshness === "stale" ? "先前快照已過期" : formatMonthlyTwd(finance.monthlyPaymentTwd)} />
      <MetricRow label="已知每月住房成本" value={finance.freshness === "stale" ? "先前快照已過期" : formatMonthlyTwd(finance.knownRecurringMonthlyTwd)} />
      <MetricRow label="負擔能力" value={finance.affordabilityStatus === "stale" ? "先前評估已過期" : finance.affordabilityStatus === "assessed" ? "已依收入評估" : "尚未評估（未提供月收入）"} />
    </div>
    {finance.freshness === "stale" && <Message variant="warning">先前資金試算屬於不同物件狀態，不作為目前數值；重新確認物件後再檢視或計算。</Message>}
    {finance.freshness !== "stale" && finance.calculationStatus === "succeeded" && finance.affordabilityStatus === "unassessed" && <Message variant="warning">試算完成，但負擔能力尚未評估；兩者維持不同狀態。</Message>}
    {finance.missingCosts.length > 0 && <ul className={styles.compactList}>{finance.missingCosts.map((cost) => <li key={cost}>{cost}</li>)}</ul>}
    <StatusLabel semanticRole={finance.freshness === "stale" ? "warning" : "information"}>{freshnessLabels[finance.freshness]}</StatusLabel>
  </OverviewSection>;
}

function sectionLabel(section: OverviewItem["section"]): string {
  return { overview: "物件確認", market: "價格與市場", location: "區位與通勤", risk: "風險與環境", finance: "資金與持有成本" }[section];
}
