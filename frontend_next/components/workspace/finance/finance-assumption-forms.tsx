"use client";

import { useEffect, useRef, useState } from "react";
import type { HoldingCostResult, LoanCalculationResult } from "@/lib/api";
import { api } from "@/lib/api";
import { CommercialButton } from "@/components/design-system/button";
import { Field, UnitInput } from "@/components/design-system/field";
import { Message } from "@/components/design-system/message";
import {
  buildHoldingCostRequest,
  buildLoanRequest,
  validateHoldingAssumptions,
  validateLoanAssumptions,
  type HoldingAssumptions,
  type LoanAssumptions,
} from "@/lib/workspace/finance-calculation";
import { monthlyPaymentTwdToWan } from "@/lib/monetary-units";

function numberValue(value: string): number {
  return value === "" ? Number.NaN : Number(value);
}

function optionalNumber(value: string): number | null {
  return value === "" ? null : Number(value);
}

export function LoanAssumptionForm({
  propertyPriceWan,
  initial,
  onCalculated,
  onDirty,
}: {
  propertyPriceWan: number;
  initial?: {
    downPaymentRatio: number | null;
    annualInterestRate: number | null;
    loanYears: number | null;
    gracePeriodYears: number | null;
    monthlyIncomeWan: number | null;
  } | null;
  onCalculated: (result: LoanCalculationResult) => void;
  onDirty: () => void;
}) {
  const [downPaymentRatioPercent, setDownPaymentRatioPercent] = useState(String((initial?.downPaymentRatio ?? 0.2) * 100));
  const [annualInterestRatePercent, setAnnualInterestRatePercent] = useState(String(initial?.annualInterestRate ?? 2.2));
  const [loanYears, setLoanYears] = useState(String(initial?.loanYears ?? 30));
  const [gracePeriodYears, setGracePeriodYears] = useState(String(initial?.gracePeriodYears ?? 0));
  const [monthlyIncomeWan, setMonthlyIncomeWan] = useState(initial?.monthlyIncomeWan === null || initial?.monthlyIncomeWan === undefined ? "" : String(initial.monthlyIncomeWan));
  const [errors, setErrors] = useState<Partial<Record<keyof LoanAssumptions, string>>>({});
  const [requestError, setRequestError] = useState("");
  const [loading, setLoading] = useState(false);
  const requestRef = useRef(0);

  useEffect(() => {
    requestRef.current += 1;
    setLoading(false);
    setErrors({});
    setRequestError("");
  }, [propertyPriceWan]);

  function dirty(setter: (value: string) => void, value: string) {
    requestRef.current += 1;
    setLoading(false);
    setter(value);
    setRequestError("");
    onDirty();
  }

  async function calculate() {
    const assumptions: LoanAssumptions = {
      propertyPriceWan,
      downPaymentRatioPercent: numberValue(downPaymentRatioPercent),
      annualInterestRatePercent: numberValue(annualInterestRatePercent),
      loanYears: numberValue(loanYears),
      gracePeriodYears: numberValue(gracePeriodYears),
      monthlyIncomeWan: optionalNumber(monthlyIncomeWan),
    };
    const nextErrors = validateLoanAssumptions(assumptions);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    const requestId = ++requestRef.current;
    setLoading(true);
    setRequestError("");
    try {
      const result = await api.loanCalculate(buildLoanRequest(assumptions));
      if (requestId !== requestRef.current) return;
      onCalculated(result);
    } catch {
      if (requestId === requestRef.current) setRequestError("房貸試算暫時無法完成。已保留其他財務結果，請稍後再試。");
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }

  return <form onSubmit={(event) => { event.preventDefault(); void calculate(); }} data-testid="loan-form" className="min-w-0">
    <fieldset className="grid min-w-0 gap-4 sm:grid-cols-2">
      <legend className="ds-visually-hidden">房貸假設</legend>
      <Field label="自備款比例" required errorText={errors.downPaymentRatioPercent}>
        <UnitInput type="number" min="0" max="100" step="1" value={downPaymentRatioPercent} onChange={(event) => dirty(setDownPaymentRatioPercent, event.target.value)} suffix="%" unitLabel="百分比" />
      </Field>
      <Field label="年利率" required errorText={errors.annualInterestRatePercent}>
        <UnitInput type="number" min="0" step="0.01" value={annualInterestRatePercent} onChange={(event) => dirty(setAnnualInterestRatePercent, event.target.value)} suffix="%" unitLabel="百分比" />
      </Field>
      <Field label="貸款年期" required errorText={errors.loanYears}>
        <UnitInput type="number" min="1" step="1" value={loanYears} onChange={(event) => dirty(setLoanYears, event.target.value)} suffix="年" unitLabel="年" />
      </Field>
      <Field label="寬限期" required errorText={errors.gracePeriodYears}>
        <UnitInput type="number" min="0" step="1" value={gracePeriodYears} onChange={(event) => dirty(setGracePeriodYears, event.target.value)} suffix="年" unitLabel="年" />
      </Field>
      <Field label="每月收入" helperText="選填；未提供時仍可完成房貸計算，但不評估負擔能力。" errorText={errors.monthlyIncomeWan} className="sm:col-span-2">
        <UnitInput type="number" min="0.01" step="0.01" value={monthlyIncomeWan} onChange={(event) => dirty(setMonthlyIncomeWan, event.target.value)} suffix="萬元／月" unitLabel="每月收入，單位萬元" />
      </Field>
    </fieldset>
    <div className="mt-5 flex flex-col items-start gap-3">
      <CommercialButton type="submit" loading={loading} loadingLabel="正在計算每月房貸" data-testid="calculate-loan">計算每月房貸</CommercialButton>
      {requestError && <div data-testid="loan-error"><Message variant="error">{requestError}</Message></div>}
    </div>
  </form>;
}

export function HoldingAssumptionForm({
  propertyPriceWan,
  initialLoanPaymentTwd,
  initialAreaPing,
  initial,
  onCalculated,
  onDirty,
}: {
  propertyPriceWan: number;
  initialLoanPaymentTwd: number | null;
  initialAreaPing: number | null;
  initial?: {
    loanMonthlyPaymentTwd: number | null;
    monthlyIncomeWan: number | null;
    areaPing: number | null;
    managementFeePerPingTwd: number | null;
    repairReservePerPingTwd: number | null;
    annualHomeTaxRatePercent: number | null;
    annualLandTaxRatePercent: number | null;
    annualInsuranceTwd: number | null;
  } | null;
  onCalculated: (result: HoldingCostResult, areaPing: number | null) => void;
  onDirty: () => void;
}) {
  const initialPaymentWan = monthlyPaymentTwdToWan(initialLoanPaymentTwd ?? initial?.loanMonthlyPaymentTwd ?? 0) ?? 0;
  const [loanMonthlyPaymentWan, setLoanMonthlyPaymentWan] = useState(String(initialPaymentWan));
  const [monthlyIncomeWan, setMonthlyIncomeWan] = useState(initial?.monthlyIncomeWan === null || initial?.monthlyIncomeWan === undefined ? "" : String(initial.monthlyIncomeWan));
  const [areaPing, setAreaPing] = useState(initialAreaPing === null ? "" : String(initialAreaPing));
  const [managementFeePerPingTwd, setManagementFeePerPingTwd] = useState(String(initial?.managementFeePerPingTwd ?? 80));
  const [repairReservePerPingTwd, setRepairReservePerPingTwd] = useState(String(initial?.repairReservePerPingTwd ?? 50));
  const [annualHomeTaxRatePercent, setAnnualHomeTaxRatePercent] = useState(String(initial?.annualHomeTaxRatePercent ?? 0.12));
  const [annualLandTaxRatePercent, setAnnualLandTaxRatePercent] = useState(String(initial?.annualLandTaxRatePercent ?? 0.1));
  const [annualInsuranceTwd, setAnnualInsuranceTwd] = useState(String(initial?.annualInsuranceTwd ?? 3000));
  const [errors, setErrors] = useState<Partial<Record<keyof HoldingAssumptions, string>>>({});
  const [requestError, setRequestError] = useState("");
  const [loading, setLoading] = useState(false);
  const requestRef = useRef(0);

  useEffect(() => {
    requestRef.current += 1;
    const paymentWan = monthlyPaymentTwdToWan(initialLoanPaymentTwd ?? 0);
    if (paymentWan !== null) setLoanMonthlyPaymentWan(String(paymentWan));
    setLoading(false);
    setRequestError("");
  }, [initialLoanPaymentTwd, propertyPriceWan]);

  function dirty(setter: (value: string) => void, value: string) {
    requestRef.current += 1;
    setLoading(false);
    setter(value);
    setRequestError("");
    onDirty();
  }

  async function calculate() {
    const assumptions: HoldingAssumptions = {
      propertyPriceWan,
      loanMonthlyPaymentWan: numberValue(loanMonthlyPaymentWan),
      monthlyIncomeWan: optionalNumber(monthlyIncomeWan),
      areaPing: optionalNumber(areaPing),
      managementFeePerPingTwd: numberValue(managementFeePerPingTwd),
      repairReservePerPingTwd: numberValue(repairReservePerPingTwd),
      annualHomeTaxRatePercent: numberValue(annualHomeTaxRatePercent),
      annualLandTaxRatePercent: numberValue(annualLandTaxRatePercent),
      annualInsuranceTwd: numberValue(annualInsuranceTwd),
    };
    const nextErrors = validateHoldingAssumptions(assumptions);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    const requestId = ++requestRef.current;
    setLoading(true);
    setRequestError("");
    try {
      const result = await api.holdingCostCalculate(buildHoldingCostRequest(assumptions));
      if (requestId !== requestRef.current) return;
      onCalculated(result, assumptions.areaPing);
    } catch {
      if (requestId === requestRef.current) setRequestError("持有成本暫時無法完成。房貸結果與既有資料仍保留，請稍後再試。");
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }

  return <form onSubmit={(event) => { event.preventDefault(); void calculate(); }} data-testid="holding-form" className="min-w-0">
    <fieldset className="grid min-w-0 gap-4 sm:grid-cols-2">
      <legend className="ds-visually-hidden">持有成本假設</legend>
      <Field label="每月房貸支出" required helperText="手動輸入使用萬元；完成房貸試算後會自動帶入對應的每月金額。" errorText={errors.loanMonthlyPaymentWan} className="sm:col-span-2">
        <UnitInput type="number" min="0" step="0.0001" value={loanMonthlyPaymentWan} onChange={(event) => dirty(setLoanMonthlyPaymentWan, event.target.value)} suffix="萬元／月" unitLabel="每月房貸支出，單位萬元" />
      </Field>
      <Field label="坪數" helperText="未提供時，管理費與修繕準備會保留為尚未估算。" errorText={errors.areaPing}>
        <UnitInput type="number" min="0" step="0.1" value={areaPing} onChange={(event) => dirty(setAreaPing, event.target.value)} suffix="坪" unitLabel="坪" />
      </Field>
      <Field label="每月收入" helperText="選填；用於總住宅支出負擔比例。" errorText={errors.monthlyIncomeWan}>
        <UnitInput type="number" min="0.01" step="0.01" value={monthlyIncomeWan} onChange={(event) => dirty(setMonthlyIncomeWan, event.target.value)} suffix="萬元／月" unitLabel="每月收入，單位萬元" />
      </Field>
      <Field label="每坪管理費" required errorText={errors.managementFeePerPingTwd}>
        <UnitInput type="number" min="0" step="1" value={managementFeePerPingTwd} onChange={(event) => dirty(setManagementFeePerPingTwd, event.target.value)} prefix="NT$" suffix="／坪／月" unitLabel="新臺幣，每坪每月" />
      </Field>
      <Field label="每坪修繕準備" required errorText={errors.repairReservePerPingTwd}>
        <UnitInput type="number" min="0" step="1" value={repairReservePerPingTwd} onChange={(event) => dirty(setRepairReservePerPingTwd, event.target.value)} prefix="NT$" suffix="／坪／月" unitLabel="新臺幣，每坪每月" />
      </Field>
      <Field label="房屋稅年率" required errorText={errors.annualHomeTaxRatePercent}>
        <UnitInput type="number" min="0" step="0.01" value={annualHomeTaxRatePercent} onChange={(event) => dirty(setAnnualHomeTaxRatePercent, event.target.value)} suffix="%" unitLabel="百分比" />
      </Field>
      <Field label="地價稅年率" required errorText={errors.annualLandTaxRatePercent}>
        <UnitInput type="number" min="0" step="0.01" value={annualLandTaxRatePercent} onChange={(event) => dirty(setAnnualLandTaxRatePercent, event.target.value)} suffix="%" unitLabel="百分比" />
      </Field>
      <Field label="年度保險" required errorText={errors.annualInsuranceTwd} className="sm:col-span-2">
        <UnitInput type="number" min="0" step="1" value={annualInsuranceTwd} onChange={(event) => dirty(setAnnualInsuranceTwd, event.target.value)} prefix="NT$" suffix="／年" unitLabel="新臺幣每年" />
      </Field>
    </fieldset>
    <div className="mt-5 flex flex-col items-start gap-3">
      <CommercialButton type="submit" loading={loading} loadingLabel="正在估算持有成本" data-testid="calculate-holding">估算持有成本</CommercialButton>
      {requestError && <div data-testid="holding-error"><Message variant="error">{requestError}</Message></div>}
    </div>
  </form>;
}
