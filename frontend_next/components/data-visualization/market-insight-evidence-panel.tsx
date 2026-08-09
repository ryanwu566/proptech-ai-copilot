import type { MarketResult } from "@/lib/api";
import { getMarketMetricPresentation, type MarketInsightVisualModel, type MarketDistributionPoint } from "@/lib/market-insight-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { MetricTile } from "@/components/product-ui";
import { buildMarketInsightSnapshot } from "@/lib/market-insight-snapshot";

type Locale = "zh-TW" | "en" | "ja" | "ko";

type MarketLabels = {
  median: string;
  averageDirect: string;
  averageNtdSqm: string;
  medianTotal: string;
  count: string;
  countUnit: string;
  period: string;
  history: string;
  historyAverage: string;
  historyCount: string;
  change: string;
  yoy: string;
  source: string;
  sourceUpdated: string;
  coverage: string;
  covered: string;
  freshness: string;
  sample: string;
  included: string;
  excluded: string;
  distributions: string;
  priceDistribution: string;
  buildingDistribution: string;
  ageDistribution: string;
  methodology: string;
  print: string;
  reportTitle: string;
  boundary: string;
  snapshot: string;
  generated: string;
};

const LABELS: Record<Locale, MarketLabels> = {
  "zh-TW": { median: "中位單價（元／平方公尺）", averageDirect: "平均單價（萬元／坪）", averageNtdSqm: "平均單價（元／平方公尺）", medianTotal: "中位總價（元）", count: "本期交易筆數", countUnit: "筆", period: "資料期別", history: "最近期別", historyAverage: "平均單價（萬元／坪）", historyCount: "交易筆數（筆）", change: "期間變化", yoy: "年對年變化", source: "資料來源", sourceUpdated: "資料更新", coverage: "涵蓋狀態", covered: "已有資料涵蓋", freshness: "資料新鮮度", sample: "樣本狀態", included: "納入筆數", excluded: "排除筆數", distributions: "資料分布", priceDistribution: "價格分布", buildingDistribution: "建物類型分布", ageDistribution: "屋齡分布", methodology: "方法與限制", print: "列印目前摘要", reportTitle: "市場洞察摘要", boundary: "市場資料僅供區域交易參考，不是估價、核貸或購買建議。", snapshot: "安全案件快照", generated: "產生時間" },
  en: { median: "Median unit price (NTD/sqm)", averageDirect: "Average unit price (NTD 10,000/ping)", averageNtdSqm: "Average unit price (NTD/sqm)", medianTotal: "Median total price (NTD)", count: "Transactions in period", countUnit: "records", period: "Data period", history: "Recent periods", historyAverage: "Average unit price (NTD 10,000/ping)", historyCount: "Transactions (records)", change: "Period change", yoy: "Year-over-year change", source: "Source", sourceUpdated: "Source updated", coverage: "Coverage", covered: "Data covered", freshness: "Freshness", sample: "Sample status", included: "Included", excluded: "Excluded", distributions: "Distributions", priceDistribution: "Price distribution", buildingDistribution: "Building type distribution", ageDistribution: "Age-band distribution", methodology: "Methodology and limits", print: "Print current summary", reportTitle: "Market Insight Summary", boundary: "Market data is regional transaction reference only, not an appraisal, lending decision, or purchase recommendation.", snapshot: "Safe property-case snapshot", generated: "Generated" },
  ja: { median: "中央値単価（台湾ドル／㎡）", averageDirect: "平均単価（万元／坪）", averageNtdSqm: "平均単価（台湾ドル／㎡）", medianTotal: "中央値総額（台湾ドル）", count: "当期取引件数", countUnit: "件", period: "データ期間", history: "最近の期間", historyAverage: "平均単価（万元／坪）", historyCount: "取引件数（件）", change: "期間変化", yoy: "前年比", source: "出典", sourceUpdated: "更新日", coverage: "カバレッジ", covered: "データあり", freshness: "更新状態", sample: "標本状態", included: "採用件数", excluded: "除外件数", distributions: "分布", priceDistribution: "価格分布", buildingDistribution: "建物種類の分布", ageDistribution: "築年帯の分布", methodology: "方法と制限", print: "現在の概要を印刷", reportTitle: "市場洞察概要", boundary: "市場データは地域取引の参考であり、査定・融資判断・購入推奨ではありません。", snapshot: "安全な案件スナップショット", generated: "生成日時" },
  ko: { median: "중위 단가 (NTD/㎡)", averageDirect: "평균 단가 (만 NTD/평)", averageNtdSqm: "평균 단가 (NTD/㎡)", medianTotal: "중위 총액 (NTD)", count: "해당 기간 거래 건수", countUnit: "건", period: "데이터 기간", history: "최근 기간", historyAverage: "평균 단가 (만 NTD/평)", historyCount: "거래 건수 (건)", change: "기간 변화", yoy: "전년 대비 변화", source: "출처", sourceUpdated: "업데이트", coverage: "데이터 범위", covered: "데이터 있음", freshness: "최신성", sample: "표본 상태", included: "포함", excluded: "제외", distributions: "분포", priceDistribution: "가격 분포", buildingDistribution: "건물 유형 분포", ageDistribution: "연식 구간 분포", methodology: "방법과 제한", print: "현재 요약 인쇄", reportTitle: "시장 인사이트 요약", boundary: "시장 데이터는 지역 거래 참고용이며 감정, 대출 결정 또는 구매 권고가 아닙니다.", snapshot: "안전한 사건 스냅샷", generated: "생성 시각" },
};

function formatNumber(value: number | null | undefined, locale: Locale): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString(locale) : "—";
}

function formatChange(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)}%` : "—";
}

function DistributionTable({ title, items }: { title: string; items: MarketDistributionPoint[] }) {
  if (!items.length) return null;
  const total = items.reduce((sum, item) => sum + item.count, 0);
  return <section aria-labelledby={`${title}-heading`} className="min-w-0 rounded-lg border border-stone-200 bg-stone-50 p-3">
    <h4 id={`${title}-heading`} className="text-xs font-bold text-slate-800">{title}</h4>
    <div className="mt-2 space-y-2" aria-label={title}>
      {items.map((item) => <div key={item.label} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 text-xs"><span className="truncate text-slate-600">{item.label}</span><span className="font-bold text-slate-800">{item.count}</span><div className="col-span-2 h-1.5 overflow-hidden rounded-full bg-white"><div className="h-full rounded-full bg-cyan-600" style={{ width: `${Math.min(100, total ? (item.count / total) * 100 : 0)}%` }} /></div></div>)}
    </div>
    <table className="sr-only"><caption>{title}</caption><thead><tr><th>Label</th><th>Count</th></tr></thead><tbody>{items.map((item) => <tr key={item.label}><td>{item.label}</td><td>{item.count}</td></tr>)}</tbody></table>
  </section>;
}

export function MarketInsightEvidencePanel({ result, model }: { result: MarketResult; model: MarketInsightVisualModel }) {
  const { locale: rawLocale } = useExperienceLocale();
  const locale = (rawLocale in LABELS ? rawLocale : "zh-TW") as Locale;
  const labels = LABELS[locale];
  const presentation = getMarketMetricPresentation(result);
  const snapshot = buildMarketInsightSnapshot(result);
  const hasAnalysisMetadata = presentation.periodChange !== null
    || presentation.yearOverYearChange !== null
    || presentation.inclusionCount !== null
    || presentation.exclusionCount !== null;
  const hasSourceMetadata = Boolean(
    presentation.period
    || presentation.sourceName
    || presentation.sourceUpdatedAt
    || presentation.coverageStatus
    || presentation.freshnessStatus
    || presentation.sampleStatus,
  );
  const hasDistributions = model.priceDistribution.length > 0
    || model.buildingTypeDistribution.length > 0
    || model.ageBandDistribution.length > 0;
  return <div className="space-y-4">
    <div data-testid="market-primary-metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {presentation.averageUnitPrice !== null && <MetricTile label={labels.averageDirect} value={formatNumber(presentation.averageUnitPrice, locale)} />}
      {presentation.transactionCount !== null && <MetricTile label={labels.count} value={formatNumber(presentation.transactionCount, locale)} note={presentation.period ? `${labels.period}：${presentation.period}` : undefined} />}
      {presentation.medianUnitPrice !== null && <MetricTile label={labels.median} value={formatNumber(presentation.medianUnitPrice, locale)} />}
      {presentation.medianTotalPrice !== null && <MetricTile label={labels.medianTotal} value={formatNumber(presentation.medianTotalPrice, locale)} />}
    </div>
    <button type="button" onClick={() => window.print()} className="rounded-lg border border-cyan-700 px-3 py-2 text-xs font-bold text-cyan-800 hover:bg-cyan-50 print:hidden">{labels.print}</button>
    {hasAnalysisMetadata && <div className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
      {presentation.periodChange !== null && <MetaField label={labels.change} value={formatChange(presentation.periodChange)} />}
      {presentation.yearOverYearChange !== null && <MetaField label={labels.yoy} value={formatChange(presentation.yearOverYearChange)} />}
      {presentation.inclusionCount !== null && <MetaField label={labels.included} value={formatNumber(presentation.inclusionCount, locale)} />}
      {presentation.exclusionCount !== null && <MetaField label={labels.excluded} value={formatNumber(presentation.exclusionCount, locale)} />}
    </div>}
    {hasSourceMetadata && <div data-testid="market-source-metadata" className="rounded-lg border border-cyan-100 bg-cyan-50/60 p-3 text-xs leading-5 text-cyan-950">
      {presentation.period && <p><strong>{labels.period}:</strong> {presentation.period}</p>}
      {presentation.sourceName && <p><strong>{labels.source}:</strong> {presentation.sourceName}</p>}
      {presentation.sourceUpdatedAt && <p><strong>{labels.sourceUpdated}:</strong> {presentation.sourceUpdatedAt}</p>}
      {presentation.coverageStatus && <p><strong>{labels.coverage}:</strong> {formatCoverage(presentation.coverageStatus, labels)}</p>}
      {presentation.freshnessStatus && <p><strong>{labels.freshness}:</strong> {presentation.freshnessStatus}</p>}
      {presentation.sampleStatus && <p><strong>{labels.sample}:</strong> {presentation.sampleStatus}</p>}
    </div>}
    {model.history.length > 0 && <section aria-labelledby="market-history-heading" className="rounded-lg border border-stone-200 bg-white p-3">
      <h4 id="market-history-heading" className="text-xs font-bold text-slate-800">{labels.history}</h4>
      <div className="mt-2 max-w-full overflow-x-auto">
        <table data-testid="market-history-table" className="w-full min-w-[480px] text-left text-xs">
          <thead><tr className="bg-stone-50"><th className="p-2">{labels.period}</th><th className="p-2">{labels.historyAverage}</th><th className="p-2">{labels.historyCount}</th></tr></thead>
          <tbody>{model.history.map((point) => <tr key={point.period} className="border-t border-stone-100"><td className="p-2">{point.period}</td><td className="p-2">{formatNumber(point.average_unit_price, locale)}</td><td className="p-2">{formatNumber(point.transaction_count, locale)} {labels.countUnit}</td></tr>)}</tbody>
        </table>
      </div>
    </section>}
    {hasDistributions && <DetailDisclosure title={labels.distributions}>
      <div className="grid gap-3 md:grid-cols-3">
        <DistributionTable title={labels.priceDistribution} items={model.priceDistribution} />
        <DistributionTable title={labels.buildingDistribution} items={model.buildingTypeDistribution} />
        <DistributionTable title={labels.ageDistribution} items={model.ageBandDistribution} />
      </div>
    </DetailDisclosure>}
    <DetailDisclosure title={labels.methodology}>
      <p className="text-xs leading-5 text-slate-700">{result.methodology || result.aggregation_method || labels.boundary}</p>
      {result.caveat && <p className="mt-2 text-xs leading-5 text-amber-900">{result.caveat}</p>}
      <p className="mt-2 text-xs leading-5 text-amber-900">{result.disclaimer || labels.boundary}</p>
    </DetailDisclosure>
    {snapshot && <DetailDisclosure title={labels.snapshot}>
      <dl className="grid gap-2 text-xs text-slate-700 sm:grid-cols-2">
        <MetaField label={regionLabel(locale)} value={`${snapshot.county} / ${snapshot.district}`} />
        <MetaField label={labels.generated} value={snapshot.generated_at} />
        {presentation.medianUnitPrice !== null && <MetaField label={labels.median} value={formatNumber(presentation.medianUnitPrice, locale)} />}
        {presentation.meanUnitPriceNtdSqm !== null && <MetaField label={labels.averageNtdSqm} value={formatNumber(presentation.meanUnitPriceNtdSqm, locale)} />}
        {presentation.transactionCount !== null && <MetaField label={labels.count} value={formatNumber(presentation.transactionCount, locale)} />}
        {presentation.sampleStatus && <MetaField label={labels.sample} value={presentation.sampleStatus} />}
      </dl>
    </DetailDisclosure>}
    <div className="hidden print:block" data-testid="market-insight-print-report">
      <h2 className="text-xl font-bold">{labels.reportTitle}</h2>
      <p>{result.county || result.city} / {result.district || "—"}{presentation.period ? ` · ${presentation.period}` : ""}</p>
      {presentation.averageUnitPrice !== null && <p>{labels.averageDirect}: {formatNumber(presentation.averageUnitPrice, locale)}</p>}
      {presentation.transactionCount !== null && <p>{labels.count}: {formatNumber(presentation.transactionCount, locale)}</p>}
      {presentation.medianUnitPrice !== null && <p>{labels.median}: {formatNumber(presentation.medianUnitPrice, locale)}</p>}
      {presentation.medianTotalPrice !== null && <p>{labels.medianTotal}: {formatNumber(presentation.medianTotalPrice, locale)}</p>}
      {presentation.sourceName && <p>{labels.source}: {presentation.sourceName}</p>}
      {presentation.sourceUpdatedAt && <p>{labels.sourceUpdated}: {presentation.sourceUpdatedAt}</p>}
      {presentation.coverageStatus && <p>{labels.coverage}: {formatCoverage(presentation.coverageStatus, labels)}</p>}
      {presentation.freshnessStatus && <p>{labels.freshness}: {presentation.freshnessStatus}</p>}
      {presentation.sampleStatus && <p>{labels.sample}: {presentation.sampleStatus}</p>}
      <p>{result.disclaimer || labels.boundary}</p>
    </div>
  </div>;
}

function MetaField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-stone-200 bg-white p-3"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className="mt-1 font-bold text-slate-900">{value}</p></div>;
}

function formatCoverage(status: MarketResult["coverage_status"], labels: MarketLabels): string {
  return status === "covered" || status === "nationwide" ? labels.covered : status.replaceAll("_", " ");
}

function regionLabel(locale: Locale): string {
  return locale === "en" ? "Region" : locale === "ja" ? "地域" : locale === "ko" ? "지역" : "區域";
}
