"use client";

import { ValuationRenderErrorBoundary } from "@/components/valuation-result-boundary";
import { DataTable, DataTableCell, DataTableHeader } from "@/components/design-system/data-table";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Section } from "@/components/design-system/section";
import { StatusLabel } from "@/components/design-system/status-label";
import { MetricItem, SummaryStrip } from "@/components/design-system/summary-strip";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import {
  formatAreaPing,
  formatDistance,
  formatMissing,
  formatValuationConfidence,
  formatWan,
  formatWanPerPing,
} from "@/lib/commercial/formatters";
import type { MarketPriceEvidenceStatus } from "@/lib/workspace/market-price-model";

const statusCopy: Record<MarketPriceEvidenceStatus, string> = {
  not_started: "尚未查詢此區段",
  insufficient: "資料不足，無法判讀",
  limited: "已恢復有限摘要",
  unavailable: "目前無法取得證據",
  stale: "資料可能已過期",
};

function EvidenceStatus({ status }: { status: MarketPriceEvidenceStatus }) {
  const role = status === "unavailable" ? "error" : status === "insufficient" || status === "limited" || status === "stale" ? "warning" : "neutral";
  return <StatusLabel semanticRole={role}>{statusCopy[status]}</StatusLabel>;
}

function analysisLevelCopy(level: string | null, fallbackApplied: boolean): string {
  if (level === "ROAD") return "路段";
  if (level === "DISTRICT") return fallbackApplied ? "行政區（已回退）" : "行政區";
  return formatMissing("not_provided");
}

export function MarketPriceView() {
  const workspace = useWorkspace();
  const model = workspace.marketPrice;
  const market = model.market.result;
  const valuation = model.valuation.result;
  const comparables = model.valuation.comparables;
  const history = model.market.history;

  return <div className="min-w-0 space-y-8" data-testid="market-price-workspace">
    <header className="space-y-2">
      <p className="text-meta text-[color:var(--ds-text-muted)]">目前物件的價格證據</p>
      <h1 className="text-page">價格與市場</h1>
      <p className="text-body text-[color:var(--ds-text-secondary)]">可取得的市場證據對這個物件的價格提供了什麼訊息？</p>
    </header>

    {model.isStale && <div role="alert" className="ds-async-state ds-role-warning">
      <span className="ds-status__icon" aria-hidden="true">!</span>
      <div className="ds-async-state__body">
        <strong className="ds-async-state__title">物件資料已變更，價格證據需重新確認</strong>
        <p className="text-body">以下內容保留供核對，但不能視為目前物件的有效價格依據。</p>
      </div>
    </div>}

    <Section title="價格基準" description="開價、使用中的比較基準、成交資料推估與市場成交統計各自代表不同證據。">
      <div data-testid="market-price-context"><SummaryStrip label="價格基準">
        <MetricItem label={model.priceContext.askingPrice?.label ?? "開價"} value={model.priceContext.askingPrice?.formatted ?? formatMissing("not_provided")} primary />
        <MetricItem label={`目前使用：${model.priceContext.activePrice.label}`} value={model.priceContext.activePrice.formatted} note="供後續資金情境使用，不代表成交價" />
        <MetricItem label={model.priceContext.estimateRange?.label ?? "成交資料推估區間"} value={model.priceContext.estimateRange?.formatted ?? formatMissing("not_estimated")} />
        <MetricItem label="市場成交總價中位數" value={model.priceContext.marketMedianTotal?.formatted ?? formatMissing("unavailable")} />
        <MetricItem label="市場成交中位數" value={model.priceContext.marketMedianUnit?.formatted ?? formatMissing("unavailable")} />
      </SummaryStrip></div>
    </Section>

    <Section title="主要市場發現" description="以目前已儲存的成交證據進行初步比較，不構成正式鑑價或交易建議。">
      <div data-testid="market-primary-finding" className="border-l-4 border-[color:var(--ds-action)] py-2 pl-4 text-body text-[color:var(--ds-text-primary)]">
        {model.isStale ? "目前物件需要重新確認，既有價格差異暫不作為結論。" : model.primaryFinding}
      </div>
    </Section>

    <Section title="可比成交證據" description="逐筆成交是判斷物件條件差異的主要證據；只顯示目前案件實際保留的資料。">
      <div data-evidence-key="market" className="mb-4 flex flex-wrap items-center gap-3">
        <strong className="text-label">市場資料</strong>
        <EvidenceStatus status={model.market.status} />
      </div>
      <dl data-testid="market-scope-context" className="mb-4 grid gap-3 border-y border-[color:var(--ds-border-subtle)] py-4 text-dense sm:grid-cols-3" aria-label="市場證據範圍">
        <div><dt className="font-semibold">有效範圍</dt><dd>{model.market.scopeLabel ?? formatMissing("not_provided")}</dd></div>
        <div><dt className="font-semibold">分析層級</dt><dd>{analysisLevelCopy(model.market.analysisLevel, model.market.fallbackApplied)}</dd></div>
        <div><dt className="font-semibold">有效樣本</dt><dd>{model.market.sampleCount ? `${model.market.sampleCount.toLocaleString("zh-TW")} 筆` : formatMissing("not_provided")}</dd></div>
      </dl>
      {comparables.length > 0 ? <ComparableTable rows={comparables} /> : <div role="status" className="border-y border-[color:var(--ds-border-subtle)] py-5">
        <p className="text-body font-semibold text-[color:var(--ds-text-primary)]">已儲存案件未保留逐筆可比成交</p>
        <p className="mt-1 text-body text-[color:var(--ds-text-secondary)]">系統不會從摘要重建或猜測交易資料；進一步議價前請重新取得逐筆證據。</p>
      </div>}
    </Section>

    <Section title="市場範圍與近期變化" description="用同一個每坪單價口徑查看觀察範圍與最近期間，缺漏期間不補成零。">
      {model.overview.marketRange && <p className="mb-4 text-number font-semibold tabular-nums">觀察四分位範圍：{model.overview.marketRange}</p>}
      {history.length > 0 ? <DataTable caption="近期市場成交趨勢" regionLabel="近期市場成交趨勢">
        <thead><tr><DataTableHeader>成交期間</DataTableHeader><DataTableHeader numeric unit="萬元／坪">平均成交單價</DataTableHeader><DataTableHeader numeric unit="筆">成交筆數</DataTableHeader></tr></thead>
        <tbody>{history.map((row) => <tr key={row.period!}>
          <DataTableCell>{row.period}</DataTableCell>
          <DataTableCell numeric>{formatWanPerPing(row.average_unit_price).replace(" 萬元／坪", "")}</DataTableCell>
          <DataTableCell numeric>{row.transaction_count.toLocaleString("zh-TW")}</DataTableCell>
        </tr>)}</tbody>
      </DataTable> : <p className="text-body text-[color:var(--ds-text-secondary)]">目前沒有足以呈現近期變化的連續期間資料。</p>}
      <dl className="mt-4 grid gap-3 border-t border-[color:var(--ds-border-subtle)] pt-4 text-dense sm:grid-cols-3" aria-label="市場證據來源與期間">
        <div><dt className="font-semibold">資料來源</dt><dd>{model.source.sourceName ?? formatMissing("unavailable")}</dd></div>
        <div><dt className="font-semibold">有效期間</dt><dd>{model.source.effectivePeriod ?? formatMissing("not_provided")}</dd></div>
        <div><dt className="font-semibold">資料更新</dt><dd>{model.source.updatedAt ?? formatMissing("not_provided")}</dd></div>
      </dl>
    </Section>

    <Section title="價格推估證據" description="成交資料推估與市場統計分開呈現；只有通過可靠性檢查的數值才會顯示。">
      <div data-evidence-key="valuation" className="mb-4 flex flex-wrap items-center gap-3">
        <strong className="text-label">價格推估</strong>
        <EvidenceStatus status={model.valuation.status} />
      </div>
      <ValuationRenderErrorBoundary message="價格推估內容目前無法安全顯示，其他市場證據仍可使用。">
        {model.valuation.estimate && model.priceContext.estimateRange ? <SummaryStrip label="價格推估摘要">
          <MetricItem label="成交資料推估區間" value={model.priceContext.estimateRange.formatted} primary />
          <MetricItem label="推估中點" value={model.valuation.estimate.formatted} />
          <MetricItem label="價格推估可信度" value={formatValuationConfidence(valuation?.confidence)} note={valuation?.confidence_reason} />
          <MetricItem label="採用樣本" value={`${valuation?.valuation_explanation.sample_count.toLocaleString("zh-TW")} 筆`} note={model.valuation.comparablesAvailable ? "逐筆證據可檢視" : "案件僅保留驗證後摘要"} />
        </SummaryStrip> : <p className="text-body text-[color:var(--ds-text-secondary)]">目前尚未取得可安全判讀的價格推估；開價與市場成交證據仍分別保留。</p>}
      </ValuationRenderErrorBoundary>
    </Section>

    <Section title="證據限制與下一步" description="先處理會改變價格判讀的缺口，再用於議價或客戶討論。">
      <ol className="list-decimal space-y-2 pl-5 text-body">
        {model.isStale && <li>重新確認目前物件，再更新價格與市場證據。</li>}
        {!model.valuation.comparablesAvailable && <li>重新取得逐筆可比成交，核對面積、屋齡、樓層與建物型態。</li>}
        <li>確認開價來源、物件現況及未反映在成交資料中的個別條件。</li>
      </ol>
    </Section>

    <DetailsDisclosure summary="資料來源、期間與方法">
      {market?.methodology && <p className="mt-4 text-body">{market.methodology}</p>}
      {market?.caveat && <p className="mt-2 text-body">限制：{market.caveat}</p>}
      <p className="mt-2 text-body">{market?.disclaimer ?? valuation?.disclaimer ?? "成交與推估資料僅供初步判讀，不取代正式鑑價或專業查核。"}</p>
    </DetailsDisclosure>
  </div>;
}

function ComparableTable({ rows }: { rows: NonNullable<ReturnType<typeof useWorkspace>["marketPrice"]["valuation"]["result"]>["comparables"] }) {
  return <DataTable caption="逐筆可比成交" regionLabel="逐筆可比成交">
    <thead><tr>
      <DataTableHeader>成交期間</DataTableHeader><DataTableHeader>位置</DataTableHeader><DataTableHeader>建物型態</DataTableHeader>
      <DataTableHeader numeric unit="坪">面積</DataTableHeader><DataTableHeader numeric unit="萬元">總價</DataTableHeader>
      <DataTableHeader numeric unit="萬元／坪">單價</DataTableHeader><DataTableHeader>條件關係</DataTableHeader>
    </tr></thead>
    <tbody>{rows.map((row, index) => <tr key={`${row.transaction_period}-${row.road}-${index}`}>
      <DataTableCell>{row.transaction_period}</DataTableCell><DataTableCell>{row.road}</DataTableCell><DataTableCell>{row.building_type}</DataTableCell>
      <DataTableCell numeric>{formatAreaPing(row.area_ping).replace(" 坪", "")}</DataTableCell>
      <DataTableCell numeric>{formatWan(row.total_price).replace(" 萬元", "")}</DataTableCell>
      <DataTableCell numeric>{formatWanPerPing(row.unit_price_per_ping).replace(" 萬元／坪", "")}</DataTableCell>
      <DataTableCell>{row.note}{row.distance_m !== null ? `；距離 ${formatDistance(row.distance_m)}` : ""}</DataTableCell>
    </tr>)}</tbody>
  </DataTable>;
}
