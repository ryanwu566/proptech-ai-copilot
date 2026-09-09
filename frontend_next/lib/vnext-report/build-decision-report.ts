import { buildTerrainReferenceEvidence } from "@/lib/terrain-reference-evidence";
import { classifyTerrainSafety } from "@/lib/terrain-safety-gate";
import { buildViewingDecision } from "@/lib/viewing-decision";
import type { ViewingDecision, ViewingDecisionInputs } from "@/lib/viewing-decision";
import type {
  DecisionReportAdapterInput,
  DecisionReportModel,
  ReportDecisionModel,
  ReportEvidenceInput,
  ReportEvidenceStatus,
  ReportIdentityInput,
  ReportMetric,
  ReportSectionId,
  ReportSectionModel,
} from "@/lib/vnext-report/types";

const STATUS_LABELS: Record<ReportEvidenceStatus, string> = {
  available: "可用",
  partial: "部分可用",
  limited: "涵蓋有限",
  stale: "已過時",
  conflicting: "資料衝突",
  unknown: "未知",
  unavailable: "暫時不可用",
  error: "檢查失敗",
  no_match: "未命中",
  not_assessed: "未評估",
  unverified: "未驗證",
};

const CRITICAL_LABELS: Record<string, string> = {
  valuation: "估價與市場資料",
  loan: "貸款負擔資料",
  holding: "持有成本資料",
  location: "區位資料",
};

const ACTION_LABELS: Record<string, string> = {
  valuation: "補查估價與市場依據",
  loan: "補查貸款負擔",
  holding: "補查持有成本",
  location: "補查區位資料",
  check_terrain: "釐清地勢與災害風險",
  check_location: "釐清區位風險設施",
  check_loan: "重新檢視貸款負擔",
  check_holding: "重新檢視持有成本",
  check_risk: "釐清已知風險",
  view_report: "帶著本報告進行現場查核",
};

const DEFAULT_LIMITATIONS = [
  "本報告整理既有規則式結果與已提供證據，不是正式鑑價、銀行核貸、投資建議或法律意見。",
  "資料未知、不可用、未命中或未評估，都不代表數值為零、沒有風險或已通過檢查。",
  "人工確認物件身分只表示使用者完成辨識流程，不保證產權、界址、屋況或安全。",
];

export function evidenceStatusLabel(status: ReportEvidenceStatus): string {
  return STATUS_LABELS[status];
}

export function buildDecisionReport(input: DecisionReportAdapterInput): DecisionReportModel {
  const engineInput: ViewingDecisionInputs = {
    valuation: input.valuation,
    loan: input.loan,
    holding: input.holding,
    location: input.location,
    terrainRisk: input.terrainRisk,
    riskSummary: input.riskSummary,
    taxOracleResult: input.taxOracleResult,
  };
  const generatedDecision = buildViewingDecision(engineInput);
  const selectedDecision = input.decision ?? generatedDecision;
  const decisionConflict = Boolean(input.decision && input.decision.status !== generatedDecision.status);
  const evidence = (input.evidence ?? []).map((item) => ({ ...item, id: boundedIdentifier(item.id) }));
  const decision = buildDecisionModel(selectedDecision, generatedDecision, decisionConflict, evidence, input);
  const sections = [
    buildValuationSection(input, evidence),
    buildAffordabilitySection(input, evidence),
    buildTerrainSection(input, evidence),
    buildTaxSection(input, evidence),
  ];
  const suppliedActions = input.suppliedNextActions?.length
    ? input.suppliedNextActions
    : (input.riskSummary?.nextActions ?? []).map((label, index) => ({ id: `risk-action-${index + 1}`, label }));
  const fallbackAction = {
    id: selectedDecision.nextAction.targetId,
    label: ACTION_LABELS[selectedDecision.nextAction.label] ?? selectedDecision.nextAction.label,
    detail: "依既有看屋決策規則建議的下一步。",
  };
  const actions = suppliedActions.length ? suppliedActions : [fallbackAction];

  return {
    schemaVersion: 1,
    caseLabel: safeText(input.caseLabel, "未提供案件標籤"),
    propertyLabel: safeText(input.propertyLabel, "未提供物件標籤"),
    generatedAt: safeText(input.generatedAt, "產生時間未提供"),
    syntheticPreview: input.syntheticPreview,
    identity: buildIdentity(input.identity),
    decision,
    sections,
    evidence,
    checklist: actions.map((action) => ({
      ...action,
      id: safeIdentifier(action.id),
      reviewOnlyNotice: "勾選只記錄本頁的個人檢視進度，不會驗證證據、確認物件身分或寫入案件。",
    })),
    otherObservations: input.otherObservations ?? [],
    limitations: unique([...DEFAULT_LIMITATIONS, ...(input.reportLimitations ?? [])]),
  };
}

function buildDecisionModel(
  selected: ViewingDecision,
  generated: ViewingDecision,
  conflict: boolean,
  evidence: Array<ReportEvidenceInput & { id: string | null }>,
  input: DecisionReportAdapterInput,
): ReportDecisionModel {
  const knownRisks = selected.riskSources.map(riskSourceLabel);
  const terrainSafety = classifyTerrainSafety(input.terrainRisk);
  if (terrainSafety === "known_high") knownRisks.unshift("地勢／災害證據已顯示高風險，應先釐清後再決定後續行動。");
  const missingInformation = selected.missingCriticalData.map((key) => `${CRITICAL_LABELS[key] ?? key}尚未提供或不可用。`);
  if (terrainSafety === "incomplete" || terrainSafety === "absent") {
    missingInformation.push("地勢／空間證據未知、不可用或尚未評估；不能解讀為低風險。");
  }
  for (const item of evidence) {
    const warning = evidenceWarning(item);
    if (warning) missingInformation.push(warning);
  }
  if (conflict) {
    missingInformation.unshift(`供應的決策狀態（${selected.status}）與既有規則重新判定（${generated.status}）不一致。`);
  }
  const displayStatus = conflict ? "cannot_determine" : selected.status;
  const label = displayStatus === "cannot_determine"
    ? "無法判定：決策輸入與結果不一致"
    : {
      ready_to_view: "可安排看屋，仍需現場查核",
      needs_more_data: "資料不足，建議先補查",
      clarify_risk_first: "已知風險，建議先釐清",
    }[displayStatus];
  const summary = displayStatus === "cannot_determine"
    ? "目前輸入無法支持一致的呈現結論；保留已知風險並要求人工釐清。"
    : displayStatus === "clarify_risk_first"
      ? "已知高風險優先於其他缺漏；本報告不以整體缺資料掩蓋已知風險。"
      : displayStatus === "needs_more_data"
        ? "仍有關鍵資料缺漏或未知；這不是負面定論，也不是安全或適合購買的判定。"
        : "既有規則未發現已知高風險且關鍵分析已提供；這只代表可進一步看屋，不是購買建議。";

  return {
    sourceStatus: selected.status,
    displayStatus,
    label,
    summary,
    reasons: selected.reasons.map(decisionReasonLabel),
    knownRisks: unique(knownRisks),
    missingInformation: unique(missingInformation),
  };
}

function buildIdentity(identity: ReportIdentityInput): DecisionReportModel["identity"] {
  const label = {
    confirmed: "已由使用者確認",
    unverified: "尚未驗證",
    legacy_unverified: "舊案件／尚未驗證",
    resolving: "辨識處理中",
    conflicting: "身分資料衝突",
    unknown: "身分狀態未知",
  }[identity.status];
  const inconsistent = identity.status === "confirmed" && !identity.humanConfirmed;
  return {
    status: inconsistent ? "unknown" : identity.status,
    humanConfirmed: inconsistent ? false : identity.humanConfirmed,
    detail: inconsistent ? "確認狀態與人工確認紀錄不一致，無法判定。" : identity.detail,
    label: inconsistent ? "無法判定：確認紀錄不一致" : label,
    boundary: "人工確認僅代表身分辨識流程已完成，不保證法律產權、界址、屋況或安全。",
  };
}

function buildValuationSection(
  input: DecisionReportAdapterInput,
  evidence: Array<ReportEvidenceInput & { id: string | null }>,
): ReportSectionModel {
  const valuation = input.valuation;
  const status = input.sectionStates?.valuation ?? (valuation ? valuationStatus(valuation.data_status.freshness_status) : "not_assessed");
  const metrics: ReportMetric[] = [
    { label: "估算總價", value: valuation ? formatWan(valuation.estimate_total_price) : null },
    { label: "估價區間", value: valuation ? formatRange(valuation.price_range.low, valuation.price_range.high) : null },
    { label: "每坪估算", value: valuation ? formatWan(valuation.estimate_unit_price_per_ping, "萬／坪") : null },
    { label: "可比樣本", value: valuation && finite(valuation.valuation_explanation.sample_count) ? `${valuation.valuation_explanation.sample_count} 筆` : null },
  ];
  const observations = valuation
    ? [valuation.confidence_reason, `既有估價信心：${confidenceLabel(valuation.confidence)}。`, ...(input.propertySearch ? [input.propertySearch.summary.message] : [])]
    : ["估價與市場結果尚未提供，無法顯示價格數值。"];
  return sectionModel("valuation", "價格脈絡", "估價與市場摘要", status, metrics, observations, valuation ? [valuation.disclaimer] : ["缺少估價結果不表示物件價值為 0。"], evidence);
}

function buildAffordabilitySection(
  input: DecisionReportAdapterInput,
  evidence: Array<ReportEvidenceInput & { id: string | null }>,
): ReportSectionModel {
  const hasAny = Boolean(input.loan || input.holding);
  const derivedStatus = input.loan && input.holding ? "available" : hasAny ? "partial" : "not_assessed";
  const status = input.sectionStates?.affordability ?? derivedStatus;
  const metrics: ReportMetric[] = [
    { label: "每月房貸", value: input.loan ? formatCurrency(input.loan.monthly_payment) : null },
    { label: "房貸收入負擔", value: input.loan ? formatRatio(input.loan.income_burden_ratio) : null },
    { label: "每月總持有成本", value: input.holding ? formatCurrency(input.holding.monthly_total_holding_cost) : null },
    { label: "持有成本收入負擔", value: input.holding ? formatRatio(input.holding.income_burden_ratio) : null },
  ];
  const observations = [input.loan?.affordability_message, input.holding?.affordability_message].filter((value): value is string => Boolean(value));
  if (!observations.length) observations.push("負擔能力與持有成本尚未完成評估。");
  const limitations = [input.loan?.disclaimer, input.holding?.disclaimer].filter((value): value is string => Boolean(value));
  if (!limitations.length) limitations.push("缺少財務數值不表示付款或持有成本為 0。");
  return sectionModel("affordability", "現金流脈絡", "負擔能力與持有成本", status, metrics, observations, limitations, evidence);
}

function buildTerrainSection(
  input: DecisionReportAdapterInput,
  evidence: Array<ReportEvidenceInput & { id: string | null }>,
): ReportSectionModel {
  const reference = buildTerrainReferenceEvidence(input.terrainRisk);
  const safety = classifyTerrainSafety(input.terrainRisk);
  const status = input.sectionStates?.terrain ?? terrainState(reference.status);
  const metrics: ReportMetric[] = [
    { label: "安全分類閘門", value: terrainSafetyLabel(safety) },
    { label: "資料圖層", value: reference.layers.length ? `${reference.layers.length} 層` : null },
    { label: "整體風險層級", value: input.terrainRisk?.overall?.label ?? null },
    { label: "檢查時間", value: input.terrainRisk?.data_quality.checked_at ?? null },
  ];
  const observations = [reference.summary, ...(input.terrainRisk?.risk_factors.map((item) => `${item.title}：${item.message}`) ?? [])];
  const limitations = unique([reference.notice, input.terrainRisk?.disclaimer ?? "地勢／空間分析尚未完成，不能視為安全或無風險。"]) ;
  return sectionModel("terrain", "空間脈絡", "地勢與空間證據", status, metrics, observations, limitations, evidence);
}

function buildTaxSection(
  input: DecisionReportAdapterInput,
  evidence: Array<ReportEvidenceInput & { id: string | null }>,
): ReportSectionModel {
  const tax = input.taxOracleResult;
  const status = input.sectionStates?.tax ?? (tax ? "available" : "not_assessed");
  const metrics: ReportMetric[] = [
    { label: "既有資格結果", value: tax ? taxEligibilityLabel(tax.eligibility_status) : null },
    { label: "既有風險燈號", value: tax ? taxSignalLabel(tax.signal_color) : null },
    { label: "規則版本", value: tax?.official_rule_trace?.rule_version ?? null },
    { label: "規則生效日", value: tax?.official_rule_trace?.effective_date ?? null },
  ];
  const observations = tax
    ? [tax.ai_explanation.headline, ...(tax.manual_review_rules.length ? [`需人工複核：${tax.manual_review_rules.join("、")}`] : [])]
    : ["稅務與其他觀察尚未提供；本報告不自行計算或推定稅額。"];
  const limitations = tax ? [tax.disclaimer, tax.official_rule_trace?.limitation].filter((value): value is string => Boolean(value)) : ["未評估不代表符合資格，也不代表沒有稅務風險。"];
  return sectionModel("tax", "交易脈絡", "稅務與其他觀察", status, metrics, observations, limitations, evidence);
}

function sectionModel(
  id: ReportSectionId,
  eyebrow: string,
  title: string,
  status: ReportEvidenceStatus,
  metrics: ReportMetric[],
  observations: string[],
  limitations: string[],
  evidence: Array<ReportEvidenceInput & { id: string | null }>,
): ReportSectionModel {
  const linked = evidence.filter((item) => item.section === id && item.id).map((item) => item.id as string);
  return {
    id,
    eyebrow,
    title,
    status,
    summary: sectionSummary(status),
    metrics,
    observations: unique(observations.filter(Boolean)),
    limitations: unique(limitations.filter(Boolean)),
    evidenceIds: unique(linked),
  };
}

function decisionReasonLabel(reason: string): string {
  if (reason.startsWith("missing:")) {
    const labels = reason.slice("missing:".length).split(",").map((key) => CRITICAL_LABELS[key] ?? key);
    return `缺少關鍵分析：${labels.join("、")}。`;
  }
  if (reason.startsWith("high_item:")) return `既有風險摘要標示高風險：${reason.slice("high_item:".length)}。`;
  return {
    high_risk_default: "既有規則辨識到高風險訊號。",
    red_signal: "既有風險摘要為紅色警示。",
    loan_risky: "既有貸款計算顯示負擔風險。",
    holding_risky: "既有持有成本計算顯示負擔風險。",
    location_facility: "區位結果包含需釐清的風險設施。",
    tax_high: "既有稅務快篩顯示高風險或不符合資格。",
    terrain_high: "既有地勢分類顯示高風險。",
    missing_not_low_risk: "缺少資料不能解讀為低風險。",
    terrain_incomplete_not_low_risk: "地勢證據不完整，不能解讀為低風險。",
    ready_no_high_risk: "既有規則目前未辨識到已知高風險。",
    ready_on_site: "仍應在現場查核屋況、環境與文件。",
  }[reason] ?? `既有規則理由：${safeText(reason, "未提供")}`;
}

function riskSourceLabel(source: string): string {
  return decisionReasonLabel(source);
}

function evidenceWarning(item: ReportEvidenceInput): string | null {
  if (item.status === "available") return null;
  const subject = safeText(item.label, "未命名證據");
  return `${subject}：${evidenceStatusLabel(item.status)}。${statusBoundary(item.status)}`;
}

function statusBoundary(status: ReportEvidenceStatus): string {
  return {
    available: "",
    partial: "僅部分內容可用，未涵蓋處仍待查。",
    limited: "目前涵蓋有限，不能外推到未涵蓋範圍。",
    stale: "資料已超出新鮮度政策，後續行動前應更新。",
    conflicting: "來源間有實質不一致，應阻擋自動確認。",
    unknown: "目前無法判定，未知不等於低風險。",
    unavailable: "來源未能供應資料，不表示事實不存在。",
    error: "檢查未完成；錯誤狀態不能解讀為低風險或通過。",
    no_match: "只表示在已聲明的查詢範圍未命中，不代表沒有風險。",
    not_assessed: "尚未執行評估，不能視為通過。",
    unverified: "內容尚未驗證，不能作為權威確認。",
  }[status];
}

function sectionSummary(status: ReportEvidenceStatus): string {
  return status === "available" ? "目前有資料可供檢視；仍須連同來源、時間與限制閱讀。" : statusBoundary(status);
}

function terrainState(status: ReturnType<typeof buildTerrainReferenceEvidence>["status"]): ReportEvidenceStatus {
  return status;
}

function terrainSafetyLabel(status: ReturnType<typeof classifyTerrainSafety>): string {
  return {
    known_low: "已有低風險參考（不形成安全保證）",
    known_high: "已知高風險",
    caution: "需審慎檢視",
    incomplete: "資料不完整／不可用",
    absent: "未評估",
  }[status];
}

function valuationStatus(status: string): ReportEvidenceStatus {
  if (status === "stale") return "stale";
  if (status === "unknown" || status === "no_official_data" || status === "unavailable") return status === "unavailable" ? "unavailable" : "unknown";
  if (status === "aging") return "limited";
  return "available";
}

function confidenceLabel(value: "high" | "medium" | "low"): string {
  return { high: "高", medium: "中", low: "低" }[value];
}

function taxEligibilityLabel(value: "eligible" | "manual_review" | "not_eligible"): string {
  return { eligible: "初步符合", manual_review: "需人工複核", not_eligible: "初步不符合" }[value];
}

function taxSignalLabel(value: "green" | "yellow" | "red"): string {
  return { green: "綠燈", yellow: "黃燈", red: "紅燈" }[value];
}

function formatWan(value: number, unit = "萬"): string | null {
  return finite(value) ? `${new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 1 }).format(value)} ${unit}` : null;
}

function formatRange(low: number, high: number): string | null {
  const lowLabel = formatWan(low);
  const highLabel = formatWan(high);
  return lowLabel && highLabel ? `${lowLabel}－${highLabel}` : null;
}

function formatCurrency(value: number): string | null {
  return finite(value) ? new Intl.NumberFormat("zh-TW", { style: "currency", currency: "TWD", maximumFractionDigits: 0 }).format(value) : null;
}

function formatRatio(value: number | null): string | null {
  return finite(value) ? `${new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 1 }).format(value as number)}%` : null;
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function boundedIdentifier(value?: string | null): string | null {
  if (!value || !value.trim()) return null;
  const selected = value.trim();
  return selected.length <= 64 ? selected : `${selected.slice(0, 40)}…${selected.slice(-12)}`;
}

function safeIdentifier(value: string): string {
  const selected = value.trim().replace(/[^a-zA-Z0-9_-]/g, "-").slice(0, 80);
  return selected || "review-item";
}

function safeText(value: string, fallback: string): string {
  const selected = value?.trim();
  return selected ? selected.slice(0, 4000) : fallback;
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}
