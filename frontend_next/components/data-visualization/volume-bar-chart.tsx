import { selectChartLabelIndexes, type MarketHistoryPoint } from "@/lib/market-insight-visualization";
import type { MarketDisplayState } from "@/lib/market-result-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { formatMarketCopy, getMarketInsightCopy } from "@/lib/market-insight-copy";

export function VolumeBarChart({ data, status }: { data: MarketHistoryPoint[]; status: MarketDisplayState }) {
  const { locale } = useExperienceLocale();
  const labels = getMarketInsightCopy(locale);
  if (status !== "available" || data.length === 0) {
    return <p data-testid="market-volume-trend-empty" role="status" className="rounded-lg bg-stone-50 p-4 text-sm text-slate-600">{labels.chartNoHistory}</p>;
  }
  const max = Math.max(...data.map((point) => point.transaction_count));
  const labelIndexes = selectChartLabelIndexes(data.length);
  const textSummary = data.length === 1
    ? labels.chartOnePeriod
    : formatMarketCopy(labels.volumeChartSummary, { count: data.length });
  return <div data-testid="market-volume-trend" className="max-w-full overflow-hidden" aria-label={`${labels.volumeTrend} · ${textSummary}`}>
    <svg viewBox="0 0 640 280" role="img" aria-label={labels.volumeTrend} className="h-auto w-full">
      <title>{labels.volumeTrend}</title><desc>{textSummary}</desc>
      {data.map((point, index) => { const x = 48 + (index * 544) / data.length; const barWidth = Math.max(8, 480 / data.length); const barHeight = (point.transaction_count / max) * 200; return <g key={`${point.period}-${index}`} tabIndex={0} aria-label={`${point.period}: ${point.transaction_count} ${labels.countUnit}`} className="outline-none focus-visible:[&_rect]:stroke-slate-950 focus-visible:[&_rect]:stroke-[3px]"><title>{point.period}: {point.transaction_count} {labels.countUnit}</title><rect x={x} y={224 - barHeight} width={barWidth} height={barHeight} className="fill-cyan-600" /></g>; })}
      {labelIndexes.map((index) => { const point = data[index]; const x = 48 + (index * 544) / data.length; const barWidth = Math.max(8, 480 / data.length); return <text key={`${point.period}-label-${index}`} x={x + barWidth / 2} y="252" textAnchor="middle" className="fill-slate-600 text-[11px]">{point.period}</text>; })}
    </svg>
    <p className="mt-2 text-xs text-slate-600">{textSummary}</p>
  </div>;
}
