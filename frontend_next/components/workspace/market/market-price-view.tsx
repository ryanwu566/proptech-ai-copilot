"use client";
import { ComparableExplanation } from "./comparable-explanation";

import { useEffect, useMemo, useRef, useState } from "react";
import { ValuationRenderErrorBoundary } from "@/components/valuation-result-boundary";
import { AsyncState } from "@/components/design-system/async-state";
import { CommercialButton } from "@/components/design-system/button";
import { DataTable, DataTableCell, DataTableHeader } from "@/components/design-system/data-table";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
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
import { api, type MarketResult, type ValuationResult, type ValuationTrendResult } from "@/lib/api";
import { readSavedCases, updateSavedCaseMarketEvidence, updateSavedCaseValuationEvidence } from "@/lib/case-storage";
import { getValuationDisplayState, getValuationTrendDisplayState } from "@/lib/valuation-result-state";
import { buildMarketPriceModel, type MarketPriceEvidenceStatus } from "@/lib/workspace/market-price-model";
import {
  buildMarketRefreshContext,
  buildValuationRefreshContext,
  canCommitMarketPriceResponse,
  classifyMarketRefresh,
  classifyValuationRefresh,
  type MarketRefreshContext,
  type ValuationRefreshContext,
} from "@/lib/workspace/market-price-refresh";

type RefreshFeedback = {
  kind: "loading" | "success" | "warning" | "error";
  title: string;
  detail: string;
  fingerprint: string;
};

type LiveEvidence<T> = { result: T; fingerprint: string };

const statusCopy: Record<MarketPriceEvidenceStatus, string> = {
  not_started: "尚未查詢此區段",
  available: "證據可供目前判讀",
  insufficient: "資料不足，無法判讀",
  limited: "已恢復有限摘要",
  unavailable: "目前無法取得證據",
  stale: "資料可能已過期",
};

function EvidenceStatus({ status }: { status: MarketPriceEvidenceStatus }) {
  const role = status === "available" ? "success" : status === "unavailable" ? "error" : status === "insufficient" || status === "limited" || status === "stale" ? "warning" : "neutral";
  return <StatusLabel semanticRole={role}>{statusCopy[status]}</StatusLabel>;
}

function analysisLevelCopy(level: string | null, fallbackApplied: boolean): string {
  if (level === "ROAD") return "路段";
  if (level === "DISTRICT") return fallbackApplied ? "行政區（已回退）" : "行政區";
  return formatMissing("not_provided");
}

export function MarketPriceView() {
  const workspace = useWorkspace();
  const saved = useMemo(
    () => readSavedCases().find((row) => row.id === workspace.caseId) ?? null,
    [workspace.caseId, workspace.updatedAt],
  );
  const marketContext = useMemo(
    () => saved ? buildMarketRefreshContext(workspace, saved) : null,
    [saved, workspace],
  );
  const valuationContext = useMemo(
    () => saved ? buildValuationRefreshContext(workspace, saved) : null,
    [saved, workspace],
  );
  const marketContextRef = useRef<MarketRefreshContext | null>(marketContext);
  const valuationContextRef = useRef<ValuationRefreshContext | null>(valuationContext);
  marketContextRef.current = marketContext;
  valuationContextRef.current = valuationContext;

  const marketRequestRef = useRef<{ id: number; controller: AbortController | null }>({ id: 0, controller: null });
  const valuationRequestRef = useRef(0);
  const [marketFeedback, setMarketFeedback] = useState<RefreshFeedback | null>(null);
  const [valuationFeedback, setValuationFeedback] = useState<RefreshFeedback | null>(null);
  const [liveMarket, setLiveMarket] = useState<LiveEvidence<MarketResult> | null>(null);
  const [liveValuation, setLiveValuation] = useState<LiveEvidence<ValuationResult> | null>(null);
  const [liveTrend, setLiveTrend] = useState<LiveEvidence<ValuationTrendResult> | null>(null);
  const [savedMarketFingerprint, setSavedMarketFingerprint] = useState<string | null>(
    () => workspace.marketPrice.market.result && marketContext ? marketContext.fingerprint : null,
  );
  const [savedValuationFingerprint, setSavedValuationFingerprint] = useState<string | null>(
    () => workspace.marketPrice.valuation.result && valuationContext ? valuationContext.fingerprint : null,
  );

  useEffect(() => () => {
    marketRequestRef.current.controller?.abort();
    valuationRequestRef.current += 1;
  }, []);

  const currentLiveMarket = liveMarket && liveMarket.fingerprint === marketContext?.fingerprint ? liveMarket.result : undefined;
  const currentLiveValuation = liveValuation && liveValuation.fingerprint === valuationContext?.fingerprint ? liveValuation.result : undefined;
  const currentLiveTrend = liveTrend && liveTrend.fingerprint === valuationContext?.fingerprint ? liveTrend.result : undefined;
  const marketContextStale = Boolean(
    workspace.marketPrice.market.result
    && savedMarketFingerprint
    && savedMarketFingerprint !== marketContext?.fingerprint,
  ) || Boolean(liveMarket && liveMarket.fingerprint !== marketContext?.fingerprint);
  const valuationContextStale = Boolean(
    workspace.marketPrice.valuation.result
    && savedValuationFingerprint
    && savedValuationFingerprint !== valuationContext?.fingerprint,
  ) || Boolean(liveValuation && liveValuation.fingerprint !== valuationContext?.fingerprint);
  const model = buildMarketPriceModel({
    identityConfirmed: workspace.identity.state === "confirmed",
    activePriceBasis: workspace.assumptions.activePriceBasis,
    activePriceWan: workspace.assumptions.activePriceWan,
    askingPriceWan: workspace.assumptions.askingPriceWan,
    market: currentLiveMarket ?? workspace.marketPrice.market.result ?? undefined,
    valuation: currentLiveValuation ?? workspace.marketPrice.valuation.result ?? undefined,
    trend: currentLiveTrend,
    stale: workspace.marketPrice.isStale,
    marketStale: marketContextStale,
    valuationStale: valuationContextStale,
    marketFresh: Boolean(currentLiveMarket),
    valuationFresh: Boolean(currentLiveValuation),
  });
  const market = model.market.result;
  const valuation = model.valuation.result;
  const comparables = model.valuation.comparables;
  const history = model.market.history;

  const marketFeedbackSuperseded = Boolean(
    marketFeedback && marketFeedback.fingerprint !== marketContext?.fingerprint,
  );
  const valuationFeedbackSuperseded = Boolean(
    valuationFeedback && valuationFeedback.fingerprint !== valuationContext?.fingerprint,
  );

  async function refreshMarket() {
    const responseContext = marketContext;
    if (!responseContext) return;
    marketRequestRef.current.controller?.abort();
    const controller = new AbortController();
    const requestId = marketRequestRef.current.id + 1;
    marketRequestRef.current = { id: requestId, controller };
    setMarketFeedback({
      kind: "loading",
      title: "正在更新市場資料",
      detail: "已儲存的市場證據會保留顯示，完成前不會改變任何價格基準。",
      fingerprint: responseContext.fingerprint,
    });

    try {
      const result = await api.marketInsight(
        responseContext.payload.county,
        responseContext.payload.district,
        responseContext.payload.road,
        undefined,
        controller.signal,
      );
      const current = marketContextRef.current;
      if (
        requestId !== marketRequestRef.current.id
        || !current
        || !canCommitMarketPriceResponse(current, responseContext)
      ) return;
      const outcome = classifyMarketRefresh(result);
      if (!outcome.shouldPersist) {
        setMarketFeedback({
          kind: "error",
          title: "市場資料目前無法更新",
          detail: "既有證據仍保留；這次回應沒有取代已儲存的市場摘要。",
          fingerprint: responseContext.fingerprint,
        });
        return;
      }
      if (!updateSavedCaseMarketEvidence(responseContext.caseId, result, responseContext.identity)) return;
      setLiveMarket({ result, fingerprint: responseContext.fingerprint });
      setSavedMarketFingerprint(responseContext.fingerprint);
      setMarketFeedback(marketRefreshFeedback(result, responseContext.fingerprint));
    } catch {
      if (controller.signal.aborted) return;
      const current = marketContextRef.current;
      if (
        requestId !== marketRequestRef.current.id
        || !current
        || !canCommitMarketPriceResponse(current, responseContext)
      ) return;
      setMarketFeedback({
        kind: "error",
        title: "市場資料更新失敗",
        detail: "已儲存的市場證據仍保留，請稍後再試。",
        fingerprint: responseContext.fingerprint,
      });
    }
  }

  async function refreshValuation() {
    const responseContext = valuationContext;
    if (!responseContext) return;
    const requestId = valuationRequestRef.current + 1;
    valuationRequestRef.current = requestId;
    setValuationFeedback({
      kind: "loading",
      title: "正在更新價格推估",
      detail: "推估與趨勢會使用同一組物件輸入；既有摘要會保留到新結果通過檢查。",
      fingerprint: responseContext.fingerprint,
    });

    const [valuationResponse, trendResponse] = await Promise.allSettled([
      api.valuation(responseContext.payload),
      api.valuationTrend(responseContext.trendPayload),
    ]);
    const current = valuationContextRef.current;
    if (
      requestId !== valuationRequestRef.current
      || !current
      || !canCommitMarketPriceResponse(current, responseContext)
    ) return;
    if (valuationResponse.status === "rejected") {
      setValuationFeedback({
        kind: "error",
        title: "價格推估更新失敗",
        detail: "已儲存的價格推估摘要仍保留，且沒有改變開價或目前使用中的價格。",
        fingerprint: responseContext.fingerprint,
      });
      return;
    }

    const result = valuationResponse.value;
    const outcome = classifyValuationRefresh(result);
    if (!outcome.shouldPersist) {
      const display = getValuationDisplayState(result);
      setValuationFeedback({
        kind: outcome.query === "failed" ? "error" : "warning",
        title: display.kind === "no_data" ? "價格推估證據不足" : "價格推估無法採用",
        detail: display.message || "這次結果未通過可採用檢查，因此不會取代已儲存的推估摘要。",
        fingerprint: responseContext.fingerprint,
      });
      return;
    }
    if (!updateSavedCaseValuationEvidence(responseContext.caseId, result, responseContext.identity)) return;

    let acceptedTrend: ValuationTrendResult | undefined;
    if (
      trendResponse.status === "fulfilled"
      && canCommitMarketPriceResponse(current, responseContext)
      && getValuationTrendDisplayState(trendResponse.value).actionable
    ) acceptedTrend = trendResponse.value;
    setLiveValuation({ result, fingerprint: responseContext.fingerprint });
    setLiveTrend(acceptedTrend ? { result: acceptedTrend, fingerprint: responseContext.fingerprint } : null);
    setSavedValuationFingerprint(responseContext.fingerprint);
    setValuationFeedback({
      kind: "success",
      title: "價格推估已更新",
      detail: acceptedTrend
        ? "推估已通過可靠性檢查；趨勢細節只保留於本次工作階段。"
        : "推估已通過可靠性檢查；趨勢資料不足或目前無法取得。",
      fingerprint: responseContext.fingerprint,
    });
  }

  return <div className="workspace-view" data-testid="market-price-workspace">
    <header className="space-y-2">
      <p className="text-meta text-[color:var(--text-muted)]">目前物件的價格證據</p>
      <h1 className="text-page">價格與市場</h1>
      <p className="text-body text-[color:var(--text-secondary)]">可取得的市場證據對這個物件的價格提供了什麼訊息？</p>
      <div className="flex flex-col gap-3 pt-3 sm:flex-row sm:flex-wrap" aria-label="市場與價格推估更新">
        <CommercialButton
          onClick={refreshMarket}
          loading={marketFeedback?.kind === "loading" && !marketFeedbackSuperseded}
          loadingLabel="更新市場資料中"
          disabled={!marketContext}
          data-testid="market-refresh-button"
        >更新市場資料</CommercialButton>
        <CommercialButton
          variant="secondary"
          onClick={refreshValuation}
          loading={valuationFeedback?.kind === "loading" && !valuationFeedbackSuperseded}
          loadingLabel="更新價格推估中"
          disabled={!valuationContext}
          data-testid="valuation-refresh-button"
        >更新價格推估</CommercialButton>
      </div>
    </header>

    {(!marketContext || !valuationContext) && <div data-testid="market-refresh-input-required">
      <AsyncState
        kind="input_required"
        title="請先確認目前物件與價格推估輸入"
        detail="更新只會使用這個已儲存案件中已確認的地址、座標、面積、屋齡、樓層與建物型態。"
      />
    </div>}

    <RefreshFeedbackPanel
      channel="market"
      feedback={marketFeedback}
      superseded={marketFeedbackSuperseded}
    />
    <RefreshFeedbackPanel
      channel="valuation"
      feedback={valuationFeedback}
      superseded={valuationFeedbackSuperseded}
    />

    {model.isStale && <div role="alert" className="ds-async-state ds-role-warning">
      <span className="ds-status__icon" aria-hidden="true">!</span>
      <div className="ds-async-state__body">
        <strong className="ds-async-state__title">物件或推估輸入已變更，既有證據需重新確認</strong>
        <p className="text-body">以下內容保留供核對，但已明確標示為過期，不能視為目前輸入的有效價格依據。</p>
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
      <div data-testid="market-primary-finding" className="border-l-4 border-[color:var(--action)] py-2 pl-4 text-body text-[color:var(--text-primary)]">
        {model.market.status === "stale" ? "目前物件需要重新確認，既有價格差異暫不作為結論。" : model.primaryFinding}
      </div>
    </Section>

    <Section title="市場範圍與近期變化" description="用同一個每坪單價口徑查看觀察範圍與最近期間，缺漏期間不補成零。">
      <div data-evidence-key="market" className="mb-4 flex flex-wrap items-center gap-3">
        <strong className="text-label">市場資料</strong>
        <EvidenceStatus status={model.market.status} />
      </div>
      <dl data-testid="market-scope-context" className="mb-4 grid gap-3 border-y border-[color:var(--border-subtle)] py-4 text-dense sm:grid-cols-3" aria-label="市場證據範圍">
        <div><dt className="font-semibold">有效範圍</dt><dd>{model.market.scopeLabel ?? formatMissing("not_provided")}</dd></div>
        <div><dt className="font-semibold">分析層級</dt><dd>{analysisLevelCopy(model.market.analysisLevel, model.market.fallbackApplied)}</dd></div>
        <div><dt className="font-semibold">有效樣本</dt><dd>{model.market.sampleCount ? `${model.market.sampleCount.toLocaleString("zh-TW")} 筆` : formatMissing("not_provided")}</dd></div>
      </dl>
      {model.overview.marketRange && <p className="mb-4 text-number font-semibold tabular-nums">觀察四分位範圍：{model.overview.marketRange}</p>}
      {history.length > 0 ? <DataTable caption="近期市場成交趨勢" regionLabel="近期市場成交趨勢">
        <thead><tr><DataTableHeader>成交期間</DataTableHeader><DataTableHeader numeric unit="萬元／坪">平均成交單價</DataTableHeader><DataTableHeader numeric unit="筆">成交筆數</DataTableHeader></tr></thead>
        <tbody>{history.map((row) => <tr key={row.period!}>
          <DataTableCell>{row.period}</DataTableCell>
          <DataTableCell numeric>{formatWanPerPing(row.average_unit_price).replace(" 萬元／坪", "")}</DataTableCell>
          <DataTableCell numeric>{row.transaction_count.toLocaleString("zh-TW")}</DataTableCell>
        </tr>)}</tbody>
      </DataTable> : <p className="text-body text-[color:var(--text-secondary)]">目前沒有足以呈現近期變化的連續期間資料。</p>}
      <dl className="mt-4 grid gap-3 border-t border-[color:var(--border-subtle)] pt-4 text-dense sm:grid-cols-3" aria-label="市場證據來源與期間">
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
        </SummaryStrip> : <p className="text-body text-[color:var(--text-secondary)]">目前尚未取得可安全判讀的價格推估；開價與市場成交證據仍分別保留。</p>}
        {model.valuation.trend && <dl data-testid="valuation-trend-summary" className="mt-4 grid gap-3 border-t border-[color:var(--border-subtle)] pt-4 text-dense sm:grid-cols-3">
          <div><dt className="font-semibold">趨勢期間</dt><dd>{model.valuation.trend.period_min ?? formatMissing("not_provided")}–{model.valuation.trend.period_max ?? formatMissing("not_provided")}</dd></div>
          <div><dt className="font-semibold">近期每坪中位數</dt><dd>{formatWanPerPing(model.valuation.trend.recent_median_unit_price)}</dd></div>
          <div><dt className="font-semibold">年化趨勢</dt><dd>{typeof model.valuation.trend.trend_annualized_rate === "number" ? `${model.valuation.trend.trend_annualized_rate.toFixed(1)}%` : formatMissing("unavailable")}</dd></div>
        </dl>}
      </ValuationRenderErrorBoundary>
      <ComparableExplanation value={valuation?.comparable_decision_trace} stale={model.valuation.status === "stale"} />
    </Section>

    <Section title="可比成交證據" description="逐筆成交是判斷物件條件差異的主要證據；只顯示目前案件實際保留的資料。">
      {comparables.length > 0 ? <ComparableTable rows={comparables} /> : <div role="status" className="border-y border-[color:var(--border-subtle)] py-5">
        <p className="text-body font-semibold text-[color:var(--text-primary)]">已儲存案件未保留逐筆可比成交</p>
        <p className="mt-1 text-body text-[color:var(--text-secondary)]">系統不會從摘要重建或猜測交易資料；進一步議價前請重新取得逐筆證據。</p>
      </div>}
    </Section>

    <Section title="證據限制與下一步" description="先處理會改變價格判讀的缺口，再用於議價或客戶討論。">
      <ol className="list-decimal space-y-2 pl-5 text-body">
        {model.market.status === "stale" && <li>重新確認目前物件，再更新市場證據。</li>}
        {model.valuation.status === "stale" && <li>重新確認目前價格推估輸入，再更新價格推估。</li>}
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

function marketRefreshFeedback(result: MarketResult, fingerprint: string): RefreshFeedback {
  const outcome = classifyMarketRefresh(result);
  if (outcome.evidence === "no_match") return {
    kind: "warning",
    title: "目前範圍沒有可用成交資料",
    detail: "沒有把缺漏資料當成零；本次查詢狀態已保存供後續確認。",
    fingerprint,
  };
  if (outcome.evidence === "no_coverage" || outcome.evidence === "unverified") return {
    kind: "warning",
    title: "目前範圍的市場覆蓋有限",
    detail: "系統保留來源與範圍限制，未把這次結果提升為完整市場證據。",
    fingerprint,
  };
  if (outcome.evidence === "limited" || outcome.evidence === "stale") return {
    kind: "warning",
    title: "市場資料已更新，但證據有限",
    detail: "請依畫面中的樣本、回退範圍與資料日期判讀。",
    fingerprint,
  };
  return {
    kind: "success",
    title: "市場資料已更新",
    detail: "已保存有限範圍的市場摘要；逐筆與供應商內部資料不會寫入案件儲存。",
    fingerprint,
  };
}

function RefreshFeedbackPanel({
  channel,
  feedback,
  superseded,
}: {
  channel: "market" | "valuation";
  feedback: RefreshFeedback | null;
  superseded: boolean;
}) {
  if (!feedback) return null;
  const testId = `${channel}-refresh-state`;
  if (superseded) return <div data-testid={testId}>
    <Message variant="warning" title="輸入已變更，先前更新已作廢">
      先前證據仍可供核對，但不是目前物件或輸入的有效結果；任何較晚回應都會被忽略。
    </Message>
  </div>;
  if (feedback.kind === "loading") return <div data-testid={testId}>
    <AsyncState kind="loading" title={feedback.title} detail={feedback.detail} />
  </div>;
  return <div data-testid={testId} aria-live="polite">
    <Message variant={feedback.kind} title={feedback.title}>{feedback.detail}</Message>
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
