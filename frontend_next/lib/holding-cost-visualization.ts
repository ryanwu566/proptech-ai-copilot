import type { HoldingCostResult } from "./api";

export type HoldingCostBreakdownPoint = { key: string; label: string; monthlyAmount: number; percentage: number | null };
export type HoldingCostVisualModel = {
  state: "available" | "unavailable";
  summary: string;
  affordability: { key: HoldingCostResult["affordability_level"]; label: string; message: string };
  metrics: { monthlyTotal: number | null; annualTotal: number | null; incomeBurden: number | null; annualTaxEstimate: number | null };
  breakdown: HoldingCostBreakdownPoint[];
  omittedBreakdownCount: number;
  evidence: { key: string; label: string; value: string }[];
};

const positive = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value > 0;
const nonNegative = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0;
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;

const affordabilityLabels: Record<HoldingCostResult["affordability_level"], string> = {
  comfortable: "舒適",
  manageable: "可管理",
  tight: "偏緊",
  risky: "負擔偏高",
  unknown: "未評估",
};

function emptyModel(message = "持有成本結果目前無法安全呈現。 "): HoldingCostVisualModel {
  return {
    state: "unavailable",
    summary: message.trim(),
    affordability: { key: "unknown", label: "未評估", message: "收入負擔目前未評估，不代表財務或稅務結論。" },
    metrics: { monthlyTotal: null, annualTotal: null, incomeBurden: null, annualTaxEstimate: null },
    breakdown: [],
    omittedBreakdownCount: 0,
    evidence: [],
  };
}

export function buildHoldingCostVisualModel(result: HoldingCostResult | undefined): HoldingCostVisualModel {
  if (!result) return emptyModel();
  if (!positive(result.monthly_total_holding_cost) || !positive(result.annual_total_holding_cost)) return emptyModel("持有成本總額無效，暫不顯示占比或成本圖表。 ");
  const breakdown = result.cost_breakdown.filter((item) => text(item.key) && text(item.label) && nonNegative(item.monthly_amount)).map((item) => ({
    key: item.key,
    label: item.label,
    monthlyAmount: item.monthly_amount,
    percentage: (item.monthly_amount / result.monthly_total_holding_cost) * 100,
  }));
  const incomeBurden = result.income_burden_ratio === null || nonNegative(result.income_burden_ratio) ? result.income_burden_ratio : null;
  const annualTaxEstimate = nonNegative(result.annual_home_tax_estimate) && nonNegative(result.annual_land_tax_estimate) ? result.annual_home_tax_estimate + result.annual_land_tax_estimate : null;
  return {
    state: "available",
    summary: `每月持有成本約 ${result.monthly_total_holding_cost.toLocaleString()} 元，年持有成本約 ${result.annual_total_holding_cost.toLocaleString()} 元；這是簡化估算，不是正式稅務或財務意見。`,
    affordability: { key: result.affordability_level, label: affordabilityLabels[result.affordability_level], message: result.affordability_message },
    metrics: { monthlyTotal: result.monthly_total_holding_cost, annualTotal: result.annual_total_holding_cost, incomeBurden, annualTaxEstimate },
    breakdown,
    omittedBreakdownCount: Math.max(0, breakdown.length - 6),
    evidence: [
      ["property_price", "房屋總價假設", `${result.input.property_price_wan.toLocaleString()} 萬元`],
      ["loan_payment", "房貸月付假設", `${result.input.loan_monthly_payment.toLocaleString()} 元`],
      ["management_fee", "管理費假設", `${result.input.management_fee_per_ping} 元／坪／月`],
      ["repair_reserve", "修繕預備金假設", `${result.input.repair_reserve_per_ping} 元／坪／月`],
      ["tax", "稅費說明", "房屋稅與地價稅為簡化估算，實際費用可能不同。"],
      ["disclaimer", "使用提醒", result.disclaimer],
    ].map(([key, label, value]) => ({ key, label, value })),
  };
}

export { nonNegative as isNonNegativeHoldingValue, positive as isPositiveHoldingValue };
