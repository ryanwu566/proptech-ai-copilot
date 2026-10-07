import type { SavedCase } from "../case-storage";
export const E9_NOW = "2026-10-07T03:00:00.000Z";
/** Deterministic fixture shared by model and browser tests, never imported by UI. */
export function e9Case(id = "case-a"): SavedCase {
  const address = `臺中市西屯區臺灣大道三段${id === "case-a" ? "100" : "200"}號`;
  const anchorId = `journey-browser-11111111-2222-4333-8444-${id === "case-a" ? "555555555555" : "666666666666"}`;
  return {
    id, title: `案件 ${id.slice(-1).toUpperCase()}`, createdAt: E9_NOW, updatedAt: E9_NOW, version: 1, workflowMode: "buying_wizard", activeWizardStep: "report", progress: 60,
    inputSummary: { city: "臺中市", district: "西屯區", road: address.replace("臺中市西屯區", ""), propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺中市", district: "西屯區", road: address.replace("臺中市西屯區", ""), building_type: "住宅大樓", area_ping: 30, building_age_years: 8, floor: 12 },
      propertyIdentityAnchor: {
        version: 1, scope: "journey_browser_anchor", journey_anchor_id: anchorId, address_input: address, normalized_address: address,
        coordinates: { latitude: 24.16525, longitude: 120.64555 }, administrative_location: { city: "臺中市", district: "西屯區", village: "潮洋里", village_code: "66000060-020" }, location_status: "candidate",
        parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
        building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_building_identity_evidence"], confirmation: null },
        confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["normalized_address", "trusted_geocoding_coordinates"], limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"] },
        evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: E9_NOW }], checked_at: E9_NOW, limitations: ["journey_browser_correlation_only"] }, revalidation: { status: "current", conflicts: [] },
      },
      journeyContext: { version: 1, propertyContext: { city: "臺中市", district: "西屯區", road: address, addressSummary: address, sourceLabel: "已儲存案件", selectionStatus: "selected", askingPriceWan: 2480 }, priceBasis: "asking", activePriceWan: 2480, valuationStatus: "unavailable" },
      marketInsight: { city: "臺中市", district: "西屯區", period: "2025-01–2026-07", average_unit_price: 53.1, avg_price_per_ping: 53.1, transaction_count: 18, transaction_volume: 18, summary: "成交摘要", source_name: "內政部不動產實價登錄", source_updated_at: "2026-08-31", coverage_status: "covered", data_status: "available", caveat: "區域成交分布不等同個案價值", disclaimer: "非正式估價", history: [], sample_status: "sufficient", freshness_status: "fresh", median_total_price: 1850, median_unit_price_per_ping: 52.4, p25_unit_price_per_ping: 49.8, p75_unit_price_per_ping: 55.6, effective_sample_count: 18, effective_scope_label: "臺中市西屯區", effective_analysis_level: "DISTRICT" },
      commuteRoute: { source: "google_routes", origin: { latitude: 24.16525, longitude: 120.64555 }, destination: { address: "臺中車站" }, mode: "driving", distance_m: 9800, duration_seconds: 1440, duration_min: 24, checked_at: E9_NOW, reason_code: "success", status: "resolved", partial: false, fallback: false },
      commuteTransit: { status: "unavailable", source: "tdx", station_name: null, line_ids: [], distance_meters: null, source_updated_at: null, snapshot_generated_at: E9_NOW, message: "unavailable" },
      terrainReference: { schema_version: 1, kind: "terrain_reference", status: "partial", summary: "部分來源", notice: "未知仍為未知", layers: [
        { layer_id: "flood", display_name: "淹水", state: "no_match", source_name: "水利署", coverage_status: "covered", caveat: "未命中不代表安全" },
        { layer_id: "landslide", display_name: "山崩", state: "available", source_name: "農村水保署", coverage_status: "covered", caveat: "命中範圍需現場確認" },
        { layer_id: "geological_sensitivity", display_name: "地質敏感區", state: "unavailable", source_name: "地質調查及礦業管理中心", coverage_status: "unknown", caveat: "目前無法取得" },
      ] }, riskEvidenceCheckedAt: E9_NOW,
      financeEvidence: {
        version: 1, case_id: id, revision: 1, input_fingerprint: `finance-v1|${id}|1|${anchorId}|asking|2480|30`, assumptions: { price_basis: "asking", active_price_wan: 2480, area_ping: 30 },
        calculation: { query: "succeeded", usability: "usable", completeness: "partial" },
        loan: { property_price_wan: 2480, down_payment_ratio: 0.2, down_payment_wan: 496, principal_wan: 1984, annual_interest_rate: 0, loan_years: 30, grace_period_years: 0, monthly_income_wan: null, monthly_payment_twd: 55111, grace_period_monthly_payment_twd: null, post_grace_monthly_payment_twd: null, total_interest_twd: 0 },
        holding: { known_monthly_subtotal_twd: 55111, known_annual_subtotal_twd: 661332, total_kind: "known_subtotal", assumptions: { loan_monthly_payment_twd: 55111, monthly_income_wan: null, area_ping: 30, management_fee_per_ping_twd: null, repair_reserve_per_ping_twd: null, annual_home_tax_rate_percent: null, annual_land_tax_rate_percent: null, annual_insurance_twd: 0 }, breakdown: [{ key: "insurance", label: "保險", status: "estimated", monthly_amount_twd: 0, missing_reason: null }] },
        affordability: { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null }, tax: { query: "not_started", summary: null }, missing_costs: ["管理費（尚未提供）", "交易成本（未納入）"], unresolved_actions: ["提供月收入"], calculated_at: E9_NOW,
      },
    },
  };
}
