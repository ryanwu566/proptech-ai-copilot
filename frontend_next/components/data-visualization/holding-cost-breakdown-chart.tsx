import type { HoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getSurfaceCopy } from "@/lib/surface-copy";
import { formatCurrency, formatHoldingBreakdownKey } from "@/lib/taxoracle-presentation";

// Null percentage remains explicit: 無法計算占比. No zero is synthesized.
// Omitted items are described as 另有 additional cost items, never silently dropped.

export function HoldingCostBreakdownChart({ model }: { model: HoldingCostVisualModel }) {
  const { locale } = useExperienceLocale(); const copy = getSurfaceCopy(locale).holding;
  if (!model.breakdown.length) return <VisualDataUnavailableState message={copy.noBreakdown} />;
  const max = Math.max(...model.breakdown.map((item) => item.monthlyAmount), 1);
  return <section aria-label={copy.breakdownTitle} className="max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">{copy.breakdownTitle}</h3><svg viewBox={`0 0 640 ${Math.max(220, model.breakdown.length * 42 + 50)}`} role="img" aria-label={copy.breakdownTitle} className="mt-3 h-auto w-full"><title>{copy.breakdownTitle}</title><desc>{copy.limitation}</desc>{model.breakdown.map((item, index) => { const y = 35 + index * 42; const width = (item.monthlyAmount / max) * 380; return <g key={item.key}><text x="0" y={y + 5} className="fill-slate-700 text-[11px]">{formatHoldingBreakdownKey(locale, item.key)}</text><rect x="170" y={y - 10} width={width} height="20" rx="10" className="fill-cyan-600" /><text x={180 + width} y={y + 5} className="fill-slate-700 text-[11px]">{formatCurrency(item.monthlyAmount, locale)} · {item.percentage === null ? copy.unavailable : `${item.percentage.toFixed(1)}%`}</text></g>; })}</svg>{model.omittedBreakdownCount > 0 && <p className="mt-2 text-xs text-slate-600">{copy.omitted.replace("{count}", String(model.omittedBreakdownCount))}</p>}<p className="mt-2 text-xs text-slate-600">{copy.limitation}</p></section>;
}
