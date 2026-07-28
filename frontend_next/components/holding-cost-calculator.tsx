"use client";

import { useEffect, useState } from "react";
import { api, HoldingCostResult } from "@/lib/api";
import { Button } from "@/components/ui";
import { ErrorState, SectionCard } from "@/components/product-ui";
import { buildHoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import { HoldingCostVisualPanel } from "@/components/data-visualization/holding-cost-visual-panel";


export type HoldingCostPrefill = {
  property_price: number;
  loan_monthly_payment?: number;
  monthly_income?: number | null;
  area_ping?: number | null;
};

export const HOLDING_COST_PREFILL_EVENT = "proptech:holding-cost-prefill";
export const HOLDING_COST_SESSION_KEY = "proptech:holding-cost-result";
export const HOLDING_COST_RESULT_EVENT = "proptech:holding-cost-result-ready";

export function HoldingCostCalculator({ prefill, onResult, embedded = false }: { prefill?: HoldingCostPrefill; onResult?: (result: HoldingCostResult) => void; embedded?: boolean }) {
  const [propertyPrice, setPropertyPrice] = useState<number | "">(prefill?.property_price ?? (embedded ? "" : 2000));
  const [loanMonthlyPayment, setLoanMonthlyPayment] = useState(prefill?.loan_monthly_payment ?? 0);
  const [monthlyIncome, setMonthlyIncome] = useState<number | "">(prefill?.monthly_income ?? "");
  const [areaPing, setAreaPing] = useState<number | "">(prefill?.area_ping ?? "");
  const [managementFee, setManagementFee] = useState(80);
  const [repairReserve, setRepairReserve] = useState(50);
  const [homeTaxRate, setHomeTaxRate] = useState(0.0012);
  const [landTaxRate, setLandTaxRate] = useState(0.001);
  const [annualInsurance, setAnnualInsurance] = useState(3000);
  const [result, setResult] = useState<HoldingCostResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!prefill) return;
    setPropertyPrice(prefill.property_price);
    setLoanMonthlyPayment(prefill.loan_monthly_payment ?? 0);
    setMonthlyIncome(prefill.monthly_income ?? "");
    setAreaPing(prefill.area_ping ?? "");
    setResult(undefined);
    window.sessionStorage.removeItem(HOLDING_COST_SESSION_KEY);
  }, [prefill]);

  useEffect(() => {
    function applyEvent(event: Event) {
      const detail = (event as CustomEvent<HoldingCostPrefill>).detail;
      if (!detail?.property_price) return;
      setPropertyPrice(detail.property_price);
      setLoanMonthlyPayment(detail.loan_monthly_payment ?? 0);
      setMonthlyIncome(detail.monthly_income ?? "");
      setAreaPing(detail.area_ping ?? "");
      setResult(undefined);
      window.sessionStorage.removeItem(HOLDING_COST_SESSION_KEY);
    }
    window.addEventListener(HOLDING_COST_PREFILL_EVENT, applyEvent);
    return () => window.removeEventListener(HOLDING_COST_PREFILL_EVENT, applyEvent);
  }, []);

  useEffect(() => {
    function applyResult(event: Event) {
      setResult((event as CustomEvent<HoldingCostResult>).detail);
    }
    window.addEventListener(HOLDING_COST_RESULT_EVENT, applyResult);
    return () => window.removeEventListener(HOLDING_COST_RESULT_EVENT, applyResult);
  }, []);

  async function calculate() {
    setLoading(true);
    setError("");
    try {
      const next = await api.holdingCostCalculate({
        property_price: propertyPrice === "" ? 0 : propertyPrice,
        loan_monthly_payment: loanMonthlyPayment,
        monthly_income: monthlyIncome === "" ? undefined : monthlyIncome,
        area_ping: areaPing === "" ? undefined : areaPing,
        management_fee_per_ping: managementFee,
        repair_reserve_per_ping: repairReserve,
        annual_home_tax_rate: homeTaxRate,
        annual_land_tax_rate: landTaxRate,
        annual_insurance: annualInsurance,
        include_tax_estimate: true,
      });
      setResult(next);
      window.sessionStorage.setItem(HOLDING_COST_SESSION_KEY, JSON.stringify(next));
      window.dispatchEvent(new CustomEvent<HoldingCostResult>(HOLDING_COST_RESULT_EVENT, { detail: next }));
      onResult?.(next);
    } catch {
      setError("持有成本試算暫時無法完成，請稍後再試。" );
    } finally {
      setLoading(false);
    }
  }

  return <div id="holding-cost-calculator" className="scroll-mt-20"><span id="holding-cost" className="block scroll-mt-20" aria-hidden="true" /><SectionCard title="每月持有成本" description="把房貸、管理費、修繕、簡化稅費與保險合併成買房後的每月成本壓力估算。">
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="grid min-w-0 gap-3">
        <CostField label="房屋總價（萬元）" value={propertyPrice} onChange={setPropertyPrice} min={0.01} />
        <CostField label="房貸月付（元／月）" value={loanMonthlyPayment} onChange={setLoanMonthlyPayment} min={0} />
        <OptionalCostField label="月收入（萬元／月，可選）" value={monthlyIncome} onChange={setMonthlyIncome} />
        <OptionalCostField label="坪數（可選）" value={areaPing} onChange={setAreaPing} />
        <CostField label="管理費（元／坪／月）" value={managementFee} onChange={setManagementFee} min={0} />
        <CostField label="修繕預備金（元／坪／月）" value={repairReserve} onChange={setRepairReserve} min={0} />
        <CostField label="房屋稅簡化估算率" value={homeTaxRate} onChange={setHomeTaxRate} min={0} step={0.0001} />
        <CostField label="地價稅簡化估算率" value={landTaxRate} onChange={setLandTaxRate} min={0} step={0.0001} />
        <CostField label="年保險費（元）" value={annualInsurance} onChange={setAnnualInsurance} min={0} />
        <Button className="w-full" disabled={loading || propertyPrice === "" || propertyPrice <= 0} onClick={calculate}>{loading ? "試算中..." : "計算每月持有成本"}</Button>
        {(propertyPrice === "" || propertyPrice <= 0) && <p className="text-[10px] leading-5 text-amber-700">請先完成貸款帶入，或輸入有效房屋總價與月付。</p>}
        {error && <ErrorState message={error} />}
      </div>
      <div className="min-w-0">
        {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500">請先完成貸款或輸入月付，再確認管理費、稅費與修繕假設。</div> : <HoldingCostResults result={result} />}
      </div>
    </div>
  </SectionCard></div>;
}

export function prefillHoldingCost(prefill: HoldingCostPrefill) {
  window.dispatchEvent(new CustomEvent<HoldingCostPrefill>(HOLDING_COST_PREFILL_EVENT, { detail: prefill }));
}

function HoldingCostResults({ result }: { result: HoldingCostResult }) {
  return <HoldingCostVisualPanel model={buildHoldingCostVisualModel(result)} result={result} />;
}

function CostField({ label, value, onChange, min, step }: { label: string; value: number | ""; onChange: (value: number) => void; min: number; step?: number }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min={min} step={step} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>;
}

function OptionalCostField({ label, value, onChange }: { label: string; value: number | ""; onChange: (value: number | "") => void }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min="0" onChange={(event) => onChange(event.target.value === "" ? "" : Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>;
}
