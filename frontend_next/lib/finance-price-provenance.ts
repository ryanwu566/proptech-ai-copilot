/** Calculation provenance is separate from the property's asking price. Amounts are canonical TWD. */
export type FinancePriceSource = "ASKING_PRICE" | "COMPARABLE_ESTIMATE" | "MANUAL_SCENARIO";
export type FinancePriceEvidence = { price_twd: number; source: FinancePriceSource; calculated_at: string };

export function financeWanUnit(locale: "zh-TW" | "en" | "ja" | "ko"): string {
  return { "zh-TW": "萬元", en: "TWD ten-thousands", ja: "万台湾ドル", ko: "만 NTD" }[locale];
}

export function normalizeFinancePriceEvidence(value: unknown): FinancePriceEvidence | null {
  if (!value || typeof value !== "object") return null;
  const row = value as FinancePriceEvidence;
  if (!Number.isFinite(row.price_twd) || row.price_twd <= 0
    || !["ASKING_PRICE", "COMPARABLE_ESTIMATE", "MANUAL_SCENARIO"].includes(row.source)
    || typeof row.calculated_at !== "string" || !Number.isFinite(Date.parse(row.calculated_at))) return null;
  return { price_twd: row.price_twd, source: row.source, calculated_at: row.calculated_at };
}

export function financePriceSourceLabel(source: FinancePriceSource | null | undefined): string {
  return source === "ASKING_PRICE" ? "開價" : source === "COMPARABLE_ESTIMATE" ? "成交資料推估" : source === "MANUAL_SCENARIO" ? "手動試算情境" : "價格來源未保存";
}

export function priceSourceFromBasis(basis: "asking" | "estimate" | "valuation" | "manual"): FinancePriceSource {
  return basis === "asking" ? "ASKING_PRICE" : basis === "manual" ? "MANUAL_SCENARIO" : "COMPARABLE_ESTIMATE";
}
