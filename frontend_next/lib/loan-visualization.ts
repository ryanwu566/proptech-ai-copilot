import type { LoanCalculationResult } from "./api";

export type LoanSensitivityPoint = {
  annualInterestRate: number;
  monthlyPayment: number;
  totalInterest: number;
  differenceFromBase: number;
};

export type LoanVisualModel = {
  state: "available" | "unavailable";
  summary: string;
  affordability: { key: LoanCalculationResult["affordability_level"]; label: string; message: string };
  metrics: { downPayment: number | null; loanAmount: number | null; monthlyPayment: number | null; totalInterest: number | null };
  structure: { propertyPrice: number; downPayment: number; loanAmount: number; downPaymentRatio: number; loanRatio: number } | null;
  sensitivity: LoanSensitivityPoint[];
  gracePeriodRequested: boolean;
  gracePeriod: { graceMonthlyPayment: number; postGraceMonthlyPayment: number; baselineMonthlyPayment: number } | null;
  evidence: { key: string; label: string; value: string }[];
};

const positive = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value > 0;
const nonNegative = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0;
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const ratio = (value: unknown): value is number => finite(value) && value >= 0 && value <= 1;

const affordabilityLabels: Record<LoanCalculationResult["affordability_level"], string> = {
  comfortable: "舒適",
  manageable: "可管理",
  tight: "偏緊",
  risky: "負擔偏高",
  unknown: "未評估",
};

function emptyModel(message = "貸款結果目前無法安全呈現，請確認輸入與回傳資料。 "): LoanVisualModel {
  return {
    state: "unavailable",
    summary: message.trim(),
    affordability: { key: "unknown", label: "未評估", message: "收入負擔目前未評估，不代表銀行核貸結果。" },
    metrics: { downPayment: null, loanAmount: null, monthlyPayment: null, totalInterest: null },
    structure: null,
    sensitivity: [],
    gracePeriodRequested: false,
    gracePeriod: null,
    evidence: [],
  };
}

export function buildLoanVisualModel(result: LoanCalculationResult | undefined): LoanVisualModel {
  if (!result) return emptyModel();
  const coreValid = positive(result.property_price_wan) && ratio(result.down_payment_ratio) && nonNegative(result.down_payment_wan)
    && positive(result.loan_amount_wan) && positive(result.monthly_payment) && positive(result.total_payment)
    && nonNegative(result.total_interest) && (result.income_burden_ratio === null || nonNegative(result.income_burden_ratio));
  if (!coreValid) return emptyModel("貸款結果資料不足，暫不顯示數值圖表。 ");

  const total = result.property_price_wan;
  const structureMatches = Math.abs(result.down_payment_wan + result.loan_amount_wan - total) <= Math.max(0.01, total * 0.00001);
  const structure = structureMatches ? {
    propertyPrice: total,
    downPayment: result.down_payment_wan,
    loanAmount: result.loan_amount_wan,
    downPaymentRatio: result.down_payment_wan / total,
    loanRatio: result.loan_amount_wan / total,
  } : null;
  const sensitivity = result.sensitivity.filter((item) => finite(item.annual_interest_rate) && positive(item.monthly_payment) && nonNegative(item.total_interest) && finite(item.difference_from_base)).map((item) => ({
    annualInterestRate: item.annual_interest_rate,
    monthlyPayment: item.monthly_payment,
    totalInterest: item.total_interest,
    differenceFromBase: item.difference_from_base,
  }));
  const gracePeriod = result.grace_period_years > 0 && positive(result.grace_period_monthly_payment) && positive(result.post_grace_monthly_payment) && positive(result.monthly_payment)
    ? { graceMonthlyPayment: result.grace_period_monthly_payment, postGraceMonthlyPayment: result.post_grace_monthly_payment, baselineMonthlyPayment: result.monthly_payment }
    : null;
  const incomeMessage = result.income_burden_ratio === null ? "尚未輸入收入，收入負擔率未評估。" : `收入負擔率約 ${(result.income_burden_ratio * 100).toFixed(1)}%，仍需依銀行實際審核。`;
  return {
    state: "available",
    summary: `此條件下每月月付約為 ${result.monthly_payment.toLocaleString()} 元；${incomeMessage}`,
    affordability: { key: result.affordability_level, label: affordabilityLabels[result.affordability_level], message: result.affordability_message },
    metrics: { downPayment: result.down_payment_wan, loanAmount: result.loan_amount_wan, monthlyPayment: result.monthly_payment, totalInterest: result.total_interest },
    structure,
    sensitivity,
    gracePeriodRequested: result.grace_period_years > 0,
    gracePeriod,
    evidence: [
      ["property_price", "試算總價", `${result.property_price_wan.toLocaleString()} 萬元`],
      ["down_payment_ratio", "頭期款比例", `${(result.down_payment_ratio * 100).toFixed(1)}%`],
      ["annual_interest_rate", "年利率", `${result.annual_interest_rate}%`],
      ["loan_years", "貸款年限", `${result.loan_years} 年`],
      ["total_payment", "總還款", `${result.total_payment.toLocaleString()} 元`],
      ["income", "月收入", result.monthly_income_wan === null ? "未輸入" : `${result.monthly_income_wan} 萬元`],
      ["disclaimer", "使用提醒", result.disclaimer],
    ].map(([key, label, value]) => ({ key, label, value })),
  };
}

export { finite as isFiniteLoanValue, nonNegative as isNonNegativeLoanValue, positive as isPositiveLoanValue };
