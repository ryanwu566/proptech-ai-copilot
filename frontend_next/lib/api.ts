const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, "");
const localApiBase = ["http://localhost", "8000"].join(":");

export const API_BASE = configuredApiBase || (process.env.NODE_ENV === "development" ? localApiBase : "");

function apiUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("未設定 NEXT_PUBLIC_API_BASE_URL，線上環境無法連線至 FastAPI backend。");
  }
  return `${API_BASE}${path}`;
}

function connectionError(): Error {
  return new Error("後端服務暫時無法連線，請稍後再試。");
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
  source_chain: ("google_geocoding" | "tgos_geocoding" | "mock")[];
  formatted_address: string;
  place_id: string;
  confidence: "high" | "medium" | "mock";
  location_note: string;
  disclaimer: string;
};
export type GoogleHealth = {
  google_key_configured: boolean;
  geocoding_enabled: boolean | null;
  places_enabled: boolean | null;
  last_error: string;
  mode: "google" | "mock";
  safe_message: string;
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
  opening_status: "open_now" | "closed_now" | "operational" | "hours_available" | "unknown";
  opening_status_label: string;
  opening_hours_source: "currentOpeningHours" | "regularOpeningHours" | "businessStatus" | "mock";
  distance_m: number;
  types: string[];
  category: string;
  source: "google_places" | "mock";
};
export type NearbyCategory = { category: string; label: string; count: number; places: NearbyPlace[] };
export type CategoryScore = {
  category: string;
  label: string;
  weight: number;
  score: number;
  level: string;
  poi_count: number;
  nearest_distance_m: number | null;
  explanation: string;
};
export type MortgageRateReference = {
  source: "central_bank_opendata" | "mock";
  source_name: string;
  period: string;
  reference_rate: number;
  rate_type: string;
  available_fields: string[];
  notes: string[];
  fetched_at: string;
};
export type BankInstitution = { bank_code: string; bank_name: string };
export type BankRateResult = { source: "central_bank_opendata" | "mock"; bank_code: string; bank_name: string; items: { rate_name: string; rate_type: string; fixed_rate: number | null; variable_rate: number | null; effective_date: string; raw_rate_name: string }[]; summary_rate: number | null; summary_label: string; notes: string[]; fetched_at: string };
export type ValuationDataStatus = { active_source: "real_price_sample" | "sqlite_index" | "postgres" | "mock_fallback"; is_demo_data: boolean; is_full_taiwan: boolean; data_composition?: "sample" | "official" | "mixed"; official_records_count?: number; sample_records_count?: number; coverage: { cities: string[]; districts: string[]; roads_count: number; records_count: number }; last_updated: string | null; update_frequency_note: string; source_note: string; user_message: string };
export type ValuationResult = { source: ValuationDataStatus["active_source"]; data_status: ValuationDataStatus; data_composition: "sample" | "official" | "official_limited" | "official_district" | "mixed"; estimate_data_composition: "sample" | "official" | "official_limited" | "official_district" | "mixed"; estimate_source_label: string; official_same_road_count: number; official_same_district_count: number; sample_same_road_count: number; estimate_level: "community" | "road" | "district" | "city" | "fallback"; matched_community: { community_id: string; community_name: string; confidence: "high" | "medium" | "low" } | null; confidence_reason: string; source_details: { file: string; nature: string; complete_real_price_registry: boolean; formal_appraisal: boolean; bank_appraisal: boolean; future_adapter: string }; estimate_total_price: number; estimate_unit_price_per_ping: number; price_range: { low: number; mid: number; high: number }; unit_price_distribution: { weighted_mean: number; weighted_median: number; p25: number; p75: number }; confidence: "high" | "medium" | "low"; confidence_score: number; comparables: { transaction_period: string; city: string; district: string; road: string; building_type: string; normalized_building_type?: string; area_ping: number; unit_price_per_ping: number; total_price: number; building_age_years: number; distance_m: number | null; similarity_score: number; weight: number; note: string; source: "official_plvr_opendata" | "real_price_sample" | "mock_fallback"; source_label: string }[]; valuation_explanation: { sample_count: number; same_road_count: number; same_district_count: number; same_city_count: number; same_building_type_count: number; nearest_distance_m: number | null; average_area_difference_ping: number | null; average_age_difference_years: number | null; average_similarity_score: number; method: string }; methodology: string[]; disclaimer: string };
export type MapNearbyResult = {
  center: { lat: number; lng: number };
  radius_m: number;
  source: "google_places" | "mock";
  categories: NearbyCategory[];
  livability_score: number;
  livability_level: string;
  score_summary: string;
  category_scores: CategoryScore[];
  category_score_map: Record<string, number>;
  nearest_places: NearbyPlace[];
  recommendation_text: string;
  score_explanation: string;
  scoring_criteria: {
    radius_m: number;
    category_weights: Record<string, number>;
    distance_bands: { range: string; weight: "high" | "medium" | "excluded" }[];
    disclaimer: string;
  };
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
      if (response.status === 404) throw new Error("後端尚未部署最新資料服務，請稍後再試。");
      if (response.status >= 500) throw new Error("資料暫時無法載入，請稍後再試。");
      throw new Error("資料請求未完成，請確認輸入後再試。");
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
  mapGoogleHealth: () => request<GoogleHealth>("/map/google-health"),
  roadCities: () => request<{ cities: string[]; message: string }>("/roads/cities"),
  roadDistricts: (city: string) => request<{ city: string; districts: string[]; message: string }>(`/roads/districts?city=${encodeURIComponent(city)}`),
  roads: (city: string, district: string) => request<{ city: string; district: string; roads: string[]; message: string }>(`/roads/roads?city=${encodeURIComponent(city)}&district=${encodeURIComponent(district)}`),
  mapSearch: (query: string) => request<MapSearchResult>("/map/search", { method: "POST", body: JSON.stringify({ query }) }),
  mapInsight: (query: string) => request<MapInsightResult>("/map/insight", { method: "POST", body: JSON.stringify({ query }) }),
  mapNearby: (center: { lat: number; lng: number }, categories: string[], radius_m = 800) =>
    request<MapNearbyResult>("/map/nearby", { method: "POST", body: JSON.stringify({ ...center, radius_m, categories, language_code: "zh-TW" }) }),
  aegis: (payload: Record<string, number>) =>
    request<{ risk_score: number; signal_color: string; traces: string[] }>("/aegis-credit/analyze", { method: "POST", body: JSON.stringify(payload) }),
  mortgageRate: () => request<MortgageRateReference>("/mortgage-rates/latest"),
  bankInstitutions: () => request<{ source: string; institution_count: number; institutions: BankInstitution[]; updated_at: string; notes: string[] }>("/bank-rates/institutions"),
  bankMortgageRates: (bankCode: string) => request<BankRateResult>(`/bank-rates/mortgage?bank_code=${encodeURIComponent(bankCode)}`),
  valuationDataStatus: () => request<ValuationDataStatus>("/valuation/data-status"),
  valuation: (payload: Record<string, string | number>) => request<ValuationResult>("/valuation/estimate", { method: "POST", body: JSON.stringify(payload) }),
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
