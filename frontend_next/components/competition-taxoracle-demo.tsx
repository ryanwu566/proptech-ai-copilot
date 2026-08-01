"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Notice } from "@/components/ui";
import { ErrorState, PageHeader, SectionCard } from "@/components/product-ui";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { ReadAloudControls } from "@/components/read-aloud-controls";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { api, type HoldingCostResult, type TaxCase, type TaxResult } from "@/lib/api";
import { COMPETITION_NOTICE, getCompetitionCopy } from "@/lib/competition-release";
import { createSafeSpeechSummary } from "@/lib/safe-speech";
import {
  formatBoolean,
  formatCurrency,
  formatHoldingBreakdownKey,
  formatOutcome,
  formatPropertyPrice,
  formatRuleVersion,
  getTaxFieldCopy,
  getTaxFieldKeys,
  getTaxGroupLabel,
  getTaxText,
  humanSourceStatus,
} from "@/lib/taxoracle-presentation";

const EXAMPLE: TaxCase = {
  case_id: "COMPETITION-EXAMPLE",
  client_name: "Illustrative property case",
  sold_self_occupied: true,
  residency_condition_met: true,
  purchase_within_reasonable_period: true,
  purchased_self_occupied: true,
  same_owner: true,
  land_value_available: true,
  required_docs_complete: true,
  enters_five_year_monitoring: true,
  exceptional_circumstances: false,
};
const groups = ["property", "occupancy", "documents", "review"] as const;

export function CompetitionTaxOracleDemo({ onEvidence, onPrivacy, onTerms }: { onEvidence: () => void; onPrivacy: () => void; onTerms: () => void }) {
  const { locale } = useExperienceLocale();
  const copy = getCompetitionCopy(locale);
  const [taxCase, setTaxCase] = useState<TaxCase>(EXAMPLE);
  const [propertyPrice, setPropertyPrice] = useState(2000);
  const [taxResult, setTaxResult] = useState<TaxResult | null>(null);
  const [holdingResult, setHoldingResult] = useState<HoldingCostResult | null>(null);
  const [source, setSource] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [step, setStep] = useState(1);
  const fieldKeys = getTaxFieldKeys();
  const negativeCount = useMemo(() => fieldKeys.filter((key) => taxCase[key] === false).length, [fieldKeys, taxCase]);
  const speech = createSafeSpeechSummary([
    getTaxText(locale, "outcomeTitle"),
    taxResult ? formatOutcome(taxResult.eligibility_status, locale) : copy.incomplete,
    holdingResult ? `${getTaxText(locale, "holdingMonthly")}: ${formatCurrency(holdingResult.monthly_total_holding_cost, locale)}` : "",
    getTaxText(locale, "boundary"),
  ], locale);

  useEffect(() => {
    api.taxOracleSources().then(setSource).catch(() => setSource(null));
  }, []);

  async function calculate() {
    if (!Number.isFinite(propertyPrice) || propertyPrice <= 0) {
      setError("Please enter a property price greater than zero.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (offline) {
        const failed = [taxCase.sold_self_occupied, taxCase.residency_condition_met, taxCase.purchase_within_reasonable_period, taxCase.purchased_self_occupied, taxCase.same_owner, taxCase.land_value_available, taxCase.required_docs_complete, !taxCase.exceptional_circumstances].filter((value) => !value).length;
        const riskScore = failed * 20;
        setTaxResult({ eligibility_status: riskScore >= 40 ? "not_eligible" : riskScore ? "manual_review" : "eligible", risk_score: riskScore, signal_color: riskScore >= 55 ? "red" : riskScore ? "yellow" : "green", hard_fail_rules: [], manual_review_rules: [], missing_docs: [], reminder_timeline: [], rule_traces: [], ai_explanation: { headline: "Offline reference only", customer_script: "", source: "local demo model" }, disclaimer: COMPETITION_NOTICE, case_input: taxCase, tax_output_boundary: "preliminary_screening_only" });
        setHoldingResult({ property_price_wan: propertyPrice, loan_monthly_payment: 0, monthly_management_fee: 0, monthly_repair_reserve: 0, monthly_tax_estimate: Math.round(propertyPrice * 0.0012), annual_home_tax_estimate: Math.round(propertyPrice * 0.0012 * 12), annual_land_tax_estimate: 0, monthly_insurance: 0, monthly_total_holding_cost: Math.round(propertyPrice * 0.0012), annual_total_holding_cost: Math.round(propertyPrice * 0.0012 * 12), income_burden_ratio: null, affordability_level: "unknown", affordability_message: "Offline reference only", cost_breakdown: [], disclaimer: COMPETITION_NOTICE, input: { property_price_wan: propertyPrice, loan_monthly_payment: 0, monthly_income_wan: null, area_ping: null, management_fee_per_ping: 0, repair_reserve_per_ping: 0, annual_home_tax_rate: 0.0012, annual_land_tax_rate: 0, annual_insurance: 0, include_tax_estimate: true } });
      } else {
        const [tax, holding] = await Promise.all([
          api.runTaxOracleCase(taxCase),
          api.holdingCostCalculate({ property_price: propertyPrice, loan_monthly_payment: 0, include_tax_estimate: true }),
        ]);
        setTaxResult(tax);
        setHoldingResult(holding);
      }
      setStep(4);
    } catch {
      setError("The calculation is temporarily unavailable. Your inputs were preserved and no conclusion was inferred.");
    } finally {
      setLoading(false);
    }
  }

  function update(key: keyof TaxCase, value: boolean) {
    setTaxCase((current) => ({ ...current, [key]: value }));
    setTaxResult(null);
    setHoldingResult(null);
    setStep(1);
  }

  function reset() {
    setTaxCase(EXAMPLE);
    setPropertyPrice(2000);
    setTaxResult(null);
    setHoldingResult(null);
    setError("");
    setStep(1);
    setOffline(false);
  }

  const sourceStatus = humanSourceStatus(source?.source_status, locale);
  return (
    <div className="space-y-5" data-testid="competition-demo">
      <PageHeader kicker={copy.eyebrow} title={copy.demoTitle} description={copy.demoDescription} />
      <Notice tone="warning">{copy.illustrative}. {copy.boundary}</Notice>
      <div className="grid grid-cols-4 gap-2" aria-label="Demo progress">
        {copy.steps.map((label, index) => <div key={label} className={`rounded-lg px-2 py-2 text-center text-[11px] font-bold ${step >= index + 1 ? "bg-cyan-100 text-cyan-900" : "bg-stone-100 text-slate-500"}`}><span className="block text-[10px]">{index + 1}</span>{label}</div>)}
      </div>
      {offline && <Notice>{copy.offline}</Notice>}
      {error && <ErrorState message={error} />}
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,390px)_minmax(0,1fr)]">
        <SectionCard title={copy.inputs} description={copy.demoDescription}>
          <p className="mb-4 rounded-lg bg-stone-50 p-3 text-xs leading-5 text-slate-600">{getTaxText(locale, "exampleDisclosure")}</p>
          <label className="block text-xs font-bold text-slate-700">{getTaxText(locale, "price")} <span className="font-normal text-slate-500">({getTaxText(locale, "currency")})</span><input aria-label={getTaxText(locale, "price")} data-testid="demo-property-price" type="number" min="1" value={propertyPrice} onChange={(event) => { setPropertyPrice(Number(event.target.value)); setTaxResult(null); setHoldingResult(null); setStep(1); }} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" /><span className="mt-1 block text-[11px] font-normal text-slate-500">{formatPropertyPrice(propertyPrice, locale)}</span></label>
          <div className="mt-5 space-y-4">
            {groups.map((group) => <fieldset key={group} className="rounded-xl border border-stone-200 p-3"><legend className="px-1 text-xs font-bold text-slate-800">{getTaxGroupLabel(locale, group)}</legend><div className="space-y-2">{fieldKeys.filter((key) => getTaxFieldCopy(locale, key).group === group).map((key) => { const field = getTaxFieldCopy(locale, key); return <label key={key} className="flex min-w-0 items-start gap-3 rounded-lg border border-stone-100 px-3 py-2.5 text-xs text-slate-700"><input data-testid={`demo-${key}`} type="checkbox" checked={taxCase[key]} onChange={(event) => update(key, event.target.checked)} className="mt-0.5 h-4 w-4 shrink-0" /><span className="min-w-0"><span className="block font-semibold">{field.label}</span><span className="mt-0.5 block leading-5 text-slate-500">{field.help} · {formatBoolean(taxCase[key], locale)}</span></span></label>; })}</div></fieldset>)}
          </div>
          <div className="mt-4 flex flex-wrap gap-2"><Button className="demo-calculate-button" disabled={loading} onClick={calculate}>{loading ? copy.calculating : copy.calculate}</Button><Button secondary onClick={reset}>{copy.reset}</Button></div>
          <button type="button" className="mt-3 text-xs font-bold text-cyan-800 underline" onClick={() => setOffline((value) => !value)}>{offline ? copy.live : copy.switchOffline}</button>
        </SectionCard>
        <SectionCard title={copy.output}>
          {taxResult || holdingResult ? <div className="space-y-4"><TaxOutcome result={taxResult} locale={locale} negativeCount={negativeCount} sourceStatus={sourceStatus} /><HoldingSummary result={holdingResult} locale={locale} /><div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><strong>{getTaxText(locale, "next")}:</strong> {getTaxText(locale, "nextText")}</div><div className="flex flex-wrap items-center gap-2"><ReadAloudControls summary={speech} /><Button secondary onClick={() => window.print()}>{getTaxText(locale, "print")}</Button><Button secondary onClick={onEvidence}>{copy.evidence}</Button><Button secondary onClick={onPrivacy}>{copy.privacy}</Button><Button secondary onClick={onTerms}>{copy.terms}</Button></div><PrintReport taxResult={taxResult} holdingResult={holdingResult} locale={locale} sourceStatus={sourceStatus} price={propertyPrice} /></div> : <p className="rounded-xl border border-dashed border-stone-300 p-5 text-sm leading-6 text-slate-500">{copy.incomplete}</p>}
        </SectionCard>
      </div>
    </div>
  );
}

function TaxOutcome({ result, locale, negativeCount, sourceStatus }: { result: TaxResult | null; locale: Parameters<typeof formatOutcome>[1]; negativeCount: number; sourceStatus: string }) {
  if (!result) return null;
  return <section className="rounded-xl border border-cyan-200 bg-cyan-50/50 p-4" data-testid="human-tax-outcome"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-cyan-800">{getTaxText(locale, "outcomeTitle")}</p><h3 className="mt-1 text-lg font-black text-slate-950">{formatOutcome(result.eligibility_status, locale)}</h3></div><span className="rounded-full bg-white px-2 py-1 text-[10px] font-bold text-cyan-900">{getTaxText(locale, "professional")}</span></div><p className="mt-3 text-sm leading-6 text-slate-700">{getTaxText(locale, result.eligibility_status)}</p><div className="mt-4 grid gap-2 sm:grid-cols-3"><Metric label={getTaxText(locale, "facts")} value={Math.max(0, result.rule_traces.length - negativeCount)} /><Metric label={getTaxText(locale, "missing")} value={result.missing_docs.length} /><Metric label={getTaxText(locale, "reviewSignals")} value={result.manual_review_rules.length + negativeCount} /></div><p className="mt-3 text-xs leading-5 text-slate-600"><strong>{getTaxText(locale, "source")}:</strong> {sourceStatus}. <strong>{getTaxText(locale, "calculation")}:</strong> {getTaxText(locale, "calculationText")}</p><p className="mt-2 text-xs leading-5 text-slate-600">{getTaxText(locale, "boundary")}</p><DetailDisclosure title={getTaxText(locale, "technical")}><dl className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2"><div><dt className="font-bold">{getTaxText(locale, "caseId")}</dt><dd>{result.case_input.case_id}</dd></div><div><dt className="font-bold">{getTaxText(locale, "internalVersion")}</dt><dd>{formatRuleVersion(result.official_rule_trace?.rule_version, locale)}</dd></div><div><dt className="font-bold">Rule IDs</dt><dd>{result.official_rule_trace?.rule_version ? "TX001–TX009" : getTaxText(locale, "unavailable")}</dd></div><div><dt className="font-bold">Source status</dt><dd>{sourceStatus}</dd></div></dl></DetailDisclosure></section>;
}

function HoldingSummary({ result, locale }: { result: HoldingCostResult | null; locale: Parameters<typeof formatCurrency>[1] }) {
  if (!result) return null;
  const breakdown = result.cost_breakdown.filter((item) => item.monthly_amount > 0);
  return <section className="rounded-xl border border-stone-200 bg-white p-4" data-testid="human-holding-cost"><p className="text-[10px] font-bold tracking-wider text-slate-500">Holding Cost</p><div className="mt-2 grid gap-3 sm:grid-cols-2"><div><p className="text-xs font-semibold text-slate-500">{getTaxText(locale, "holdingMonthly")}</p><p className="mt-1 text-2xl font-black text-slate-950">{formatCurrency(result.monthly_total_holding_cost, locale)}</p><p className="text-xs text-slate-500">{getTaxText(locale, "monthly")}</p></div><div><p className="text-xs font-semibold text-slate-500">{getTaxText(locale, "holdingAnnual")}</p><p className="mt-1 text-2xl font-black text-slate-950">{formatCurrency(result.annual_total_holding_cost, locale)}</p><p className="text-xs text-slate-500">{getTaxText(locale, "annual")}</p></div></div><p className="mt-3 text-xs leading-5 text-slate-600">{getTaxText(locale, "holdingMeaning")}</p><h4 className="mt-4 text-xs font-bold text-slate-800">{getTaxText(locale, "breakdown")}</h4>{breakdown.length ? <ul className="mt-2 space-y-1 text-xs text-slate-600">{breakdown.map((item) => <li key={item.key} className="flex justify-between gap-3 border-b border-stone-100 py-2"><span>{formatHoldingBreakdownKey(locale, item.key)}</span><strong>{formatCurrency(item.monthly_amount, locale)} / {getTaxText(locale, "monthly")}</strong></li>)}</ul> : <p className="mt-2 text-xs text-slate-500">{getTaxText(locale, "notIncluded")}</p>}{result.input.monthly_income_wan === null && <p className="mt-3 text-xs text-slate-500">{getTaxText(locale, "noIncome")}</p>}<p className="mt-3 text-xs text-slate-600">{result.disclaimer || COMPETITION_NOTICE}</p></section>;
}

function PrintReport({ taxResult, holdingResult, locale, sourceStatus, price }: { taxResult: TaxResult | null; holdingResult: HoldingCostResult | null; locale: Parameters<typeof formatCurrency>[1]; sourceStatus: string; price: number }) {
  return <div className="hidden print:block" data-testid="competition-print-report"><h1 className="text-2xl font-bold">{getTaxText(locale, "reportTitle")}</h1><p>{getTaxText(locale, "exampleDisclosure")}</p><p>{getTaxText(locale, "generated")}: {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date())}</p><h2 className="mt-4 font-bold">{getTaxText(locale, "price")}</h2><p>{formatPropertyPrice(price, locale)}</p><h2 className="mt-4 font-bold">{getTaxText(locale, "outcomeTitle")}</h2><p>{taxResult ? formatOutcome(taxResult.eligibility_status, locale) : getTaxText(locale, "unavailable")}</p><p>{getTaxText(locale, "missing")}: {taxResult?.missing_docs.length ?? 0}</p><h2 className="mt-4 font-bold">Holding Cost</h2><p>{holdingResult ? `${getTaxText(locale, "holdingMonthly")}: ${formatCurrency(holdingResult.monthly_total_holding_cost, locale)}; ${getTaxText(locale, "holdingAnnual")}: ${formatCurrency(holdingResult.annual_total_holding_cost, locale)}` : getTaxText(locale, "unavailable")}</p><p>{getTaxText(locale, "source")}: {sourceStatus}</p><p>{getTaxText(locale, "boundary")}</p></div>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg bg-white px-3 py-2"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 text-lg font-black text-slate-950">{value}</p></div>;
}
