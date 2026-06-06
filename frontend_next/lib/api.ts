const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, "");
const localApiBase = "http://localhost:8000";

export const API_BASE = configuredApiBase || (process.env.NODE_ENV === "development" ? localApiBase : "");

function apiUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("未設定 NEXT_PUBLIC_API_BASE_URL，線上環境無法連線至 FastAPI backend。");
  }
  return `${API_BASE}${path}`;
}

function connectionError(): Error {
  return new Error(`無法連線至 FastAPI backend：${API_BASE || "NEXT_PUBLIC_API_BASE_URL 未設定"}`);
}

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

export type MapPoint = { name: string; lat: number; lng: number; score_weight: number };
export type MapPoiLayer = { category: string; label: string; points: MapPoint[] };
export type MapSearchResult = {
  query: string;
  matched: boolean;
  center: { lat: number; lng: number } | null;
  city: string;
  district: string;
  road: string;
  source: string;
  disclaimer: string;
};
export type MapInsightResult = {
  center: { lat: number; lng: number };
  zoom: number;
  area_summary: string;
  poi_layers: MapPoiLayer[];
  livability_score: number;
  poi_summary: string;
  source: string;
  disclaimer: string;
};
export type NearbyPlace = {
  place_id: string;
  name: string;
  lat: number;
  lng: number;
  address: string;
  rating: number | null;
  user_rating_count: number;
  business_status: string;
  distance_m: number;
  types: string[];
  category: string;
  source: "google_places" | "mock";
};
export type NearbyCategory = { category: string; label: string; count: number; places: NearbyPlace[] };
export type MapNearbyResult = {
  center: { lat: number; lng: number };
  radius_m: number;
  source: "google_places" | "mock";
  categories: NearbyCategory[];
  livability_score: number;
  category_scores: Record<string, number>;
  nearest_places: NearbyPlace[];
  recommendation_text: string;
  score_explanation: string;
  summary: string;
  disclaimer: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "API 請求失敗" }));
      throw new Error(payload.detail ?? "API 請求失敗");
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError) throw connectionError();
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
  mapRegions: () => request<{ id: string; city: string; district: string; road: string; center: { lat: number; lng: number } }[]>("/map/regions"),
  mapCategories: () => request<{ category: string; label: string }[]>("/map/poi-categories"),
  mapSearch: (query: string) => request<MapSearchResult>("/map/search", { method: "POST", body: JSON.stringify({ query }) }),
  mapInsight: (query: string) => request<MapInsightResult>("/map/insight", { method: "POST", body: JSON.stringify({ query }) }),
  mapNearby: (center: { lat: number; lng: number }, categories: string[], radius_m = 800) =>
    request<MapNearbyResult>("/map/nearby", { method: "POST", body: JSON.stringify({ ...center, radius_m, categories, language_code: "zh-TW" }) }),
  aegis: (payload: Record<string, number>) =>
    request<{ risk_score: number; signal_color: string; traces: string[] }>("/aegis-credit/analyze", { method: "POST", body: JSON.stringify(payload) }),
  lexprop: (payload: Record<string, string>) =>
    request<{ risk_score: number; match_count: number; summary: string }>("/lexprop/query", { method: "POST", body: JSON.stringify(payload) }),
};

export async function downloadTaxReport(taxCase: TaxCase) {
  try {
    const response = await fetch(apiUrl("/taxoracle/report"), {
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
    if (error instanceof TypeError) throw connectionError();
    throw error;
  }
}
