const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, "");
const isDevelopment = process.env.NODE_ENV === "development";
const productionLocalhostConfigured = Boolean(
  configuredApiBase && !isDevelopment && /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(configuredApiBase),
);
const localApiBase = ["http://localhost", "8000"].join(":");

export const API_BASE = productionLocalhostConfigured ? "" : configuredApiBase || (isDevelopment ? localApiBase : "");

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
  county?: string;
  district: string;
  period: string | null;
  average_unit_price: number | null;
  avg_price_per_ping: number | null;
  transaction_count: number | null;
  transaction_volume: number | null;
  record_count?: number | null;
  summary: string;
  source_name: string | null;
  source_updated_at: string | null;
  coverage_status: "nationwide" | "partial" | "unknown";
  data_status: "available" | "no_data" | "unavailable" | "incomplete" | "invalid";
  caveat: string;
  disclaimer: string;
  source_file_hash?: string | null;
  aggregation_method?: string | null;
  history: { period: string | null; average_unit_price: number | null; transaction_count: number }[];
};
export type MarketRegion = { city: string; county?: string; district: string; period?: string | null; data_status?: MarketResult["data_status"] };
export type MarketRegionCatalog = {
  read_model_status: "ready" | "missing" | "stale" | "unavailable";
  regions: MarketRegion[];
  available_counties?: string[];
  data_status: MarketResult["data_status"];
  coverage_status: MarketResult["coverage_status"];
  source_name: string | null;
  source_updated_at: string | null;
  available_county_count?: number;
  available_district_count?: number;
  earliest_period?: string | null;
  latest_period?: string | null;
  built_at?: string | null;
  caveat: string;
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
export type LoanCalculationResult = { property_price_wan: number; down_payment_ratio: number; down_payment_wan: number; loan_amount_wan: number; annual_interest_rate: number; loan_years: number; grace_period_years: number; monthly_income_wan: number | null; monthly_payment: number; grace_period_monthly_payment: number | null; post_grace_monthly_payment: number | null; total_payment: number; total_interest: number; income_burden_ratio: number | null; affordability_level: "comfortable" | "manageable" | "tight" | "risky" | "unknown"; affordability_message: string; sensitivity: { annual_interest_rate: number; monthly_payment: number; total_interest: number; difference_from_base: number }[]; disclaimer: string };
export type HoldingCostResult = { input: { property_price_wan: number; loan_monthly_payment: number; monthly_income_wan: number | null; area_ping: number | null; management_fee_per_ping: number; repair_reserve_per_ping: number; annual_home_tax_rate: number; annual_land_tax_rate: number; annual_insurance: number; include_tax_estimate: boolean }; property_price_wan: number; loan_monthly_payment: number; monthly_management_fee: number; monthly_repair_reserve: number; monthly_tax_estimate: number; annual_home_tax_estimate: number; annual_land_tax_estimate: number; monthly_insurance: number; monthly_total_holding_cost: number; annual_total_holding_cost: number; income_burden_ratio: number | null; affordability_level: "comfortable" | "manageable" | "tight" | "risky" | "unknown"; affordability_message: string; cost_breakdown: { key: string; label: string; monthly_amount: number }[]; disclaimer: string };
export type LocationInsightResult = { input: Record<string, string | number | boolean | null>; resolved_location: { address_label: string; latitude: number; longitude: number; geocoding_confidence: string } | null; radius_m: number; location_score: number | null; category_scores: { transit_score: number; convenience_score: number; education_score: number; green_space_score: number; medical_score: number; risk_score: number }; poi_summary: { transit_count: number; convenience_count: number; school_count: number; park_count: number; medical_count: number; risk_facility_count: number }; nearest_pois: { category: string; name: string; distance_m: number; source: string }[]; strengths: string[]; weaknesses: string[]; buyer_fit: { self_use_family: string; commuter: string; investor: string; elderly: string }; valuation_context: { supports_price_reasonableness: boolean | "unknown"; explanation: string }; data_quality: { status: "good" | "limited" | "unavailable"; missing_sources: string[]; warnings: string[] }; scoring_method: { weights: Record<string, number>; explanation: string }; disclaimer: string };
export type CommuteAddressLookupResult = { status: "resolved" | "unresolved" | "unavailable"; source: "tdx" | "none"; station_name: string | null; line_ids: string[]; distance_meters: number | null; source_updated_at: string | null; snapshot_generated_at: string | null; message: string };
export type TerrainRiskLayerStatus = "available" | "limited" | "unavailable" | "error" | "skipped";
export type TerrainRiskLevel = "low" | "medium" | "high" | "unknown";
export type TerrainRiskSource = { name: string; agency: string; source_url?: string; fetched_at?: string; data_updated_at?: string; status: string; data_vintage?: string; data_quality?: string; limitation?: string };
export type TerrainRiskSourceTransparencyLayer = {
  layer_id: string;
  display_name: string;
  source_name: string;
  source_kind: string;
  assessment_status: "matched" | "not_matched" | "unavailable" | "not_assessed";
  coverage_status: "covered" | "not_covered" | "unknown";
  data_updated_at: string;
  caveat: string;
};
export type TerrainHazardLayer = { key: string; label: string; status: TerrainRiskLayerStatus; level: TerrainRiskLevel; matched: boolean; distance_m: number | null; value: string | number | null; explanation: string; source?: TerrainRiskSource };
export type TerrainRiskResult = {
  input: Record<string, string | number | string[] | null | undefined>;
  resolved_location: { address_label?: string; latitude?: number; longitude?: number; geocoding_confidence?: string };
  overall: { level: TerrainRiskLevel; label: string; summary: string; confidence: "high" | "medium" | "low" | "unknown" };
  terrain: { status: TerrainRiskLayerStatus; slope_value?: number | null; slope_class?: string | null; elevation_m?: number | null; explanation: string; source?: TerrainRiskSource };
  hazards: Record<"landslide" | "debris_flow" | "flood" | "geological_sensitivity" | "liquefaction" | "active_fault", TerrainHazardLayer>;
  risk_factors: { key: string; level: TerrainRiskLevel; title: string; message: string; source_name?: string }[];
  missing_sources: string[];
  recommended_checks: string[];
  map_layers: { key: string; label: string; status: string; source_url?: string; external_view_url?: string; data_vintage?: string; data_quality?: string; limitation?: string }[];
  source_transparency?: { notice: string; layers: TerrainRiskSourceTransparencyLayer[] };
  data_quality: { status: "good" | "limited" | "unavailable"; warnings: string[]; checked_at: string };
  disclaimer: string;
};
export type ValuationDataStatus = { active_source: "real_price_sample" | "sqlite_index" | "postgres" | "mock_fallback"; is_demo_data: boolean; is_full_taiwan: boolean; data_composition?: "sample" | "official" | "mixed"; official_records_count?: number; sample_records_count?: number; official_period_min?: string | null; official_period_max?: string | null; raw_official_period_min?: string | null; raw_official_period_max?: string | null; effective_trend_period_min?: string | null; effective_trend_period_max?: string | null; excluded_future_period_count?: number; excluded_too_old_period_count?: number; data_quality_note?: string; retention_policy_years?: number; retention_cutoff_period?: string | null; records_outside_retention_count?: number; oldest_effective_period?: string | null; newest_effective_period?: string | null; retention_note?: string; official_coverage_note?: string; coverage_city_count?: number; coverage_district_count?: number; coverage_road_count?: number; coverage_cities?: string[]; coverage_summary?: string; coverage_note_short?: string; latest_import_status?: string | null; latest_import_scope?: string; latest_import_inserted_rows?: number; latest_import_skipped_duplicates?: number; coverage: { cities: string[]; districts: string[]; roads_count: number; records_count: number }; last_updated: string | null; update_frequency_note: string; source_note: string; user_message: string };
export type ValuationResult = { source: ValuationDataStatus["active_source"]; data_status: ValuationDataStatus; data_composition: "sample" | "official" | "official_limited" | "official_district" | "mixed"; estimate_data_composition: "sample" | "official" | "official_limited" | "official_district" | "mixed"; estimate_source_label: string; candidate_pool_size: number; official_same_road_count: number; official_same_district_count: number; sample_same_road_count: number; sample_same_district_count: number; estimate_level: "community" | "road" | "district" | "city" | "fallback"; matched_community: { community_id: string; community_name: string; confidence: "high" | "medium" | "low" } | null; confidence_reason: string; source_details: { file: string; nature: string; complete_real_price_registry: boolean; formal_appraisal: boolean; bank_appraisal: boolean; future_adapter: string; provider_active?: string; candidate_pool_size?: number; query_scope?: string; requested_city?: string; requested_district?: string; requested_road?: string; db_rows_returned?: number; query_status?: string; safe_error?: string }; estimate_total_price: number; estimate_unit_price_per_ping: number; price_range: { low: number; mid: number; high: number }; unit_price_distribution: { weighted_mean: number; weighted_median: number; p25: number; p75: number }; confidence: "high" | "medium" | "low"; confidence_score: number; comparables: { transaction_period: string; city: string; district: string; road: string; building_type: string; normalized_building_type?: string; area_ping: number; unit_price_per_ping: number; total_price: number; building_age_years: number; distance_m: number | null; similarity_score: number; weight: number; note: string; source: "official_plvr_opendata" | "real_price_sample" | "mock_fallback"; source_label: string }[]; valuation_explanation: { sample_count: number; same_road_count: number; same_district_count: number; same_city_count: number; same_building_type_count: number; nearest_distance_m: number | null; average_area_difference_ping: number | null; average_age_difference_years: number | null; average_similarity_score: number; method: string }; methodology: string[]; disclaimer: string };
export type ValuationTrendResult = { source: "official_plvr_opendata"; data_scope: "road" | "district_type" | "district"; raw_period_min: string | null; raw_period_max: string | null; effective_period_min: string | null; effective_period_max: string | null; excluded_future_period_count: number; excluded_out_of_window_count: number; period_min: string | null; period_max: string | null; sample_count: number; road_sample_count: number; district_sample_count: number; monthly_series: { period: string; median_unit_price_per_ping: number; p25_unit_price_per_ping: number; p75_unit_price_per_ping: number; transaction_count: number }[]; yearly_series: { year: string; median_unit_price_per_ping: number; transaction_count: number; yoy_change_percent: number | null }[]; recent_median_unit_price: number; trend_annualized_rate: number; volatility: number | null; confidence_level: "high" | "medium" | "low"; confidence_reason: string; scenario_forecast: Record<"conservative" | "base" | "optimistic", { horizon_months: number; projected_unit_price_per_ping: number; projected_total_price: number; growth_rate_used: number; explanation: string }[]>; methodology: string[]; disclaimer: string };
export type PropertySearchSuggestion = { city: string; district: string; road?: string; sample_count: number; median_total_price: number; median_unit_price_per_ping: number; median_area_ping: number; common_building_type: string; score: number; reason: string; p25_total_price?: number; p75_total_price?: number; period_min?: string; period_max?: string };
export type PropertySearchTransaction = { transaction_period: string; city: string; district: string; road: string; building_type: string; area_ping: number; total_price: number; unit_price_per_ping: number; building_age_years: number; floor: number; source_label: string };
export type PropertySearchResult = { summary: { matched_count: number; city_count: number; district_count: number; road_count: number; budget_min: number | null; budget_max: number; period_min: string | null; period_max: string | null; data_source_label: string; message: string; disclaimer: string }; district_suggestions: PropertySearchSuggestion[]; road_suggestions: PropertySearchSuggestion[]; matched_transactions: PropertySearchTransaction[]; methodology: string; disclaimer: string };
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
  runTaxOracleCase: (taxCase: TaxCase) => request<TaxResult>("/taxoracle/analyze", { method: "POST", body: JSON.stringify(taxCase) }),
  analyzeTax: (taxCase: TaxCase) => request<TaxResult>("/taxoracle/analyze", { method: "POST", body: JSON.stringify(taxCase) }),
  history: () => request<Record<string, string | number>[]>("/history"),
  marketStatus: () => request<MarketRegionCatalog>("/market-insights/status"),
  marketCatalog: () => request<MarketRegionCatalog>("/market-insights/catalog"),
  marketRegions: (county?: string) =>
    request<MarketRegionCatalog>(`/market-insights/regions${county ? `?county=${encodeURIComponent(county)}` : ""}`),
  marketInsight: (county: string, district?: string, period?: string | null) =>
    request<MarketResult>("/market-insights/query", { method: "POST", body: JSON.stringify({ county, district, period }) }),
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
  loanCalculate: (payload: Record<string, number | boolean | undefined>) => request<LoanCalculationResult>("/loan/calculate", { method: "POST", body: JSON.stringify(payload) }),
  holdingCostCalculate: (payload: Record<string, number | boolean | undefined>) => request<HoldingCostResult>("/holding-cost/calculate", { method: "POST", body: JSON.stringify(payload) }),
  locationInsight: (payload: Record<string, string | number | boolean | undefined>) => request<LocationInsightResult>("/location/insight", { method: "POST", body: JSON.stringify(payload) }),
  commuteAddressLookup: (payload: { address: string }) => request<CommuteAddressLookupResult>("/commute/address-lookup", { method: "POST", body: JSON.stringify(payload) }),
  terrainRiskAnalyze: (payload: Record<string, string | number | string[] | undefined>) => request<TerrainRiskResult>("/terrain-risk/analyze", { method: "POST", body: JSON.stringify(payload) }),
  valuationDataStatus: () => request<ValuationDataStatus>("/valuation/data-status"),
  valuation: (payload: Record<string, string | number>) => request<ValuationResult>("/valuation/estimate", { method: "POST", body: JSON.stringify(payload) }),
  valuationTrend: (payload: Record<string, string | number | number[]>) => request<ValuationTrendResult>("/valuation/trend", { method: "POST", body: JSON.stringify(payload) }),
  propertySearch: (payload: Record<string, string | number | string[] | undefined>) => request<PropertySearchResult>("/valuation/property-search", { method: "POST", body: JSON.stringify(payload) }),
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
