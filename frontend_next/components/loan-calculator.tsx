"use client";

import { useEffect, useState } from "react";
import { HoldingCostCalculator, HoldingCostPrefill } from "@/components/holding-cost-calculator";
import { LocationInsight } from "@/components/location-insight";
import { api, LoanCalculationResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";
import { GUIDED_DEMO_RESULT_EVENT, type DemoResults } from "@/lib/demo-runner";
import { DetailDisclosure } from "@/components/detail-disclosure";


export function LoanCalculator({
  propertyPriceWan,
  initialResult,
  onResult,
  onHoldingCost,
}: {
  propertyPriceWan?: number;
  initialResult?: LoanCalculationResult;
  onResult?: (result: LoanCalculationResult) => void;
  onHoldingCost?: (result: LoanCalculationResult) => void;
}) {
  const [propertyPrice, setPropertyPrice] = useState(propertyPriceWan ?? 2000);
  const [downPaymentRatio, setDownPaymentRatio] = useState(0.2);
  const [annualInterestRate, setAnnualInterestRate] = useState(2.2);
  const [loanYears, setLoanYears] = useState(30);
  const [gracePeriodYears, setGracePeriodYears] = useState(0);
  const [monthlyIncome, setMonthlyIncome] = useState<number | "">("");
  const [result, setResult] = useState<LoanCalculationResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [holdingPrefill, setHoldingPrefill] = useState<HoldingCostPrefill>(propertyPriceWan ? { property_price: propertyPriceWan } : { property_price: 2000 });

  useEffect(() => {
    if (propertyPriceWan && propertyPriceWan > 0) {
      setPropertyPrice(propertyPriceWan);
      setHoldingPrefill({ property_price: propertyPriceWan });
      setResult(undefined);
    }
  }, [propertyPriceWan]);

  useEffect(() => {
    if (initialResult) setResult(initialResult);
  }, [initialResult]);

  useEffect(() => {
    function applyDemoResult(event: Event) {
      const next = (event as CustomEvent<DemoResults>).detail.loan;
      if (next) {
        setPropertyPrice(next.property_price_wan);
        setResult(next);
      }
    }
    window.addEventListener(GUIDED_DEMO_RESULT_EVENT, applyDemoResult);
    return () => window.removeEventListener(GUIDED_DEMO_RESULT_EVENT, applyDemoResult);
  }, []);

  async function calculate() {
    setLoading(true);
    setError("");
    try {
      const next = await api.loanCalculate({
        property_price: propertyPrice,
        down_payment_ratio: downPaymentRatio,
        annual_interest_rate: annualInterestRate,
        loan_years: loanYears,
        grace_period_years: gracePeriodYears,
        monthly_income: monthlyIncome === "" ? undefined : monthlyIncome,
        include_sensitivity: true,
      });
      setResult(next);
      onResult?.(next);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function sendToHoldingCost(loan: LoanCalculationResult) {
    setHoldingPrefill({ property_price: loan.property_price_wan, loan_monthly_payment: loan.monthly_payment, monthly_income: loan.monthly_income_wan });
    onHoldingCost?.(loan);
  }

  return <div id="loan-calculator" className="min-w-0 scroll-mt-20 space-y-5"><span id="loan" className="block scroll-mt-20" aria-hidden="true" /><SectionCard title="貸款月付試算" description="用透明公式估算頭期款、月付、總利息與利率變動影響；帶入總價後不會自動送出。">
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="grid min-w-0 gap-3">
        <LoanNumberField label="房屋總價（萬元）" value={propertyPrice} onChange={setPropertyPrice} min={0.01} />
        <LoanNumberField label="頭期款比例" value={downPaymentRatio} onChange={setDownPaymentRatio} min={0} max={1} step={0.05} />
        <LoanNumberField label="年利率（%）" value={annualInterestRate} onChange={setAnnualInterestRate} min={0} step={0.1} />
        <LoanNumberField label="貸款年限（年）" value={loanYears} onChange={setLoanYears} min={1} step={1} />
        <LoanNumberField label="寬限期年數" value={gracePeriodYears} onChange={setGracePeriodYears} min={0} step={1} />
        <label className="text-xs text-slate-500">月收入（萬元，可選）
          <input type="number" min="0.01" step="0.1" value={monthlyIncome} onChange={(event) => setMonthlyIncome(event.target.value === "" ? "" : Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" />
        </label>
        <Button className="w-full" disabled={loading || propertyPrice <= 0 || loanYears <= 0 || gracePeriodYears >= loanYears} onClick={calculate}>{loading ? "試算中..." : "計算貸款月付"}</Button>
        {(propertyPrice <= 0 || loanYears <= 0 || gracePeriodYears >= loanYears) && <p className="text-[10px] leading-5 text-amber-700">請先輸入有效總價與貸款年限；寬限期必須小於貸款年限。</p>}
        {error && <ErrorState message={error} />}
      </div>
      <div className="min-w-0">
        {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500">請先輸入總價、利率與貸款年限，再計算月付、總利息與負擔率。</div> : <LoanResults result={result} onHoldingCost={sendToHoldingCost} />}
      </div>
    </div>
  </SectionCard>{!onHoldingCost && <HoldingCostCalculator prefill={holdingPrefill}/>}<LocationInsight /></div>;
}

function LoanResults({ result, onHoldingCost }: { result: LoanCalculationResult; onHoldingCost?: (result: LoanCalculationResult) => void }) {
  const levelLabels: Record<string, string> = { comfortable: "舒適", manageable: "可管理", tight: "偏緊", risky: "風險偏高", unknown: "未評估" };
  return <div className="min-w-0 space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <MetricTile label="頭期款" value={`${result.down_payment_wan.toLocaleString()} 萬`} />
      <MetricTile label="貸款金額" value={`${result.loan_amount_wan.toLocaleString()} 萬`} />
      <MetricTile label="每月月付" value={`${result.monthly_payment.toLocaleString()} 元`} note={result.grace_period_years ? "寬限期後本息月付" : undefined} />
      <MetricTile label="總還款" value={`${result.total_payment.toLocaleString()} 元`} />
      <MetricTile label="總利息" value={`${result.total_interest.toLocaleString()} 元`} />
      <MetricTile label="月收入負擔率" value={result.income_burden_ratio === null ? "未輸入收入" : `${(result.income_burden_ratio * 100).toFixed(1)}%`} note={levelLabels[result.affordability_level]} />
    </div>
    {result.grace_period_years > 0 && <div className="grid gap-3 sm:grid-cols-2"><MetricTile label="寬限期內月付" value={`${(result.grace_period_monthly_payment ?? 0).toLocaleString()} 元`} note="僅繳利息" /><MetricTile label="寬限期後月付" value={`${(result.post_grace_monthly_payment ?? 0).toLocaleString()} 元`} note="剩餘期間本息攤還" /></div>}
    <Notice>{result.affordability_message}</Notice>
    {onHoldingCost && <Button secondary className="w-full sm:w-auto" onClick={() => onHoldingCost(result)}>帶入持有成本</Button>}
    <DetailDisclosure title="查看利率敏感度詳細表">
      <p className="mb-2 text-xs font-bold text-slate-800">利率敏感度</p>
      <p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">表格可左右滑動</p>
      <div className="max-w-full touch-pan-x overflow-x-auto">
        <table className="w-full min-w-[620px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">年利率</th><th>月付</th><th>總利息</th><th>相對基準月付差</th></tr></thead><tbody>{result.sensitivity.map((item) => <tr key={item.annual_interest_rate} className="border-t border-stone-100"><td className="p-2">{item.annual_interest_rate.toFixed(2)}%</td><td>{item.monthly_payment.toLocaleString()} 元</td><td>{item.total_interest.toLocaleString()} 元</td><td>{formatDifference(item.difference_from_base)}</td></tr>)}</tbody></table>
      </div>
    </DetailDisclosure>
    <p className="text-[10px] leading-5 text-amber-700">{result.disclaimer}</p>
  </div>;
}

function LoanNumberField({ label, value, onChange, min, max, step }: { label: string; value: number; onChange: (value: number) => void; min: number; max?: number; step?: number }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>;
}

function formatDifference(value: number): string {
  if (value === 0) return "基準";
  return `${value > 0 ? "+" : ""}${value.toLocaleString()} 元`;
}
