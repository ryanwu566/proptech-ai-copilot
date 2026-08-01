import type { MarketResult } from "@/lib/api";
import type { MarketInsightVisualModel, MarketDistributionPoint } from "@/lib/market-insight-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { MetricTile } from "@/components/product-ui";
import { buildMarketInsightSnapshot } from "@/lib/market-insight-snapshot";

type Locale = "zh-TW" | "en" | "ja" | "ko";

const LABELS: Record<Locale, {
  median: string;
  average: string;
  medianTotal: string;
  count: string;
  change: string;
  yoy: string;
  source: string;
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
  unavailable: string;
  snapshot: string;
  generated: string;
}> = {
  "zh-TW": { median: "中位單價（元／平方公尺）", average: "平均單價（元／平方公尺）", medianTotal: "中位總價（元）", count: "交易筆數", change: "期間變化", yoy: "年對年變化", source: "資料來源", freshness: "資料新鮮度", sample: "樣本狀態", included: "納入筆數", excluded: "排除筆數", distributions: "資料分布", priceDistribution: "價格分布", buildingDistribution: "建物類型分布", ageDistribution: "屋齡分布", methodology: "方法與限制", print: "列印目前摘要", reportTitle: "市場洞察摘要", boundary: "市場資料僅供區域交易參考，不是估價、核貸或購買建議。", unavailable: "目前沒有可安全呈現的市場資料。", snapshot: "安全案件快照", generated: "產生時間" },
  en: { median: "Median unit price (NTD/sqm)", average: "Average unit price (NTD/sqm)", medianTotal: "Median total price (NTD)", count: "Transactions", change: "Period change", yoy: "Year-over-year change", source: "Source", freshness: "Freshness", sample: "Sample status", included: "Included", excluded: "Excluded", distributions: "Distributions", priceDistribution: "Price distribution", buildingDistribution: "Building type distribution", ageDistribution: "Age-band distribution", methodology: "Methodology and limits", print: "Print current summary", reportTitle: "Market Insight Summary", boundary: "Market data is regional transaction reference only, not an appraisal, lending decision, or purchase recommendation.", unavailable: "No market data is currently safe to present.", snapshot: "Safe property-case snapshot", generated: "Generated" },
  ja: { median: "中央値単価（台湾ドル／㎡）", average: "平均単価（台湾ドル／㎡）", medianTotal: "中央値総額（台湾ドル）", count: "取引件数", change: "期間変化", yoy: "前年比", source: "出典", freshness: "更新状態", sample: "標本状態", included: "採用件数", excluded: "除外件数", distributions: "分布", priceDistribution: "価格分布", buildingDistribution: "建物種類の分布", ageDistribution: "築年帯の分布", methodology: "方法と制限", print: "現在の概要を印刷", reportTitle: "市場洞察概要", boundary: "市場データは地域取引の参考であり、査定・融資判断・購入推奨ではありません。", unavailable: "現在、安全に表示できる市場データはありません。", snapshot: "安全な案件スナップショット", generated: "生成日時" },
  ko: { median: "중위 단가 (NTD/㎡)", average: "평균 단가 (NTD/㎡)", medianTotal: "중위 총액 (NTD)", count: "거래 건수", change: "기간 변화", yoy: "전년 대비 변화", source: "출처", freshness: "최신성", sample: "표본 상태", included: "포함", excluded: "제외", distributions: "분포", priceDistribution: "가격 분포", buildingDistribution: "건물 유형 분포", ageDistribution: "연식 구간 분포", methodology: "방법과 제한", print: "현재 요약 인쇄", reportTitle: "시장 인사이트 요약", boundary: "시장 데이터는 지역 거래 참고용이며 감정, 대출 결정 또는 구매 권고가 아닙니다.", unavailable: "현재 안전하게 표시할 시장 데이터가 없습니다.", snapshot: "안전한 사건 스냅샷", generated: "생성 시각" },
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
  const snapshot = buildMarketInsightSnapshot(result);
  const periodChange = result.period_change;
  const yearOverYearChange = result.year_over_year_change;
  return <div className="space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricTile label={labels.median} value={formatNumber(model.metrics.medianUnitPrice, locale)} />
      <MetricTile label={labels.average} value={formatNumber(model.metrics.averageUnitPrice, locale)} />
      <MetricTile label={labels.medianTotal} value={formatNumber(model.metrics.medianTotalPrice, locale)} />
      <MetricTile label={labels.count} value={formatNumber(model.metrics.transactionVolume, locale)} />
    </div>
    <button type="button" onClick={() => window.print()} className="rounded-lg border border-cyan-700 px-3 py-2 text-xs font-bold text-cyan-800 hover:bg-cyan-50 print:hidden">{labels.print}</button>
    <div className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
      <MetaField label={labels.change} value={formatChange(periodChange)} />
      <MetaField label={labels.yoy} value={formatChange(yearOverYearChange)} />
      <MetaField label={labels.included} value={formatNumber(result.inclusion_count, locale)} />
      <MetaField label={labels.excluded} value={formatNumber(result.exclusion_count, locale)} />
    </div>
    <div className="rounded-lg border border-cyan-100 bg-cyan-50/60 p-3 text-xs leading-5 text-cyan-950">
      <p><strong>{labels.source}:</strong> {result.source_name || labels.unavailable}</p>
      <p><strong>{labels.freshness}:</strong> {result.freshness_status || "unknown"}{result.latest_imported_at ? ` · ${result.latest_imported_at}` : ""}</p>
      <p><strong>{labels.sample}:</strong> {result.sample_status || "unknown"}</p>
    </div>
    <DetailDisclosure title={labels.distributions}>
      <div className="grid gap-3 md:grid-cols-3">
        <DistributionTable title={labels.priceDistribution} items={model.priceDistribution} />
        <DistributionTable title={labels.buildingDistribution} items={model.buildingTypeDistribution} />
        <DistributionTable title={labels.ageDistribution} items={model.ageBandDistribution} />
      </div>
    </DetailDisclosure>
    <DetailDisclosure title={labels.methodology}>
      <p className="text-xs leading-5 text-slate-700">{result.methodology || result.aggregation_method || labels.boundary}</p>
      <p className="mt-2 text-xs leading-5 text-amber-900">{result.caveat || labels.boundary}</p>
    </DetailDisclosure>
    {snapshot && <DetailDisclosure title={labels.snapshot}>
      <dl className="grid gap-2 text-xs text-slate-700 sm:grid-cols-2">
        <MetaField label={regionLabel(locale)} value={`${snapshot.county} / ${snapshot.district}`} />
        <MetaField label={labels.generated} value={snapshot.generated_at} />
        <MetaField label={labels.median} value={formatNumber(snapshot.median_unit_price_ntd_sqm, locale)} />
        <MetaField label={labels.average} value={formatNumber(snapshot.average_unit_price_ntd_sqm, locale)} />
        <MetaField label={labels.count} value={formatNumber(snapshot.transaction_count, locale)} />
        <MetaField label={labels.sample} value={snapshot.sample_status || "unknown"} />
      </dl>
    </DetailDisclosure>}
    <div className="hidden print:block" data-testid="market-insight-print-report">
      <h2 className="text-xl font-bold">{labels.reportTitle}</h2>
      <p>{result.county || result.city} / {result.district || "—"} · {result.period || "—"}</p>
      <p>{labels.median}: {formatNumber(model.metrics.medianUnitPrice, locale)}</p>
      <p>{labels.average}: {formatNumber(model.metrics.averageUnitPrice, locale)}</p>
      <p>{labels.medianTotal}: {formatNumber(model.metrics.medianTotalPrice, locale)}</p>
      <p>{labels.count}: {formatNumber(model.metrics.transactionVolume, locale)}</p>
      <p>{labels.source}: {result.source_name || labels.unavailable}</p>
      <p>{labels.freshness}: {result.freshness_status || "unknown"}</p>
      <p>{labels.sample}: {result.sample_status || "unknown"}</p>
      <p>{labels.boundary}</p>
    </div>
  </div>;
}

function MetaField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-stone-200 bg-white p-3"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className="mt-1 font-bold text-slate-900">{value}</p></div>;
}

function regionLabel(locale: Locale): string {
  return locale === "en" ? "Region" : locale === "ja" ? "地域" : locale === "ko" ? "지역" : "區域";
}
