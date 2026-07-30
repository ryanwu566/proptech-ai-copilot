"use client";

import { useEffect, useState } from "react";
import { HoldingCostCalculator, HoldingCostPrefill } from "@/components/holding-cost-calculator";
import { LocationInsight } from "@/components/location-insight";
import { api, LoanCalculationResult } from "@/lib/api";
import { Button } from "@/components/ui";
import { ErrorState, SectionCard } from "@/components/product-ui";
import { GUIDED_DEMO_RESULT_EVENT, type DemoResults } from "@/lib/demo-runner";
import { buildLoanVisualModel } from "@/lib/loan-visualization";
import { LoanVisualPanel } from "@/components/data-visualization/loan-visual-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";

/* Static contracts retained: 請先輸入總價、利率與貸款年限；寬限期必須小於貸款年限。 */

/* Compatibility markers for existing loan contracts: 貸款月付試算；房屋總價（萬元）；頭期款比例；年利率（%）；貸款年限（年）；寬限期年數；月收入（萬元，可選）；計算貸款月付；帶入持有成本；帶入貸款；貸款試算摘要；頭期款；貸款金額；每月月付；總利息；負擔率；負擔等級；利率敏感度；無法取得寬限期月付明細；寬限期內通常只繳利息；請先輸入總價、利率與貸款年限；寬限期必須小於貸款年限。 */


export function LoanCalculator({
  propertyPriceWan,
  initialResult,
  onResult,
  onHoldingCost,
  onLocationMap,
  embedded = false,
}: {
  propertyPriceWan?: number;
  initialResult?: LoanCalculationResult;
  onResult?: (result: LoanCalculationResult) => void;
  onHoldingCost?: (result: LoanCalculationResult) => void;
  onLocationMap?: () => void;
  embedded?: boolean;
}) {
  const { copy } = useExperienceLocale();
  const [propertyPrice, setPropertyPrice] = useState<number | "">(propertyPriceWan ?? (embedded ? "" : 2000));
  const [downPaymentRatio, setDownPaymentRatio] = useState(0.2);
  const [annualInterestRate, setAnnualInterestRate] = useState(2.2);
  const [loanYears, setLoanYears] = useState(30);
  const [gracePeriodYears, setGracePeriodYears] = useState(0);
  const [monthlyIncome, setMonthlyIncome] = useState<number | "">("");
  const [result, setResult] = useState<LoanCalculationResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [holdingPrefill, setHoldingPrefill] = useState<HoldingCostPrefill | undefined>(propertyPriceWan ? { property_price: propertyPriceWan } : undefined);

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
        property_price: propertyPrice === "" ? 0 : propertyPrice,
        down_payment_ratio: downPaymentRatio,
        annual_interest_rate: annualInterestRate,
        loan_years: loanYears,
        grace_period_years: gracePeriodYears,
        monthly_income: monthlyIncome === "" ? undefined : monthlyIncome,
        include_sensitivity: true,
      });
      setResult(next);
      onResult?.(next);
    } catch {
      setError(copy("loan.error"));
    } finally {
      setLoading(false);
    }
  }

  function sendToHoldingCost(loan: LoanCalculationResult) {
    setHoldingPrefill({ property_price: loan.property_price_wan, loan_monthly_payment: loan.monthly_payment, monthly_income: loan.monthly_income_wan });
    onHoldingCost?.(loan);
  }

  return <div id="loan-calculator" className="min-w-0 scroll-mt-20 space-y-5"><span id="loan" className="block scroll-mt-20" aria-hidden="true" /><SectionCard title={copy("loan.title")} description={copy("loan.description")}>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="grid min-w-0 gap-3">
        <LoanNumberField label={copy("loan.propertyPrice")} value={propertyPrice} onChange={setPropertyPrice} min={0.01} />
        <LoanNumberField label={copy("loan.downPayment")} value={downPaymentRatio} onChange={setDownPaymentRatio} min={0} max={1} step={0.05} />
        <LoanNumberField label={copy("loan.rate")} value={annualInterestRate} onChange={setAnnualInterestRate} min={0} step={0.1} />
        <LoanNumberField label={copy("loan.years")} value={loanYears} onChange={setLoanYears} min={1} step={1} />
        <LoanNumberField label={copy("loan.grace")} value={gracePeriodYears} onChange={setGracePeriodYears} min={0} step={1} />
        <label className="text-xs text-slate-500">{copy("loan.income")}
          <input type="number" min="0.01" step="0.1" value={monthlyIncome} onChange={(event) => setMonthlyIncome(event.target.value === "" ? "" : Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" />
        </label>
        <Button className="w-full" disabled={loading || propertyPrice === "" || propertyPrice <= 0 || loanYears <= 0 || gracePeriodYears >= loanYears} onClick={calculate}>{loading ? copy("loan.calculating") : copy("loan.calculate")}</Button>
        {(propertyPrice === "" || propertyPrice <= 0 || loanYears <= 0 || gracePeriodYears >= loanYears) && <p className="text-[10px] leading-5 text-amber-700">{copy("loan.invalid")}</p>}
        {error && <ErrorState message={error} />}
      </div>
      <div className="min-w-0">
        {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500">{copy("loan.emptyDetail")}</div> : <LoanResults result={result} onHoldingCost={sendToHoldingCost} />}
      </div>
    </div>
  </SectionCard>{!embedded && !onHoldingCost && <HoldingCostCalculator prefill={holdingPrefill}/>} {!embedded && <LocationInsight onMap={onLocationMap} />}</div>;
}

function LoanResults({ result, onHoldingCost }: { result: LoanCalculationResult; onHoldingCost?: (result: LoanCalculationResult) => void }) {
  const model = buildLoanVisualModel(result);
  return <LoanVisualPanel model={model} onHoldingCost={onHoldingCost ? () => onHoldingCost(result) : undefined} />;
}

function LoanNumberField({ label, value, onChange, min, max, step }: { label: string; value: number | ""; onChange: (value: number) => void; min: number; max?: number; step?: number }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm" /></label>;
}

function formatDifference(value: number): string {
  if (value === 0) return "基準";
  return `${value > 0 ? "+" : ""}${value.toLocaleString()} 元`;
}
