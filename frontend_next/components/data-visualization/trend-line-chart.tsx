import { selectChartLabelIndexes, type MarketHistoryPoint } from "@/lib/market-insight-visualization";
import { marketStateHasEvidence, type MarketDisplayState } from "@/lib/market-result-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { formatMarketCopy, getMarketInsightCopy } from "@/lib/market-insight-copy";

export function TrendLineChart({ data, status }: { data: MarketHistoryPoint[]; status: MarketDisplayState }) {
  const { locale } = useExperienceLocale();
  const labels = getMarketInsightCopy(locale);
  if (!marketStateHasEvidence(status) || data.length === 0) {
    return <p data-testid="market-price-trend-empty" role="status" className="rounded-lg bg-stone-50 p-4 text-sm text-slate-600">{labels.chartNoHistory}</p>;
  }
  const width = 640;
  const height = 280;
  const min = Math.min(...data.map((point) => point.average_unit_price));
  const max = Math.max(...data.map((point) => point.average_unit_price));
  const range = max - min || 1;
  const xFor = (index: number) => data.length === 1 ? width / 2 : 40 + (index * 560) / (data.length - 1);
  const yFor = (value: number) => 24 + (1 - (value - min) / range) * 200;
  const points = data.map((point, index) => `${xFor(index)},${yFor(point.average_unit_price)}`).join(" ");
  const labelIndexes = selectChartLabelIndexes(data.length);
  const textSummary = data.length === 1
    ? labels.chartOnePeriod
    : formatMarketCopy(labels.priceChartSummary, { count: data.length });
  return <div data-testid="market-price-trend" className="max-w-full overflow-hidden" aria-label={`${labels.priceTrend} · ${textSummary}`}>
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={labels.priceTrend} className="h-auto w-full">
      <title>{labels.priceTrend}</title><desc>{textSummary}</desc>
      {data.length > 1 && <polyline fill="none" stroke="currentColor" strokeWidth="4" points={points} className="text-cyan-700" />}
      {data.map((point, index) => <g key={`${point.period}-point-${index}`} tabIndex={0} aria-label={`${point.period}: ${point.average_unit_price} ${labels.unitWanPerPing}`} className="outline-none focus-visible:[&_circle]:stroke-slate-950 focus-visible:[&_circle]:stroke-[3px]">
        <title>{point.period}: {point.average_unit_price} {labels.unitWanPerPing}</title>
        <circle cx={xFor(index)} cy={yFor(point.average_unit_price)} r="6" className="fill-white stroke-cyan-700 stroke-[3px]" />
      </g>)}
      {labelIndexes.map((index) => { const point = data[index]; return <text key={`${point.period}-${index}`} x={xFor(index)} y="252" textAnchor="middle" className="fill-slate-600 text-[11px]">{point.period}</text>; })}
    </svg>
    <p className="mt-2 text-xs text-slate-600">{textSummary}</p>
  </div>;
}
