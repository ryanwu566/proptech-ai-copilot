import type {
  HoldingCostResult,
  LoanCalculationResult,
  LocationInsightResult,
  TaxResult,
  TerrainHazardLayer,
  TerrainRiskResult,
  ValuationResult,
} from "@/lib/api";
import { buildDecisionReport } from "@/lib/vnext-report";
import type { DecisionReportAdapterInput, DecisionReportModel, ReportEvidenceInput } from "@/lib/vnext-report";
import { buildViewingDecision } from "@/lib/viewing-decision";

export type ReportPreviewScenario = {
  id: string;
  title: string;
  description: string;
  report: DecisionReportModel;
};

const GENERATED_AT = "2026-09-09T02:30:00Z";
const RETRIEVED_AT = "2026-09-08T06:15:00Z";
const EFFECTIVE_AT = "2026-08-31T16:00:00Z";

const baseValuation: ValuationResult = {
  source: "mock_fallback",
  data_status: {
    active_source: "mock_fallback",
    is_demo_data: true,
    is_full_taiwan: false,
    coverage: { cities: ["合成城市"], districts: ["合成行政區"], roads_count: 1, records_count: 8 },
    last_updated: RETRIEVED_AT,
    update_frequency_note: "合成預覽固定資料，不會更新。",
    source_note: "僅供本機 UI 預覽。",
    user_message: "合成估價結果。",
    freshness_status: "fresh",
    freshness_reason_code: "synthetic_preview_fixed_time",
    freshness_as_of: GENERATED_AT,
    latest_import_at: RETRIEVED_AT,
    latest_import_age_days: 1,
    newest_effective_period_lag_months: 1,
    operator_attention_required: false,
    freshness_user_message: "合成資料的新鮮度只用於呈現測試。",
  },
  data_composition: "sample",
  estimate_data_composition: "sample",
  estimate_source_label: "合成可比案例（測試）",
  candidate_pool_size: 8,
  official_same_road_count: 0,
  official_same_district_count: 0,
  sample_same_road_count: 5,
  sample_same_district_count: 8,
  estimate_level: "road",
  matched_community: null,
  confidence_reason: "合成案例有 8 筆可比資料；僅測試報告版面，不代表真實市場信心。",
  source_details: {
    file: "synthetic-preview-fixture",
    nature: "test",
    complete_real_price_registry: false,
    formal_appraisal: false,
    bank_appraisal: false,
    future_adapter: "Future Case/Evidence presentation adapter",
  },
  estimate_total_price: 1688,
  estimate_unit_price_per_ping: 51.2,
  price_range: { low: 1580, mid: 1688, high: 1795 },
  unit_price_distribution: { weighted_mean: 51.2, weighted_median: 50.8, p25: 48.6, p75: 53.4 },
  confidence: "medium",
  confidence_score: 72,
  comparables: [],
  valuation_explanation: {
    sample_count: 8,
    same_road_count: 5,
    same_district_count: 8,
    same_city_count: 8,
    same_building_type_count: 6,
    nearest_distance_m: 180,
    average_area_difference_ping: 2.4,
    average_age_difference_years: 3,
    average_similarity_score: 0.81,
    method: "既有估價引擎輸出的合成固定結果。",
  },
  methodology: ["沿用既有估價結果；報告層不重新計算。"],
  disclaimer: "合成估價僅供 UI 預覽，不是正式鑑價或銀行估價。",
};

const baseLoan: LoanCalculationResult = {
  property_price_wan: 1688,
  down_payment_ratio: 0.3,
  down_payment_wan: 506.4,
  loan_amount_wan: 1181.6,
  annual_interest_rate: 2.25,
  loan_years: 30,
  grace_period_years: 0,
  monthly_income_wan: 18,
  monthly_payment: 45178,
  grace_period_monthly_payment: null,
  post_grace_monthly_payment: null,
  total_payment: 16264080,
  total_interest: 4448080,
  income_burden_ratio: 25.1,
  affordability_level: "manageable",
  affordability_message: "既有貸款計算顯示目前負擔屬可管理範圍；仍須以銀行實際核貸為準。",
  sensitivity: [],
  disclaimer: "貸款試算不是銀行核貸承諾，利率與條件需另行確認。",
};

const baseHolding: HoldingCostResult = {
  input: {
    property_price_wan: 1688,
    loan_monthly_payment: 45178,
    monthly_income_wan: 18,
    area_ping: 33,
    management_fee_per_ping: 85,
    repair_reserve_per_ping: 45,
    annual_home_tax_rate: 0.012,
    annual_land_tax_rate: 0.002,
    annual_insurance: 7200,
    include_tax_estimate: true,
  },
  property_price_wan: 1688,
  loan_monthly_payment: 45178,
  monthly_management_fee: 2805,
  monthly_repair_reserve: 1485,
  monthly_tax_estimate: 3376,
  annual_home_tax_estimate: 33760,
  annual_land_tax_estimate: 6752,
  monthly_insurance: 600,
  monthly_total_holding_cost: 53444,
  annual_total_holding_cost: 641328,
  income_burden_ratio: 29.7,
  affordability_level: "manageable",
  affordability_message: "既有持有成本計算顯示可管理；修繕與實際稅費仍待查。",
  cost_breakdown: [],
  disclaimer: "持有成本為既有試算結果，不是實際帳單或新稅額計算。",
};

const baseLocation: LocationInsightResult = {
  input: { synthetic: true },
  resolved_location: { address_label: "合成地址標籤", latitude: 25.01, longitude: 121.48, geocoding_confidence: "synthetic" },
  radius_m: 800,
  location_score: 74,
  category_scores: { transit_score: 78, convenience_score: 75, education_score: 68, green_space_score: 72, medical_score: 76, risk_score: 70 },
  poi_summary: { transit_count: 4, convenience_count: 8, school_count: 2, park_count: 2, medical_count: 3, risk_facility_count: 0 },
  nearest_pois: [],
  strengths: ["合成情境：步行生活機能資料已提供。"],
  weaknesses: ["尖峰通勤與夜間噪音仍須現場確認。"],
  buyer_fit: { self_use_family: "待實地確認", commuter: "可進一步看屋", investor: "未評估", elderly: "待確認無障礙動線" },
  valuation_context: { supports_price_reasonableness: "unknown", explanation: "區位結果僅提供脈絡，不直接決定價格合理性。" },
  data_quality: { status: "good", missing_sources: [], warnings: ["全部為合成固定資料。"] },
  scoring_method: { weights: {}, explanation: "沿用既有區位結果；報告不重算分數。" },
  disclaimer: "區位資訊需以現場狀況與各來源涵蓋範圍為準。",
};

const baseTax: TaxResult = {
  eligibility_status: "manual_review",
  risk_score: 20,
  signal_color: "yellow",
  hard_fail_rules: [],
  manual_review_rules: ["synthetic_documents_review"],
  missing_docs: ["合成文件 A"],
  reminder_timeline: [],
  rule_traces: [],
  ai_explanation: { headline: "既有 TaxOracle 結果要求人工複核文件。", customer_script: "合成預覽文案。", source: "existing_taxoracle_result" },
  disclaimer: "TaxOracle 僅為初步快篩，不是稅務核定或法律意見。",
  case_input: {
    case_id: "synthetic-case-c",
    client_name: "合成使用者",
    sold_self_occupied: true,
    residency_condition_met: true,
    purchase_within_reasonable_period: true,
    purchased_self_occupied: true,
    same_owner: true,
    land_value_available: true,
    required_docs_complete: false,
    enters_five_year_monitoring: false,
    exceptional_circumstances: false,
  },
  official_rule_trace: {
    rule_version: "synthetic-rule-fixture-v1",
    jurisdiction: "合成管轄區",
    effective_date: EFFECTIVE_AT,
    source_name: "合成規則來源（測試）",
    source_status: "test",
    calculation_kind: "existing_result_fixture",
    limitation: "不是官方規則或最新法規，只測試既有結果的呈現。",
  },
  tax_output_boundary: "preliminary_screening_only",
};

function hazard(key: TerrainHazardLayer["key"], label: string, level: TerrainHazardLayer["level"] = "low", status: TerrainHazardLayer["status"] = "available"): TerrainHazardLayer {
  return {
    key,
    label,
    status,
    level,
    matched: status === "available",
    distance_m: null,
    value: null,
    explanation: status === "available" ? `${label}合成圖層已完成參考比對。` : `${label}合成圖層暫時不可用。`,
    source: { name: "synthetic-terrain-layer", agency: "合成資料提供者（測試）", status: "test", fetched_at: RETRIEVED_AT, data_updated_at: EFFECTIVE_AT, limitation: "非真實官方來源。" },
  };
}

function terrainResult(mode: "low" | "high" | "unavailable"): TerrainRiskResult {
  const unavailable = mode === "unavailable";
  const level = unavailable ? "unknown" : mode;
  const status = unavailable ? "unavailable" : "available";
  const layers = [
    ["slope", "坡度"], ["landslide", "崩塌"], ["debris_flow", "土石流"], ["flood", "淹水"],
    ["geological_sensitivity", "地質敏感"], ["liquefaction", "土壤液化"], ["active_fault", "活動斷層"],
  ].map(([layer_id, display_name]) => ({
    layer_id,
    display_name,
    source_name: "合成地勢資料集（測試）",
    source_kind: "test",
    assessment_status: unavailable ? "unavailable" as const : "matched" as const,
    coverage_status: unavailable ? "unknown" as const : "covered" as const,
    data_updated_at: EFFECTIVE_AT,
    caveat: unavailable ? "提供者不可用；不代表沒有風險。" : "合成預覽結果，不形成安全結論。",
  }));
  return {
    input: { synthetic: "track-c-preview" },
    resolved_location: { address_label: "合成定位點", geocoding_confidence: "synthetic", geocoding_source: "mock" },
    overall: {
      level,
      label: unavailable ? "無法判定" : mode === "high" ? "高風險" : "低風險參考",
      summary: unavailable ? "合成提供者不可用。" : mode === "high" ? "合成高風險圖層命中，必須先釐清。" : "合成資料目前為低風險參考。",
      confidence: unavailable ? "unknown" : "medium",
    },
    terrain: { status, explanation: unavailable ? "坡度資料不可用。" : "合成坡度資料已評估。", source: hazard("slope", "坡度", level, status).source },
    hazards: {
      landslide: hazard("landslide", "崩塌", mode === "high" ? "high" : level, status),
      debris_flow: hazard("debris_flow", "土石流", level, status),
      flood: hazard("flood", "淹水", level, status),
      geological_sensitivity: hazard("geological_sensitivity", "地質敏感", level, status),
      liquefaction: hazard("liquefaction", "土壤液化", level, status),
      active_fault: hazard("active_fault", "活動斷層", level, status),
    },
    risk_factors: mode === "high" ? [{ key: "synthetic-landslide", level: "high", title: "合成崩塌風險", message: "已知高風險測試訊號不得被缺漏資料隱藏。", source_name: "合成地勢資料集（測試）" }] : [],
    missing_sources: unavailable ? ["synthetic_terrain_provider"] : [],
    recommended_checks: ["看屋前向合格專業人員確認地勢與災害資料。"],
    map_layers: [],
    source_transparency: { notice: "合成測試來源，非官方資料。", layers },
    data_quality: { status: unavailable ? "unavailable" : "good", warnings: ["合成預覽資料。"], checked_at: RETRIEVED_AT },
    disclaimer: "地勢與災害資料僅供看房風險參考，不形成安全結論。",
  };
}

function evidence(statuses: Partial<Record<"valuation" | "affordability" | "terrain" | "tax" | "identity", ReportEvidenceInput["status"]>> = {}): ReportEvidenceInput[] {
  return [
    evidenceItem("valuation", "ev-synth-valuation-0001", "合成估價可比資料", statuses.valuation ?? "available"),
    evidenceItem("affordability", "ev-synth-affordability-0002", "既有貸款與持有成本結果", statuses.affordability ?? "available"),
    evidenceItem("terrain", "ev-synth-terrain-0003", "合成地勢圖層摘要", statuses.terrain ?? "available"),
    evidenceItem("tax", "ev-synth-tax-0004", "既有 TaxOracle 快篩結果", statuses.tax ?? "available"),
    evidenceItem("identity", "ev-synth-identity-0005", "合成人工身分確認紀錄", statuses.identity ?? "available"),
  ];
}

function evidenceItem(section: ReportEvidenceInput["section"], id: string, label: string, status: ReportEvidenceInput["status"]): ReportEvidenceInput {
  return {
    id,
    section,
    label,
    status,
    sourceLabel: "合成固定資料（test environment）",
    retrievedAt: RETRIEVED_AT,
    effectiveAt: EFFECTIVE_AT,
    coverage: status === "partial" || status === "limited" ? "只涵蓋合成案例的部分欄位" : "只涵蓋本機合成預覽情境",
    limitation: status === "available" ? "僅供 UI 與列印測試，不代表真實或官方證據。" : `${status} 狀態刻意保留，不可提升為可用。`,
  };
}

const sufficientInput: DecisionReportAdapterInput = {
  caseLabel: "Synthetic Case C-001",
  propertyLabel: "合成物件｜河岸生活圈 33 坪",
  generatedAt: GENERATED_AT,
  syntheticPreview: true,
  identity: { status: "confirmed", humanConfirmed: true, detail: "合成情境中已完成使用者身分辨識；不代表產權或安全確認。" },
  valuation: baseValuation,
  loan: baseLoan,
  holding: baseHolding,
  location: baseLocation,
  terrainRisk: terrainResult("low"),
  taxOracleResult: baseTax,
  decision: buildViewingDecision({ valuation: baseValuation, loan: baseLoan, holding: baseHolding, location: baseLocation, terrainRisk: terrainResult("low"), taxOracleResult: baseTax }),
  evidence: evidence(),
  otherObservations: ["區位資料建議在白天與夜間各完成一次現場觀察。", "管理規約、修繕紀錄與實際費用尚須向賣方或管理單位確認。"],
  suppliedNextActions: [
    { id: "documents", label: "攜帶待確認文件清單", detail: "確認權狀、謄本、管理規約與修繕紀錄是否可供檢視。" },
    { id: "terrain", label: "現場核對地勢與排水", detail: "低風險參考不形成安全保證。" },
    { id: "costs", label: "向銀行與管理單位核對費用", detail: "不要以試算結果代替正式報價或帳單。" },
  ],
};

function scenario(id: string, title: string, description: string, input: DecisionReportAdapterInput): ReportPreviewScenario {
  return { id, title, description, report: buildDecisionReport(input) };
}

export const REPORT_PREVIEW_SCENARIOS: ReportPreviewScenario[] = [
  scenario("sufficient", "充足的合成證據", "核心分析齊備，仍保留看屋與證據限制。", sufficientInput),
  scenario("known-high-missing", "已知高風險＋其他缺漏", "高風險優先呈現，不被持有成本缺漏掩蓋。", {
    ...sufficientInput,
    caseLabel: "Synthetic Case C-002",
    propertyLabel: "合成物件｜坡地風險釐清案例",
    terrainRisk: terrainResult("high"),
    holding: undefined,
    decision: undefined,
    evidence: evidence({ terrain: "limited", affordability: "partial" }),
  }),
  scenario("terrain-unavailable", "地勢未知／提供者不可用", "未知不能變成低風險或全數通過。", {
    ...sufficientInput,
    caseLabel: "Synthetic Case C-003",
    propertyLabel: "合成物件｜地勢來源暫時不可用",
    terrainRisk: terrainResult("unavailable"),
    decision: undefined,
    evidence: evidence({ terrain: "unavailable" }),
  }),
  scenario("mixed-quality", "部分／過時／衝突證據", "逐項保留部分、過時與衝突狀態。", {
    ...sufficientInput,
    caseLabel: "Synthetic Case C-004",
    propertyLabel: "合成物件｜多來源品質差異案例",
    evidence: evidence({ terrain: "partial", valuation: "stale", tax: "conflicting", identity: "unverified" }),
    sectionStates: { terrain: "partial", valuation: "stale", tax: "conflicting" },
    reportLimitations: ["稅務來源間存在衝突；在完成來源核對前不得視為已確認。"],
  }),
  scenario("missing-valuation-identity", "缺少估價＋身分未確認", "數值缺漏不顯示為零，身分狀態保持未驗證。", {
    ...sufficientInput,
    caseLabel: "Synthetic Case C-005",
    propertyLabel: "合成物件｜待辨識與估價",
    identity: { status: "unverified", humanConfirmed: false, detail: "目前只有使用者輸入的描述，尚未完成物件身分辨識。" },
    valuation: undefined,
    decision: undefined,
    evidence: evidence({ valuation: "not_assessed", identity: "unverified" }),
    sectionStates: { valuation: "not_assessed" },
  }),
  scenario("long-text", "長文字與窄螢幕", "驗證長來源、限制、識別碼與說明能換行。", {
    ...sufficientInput,
    caseLabel: "Synthetic Case C-006 / LONG-CONTENT-WRAPPING-PREVIEW",
    propertyLabel: "合成物件｜這是一個刻意很長的物件標籤，用來確認手機版與列印版不會因為連續文字、來源說明或限制內容而水平溢出",
    evidence: [{
      id: "synthetic-evidence-identifier-with-deliberately-long-content-abcdefghijklmnopqrstuvwxyz-0123456789",
      section: "other",
      label: "很長的合成證據名稱：都市計畫、建物管理、環境觀察與其他跨欄位資料的綜合來源顯示測試",
      status: "limited",
      sourceLabel: "合成來源名稱非常長而且不包含任何真實提供者或正式機關宣稱-synthetic-source-only-for-layout-testing",
      retrievedAt: RETRIEVED_AT,
      effectiveAt: null,
      coverage: "僅涵蓋一個合成點位、單一時間切片與部分欄位；未涵蓋法律產權、結構安全、實際屋況、未來環境變化或其他未列出的範圍。",
      limitation: "這段限制文字刻意拉長，確認畫面與 A4 列印時可以自然換行，不會截斷重要警示，也不會把未知或未提供的資料改寫成安全、零風險或已完成確認。",
    }],
    otherObservations: ["長文字測試：" + "現場仍需逐項查核屋況、採光、噪音、排水、逃生動線、管理規約與文件。".repeat(4)],
  }),
  scenario("inconsistent-input", "決策結果與輸入不一致", "供應結果與既有規則衝突時，呈現無法判定並保留已知風險。", {
    ...sufficientInput,
    caseLabel: "Synthetic Case C-008",
    propertyLabel: "合成物件｜不一致輸入失敗關閉案例",
    terrainRisk: terrainResult("high"),
    holding: undefined,
    evidence: evidence({ terrain: "conflicting", affordability: "partial" }),
  }),
  scenario("all-missing", "全部資料缺漏", "所有分析維持未評估，仍呈現來源與限制缺漏。", {
    caseLabel: "Synthetic Case C-007",
    propertyLabel: "合成物件｜全部資料尚未提供",
    generatedAt: GENERATED_AT,
    syntheticPreview: true,
    identity: { status: "unknown", humanConfirmed: false, detail: "沒有可用的身分辨識資料。" },
    evidence: [],
    otherObservations: [],
    reportLimitations: ["未提供任何 Case/Evidence 後端投影資料。"],
  }),
];

export function getReportPreviewScenario(id?: string): ReportPreviewScenario {
  return REPORT_PREVIEW_SCENARIOS.find((item) => item.id === id) ?? REPORT_PREVIEW_SCENARIOS[0];
}
