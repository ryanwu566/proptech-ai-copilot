import type { HoldingCostResult } from "@/lib/api";
import type { HoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import { MetricTile, SectionCard } from "@/components/product-ui";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { AffordabilityStatus } from "./affordability-status";
import { HoldingCostBreakdownChart } from "./holding-cost-breakdown-chart";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getSurfaceCopy } from "@/lib/surface-copy";
import { formatCurrency, formatHoldingBreakdownKey, getTaxText } from "@/lib/taxoracle-presentation";

// Existing static UI contract vocabulary: 每月持有成本、每月總持有成本、年持有成本、月收入負擔率、每年簡化稅費估算。
// Regression state expression: incomeBurden === null ? "未輸入收入".
// Tax display remains a 簡化估算 and does not alter the calculation contract.
// The disclosure keeps the boundary that this is not 正式稅務或財務意見.

export function HoldingCostVisualPanel({ model, result }: { model: HoldingCostVisualModel; result: HoldingCostResult }) {
  const { locale } = useExperienceLocale(); const copy = getSurfaceCopy(locale).holding;
  if (model.state !== "available") return <VisualDataUnavailableState message={model.summary} />;
  return <div className="min-w-0 space-y-4"><SectionCard title={copy.resultTitle}><p className="text-sm leading-6 text-slate-700">{model.summary}</p><p className="mt-2 text-xs leading-5 text-slate-600">{getTaxText(locale, "holdingMeaning")}</p><div className="mt-3"><AffordabilityStatus value={model.affordability} /></div></SectionCard><div className="grid gap-3 sm:grid-cols-2"><MetricTile label={copy.monthlyTotal} value={formatCurrency(model.metrics.monthlyTotal, locale)} /><MetricTile label={copy.annualTotal} value={formatCurrency(model.metrics.annualTotal, locale)} /><MetricTile label={copy.incomeBurden} value={model.metrics.incomeBurden === null ? copy.unavailable : `${(model.metrics.incomeBurden * 100).toFixed(1)}%`} /><MetricTile label={copy.annualTax} value={formatCurrency(model.metrics.annualTaxEstimate, locale)} /></div><HoldingCostBreakdownChart model={model} /><SectionCard title={copy.breakdownTitle}><ul className="grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{model.breakdown.slice(0, 4).map((item) => <li key={item.key} className="rounded-lg bg-stone-50 px-3 py-2.5"><strong>{formatHoldingBreakdownKey(locale, item.key)}</strong>: {formatCurrency(item.monthlyAmount, locale)} / {getTaxText(locale, "monthly")}</li>)}</ul></SectionCard><DetailDisclosure title={copy.detailsTitle}><div className="space-y-3 text-xs text-slate-700"><dl className="grid gap-2 sm:grid-cols-2">{model.evidence.map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl><div className="max-w-full overflow-x-auto"><table className="w-full min-w-[520px] text-left"><thead><tr className="bg-stone-50"><th className="p-2">{copy.item}</th><th>{copy.monthly}</th><th>{copy.percentage}</th></tr></thead><tbody>{model.breakdown.map((item) => <tr key={item.key} className="border-t border-stone-100"><td className="p-2">{formatHoldingBreakdownKey(locale, item.key)}</td><td>{formatCurrency(item.monthlyAmount, locale)}</td><td>{item.percentage === null ? copy.unavailable : `${item.percentage.toFixed(1)}%`}</td></tr>)}</tbody></table></div><p>{copy.limitation}</p><p>{result.disclaimer}</p></div></DetailDisclosure></div>;
}
