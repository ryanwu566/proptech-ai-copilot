"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Notice } from "@/components/ui";
import { ErrorState, PageHeader, SectionCard } from "@/components/product-ui";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { api, type HoldingCostResult, type TaxCase, type TaxResult } from "@/lib/api";
import { COMPETITION_NOTICE, getCompetitionCopy } from "@/lib/competition-release";

const EXAMPLE: TaxCase = { case_id: "COMPETITION-EXAMPLE", client_name: "Illustrative property case", sold_self_occupied: true, residency_condition_met: true, purchase_within_reasonable_period: true, purchased_self_occupied: true, same_owner: true, land_value_available: true, required_docs_complete: true, enters_five_year_monitoring: true, exceptional_circumstances: false };

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
  const missing = useMemo(() => Object.entries(taxCase).filter(([key, value]) => !key.includes("id") && key !== "client_name" && value === false).map(([key]) => key), [taxCase]);

  useEffect(() => { api.taxOracleSources().then(setSource).catch(() => setSource(null)); }, []);

  async function calculate() {
    if (propertyPrice <= 0) { setError("Enter a property price greater than zero."); return; }
    setLoading(true); setError("");
    try {
      if (offline) {
        const riskScore = [taxCase.sold_self_occupied, taxCase.residency_condition_met, taxCase.purchase_within_reasonable_period, taxCase.purchased_self_occupied, taxCase.same_owner, taxCase.land_value_available, taxCase.required_docs_complete, !taxCase.exceptional_circumstances].filter((value) => !value).length * 20;
        setTaxResult({ eligibility_status: riskScore >= 40 ? "not_eligible" : riskScore ? "manual_review" : "eligible", risk_score: riskScore, signal_color: riskScore >= 55 ? "red" : riskScore ? "yellow" : "green", hard_fail_rules: [], manual_review_rules: [], missing_docs: missing, reminder_timeline: [], rule_traces: missing.map((item) => ({ code: "OFFLINE-INPUT", title: item, outcome: "needs_review", detail: "This input changed in the explicitly labelled offline model.", risk_points: 20 })), ai_explanation: { headline: "Offline reference only", customer_script: "", source: "local demo model" }, disclaimer: COMPETITION_NOTICE, case_input: taxCase, tax_output_boundary: "preliminary_screening_only" });
        setHoldingResult({ property_price_wan: propertyPrice, loan_monthly_payment: 0, monthly_management_fee: 0, monthly_repair_reserve: 0, monthly_tax_estimate: Math.round(propertyPrice * 0.0012), annual_home_tax_estimate: Math.round(propertyPrice * 0.0012 * 12), annual_land_tax_estimate: 0, monthly_insurance: 0, monthly_total_holding_cost: Math.round(propertyPrice * 0.0012), annual_total_holding_cost: Math.round(propertyPrice * 0.0012 * 12), income_burden_ratio: null, affordability_level: "unknown", affordability_message: "Offline reference only", cost_breakdown: [], disclaimer: COMPETITION_NOTICE, input: { property_price_wan: propertyPrice, loan_monthly_payment: 0, monthly_income_wan: null, area_ping: null, management_fee_per_ping: 0, repair_reserve_per_ping: 0, annual_home_tax_rate: 0.0012, annual_land_tax_rate: 0, annual_insurance: 0, include_tax_estimate: true } });
      } else {
        const [tax, holding] = await Promise.all([api.runTaxOracleCase(taxCase), api.holdingCostCalculate({ property_price: propertyPrice, loan_monthly_payment: 0, include_tax_estimate: true })]);
        setTaxResult(tax); setHoldingResult(holding);
      }
      setStep(4);
    } catch { setError("The calculation is temporarily unavailable. No result was inferred."); } finally { setLoading(false); }
  }

  function update(key: keyof TaxCase, value: boolean) { setTaxCase((current) => ({ ...current, [key]: value })); setTaxResult(null); setHoldingResult(null); setStep(1); }
  function reset() { setTaxCase(EXAMPLE); setPropertyPrice(2000); setTaxResult(null); setHoldingResult(null); setError(""); setStep(1); setOffline(false); }
  return <div className="space-y-5" data-testid="competition-demo"><PageHeader kicker={copy.eyebrow} title={copy.demoTitle} description={copy.demoDescription} />
    <Notice tone="warning">{copy.illustrative}. {copy.boundary}</Notice>
    <div className="grid grid-cols-4 gap-2" aria-label="Demo progress">{copy.steps.map((label, index) => <div key={label} className={`rounded-lg px-2 py-2 text-center text-[11px] font-bold ${step >= index + 1 ? "bg-cyan-100 text-cyan-900" : "bg-stone-100 text-slate-500"}`}><span className="block text-[10px]">{index + 1}</span>{label}</div>)}</div>
    {offline && <Notice>{copy.offline}</Notice>}
    {error && <ErrorState message={error} />}
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,390px)_minmax(0,1fr)]"><SectionCard title={copy.inputs} description={copy.demoDescription}><label className="block text-xs font-bold text-slate-600">Property price (ten-thousand NTD)<input data-testid="demo-property-price" type="number" min="1" value={propertyPrice} onChange={(event) => { setPropertyPrice(Number(event.target.value)); setTaxResult(null); setHoldingResult(null); setStep(1); }} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label><div className="mt-4 space-y-2">{(["sold_self_occupied", "residency_condition_met", "purchase_within_reasonable_period", "purchased_self_occupied", "same_owner", "land_value_available", "required_docs_complete", "enters_five_year_monitoring", "exceptional_circumstances"] as const).map((key) => <label key={key} className="flex items-center gap-2 rounded-lg border border-stone-200 px-3 py-2 text-xs text-slate-700"><input data-testid={`demo-${key}`} type="checkbox" checked={key === "exceptional_circumstances" ? !taxCase[key] : taxCase[key]} onChange={(event) => update(key, key === "exceptional_circumstances" ? !event.target.checked : event.target.checked)} />{key}</label>)}</div><div className="mt-4 flex flex-wrap gap-2"><Button disabled={loading} onClick={calculate}>{loading ? copy.calculating : copy.calculate}</Button><Button secondary onClick={reset}>{copy.reset}</Button></div><button type="button" className="mt-3 text-xs font-bold text-cyan-800 underline" onClick={() => setOffline((value) => !value)}>{offline ? copy.live : copy.switchOffline}</button></SectionCard>
      <SectionCard title={copy.output}><div className="grid gap-3 sm:grid-cols-2">{taxResult && <div className="rounded-xl bg-stone-50 p-4"><p className="text-xs font-bold text-slate-500">TaxOracle</p><p className="mt-2 text-xl font-black text-slate-950">{taxResult.eligibility_status}</p><p className="mt-1 text-sm text-slate-600">Risk score: {taxResult.risk_score}</p><p className="mt-2 text-xs text-slate-500">{copy.changed}</p></div>}{holdingResult && <div className="rounded-xl bg-stone-50 p-4"><p className="text-xs font-bold text-slate-500">Holding Cost</p><p className="mt-2 text-xl font-black text-slate-950">{holdingResult.monthly_total_holding_cost}</p><p className="mt-1 text-sm text-slate-600">{copy.changed}</p></div>}</div>{!taxResult && !holdingResult && <p className="rounded-xl border border-dashed border-stone-300 p-5 text-sm text-slate-500">{copy.incomplete}</p>}{(taxResult || holdingResult) && <div className="mt-4 space-y-3 text-xs leading-5 text-slate-600"><p><strong>{copy.inputs}:</strong> {Object.entries(taxCase).filter(([key]) => key !== "client_name").map(([key, value]) => `${key}=${String(value)}`).join(", ")}; property_price={propertyPrice}</p><p><strong>{copy.missing}:</strong> {missing.length ? missing.join(", ") : "none reported"}</p><p><strong>{copy.source}:</strong> {offline ? "local demo model / not official" : String(source?.source_status ?? "source status unavailable")}; rule version: {String(taxResult?.official_rule_trace?.rule_version ?? "preliminary-screening-v1")}</p><p>{taxResult?.disclaimer ?? holdingResult?.disclaimer ?? COMPETITION_NOTICE}</p><div className="flex flex-wrap gap-2"><Button secondary onClick={() => window.print()}>{copy.print}</Button><Button secondary onClick={onEvidence}>{copy.evidence}</Button><Button secondary onClick={onPrivacy}>{copy.privacy}</Button><Button secondary onClick={onTerms}>{copy.terms}</Button></div><div className="hidden print:block" data-testid="competition-print-report"><h1 className="text-2xl font-bold">TaxOracle and Holding Cost summary</h1><p>Illustrative example; preliminary reference only.</p><h2 className="mt-4 font-bold">Property facts</h2><p>{Object.entries(taxCase).filter(([key]) => key !== "client_name").map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}</p><p>Property price: {propertyPrice}</p><h2 className="mt-4 font-bold">TaxOracle</h2><p>{taxResult?.eligibility_status ?? "not calculated"}; risk score: {taxResult?.risk_score ?? "not available"}; rule version: {String(taxResult?.official_rule_trace?.rule_version ?? "preliminary-screening-v1")}</p><h2 className="mt-4 font-bold">Holding Cost</h2><p>Monthly total: {holdingResult?.monthly_total_holding_cost ?? "not available"}</p><h2 className="mt-4 font-bold">Evidence and limitations</h2><p>Source status: {offline ? "offline demo / not official" : String(source?.source_status ?? "unknown")}. Missing facts: {missing.length ? missing.join(", ") : "none reported"}. {COMPETITION_NOTICE}</p></div></div>}</SectionCard></div>
    </div>;
}
