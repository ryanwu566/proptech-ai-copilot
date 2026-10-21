"use client";

import { useEffect, useRef, useState } from "react";
import type { HoldingCostResult, LoanCalculationResult } from "@/lib/api";
import { api } from "@/lib/api";
import { CommercialButton } from "@/components/design-system/button";
import { Field, UnitInput } from "@/components/design-system/field";
import { Message } from "@/components/design-system/message";
import { buildHoldingCostRequest, buildLoanRequest, validateHoldingAssumptions, validateLoanAssumptions, type HoldingAssumptions, type LoanAssumptions } from "@/lib/workspace/finance-calculation";
import type { FinanceModel } from "@/lib/workspace/finance-model";
import { holdingFormSeed, syncHoldingPayment } from "@/lib/workspace/money-workflow";
import { useMoneyCopy } from "./use-money-copy";

const requiredNumber = (value: string) => value === "" ? Number.NaN : Number(value);
const optionalNumber = (value: string) => value === "" ? null : Number(value);

export function LoanAssumptionForm({ propertyPriceWan, initial, onCalculated, onDirty }: {
  propertyPriceWan: number;
  initial?: FinanceModel["loan"] | null;
  onCalculated: (result: LoanCalculationResult) => void;
  onDirty: () => void;
}) {
  const { c } = useMoneyCopy();
  const saved = initial?.downPaymentRatio != null || initial?.annualInterestRate != null || initial?.loanYears != null;
  const text = (value: number | null | undefined, fallback: number) => saved ? value == null ? "" : String(value) : String(fallback);
  const [values, setValues] = useState(() => ({
    downPaymentRatioPercent: text(initial?.downPaymentRatio == null ? null : initial.downPaymentRatio * 100, 20),
    annualInterestRatePercent: text(initial?.annualInterestRate, 2.2), loanYears: text(initial?.loanYears, 30),
    gracePeriodYears: text(initial?.gracePeriodYears, 0), monthlyIncomeWan: initial?.monthlyIncomeWan == null ? "" : String(initial.monthlyIncomeWan),
  }));
  const [errors, setErrors] = useState<Partial<Record<keyof LoanAssumptions, string>>>({});
  const [requestError, setRequestError] = useState(false);
  const [loading, setLoading] = useState(false);
  const requestRef = useRef(0);
  const calculatedRef = useRef(onCalculated); calculatedRef.current = onCalculated;
  useEffect(() => () => { requestRef.current++; }, []);
  useEffect(() => { requestRef.current++; setLoading(false); setErrors({}); setRequestError(false); }, [propertyPriceWan]);
  function dirty(key: keyof typeof values, value: string) {
    requestRef.current++; setLoading(false); setRequestError(false);
    setValues(previous => ({ ...previous, [key]: value })); onDirty();
  }
  async function calculate() {
    const assumptions: LoanAssumptions = { propertyPriceWan, downPaymentRatioPercent: requiredNumber(values.downPaymentRatioPercent),
      annualInterestRatePercent: requiredNumber(values.annualInterestRatePercent), loanYears: requiredNumber(values.loanYears),
      gracePeriodYears: requiredNumber(values.gracePeriodYears), monthlyIncomeWan: optionalNumber(values.monthlyIncomeWan) };
    const nextErrors = validateLoanAssumptions(assumptions); setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    const requestId = ++requestRef.current; setLoading(true); setRequestError(false);
    try { const result = await api.loanCalculate(buildLoanRequest(assumptions)); if (requestId === requestRef.current) calculatedRef.current(result); }
    catch { if (requestId === requestRef.current) setRequestError(true); }
    finally { if (requestId === requestRef.current) setLoading(false); }
  }
  const fields = [
    ["downPaymentRatioPercent", "downRatio", "%", 0, 100, "1"],
    ["annualInterestRatePercent", "rate", "%", 0, undefined, "0.01"],
    ["loanYears", "years", c("yearUnit"), 1, undefined, "1"],
    ["gracePeriodYears", "grace", c("yearUnit"), 0, undefined, "1"],
    ["monthlyIncomeWan", "income", c("wanUnit"), 0.01, undefined, "0.01"],
  ] as const;
  return <form onSubmit={event => { event.preventDefault(); void calculate(); }} data-testid="loan-form" className="min-w-0">
    <fieldset className="grid min-w-0 gap-4 sm:grid-cols-2">
      <legend className="ds-visually-hidden">{c("loanAssumptions")}</legend>
      {fields.map(([key, label, unit, min, max, step]) => <Field key={key} label={c(label)} required={key !== "monthlyIncomeWan"}
        helperText={key === "monthlyIncomeWan" ? c("incomeHelp") : undefined} errorText={errors[key] ? c("invalid") : undefined}>
        <UnitInput type="number" min={min} max={max} step={step} value={values[key]} onChange={event => dirty(key, event.target.value)} suffix={unit} unitLabel={unit} />
      </Field>)}
    </fieldset>
    <div className="mt-5 flex flex-col items-start gap-3">
      <CommercialButton type="submit" loading={loading} loadingLabel={c("calculating")} data-testid="calculate-loan">{c("calculateLoan")}</CommercialButton>
      {requestError && <div data-testid="loan-error"><Message variant="error">{c("loanError")}</Message></div>}
    </div>
  </form>;
}

export function HoldingAssumptionForm({ propertyPriceWan, initialLoanPaymentTwd, loanPaymentRevision = 0, initialAreaPing, initial, onCalculated, onDirty }: {
  propertyPriceWan: number;
  initialLoanPaymentTwd: number | null;
  loanPaymentRevision?: number;
  initialAreaPing: number | null;
  initial?: FinanceModel["holding"]["assumptions"] | null;
  onCalculated: (result: HoldingCostResult, areaPing: number | null) => void;
  onDirty: () => void;
}) {
  const { c } = useMoneyCopy();
  const [values, setValues] = useState(() => ({ ...holdingFormSeed(initial, initialLoanPaymentTwd, initialAreaPing), paymentIsAutomatic: initialLoanPaymentTwd !== null }));
  const [errors, setErrors] = useState<Partial<Record<keyof HoldingAssumptions, string>>>({});
  const [requestError, setRequestError] = useState(false);
  const [loading, setLoading] = useState(false);
  const requestRef = useRef(0);
  const calculatedRef = useRef(onCalculated); calculatedRef.current = onCalculated;
  useEffect(() => () => { requestRef.current++; }, []);
  useEffect(() => { requestRef.current++; setLoading(false); setErrors({}); setRequestError(false); }, [propertyPriceWan]);
  useEffect(() => {
    requestRef.current++; setLoading(false); setRequestError(false);
    setValues(previous => {
      const next = syncHoldingPayment(previous.loanMonthlyPaymentWan, previous.paymentIsAutomatic, initialLoanPaymentTwd);
      return { ...previous, loanMonthlyPaymentWan: next.value, paymentIsAutomatic: next.automatic };
    });
  }, [initialLoanPaymentTwd, loanPaymentRevision]);
  function dirty(key: keyof ReturnType<typeof holdingFormSeed>, value: string) {
    requestRef.current++; setLoading(false); setRequestError(false);
    setValues(previous => ({ ...previous, [key]: value, ...(key === "loanMonthlyPaymentWan" ? { paymentIsAutomatic: false } : {}) })); onDirty();
  }
  async function calculate() {
    const assumptions: HoldingAssumptions = { propertyPriceWan, loanMonthlyPaymentWan: requiredNumber(values.loanMonthlyPaymentWan),
      monthlyIncomeWan: optionalNumber(values.monthlyIncomeWan), areaPing: optionalNumber(values.areaPing),
      managementFeePerPingTwd: requiredNumber(values.managementFeePerPingTwd), repairReservePerPingTwd: requiredNumber(values.repairReservePerPingTwd),
      annualHomeTaxRatePercent: requiredNumber(values.annualHomeTaxRatePercent), annualLandTaxRatePercent: requiredNumber(values.annualLandTaxRatePercent), annualInsuranceTwd: requiredNumber(values.annualInsuranceTwd) };
    const nextErrors = validateHoldingAssumptions(assumptions); setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    const requestId = ++requestRef.current; setLoading(true); setRequestError(false);
    try { const result = await api.holdingCostCalculate(buildHoldingCostRequest(assumptions)); if (requestId === requestRef.current) calculatedRef.current(result, assumptions.areaPing); }
    catch { if (requestId === requestRef.current) setRequestError(true); }
    finally { if (requestId === requestRef.current) setLoading(false); }
  }
  const perPingMonth = `${c("ping")}${c("perMonth")}`;
  const fields = [
    ["loanMonthlyPaymentWan", "payment", `${c("wanUnit")}${c("perMonth")}`, "0.0001", true, "paymentHelp"],
    ["areaPing", "area", c("ping"), "0.1", false, "areaHelp"],
    ["monthlyIncomeWan", "income", c("wanUnit"), "0.01", false, "incomeHelp"],
    ["managementFeePerPingTwd", "managementRate", `TWD / ${perPingMonth}`, "1", true, null],
    ["repairReservePerPingTwd", "repairRate", `TWD / ${perPingMonth}`, "1", true, null],
    ["annualHomeTaxRatePercent", "homeTax", "%", "0.01", true, null],
    ["annualLandTaxRatePercent", "landTax", "%", "0.01", true, null],
    ["annualInsuranceTwd", "insuranceYear", `TWD${c("perYear")}`, "1", true, null],
  ] as const;
  return <form onSubmit={event => { event.preventDefault(); void calculate(); }} data-testid="holding-form" className="min-w-0">
    <fieldset className="grid min-w-0 gap-4 sm:grid-cols-2">
      <legend className="ds-visually-hidden">{c("holdingAssumptions")}</legend>
      {fields.map(([key, label, unit, step, required, help]) => <Field key={key} label={c(label)} required={required} helperText={help ? c(help) : undefined} errorText={errors[key] ? c("invalid") : undefined}>
        <UnitInput type="number" min={key === "monthlyIncomeWan" ? "0.01" : "0"} step={step} value={values[key]} onChange={event => dirty(key, event.target.value)} suffix={unit} unitLabel={unit} />
      </Field>)}
    </fieldset>
    <div className="mt-5 flex flex-col items-start gap-3">
      <CommercialButton type="submit" loading={loading} loadingLabel={c("calculating")} data-testid="calculate-holding">{c("calculateHolding")}</CommercialButton>
      {requestError && <div data-testid="holding-error"><Message variant="error">{c("holdingError")}</Message></div>}
    </div>
  </form>;
}
