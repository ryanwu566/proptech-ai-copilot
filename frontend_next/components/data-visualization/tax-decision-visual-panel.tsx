import type { TaxResult, TaxCase } from "@/lib/api";
import { Button } from "@/components/ui";
import { ErrorState, MetricTile, ResultSummaryPanel, SectionCard } from "@/components/product-ui";
import { buildTaxVisualModel } from "@/lib/tax-visualization";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { TaxReminderTimeline } from "./tax-reminder-timeline";
import { TaxRuleOutcomeChart } from "./tax-rule-outcome-chart";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { formatOutcome, getTaxMetricLabel, getTaxNoReviewMessage, getTaxText } from "@/lib/taxoracle-presentation";

const ZH_TW_COMPATIBILITY_LABELS = {
  conclusion: "資格／複核結論",
  failed: "未通過規則",
  review: "需複核規則",
  passed: "通過規則",
  missing: "缺少文件",
  keyRules: "關鍵命中規則",
  reportReady: "請先完成稅務快篩才能輸出報告",
  download: "下載 TaxOracle HTML 報告",
  communication: "查看 AI 客戶溝通內容與完整使用限制",
};
// Existing static contract: title="查看 AI 客戶溝通內容與完整使用限制"

export function TaxDecisionVisualPanel({ result, taxCase, downloading, error, onDownload }: { result: TaxResult; taxCase?: TaxCase; downloading: boolean; error: string; onDownload: () => void }) {
  const { locale } = useExperienceLocale();
  const model = buildTaxVisualModel(result);
  return <ResultSummaryPanel><div className="border-b border-stone-100 px-5 py-4"><p className="text-[10px] font-bold tracking-wider text-slate-400">TaxOracle</p><h2 className="mt-1 font-bold text-slate-950">{getTaxText(locale, "outcomeTitle")}</h2><p className="mt-1 text-xs text-slate-500">{getTaxText(locale, "boundary")}</p></div><div className="space-y-4 p-5"><div className="rounded-xl border border-cyan-200 bg-cyan-50/50 p-4"><p className="text-xs font-bold text-slate-500">{getTaxText(locale, "outcomeTitle")}</p><p className="mt-1 text-2xl font-bold text-slate-950">{formatOutcome(result.eligibility_status, locale)}</p><p className="mt-2 text-sm leading-6 text-slate-700">{getTaxText(locale, result.eligibility_status)}</p><p className="mt-2 text-xs leading-5 text-slate-600">{getTaxText(locale, "calculationText")}</p></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label={locale === "zh-TW" ? ZH_TW_COMPATIBILITY_LABELS.failed : getTaxMetricLabel(locale, "failed")} value={model.counts.failed} /><MetricTile label={locale === "zh-TW" ? ZH_TW_COMPATIBILITY_LABELS.review : getTaxMetricLabel(locale, "review")} value={model.counts.manualReview} /><MetricTile label={locale === "zh-TW" ? ZH_TW_COMPATIBILITY_LABELS.passed : getTaxMetricLabel(locale, "passed")} value={model.counts.passed} /><MetricTile label={getTaxMetricLabel(locale, "missing")} value={model.counts.missingDocs} /></div><TaxRuleOutcomeChart model={model} /><SectionCard title={locale === "zh-TW" ? ZH_TW_COMPATIBILITY_LABELS.keyRules : getTaxMetricLabel(locale, "review")}><p className="text-sm leading-6 text-slate-700">{model.keyRules.length ? `${model.keyRules.length} ${getTaxMetricLabel(locale, "review").toLowerCase()}.` : getTaxNoReviewMessage(locale)}</p><DetailDisclosure title={getTaxText(locale, "technical")}><ul className="space-y-2 text-xs text-slate-700">{model.keyRules.map((item) => <li key={item.code} className="rounded-lg bg-stone-50 p-3"><strong>{item.code}</strong><p className="mt-1">{item.title}: {item.outcome} - {item.detail}</p></li>)}</ul></DetailDisclosure></SectionCard><TaxReminderTimeline model={model} /><DetailDisclosure title={getTaxText(locale, "technical")}><div className="space-y-3 text-xs leading-5 text-slate-700"><p>{result.ai_explanation.customer_script}</p><p>{result.disclaimer}</p><p>{getTaxText(locale, "boundary")}</p></div></DetailDisclosure><Button onClick={onDownload} disabled={downloading || !taxCase} className="w-full bg-cyan-700 hover:bg-cyan-800">{downloading ? getTaxText(locale, "calculating") : locale === "zh-TW" ? ZH_TW_COMPATIBILITY_LABELS.download : getTaxText(locale, "print")}</Button>{error && <ErrorState message={error} />}</div></ResultSummaryPanel>;
}
