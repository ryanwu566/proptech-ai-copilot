export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type TaxCase = {
  case_id: string;
  client_name: string;
  sold_self_occupied: boolean;
  residency_condition_met: boolean;
  purchase_within_reasonable_period: boolean;
  purchased_self_occupied: boolean;
  same_owner: boolean;
  land_value_available: boolean;
  required_docs_complete: boolean;
  enters_five_year_monitoring: boolean;
  exceptional_circumstances: boolean;
};

export type RuleTrace = { code: string; title: string; outcome: string; detail: string; risk_points: number };
export type TaxResult = {
  eligibility_status: "eligible" | "manual_review" | "not_eligible";
  risk_score: number;
  signal_color: "green" | "yellow" | "red";
  hard_fail_rules: string[];
  manual_review_rules: string[];
  missing_docs: string[];
  reminder_timeline: string[];
  rule_traces: RuleTrace[];
  ai_explanation: { headline: string; customer_script: string; source: string };
  disclaimer: string;
  case_input: TaxCase;
};

export type MarketResult = {
  city: string;
  district: string;
  avg_price_per_ping: number;
  trend: number[];
  transaction_volume: number;
  livability_score: number;
  esg_lite_score: number;
  poi_breakdown: Record<string, number>;
  sdg11_note: string;
  summary: string;
  disclaimer: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "API 請求失敗" }));
      throw new Error(payload.detail ?? "API 請求失敗");
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError) throw new Error("無法連線至 FastAPI backend。請先啟動 http://localhost:8000。");
    throw error;
  }
}

export const api = {
  demoCases: () => request<TaxCase[]>("/demo-cases"),
  analyzeTax: (taxCase: TaxCase) => request<TaxResult>("/taxoracle/analyze", { method: "POST", body: JSON.stringify(taxCase) }),
  history: () => request<Record<string, string | number>[]>("/history"),
  marketRegions: () => request<{ city: string; district: string }[]>("/market-insights"),
  marketInsight: (city: string, district: string) =>
    request<MarketResult>("/market-insights/query", { method: "POST", body: JSON.stringify({ city, district }) }),
  aegis: (payload: Record<string, number>) =>
    request<{ risk_score: number; signal_color: string; traces: string[] }>("/aegis-credit/analyze", { method: "POST", body: JSON.stringify(payload) }),
  lexprop: (payload: Record<string, string>) =>
    request<{ risk_score: number; match_count: number; summary: string }>("/lexprop/query", { method: "POST", body: JSON.stringify(payload) }),
};

export async function downloadTaxReport(taxCase: TaxCase) {
  try {
    const response = await fetch(`${API_BASE}/taxoracle/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taxCase),
    });
    if (!response.ok) throw new Error("HTML 報告產生失敗");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `taxoracle-${taxCase.case_id}.html`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    if (error instanceof TypeError) throw new Error("無法連線至 FastAPI backend，請確認 backend 已啟動。");
    throw error;
  }
}
