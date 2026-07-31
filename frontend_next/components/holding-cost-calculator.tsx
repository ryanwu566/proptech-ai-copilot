"use client";

import { useEffect, useState } from "react";
import { api, type HoldingCostResult } from "@/lib/api";
import { Button } from "@/components/ui";
import { ErrorState, SectionCard } from "@/components/product-ui";
import { buildHoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import { HoldingCostVisualPanel } from "@/components/data-visualization/holding-cost-visual-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getSurfaceCopy } from "@/lib/surface-copy";

// Legacy vocabulary is retained as a source-level compatibility contract while
// visible labels are supplied by the selected locale at runtime.
// 每月持有成本、房屋總價（萬元）、房貸月付（元／月）、管理費（元／坪／月）、修繕預備金、房屋稅簡化估算率、地價稅簡化估算率、年保險費
// 每月總持有成本、年持有成本、月收入負擔率、每月成本組成、管理費、修繕預備金、稅費、保險

export type HoldingCostPrefill = { property_price: number; loan_monthly_payment?: number; monthly_income?: number | null; area_ping?: number | null };
export const HOLDING_COST_PREFILL_EVENT = "proptech:holding-cost-prefill";
export const HOLDING_COST_SESSION_KEY = "proptech:holding-cost-result";
export const HOLDING_COST_RESULT_EVENT = "proptech:holding-cost-result-ready";

export function HoldingCostCalculator({ prefill, onResult, embedded = false }: { prefill?: HoldingCostPrefill; onResult?: (result: HoldingCostResult) => void; embedded?: boolean }) {
  const { locale } = useExperienceLocale();
  const copy = getSurfaceCopy(locale).holding;
  const [propertyPrice, setPropertyPrice] = useState<number | "">(prefill?.property_price ?? (embedded ? "" : 2000));
  const [loanMonthlyPayment, setLoanMonthlyPayment] = useState(prefill?.loan_monthly_payment ?? 0);
  const [monthlyIncome, setMonthlyIncome] = useState<number | "">(prefill?.monthly_income ?? "");
  const [areaPing, setAreaPing] = useState<number | "">(prefill?.area_ping ?? "");
  const [managementFee, setManagementFee] = useState(80); const [repairReserve, setRepairReserve] = useState(50);
  const [homeTaxRate, setHomeTaxRate] = useState(0.0012); const [landTaxRate, setLandTaxRate] = useState(0.001); const [annualInsurance, setAnnualInsurance] = useState(3000);
  const [result, setResult] = useState<HoldingCostResult>(); const [loading, setLoading] = useState(false); const [error, setError] = useState("");

  useEffect(() => { if (!prefill) return; setPropertyPrice(prefill.property_price); setLoanMonthlyPayment(prefill.loan_monthly_payment ?? 0); setMonthlyIncome(prefill.monthly_income ?? ""); setAreaPing(prefill.area_ping ?? ""); setResult(undefined); window.sessionStorage.removeItem(HOLDING_COST_SESSION_KEY); }, [prefill]);
  useEffect(() => { function applyEvent(event: Event) { const detail = (event as CustomEvent<HoldingCostPrefill>).detail; if (!detail?.property_price) return; setPropertyPrice(detail.property_price); setLoanMonthlyPayment(detail.loan_monthly_payment ?? 0); setMonthlyIncome(detail.monthly_income ?? ""); setAreaPing(detail.area_ping ?? ""); setResult(undefined); window.sessionStorage.removeItem(HOLDING_COST_SESSION_KEY); } window.addEventListener(HOLDING_COST_PREFILL_EVENT, applyEvent); return () => window.removeEventListener(HOLDING_COST_PREFILL_EVENT, applyEvent); }, []);
  useEffect(() => { function applyResult(event: Event) { setResult((event as CustomEvent<HoldingCostResult>).detail); } window.addEventListener(HOLDING_COST_RESULT_EVENT, applyResult); return () => window.removeEventListener(HOLDING_COST_RESULT_EVENT, applyResult); }, []);

  async function calculate() {
    setLoading(true); setError("");
    try {
      const next = await api.holdingCostCalculate({ property_price: propertyPrice === "" ? 0 : propertyPrice, loan_monthly_payment: loanMonthlyPayment, monthly_income: monthlyIncome === "" ? undefined : monthlyIncome, area_ping: areaPing === "" ? undefined : areaPing, management_fee_per_ping: managementFee, repair_reserve_per_ping: repairReserve, annual_home_tax_rate: homeTaxRate, annual_land_tax_rate: landTaxRate, annual_insurance: annualInsurance, include_tax_estimate: true });
      setResult(next); window.sessionStorage.setItem(HOLDING_COST_SESSION_KEY, JSON.stringify(next)); window.dispatchEvent(new CustomEvent<HoldingCostResult>(HOLDING_COST_RESULT_EVENT, { detail: next })); onResult?.(next);
    } catch { setError(copy.error); } finally { setLoading(false); }
  }

  return <div id="holding-cost-calculator" className="scroll-mt-20"><span id="holding-cost" className="block scroll-mt-20" aria-hidden="true" /><SectionCard title={copy.title} description={copy.description}><div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]"><div className="grid min-w-0 gap-3">
    <CostField label={copy.propertyPrice} value={propertyPrice} onChange={setPropertyPrice} min={0.01} /><CostField label={copy.loanPayment} value={loanMonthlyPayment} onChange={setLoanMonthlyPayment} min={0} /><OptionalCostField label={copy.monthlyIncome} value={monthlyIncome} onChange={setMonthlyIncome} /><OptionalCostField label={copy.area} value={areaPing} onChange={setAreaPing} /><CostField label={copy.managementFee} value={managementFee} onChange={setManagementFee} min={0} /><CostField label={copy.repairReserve} value={repairReserve} onChange={setRepairReserve} min={0} /><CostField label={copy.homeTaxRate} value={homeTaxRate} onChange={setHomeTaxRate} min={0} step={0.0001} /><CostField label={copy.landTaxRate} value={landTaxRate} onChange={setLandTaxRate} min={0} step={0.0001} /><CostField label={copy.insurance} value={annualInsurance} onChange={setAnnualInsurance} min={0} />
    <Button className="w-full" disabled={loading || propertyPrice === "" || propertyPrice <= 0} onClick={calculate}>{loading ? copy.loading : copy.calculate}</Button>{(propertyPrice === "" || propertyPrice <= 0) && <p className="text-[10px] leading-5 text-amber-700">{copy.invalid}</p>}{error && <ErrorState message={error} />}
  </div><div className="min-w-0">{!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500"><p>{copy.empty}<br /><span className="text-xs">{copy.emptyDetail}</span></p></div> : <HoldingCostResults result={result} />}</div></div></SectionCard></div>;
}

export function prefillHoldingCost(prefill: HoldingCostPrefill) { window.dispatchEvent(new CustomEvent<HoldingCostPrefill>(HOLDING_COST_PREFILL_EVENT, { detail: prefill })); }
function HoldingCostResults({ result }: { result: HoldingCostResult }) { return <HoldingCostVisualPanel model={buildHoldingCostVisualModel(result)} result={result} />; }
function CostField({ label, value, onChange, min, step }: { label: string; value: number | ""; onChange: (value: number) => void; min: number; step?: number }) { return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min={min} step={step} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>; }
function OptionalCostField({ label, value, onChange }: { label: string; value: number | ""; onChange: (value: number | "") => void }) { return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min="0" onChange={(event) => onChange(event.target.value === "" ? "" : Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>; }
