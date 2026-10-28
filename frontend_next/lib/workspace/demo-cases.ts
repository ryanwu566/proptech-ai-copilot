import type { SavedCase } from "../case-storage";
import type { SavedCaseReadDiagnostic } from "./saved-case-diagnostics";
import type { DecisionRoom, WorkItem } from "../decision-room-store";
import type { ExperienceLocale } from "../experience-i18n";
// @ts-expect-error Native TS runner extension.
import { DEMO_CASE_A_ID, DEMO_CASE_B_ID, DEMO_CASE_IDS, DEMO_SNAPSHOT_DATE } from "./demo-case-ids.ts";
// @ts-expect-error Native TS runner extension.
import { classifyNearbyPlace } from "./nearby-poi-category.ts";

/**
 * Demonstration snapshots for the complete example. Values are illustrative, dated
 * DEMO_SNAPSHOT_DATE, and never acquired live; every surface reads them as saved evidence.
 * UNKNOWN layers stay unknown, NO MATCH stays "not found", and nothing is ranked.
 */
const AT = `${DEMO_SNAPSHOT_DATE}T02:00:00.000Z`;
const NOTE = "示範快照：範例資料，非即時查詢、非正式官方證據。";
type Facility = { name: string; category: "transport" | "shopping" | "food" | "school" | "medical" | "park"; types?: string[]; dLat: number; dLng: number };
type Spec = {
  id: string; anchor: string; city: string; district: string; road: string; village: string; villageCode: string;
  lat: number; lng: number; askingWan: number; areaPing: number; age: number; floor: number; buildingType: string;
  market: SavedCase["data"]["marketInsight"]; commute: { destination: string; mode: "transit" | "driving"; minutes: number; meters: number };
  transit: { station: string; lines: string[]; meters: number }; facilities: Facility[];
  risk: NonNullable<SavedCase["data"]["terrainReference"]>["layers"]; finance: NonNullable<SavedCase["data"]["financeEvidence"]>;
};

const market = (city: string, district: string, period: string, unit: { avg: number; median: number; p25: number; p75: number }, totalWan: number, count: number, history: Array<[string, number, number]>): SavedCase["data"]["marketInsight"] => ({
  city, district, period, average_unit_price: unit.avg, avg_price_per_ping: unit.avg, transaction_count: count, transaction_volume: count,
  summary: `${NOTE}${city}${district}住宅成交摘要`, source_name: "內政部不動產實價登錄", source_updated_at: "2026-09-11",
  coverage_status: "covered", data_status: "available", caveat: "區域成交分布不等同個案價值；示範快照不會自動更新。", disclaimer: "非正式估價",
  history: history.map(([period, average, transactions]) => ({ period, average_unit_price: average, transaction_count: transactions })),
  sample_status: "sufficient", freshness_status: "fresh", median_total_price: totalWan, median_unit_price_per_ping: unit.median,
  p25_unit_price_per_ping: unit.p25, p75_unit_price_per_ping: unit.p75, effective_sample_count: count,
  effective_scope_label: `${city}${district}`, effective_analysis_level: "DISTRICT",
} as SavedCase["data"]["marketInsight"]);

const layer = (layer_id: string, display_name: string, state: "available" | "no_match" | "unavailable" | "limited", source_name: string, caveat: string, coverage_status: "covered" | "unknown" | "partial" = state === "unavailable" ? "unknown" : "covered") =>
  ({ layer_id, display_name, state, source_name, coverage_status, caveat, data_updated_at: DEMO_SNAPSHOT_DATE });

const SPECS: Spec[] = [{
  id: DEMO_CASE_A_ID, anchor: "journey-browser-d3e00000-0a0a-4a0a-8a0a-00000000000a",
  city: "新北市", district: "板橋區", road: "文化路一段", village: "流芳里", villageCode: "65000010-012",
  lat: 25.01440, lng: 121.46310, askingWan: 1680, areaPing: 28, age: 22, floor: 7, buildingType: "電梯大樓",
  market: market("新北市", "板橋區", "2025-10–2026-08", { avg: 54.2, median: 53.6, p25: 48.9, p75: 59.8 }, 1520, 132,
    [["2025-Q4", 52.9, 41], ["2026-Q1", 53.4, 36], ["2026-Q2", 54.6, 33], ["2026-Q3", 55.1, 22]]),
  commute: { destination: "臺北車站", mode: "transit", minutes: 24, meters: 9100 },
  transit: { station: "府中", lines: ["BL"], meters: 640 },
  facilities: [
    { name: "捷運府中站出入口", category: "transport", types: ["subway_station", "transit_station"], dLat: -0.0052, dLng: -0.0030 },
    { name: "公車站（文化路）", category: "transport", types: ["bus_stop", "transit_station"], dLat: 0.0006, dLng: 0.0004 },
    { name: "連鎖超市", category: "shopping", dLat: 0.0012, dLng: -0.0009 },
    { name: "便利商店", category: "shopping", dLat: -0.0004, dLng: 0.0007 },
    { name: "早午餐店", category: "food", dLat: 0.0009, dLng: 0.0011 },
    { name: "社區國小", category: "school", dLat: 0.0031, dLng: 0.0016 },
    { name: "家醫科診所", category: "medical", dLat: -0.0015, dLng: 0.0013 },
    { name: "社區公園", category: "park", dLat: 0.0022, dLng: -0.0024 },
  ],
  risk: [
    layer("flood", "淹水潛勢", "available", "經濟部水利署", "示範：位於淹水潛勢範圍內（24 小時 350 毫米情境）；需向管委會確認地下室與車道實際紀錄。"),
    layer("liquefaction", "土壤液化潛勢", "available", "經濟部地質調查及礦業管理中心", "示範：中潛勢區；不等同建物結構安全，需查閱結構與補強資料。"),
    layer("landslide", "山崩與地滑", "no_match", "農業部農村發展及水土保持署", "未命中不代表零風險，只表示查詢範圍內未找到圖資紀錄。"),
    layer("debris_flow", "土石流潛勢溪流", "no_match", "農業部農村發展及水土保持署", "未命中不代表零風險，只表示查詢範圍內未找到圖資紀錄。"),
    layer("geological_sensitivity", "地質敏感區", "unavailable", "經濟部地質調查及礦業管理中心", "示範快照未取得此圖層；未知仍為未知。"),
  ],
  finance: {
    version: 1, case_id: DEMO_CASE_A_ID, revision: 1, input_fingerprint: `finance-v1|${DEMO_CASE_A_ID}|1|journey-browser-d3e00000-0a0a-4a0a-8a0a-00000000000a|asking|1680|28`,
    assumptions: { price_basis: "asking", active_price_wan: 1680, area_ping: 28 },
    calculation: { query: "succeeded", usability: "usable", completeness: "partial" },
    loan: { property_price_wan: 1680, down_payment_ratio: 0.2, down_payment_wan: 336, principal_wan: 1344, annual_interest_rate: 2.185, loan_years: 30, grace_period_years: 0, monthly_income_wan: 15, monthly_payment_twd: 50929, grace_period_monthly_payment_twd: null, post_grace_monthly_payment_twd: null, total_interest_twd: 4894440 },
    holding: { known_monthly_subtotal_twd: 53469, known_annual_subtotal_twd: 641628, total_kind: "known_subtotal",
      assumptions: { loan_monthly_payment_twd: 50929, monthly_income_wan: 15, area_ping: 28, management_fee_per_ping_twd: 80, repair_reserve_per_ping_twd: null, annual_home_tax_rate_percent: null, annual_land_tax_rate_percent: null, annual_insurance_twd: 3600 },
      breakdown: [
        { key: "loan", label: "房貸月付", status: "estimated", monthly_amount_twd: 50929, missing_reason: null },
        { key: "management", label: "管理費", status: "estimated", monthly_amount_twd: 2240, missing_reason: null },
        { key: "repair_reserve", label: "修繕準備金", status: "unestimated", monthly_amount_twd: null, missing_reason: "尚未提供每坪提撥金額" },
        { key: "tax_estimate", label: "房屋稅與地價稅", status: "unestimated", monthly_amount_twd: null, missing_reason: "尚未取得稅單或稅率" },
        { key: "insurance", label: "保險", status: "estimated", monthly_amount_twd: 300, missing_reason: null },
      ] },
    affordability: { status: "assessed", ratio: 0.356, reason: "以示範假設月收入 15 萬元計算，僅含已知月支出", basis: "total_housing_cost" },
    tax: { query: "not_started", summary: null },
    missing_costs: ["修繕準備金（尚未提供）", "房屋稅與地價稅（尚未取得）", "交易成本（未納入）"],
    unresolved_actions: ["向銀行確認實際核貸成數與利率", "取得最近一期房屋稅單"], calculated_at: AT,
  },
}, {
  id: DEMO_CASE_B_ID, anchor: "journey-browser-d3e00000-0b0b-4b0b-8b0b-00000000000b",
  city: "臺北市", district: "文山區", road: "木柵路三段", village: "木柵里", villageCode: "63000080-021",
  lat: 24.98880, lng: 121.56010, askingWan: 1980, areaPing: 30, age: 38, floor: 4, buildingType: "公寓（無電梯）",
  market: market("臺北市", "文山區", "2025-10–2026-08", { avg: 63.1, median: 62.4, p25: 56.2, p75: 68.9 }, 1890, 61,
    [["2025-Q4", 62.0, 18], ["2026-Q1", 62.7, 15], ["2026-Q2", 63.5, 16], ["2026-Q3", 64.0, 12]]),
  commute: { destination: "臺北車站", mode: "transit", minutes: 41, meters: 13600 },
  transit: { station: "木柵", lines: ["BR"], meters: 420 },
  facilities: [
    { name: "捷運木柵站", category: "transport", types: ["subway_station", "transit_station"], dLat: 0.0021, dLng: 0.0018 },
    { name: "傳統市場", category: "shopping", dLat: -0.0011, dLng: 0.0008 },
    { name: "便利商店", category: "shopping", dLat: 0.0003, dLng: -0.0005 },
    { name: "小吃店", category: "food", dLat: -0.0006, dLng: -0.0010 },
    { name: "社區國中", category: "school", dLat: 0.0040, dLng: -0.0021 },
    { name: "河濱公園", category: "park", dLat: -0.0035, dLng: 0.0030 },
  ],
  risk: [
    layer("landslide", "山崩與地滑", "available", "農業部農村發展及水土保持署", "示範：查詢範圍內有山崩與地滑圖資紀錄；需現場確認邊坡與排水。"),
    layer("flood", "淹水潛勢", "no_match", "經濟部水利署", "未命中不代表零風險，只表示查詢範圍內未找到圖資紀錄。"),
    layer("liquefaction", "土壤液化潛勢", "no_match", "經濟部地質調查及礦業管理中心", "未命中不代表零風險，只表示查詢範圍內未找到圖資紀錄。"),
    layer("debris_flow", "土石流潛勢溪流", "unavailable", "農業部農村發展及水土保持署", "示範快照未取得此圖層；未知仍為未知。"),
    layer("geological_sensitivity", "地質敏感區", "limited", "經濟部地質調查及礦業管理中心", "示範：僅取得部分範圍，需人工查證是否位於地質敏感區。", "partial"),
  ],
  finance: {
    version: 1, case_id: DEMO_CASE_B_ID, revision: 1, input_fingerprint: `finance-v1|${DEMO_CASE_B_ID}|1|journey-browser-d3e00000-0b0b-4b0b-8b0b-00000000000b|asking|1980|30`,
    assumptions: { price_basis: "asking", active_price_wan: 1980, area_ping: 30 },
    calculation: { query: "succeeded", usability: "usable", completeness: "partial" },
    loan: { property_price_wan: 1980, down_payment_ratio: 0.3, down_payment_wan: 594, principal_wan: 1386, annual_interest_rate: 2.185, loan_years: 30, grace_period_years: 2, monthly_income_wan: null, monthly_payment_twd: 55183, grace_period_monthly_payment_twd: 25237, post_grace_monthly_payment_twd: 55183, total_interest_twd: 5287176 },
    holding: { known_monthly_subtotal_twd: 55433, known_annual_subtotal_twd: 665196, total_kind: "known_subtotal",
      assumptions: { loan_monthly_payment_twd: 55183, monthly_income_wan: null, area_ping: 30, management_fee_per_ping_twd: null, repair_reserve_per_ping_twd: null, annual_home_tax_rate_percent: null, annual_land_tax_rate_percent: null, annual_insurance_twd: 3000 },
      breakdown: [
        { key: "loan", label: "房貸月付（寬限期後）", status: "estimated", monthly_amount_twd: 55183, missing_reason: null },
        { key: "management", label: "管理費", status: "unestimated", monthly_amount_twd: null, missing_reason: "公寓無管委會，需確認公共修繕分攤方式" },
        { key: "repair_reserve", label: "修繕準備金", status: "unestimated", monthly_amount_twd: null, missing_reason: "屋齡較高，需自行估列屋頂與管線修繕" },
        { key: "tax_estimate", label: "房屋稅與地價稅", status: "unestimated", monthly_amount_twd: null, missing_reason: "尚未取得稅單或稅率" },
        { key: "insurance", label: "保險", status: "estimated", monthly_amount_twd: 250, missing_reason: null },
      ] },
    affordability: { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null },
    tax: { query: "not_started", summary: null },
    missing_costs: ["管理與公共修繕分攤（尚未確認）", "修繕準備金（尚未估列）", "交易成本（未納入）"],
    unresolved_actions: ["提供月收入以評估負擔", "確認寬限期結束後的月付能力"], calculated_at: AT,
  },
}];

const TITLES: Record<ExperienceLocale, [string, string]> = {
  "zh-TW": ["示範案件 A｜板橋電梯大樓", "示範案件 B｜木柵公寓"],
  en: ["Demo case A · Banqiao elevator building", "Demo case B · Muzha walk-up"],
  ja: ["デモ案件 A｜板橋のエレベーター付きマンション", "デモ案件 B｜木柵のアパート"],
  ko: ["예시 사례 A · 반차오 엘리베이터 아파트", "예시 사례 B · 무자 저층 아파트"],
};

/**
 * Illustrative village population for each demo, in the saved Location V2 shape and dated to the demo
 * snapshot like every other demo value. Never acquired from RIS; the demo notice labels it as a demo.
 */
const DEMO_POPULATION: Record<string, { total: number; households: number; child: number; working: number; elderly: number; change: number; trend: "increasing" | "decreasing" | "stable" }> = {
  [DEMO_CASE_A_ID]: { total: 6842, households: 2915, child: 0.118, working: 0.687, elderly: 0.195, change: -21, trend: "stable" },
  [DEMO_CASE_B_ID]: { total: 5127, households: 2264, child: 0.102, working: 0.654, elderly: 0.244, change: -63, trend: "decreasing" },
};

function demoVillageDemographics(spec: Spec): NonNullable<SavedCase["data"]["villageDemographics"]> {
  const people = DEMO_POPULATION[spec.id];
  return {
    version: 1, origin: { lat: spec.lat, lng: spec.lng }, checkedAt: AT,
    village: { status: "resolved", county: spec.city, town: spec.district, village: spec.village, village_code: spec.villageCode.replace("-", ""), district_code: spec.villageCode.split("-")[0],
      source: "nlsc_village_boundary", source_vintage: DEMO_SNAPSHOT_DATE, reason: "demo_snapshot" },
    demographics: { status: "available", reason: null, statistic_yyymm: "11508", statistic_month: "2026-08-01", total_population: people.total, household_count: people.households,
      average_household_size: Number((people.total / people.households).toFixed(2)), child_ratio: people.child, working_age_ratio: people.working, elderly_ratio: people.elderly,
      first_month: "11408", last_month: "11508", observed_month_count: 13, population_change: people.change, population_change_ratio: Number((people.change / people.total).toFixed(4)),
      household_change: Math.round(people.change / 3), has_month_gaps: false, trend_status: people.trend, source_provider: "RIS", source_dataset: "ODRP014" },
  };
}

function buildCase(spec: Spec, title: string): SavedCase {
  const address = `${spec.city}${spec.district}${spec.road}`;
  const places = spec.facilities.map((f, index) => ({ id: `${spec.id}-place-${index + 1}`, name: f.name, category: f.category, kind: classifyNearbyPlace(f.types, f.category), lat: Number((spec.lat + f.dLat).toFixed(6)), lng: Number((spec.lng + f.dLng).toFixed(6)), distanceM: 0 }));
  return {
    id: spec.id, title, createdAt: AT, updatedAt: AT, version: 1, workflowMode: "buying_wizard", activeWizardStep: "report", progress: 70,
    inputSummary: { city: spec.city, district: spec.district, road: spec.road, propertyPrice: spec.askingWan, areaPing: spec.areaPing },
    data: {
      inputs: { city: spec.city, district: spec.district, road: spec.road, building_type: spec.buildingType, area_ping: spec.areaPing, building_age_years: spec.age, floor: spec.floor },
      propertyIdentityAnchor: {
        version: 1, scope: "journey_browser_anchor", journey_anchor_id: spec.anchor, address_input: address, normalized_address: address,
        coordinates: { latitude: spec.lat, longitude: spec.lng }, administrative_location: { city: spec.city, district: spec.district, village: spec.village, village_code: spec.villageCode }, location_status: "candidate",
        parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
        building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_building_identity_evidence"], confirmation: null },
        confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["normalized_address"], limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"] },
        evidence: { sources: [{ source_id: "property_selection", kind: "user_selection", checked_at: AT }], checked_at: AT, limitations: ["journey_browser_correlation_only"] }, revalidation: { status: "current", conflicts: [] },
      },
      journeyContext: { version: 1, propertyContext: { city: spec.city, district: spec.district, road: address, addressSummary: address, sourceLabel: "示範快照", selectionStatus: "selected", askingPriceWan: spec.askingWan }, priceBasis: "asking", activePriceWan: spec.askingWan, valuationStatus: "unavailable" },
      marketInsight: spec.market,
      villageDemographics: demoVillageDemographics(spec),
      nearbyFacilities: { version: 1, source: "google_places", origin: { lat: spec.lat, lng: spec.lng }, radiusM: 800, checkedAt: AT, partial: false, successfulCategories: ["transport", "shopping", "food", "school", "medical", "park"], places },
      commuteRoute: { source: "google_routes", origin: { latitude: spec.lat, longitude: spec.lng }, destination: { address: spec.commute.destination }, mode: spec.commute.mode, distance_m: spec.commute.meters, duration_seconds: spec.commute.minutes * 60, duration_min: spec.commute.minutes, checked_at: AT, reason_code: "success", status: "resolved", partial: false, fallback: false },
      commuteTransit: { status: "resolved", source: "tdx", station_name: spec.transit.station, line_ids: spec.transit.lines, distance_meters: spec.transit.meters, source_updated_at: DEMO_SNAPSHOT_DATE, snapshot_generated_at: AT, message: "resolved" },
      terrainReference: { schema_version: 1, kind: "terrain_reference", status: "partial", summary: "示範快照：部分圖層有紀錄、部分未取得", notice: "示範快照，非即時查詢；未知仍為未知，未命中不代表安全。", layers: spec.risk },
      riskEvidenceCheckedAt: AT,
      financeEvidence: spec.finance,
    },
  };
}

export function buildDemoCases(locale: ExperienceLocale = "zh-TW"): SavedCase[] {
  return SPECS.map((spec, index) => buildCase(spec, TITLES[locale][index]));
}

type RoomText = { notes: string[]; items: Array<Pick<WorkItem, "kind" | "title" | "owner" | "status" | "resolution" | "note"> & { key: string; origin?: WorkItem["origin"]; sourceKey?: string; dueDate?: string }> };
const ROOMS: Record<ExperienceLocale, [RoomText, RoomText]> = {
  "zh-TW": [{
    notes: ["第二次看屋：採光良好，臨文化路一側車流聲明顯；地下室車道入口有擋水閘門。"],
    items: [
      { key: "flood", kind: "verification", title: "確認地下室與車道歷年淹水紀錄", owner: "管委會", status: "in_progress", resolution: "", origin: "risk", sourceKey: "risk-flood", note: "請管委會提供近十年颱風與豪雨的淹水紀錄。", dueDate: "2026-10-15" },
      { key: "liquefaction", kind: "verification", title: "查閱土壤液化潛勢與結構補強資料", owner: "買方", status: "open", resolution: "", origin: "risk", sourceKey: "risk-liquefaction", note: "比對官方圖資，並向屋主索取結構或耐震評估資料。" },
      { key: "fee", kind: "question", title: "管理費是否包含車位清潔與公共電費？", owner: "仲介", status: "open", resolution: "", note: "" },
      { key: "deed", kind: "task", title: "取得最新建物與土地登記謄本", owner: "代書", status: "blocked", resolution: "", note: "等待屋主提供委託書。", dueDate: "2026-10-20" },
      { key: "costs", kind: "task", title: "補齊修繕準備金與交易成本估算", owner: "買方", status: "open", resolution: "", origin: "finance", sourceKey: "finance-costs", note: "向管委會確認修繕準備金提撥標準。", dueDate: "2026-10-18" },
      { key: "asking", kind: "verification", title: "記錄開價來源與日期", owner: "買方", status: "done", resolution: "已保存仲介刊登頁面的開價與查看日期。", note: "" },
    ],
  }, {
    notes: ["看屋：四樓無電梯，屋況需整理；頂樓有加蓋，後側鄰近山坡。"],
    items: [
      { key: "slope", kind: "verification", title: "現場確認後側邊坡與排水狀況", owner: "買方", status: "open", resolution: "", origin: "risk", sourceKey: "risk-landslide", note: "雨後再看一次排水溝與擋土牆。" },
      { key: "roof", kind: "question", title: "頂樓加蓋是否有違建查報或漏水紀錄？", owner: "仲介", status: "open", resolution: "", note: "" },
      { key: "income", kind: "task", title: "整理家庭月收入，評估寬限期結束後月付", owner: "買方", status: "in_progress", resolution: "", note: "", dueDate: "2026-10-12" },
    ],
  }],
  en: [{
    notes: ["Second viewing: good daylight, noticeable traffic noise on the Wenhua Rd side; the basement ramp has a flood gate."],
    items: [
      { key: "flood", kind: "verification", title: "Confirm flood history of the basement and ramp", owner: "Management committee", status: "in_progress", resolution: "", origin: "risk", sourceKey: "risk-flood", note: "Ask management for typhoon and heavy-rain flooding records from the last ten years.", dueDate: "2026-10-15" },
      { key: "liquefaction", kind: "verification", title: "Review liquefaction potential and structural retrofit records", owner: "Buyer", status: "open", resolution: "", origin: "risk", sourceKey: "risk-liquefaction", note: "Compare the official map and ask the seller for structural or seismic assessments." },
      { key: "fee", kind: "question", title: "Does the management fee cover parking cleaning and shared electricity?", owner: "Agent", status: "open", resolution: "", note: "" },
      { key: "deed", kind: "task", title: "Obtain current building and land registry transcripts", owner: "Scrivener", status: "blocked", resolution: "", note: "Waiting for the seller's authorisation letter.", dueDate: "2026-10-20" },
      { key: "costs", kind: "task", title: "Fill in repair reserve and transaction cost estimates", owner: "Buyer", status: "open", resolution: "", origin: "finance", sourceKey: "finance-costs", note: "Ask management for the repair reserve contribution rate.", dueDate: "2026-10-18" },
      { key: "asking", kind: "verification", title: "Record the asking price source and date", owner: "Buyer", status: "done", resolution: "Saved the agent listing's asking price and viewing date.", note: "" },
    ],
  }, {
    notes: ["Viewing: 4th floor walk-up, needs renovation; rooftop addition; hillside behind the building."],
    items: [
      { key: "slope", kind: "verification", title: "Check the rear slope and drainage on site", owner: "Buyer", status: "open", resolution: "", origin: "risk", sourceKey: "risk-landslide", note: "Revisit after rain to check gutters and the retaining wall." },
      { key: "roof", kind: "question", title: "Has the rooftop addition been reported, or has it leaked?", owner: "Agent", status: "open", resolution: "", note: "" },
      { key: "income", kind: "task", title: "Gather household income to check payments after the grace period", owner: "Buyer", status: "in_progress", resolution: "", note: "", dueDate: "2026-10-12" },
    ],
  }],
  ja: [{
    notes: ["2回目の内見：採光は良好、文化路側の交通騒音が目立つ。地下スロープに止水板あり。"],
    items: [
      { key: "flood", kind: "verification", title: "地下とスロープの過去の浸水記録を確認", owner: "管理組合", status: "in_progress", resolution: "", origin: "risk", sourceKey: "risk-flood", note: "過去10年の台風・豪雨時の浸水記録を管理組合に依頼する。", dueDate: "2026-10-15" },
      { key: "liquefaction", kind: "verification", title: "液状化の可能性と構造補強の資料を確認", owner: "買主", status: "open", resolution: "", origin: "risk", sourceKey: "risk-liquefaction", note: "公式地図と照合し、売主に構造・耐震評価の資料を依頼する。" },
      { key: "fee", kind: "question", title: "管理費に駐車場清掃と共用電気代は含まれるか？", owner: "仲介業者", status: "open", resolution: "", note: "" },
      { key: "deed", kind: "task", title: "最新の建物・土地登記簿謄本を取得", owner: "代書", status: "blocked", resolution: "", note: "売主の委任状待ち。", dueDate: "2026-10-20" },
      { key: "costs", kind: "task", title: "修繕積立金と取引費用の見積もりを補う", owner: "買主", status: "open", resolution: "", origin: "finance", sourceKey: "finance-costs", note: "修繕積立金の基準を管理組合に確認する。", dueDate: "2026-10-18" },
      { key: "asking", kind: "verification", title: "売出価格の出典と日付を記録", owner: "買主", status: "done", resolution: "仲介の掲載ページの価格と閲覧日を保存済み。", note: "" },
    ],
  }, {
    notes: ["内見：4階・エレベーターなし、要リフォーム。屋上増築あり、裏手は斜面。"],
    items: [
      { key: "slope", kind: "verification", title: "裏手の斜面と排水状況を現地で確認", owner: "買主", status: "open", resolution: "", origin: "risk", sourceKey: "risk-landslide", note: "雨の後に側溝と擁壁を再確認する。" },
      { key: "roof", kind: "question", title: "屋上増築に違反建築の通報や雨漏りの記録はあるか？", owner: "仲介業者", status: "open", resolution: "", note: "" },
      { key: "income", kind: "task", title: "世帯月収を整理し、据置期間後の返済額を確認", owner: "買主", status: "in_progress", resolution: "", note: "", dueDate: "2026-10-12" },
    ],
  }],
  ko: [{
    notes: ["두 번째 방문: 채광 양호, 원화로 쪽 교통 소음이 큼. 지하 진입로에 차수판 있음."],
    items: [
      { key: "flood", kind: "verification", title: "지하층과 진입로의 과거 침수 기록 확인", owner: "관리위원회", status: "in_progress", resolution: "", origin: "risk", sourceKey: "risk-flood", note: "최근 10년간 태풍·호우 침수 기록을 관리위원회에 요청.", dueDate: "2026-10-15" },
      { key: "liquefaction", kind: "verification", title: "액상화 가능성과 구조 보강 자료 확인", owner: "매수인", status: "open", resolution: "", origin: "risk", sourceKey: "risk-liquefaction", note: "공식 지도와 대조하고 매도인에게 구조·내진 평가 자료 요청." },
      { key: "fee", kind: "question", title: "관리비에 주차장 청소와 공용 전기료가 포함되나요?", owner: "중개인", status: "open", resolution: "", note: "" },
      { key: "deed", kind: "task", title: "최신 건물·토지 등기부 등본 발급", owner: "대서인", status: "blocked", resolution: "", note: "매도인의 위임장 대기 중.", dueDate: "2026-10-20" },
      { key: "costs", kind: "task", title: "수선충당금과 거래 비용 추정치 보완", owner: "매수인", status: "open", resolution: "", origin: "finance", sourceKey: "finance-costs", note: "관리위원회에 수선충당금 적립 기준 확인.", dueDate: "2026-10-18" },
      { key: "asking", kind: "verification", title: "호가 출처와 날짜 기록", owner: "매수인", status: "done", resolution: "중개 매물 페이지의 호가와 확인 날짜를 저장함.", note: "" },
    ],
  }, {
    notes: ["방문: 4층 엘리베이터 없음, 수리 필요. 옥상 증축이 있고 건물 뒤편이 경사지."],
    items: [
      { key: "slope", kind: "verification", title: "뒤편 경사면과 배수 상태 현장 확인", owner: "매수인", status: "open", resolution: "", origin: "risk", sourceKey: "risk-landslide", note: "비 온 뒤 배수로와 옹벽을 다시 확인." },
      { key: "roof", kind: "question", title: "옥상 증축에 위반 건축 신고나 누수 기록이 있나요?", owner: "중개인", status: "open", resolution: "", note: "" },
      { key: "income", kind: "task", title: "가구 월소득을 정리해 거치 기간 이후 상환액 확인", owner: "매수인", status: "in_progress", resolution: "", note: "", dueDate: "2026-10-12" },
    ],
  }],
};
const ASKING_SOURCE: Record<ExperienceLocale, string> = {
  "zh-TW": "示範快照：仲介刊登開價（範例資料）",
  en: "Demo snapshot: agent listing asking price (example data)",
  ja: "デモスナップショット：仲介掲載の売出価格（サンプルデータ）",
  ko: "예시 스냅샷: 중개 매물 호가(예시 데이터)",
};

export function buildDemoRooms(locale: ExperienceLocale = "zh-TW"): DecisionRoom[] {
  return SPECS.map((spec, index) => {
    const text = ROOMS[locale][index];
    const items: WorkItem[] = text.items.map((item) => ({
      id: `${spec.id}-${item.key}`, kind: item.kind, title: item.title, owner: item.owner, dueDate: item.dueDate ?? "", status: item.status,
      resolution: item.resolution, origin: item.origin ?? "manual", sourceKey: item.sourceKey ?? "", note: item.note, createdAt: AT, updatedAt: AT,
    }));
    return {
      version: 1, caseId: spec.id, revision: 1, updatedAt: AT,
      notes: text.notes.map((note, n) => ({ id: `${spec.id}-note-${n + 1}`, date: "2026-09-27", text: note })),
      items, verifications: [],
      askingPrice: { priceWan: spec.askingWan, sourceUrl: "", sourceNote: ASKING_SOURCE[locale], checkedDate: DEMO_SNAPSHOT_DATE },
      history: items.map((item, n) => ({ id: `${spec.id}-history-${n + 1}`, at: AT, kind: `${item.kind}_added` as const, subject: item.title })),
    };
  });
}

export type DemoInstallMode = "ensure" | "restore";
export type DemoInstallBlocked = "storage_invalid" | "storage_unavailable" | "limit_reached";
export type DemoInstallPlan =
  | { kind: "blocked"; reason: DemoInstallBlocked }
  | { kind: "unchanged" }
  | { kind: "write"; rows: SavedCase[]; installed: string[] };

/**
 * Pure install plan. Only the two reserved demo IDs are ever inserted or replaced; every other
 * case keeps its position and content. "ensure" adds missing demos and leaves existing ones
 * (including the viewer's edits) untouched; "restore" resets both demos to the snapshot.
 * Capacity is checked against the saved-case limit; nothing is evicted to make room.
 */
export function planDemoInstall(read: Pick<SavedCaseReadDiagnostic, "status" | "cases">, mode: DemoInstallMode, demos: SavedCase[], maxCases: number): DemoInstallPlan {
  if (read.status === "storage_unavailable") return { kind: "blocked", reason: "storage_unavailable" };
  if (read.status === "parse_error" || read.status === "invalid_storage") return { kind: "blocked", reason: "storage_invalid" };
  const present = new Set(read.cases.map((row) => row.id));
  const missing = demos.filter((demo) => !present.has(demo.id));
  if (mode === "ensure" && missing.length === 0) return { kind: "unchanged" };
  if (read.cases.length + missing.length > maxCases) return { kind: "blocked", reason: "limit_reached" };
  const byId = new Map(demos.map((demo) => [demo.id, demo]));
  const rows = mode === "restore" ? read.cases.map((row) => byId.get(row.id) ?? row) : [...read.cases];
  return { kind: "write", rows: [...missing, ...rows], installed: mode === "restore" ? [...DEMO_CASE_IDS] : missing.map((demo) => demo.id) };
}
