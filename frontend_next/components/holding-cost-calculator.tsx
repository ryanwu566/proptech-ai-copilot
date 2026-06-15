"use client";

import { useEffect, useState } from "react";
import { api, HoldingCostResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";


export type HoldingCostPrefill = {
  property_price: number;
  loan_monthly_payment?: number;
  monthly_income?: number | null;
  area_ping?: number | null;
};

export const HOLDING_COST_PREFILL_EVENT = "proptech:holding-cost-prefill";
export const HOLDING_COST_SESSION_KEY = "proptech:holding-cost-result";
export const HOLDING_COST_RESULT_EVENT = "proptech:holding-cost-result-ready";

export function HoldingCostCalculator({ prefill, onResult }: { prefill?: HoldingCostPrefill; onResult?: (result: HoldingCostResult) => void }) {
  const [propertyPrice, setPropertyPrice] = useState(prefill?.property_price ?? 2000);
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
        property_price: propertyPrice,
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
    } catch (caught) {
      setError((caught as Error).message);
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
        <Button className="w-full" disabled={loading || propertyPrice <= 0} onClick={calculate}>{loading ? "試算中..." : "計算每月持有成本"}</Button>
        {propertyPrice <= 0 && <p className="text-[10px] leading-5 text-amber-700">請先完成貸款帶入，或輸入有效房屋總價與月付。</p>}
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
  const levels: Record<string, string> = { comfortable: "舒適", manageable: "可管理", tight: "偏緊", risky: "風險偏高", unknown: "未評估" };
  return <div className="min-w-0 space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <MetricTile label="每月總持有成本" value={`${result.monthly_total_holding_cost.toLocaleString()} 元`} />
      <MetricTile label="年持有成本" value={`${result.annual_total_holding_cost.toLocaleString()} 元`} />
      <MetricTile label="月收入負擔率" value={result.income_burden_ratio === null ? "未輸入收入" : `${(result.income_burden_ratio * 100).toFixed(1)}%`} note={levels[result.affordability_level]} />
    </div>
    <Notice>{result.affordability_message}</Notice>
    <div>
      <p className="mb-2 text-xs font-bold text-slate-800">每月成本 breakdown</p>
      <p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">表格可左右滑動</p>
      <div className="max-w-full touch-pan-x overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">項目</th><th>每月金額</th><th>占總成本</th></tr></thead><tbody>{result.cost_breakdown.map((item) => <tr key={item.key} className="border-t border-stone-100"><td className="p-2">{item.label}</td><td>{item.monthly_amount.toLocaleString()} 元</td><td>{result.monthly_total_holding_cost ? `${(item.monthly_amount / result.monthly_total_holding_cost * 100).toFixed(1)}%` : "0%"}</td></tr>)}</tbody></table>
      </div>
    </div>
    <div className="grid gap-3 sm:grid-cols-2"><MetricTile label="房屋稅簡化估算／年" value={`${result.annual_home_tax_estimate.toLocaleString()} 元`} /><MetricTile label="地價稅簡化估算／年" value={`${result.annual_land_tax_estimate.toLocaleString()} 元`} /></div>
    <p className="text-[10px] leading-5 text-amber-700">{result.disclaimer}</p>
  </div>;
}

function CostField({ label, value, onChange, min, step }: { label: string; value: number; onChange: (value: number) => void; min: number; step?: number }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min={min} step={step} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>;
}

function OptionalCostField({ label, value, onChange }: { label: string; value: number | ""; onChange: (value: number | "") => void }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min="0" onChange={(event) => onChange(event.target.value === "" ? "" : Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>;
}
