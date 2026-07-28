import type { PropertyCaseDraft, PropertyCaseStatus } from "@/lib/property-case";
import type {
  PropertyCaseFinancialAnalysis,
  PropertyCaseFinancialScenarioResult,
} from "@/lib/property-case-financials";
import type { DueDiligenceItem, DueDiligenceReadinessResult } from "@/lib/property-case-due-diligence";
import type { ViewingOfferReadinessResult } from "@/lib/property-case-viewing-offer";
import type { TimelineReadinessResult } from "@/lib/property-case-timeline";

export type PropertyCaseVisualState = "completed" | "partial" | "missing" | "blocked" | "not_assessed";

export type PropertyCaseVisualSection = {
  id: string;
  label: string;
  state: PropertyCaseVisualState;
  completedCount: number;
  totalCount: number;
  missingItems: string[];
};

export type PropertyCaseVisualScenario = {
  scenarioName: string;
  analysis: PropertyCaseFinancialAnalysis;
};

export type PropertyCaseVisualModel = {
  headline: string;
  addressSummary: string;
  decisionStatus: string;
  summary: string;
  sections: PropertyCaseVisualSection[];
  overall: {
    completedCount: number;
    totalCount: number;
    completionRatio: number | null;
  };
  scenarios: PropertyCaseVisualScenario[];
  missingItems: string[];
  evidence: Array<{ label: string; value: string }>;
};

export type PropertyCaseVisualInput = {
  draft: PropertyCaseDraft;
  financialAnalysis: PropertyCaseFinancialAnalysis;
  financialScenarios: PropertyCaseFinancialScenarioResult[];
  dueDiligenceReadiness: DueDiligenceReadinessResult;
  dueDiligenceItems: DueDiligenceItem[];
  viewingOfferReadiness: ViewingOfferReadinessResult;
  timelineReadiness: TimelineReadinessResult;
};

export function buildPropertyCaseVisualModel(input: PropertyCaseVisualInput): PropertyCaseVisualModel {
  const { draft } = input;
  const basic = buildBasicSection(draft);
  const financial = buildFinancialSection(input.financialAnalysis);
  const valueTax = buildStatusSection("value_tax", "估價與稅費", [
    ["估價資料", draft.analysis_status.valuation],
    ["稅費資料", draft.analysis_status.tax],
  ]);
  const locationMarket = buildStatusSection("location_market", "位置與市場", [
    ["位置分析", draft.analysis_status.location],
    ["地勢風險", draft.analysis_status.terrain],
    ["通勤參考", draft.analysis_status.commute],
  ]);
  const dueDiligence = buildDueDiligenceSection(input.dueDiligenceReadiness, input.dueDiligenceItems);
  const viewingOffer = buildViewingSection(input.viewingOfferReadiness);
  const decision = buildDecisionSection(draft);
  const timeline = buildTimelineSection(input.timelineReadiness, draft.case_milestones.length);
  const sections = [basic, financial, valueTax, locationMarket, dueDiligence, viewingOffer, decision, timeline];
  const completedCount = sections.reduce((sum, section) => sum + section.completedCount, 0);
  const totalCount = sections.reduce((sum, section) => sum + section.totalCount, 0);

  return {
    headline: draft.case_name || "尚未命名案件",
    addressSummary: draft.property_input.address || "尚未提供地址／識別",
    decisionStatus: draft.decision_status,
    summary: totalCount === 0
      ? "尚無可評估項目。"
      : `目前已完成 ${completedCount} / ${totalCount} 個明確資料項目；完整度不代表風險或購買結論。`,
    sections,
    overall: {
      completedCount,
      totalCount,
      completionRatio: totalCount > 0 ? completedCount / totalCount : null,
    },
    scenarios: [
      { scenarioName: "基準方案", analysis: input.financialAnalysis },
      ...input.financialScenarios.map((scenario) => ({ scenarioName: scenario.scenarioName, analysis: scenario })),
    ],
    missingItems: sections.flatMap((section) => section.missingItems),
    evidence: [
      { label: "估價證據狀態", value: statusLabel(draft.analysis_status.valuation) },
      { label: "位置分析狀態", value: statusLabel(draft.analysis_status.location) },
      { label: "地勢風險狀態", value: statusLabel(draft.analysis_status.terrain) },
      { label: "通勤參考狀態", value: statusLabel(draft.analysis_status.commute) },
      { label: "盡職調查狀態", value: input.dueDiligenceReadiness.readiness },
      { label: "看屋／出價狀態", value: input.viewingOfferReadiness.readiness },
      { label: "時間軸狀態", value: input.timelineReadiness.readiness },
    ],
  };
}

function buildBasicSection(draft: PropertyCaseDraft): PropertyCaseVisualSection {
  const checks: Array<[string, boolean]> = [
    ["案件名稱", Boolean(draft.case_name.trim())],
    ["地址／物件識別", Boolean(draft.property_input.address.trim())],
    ["物件類型", Boolean(draft.property_input.property_type.trim())],
    ["開價或可比較價格", positiveOrZero(draft.property_input.listing_price)],
  ];
  return section("basic", "基本資料", checks);
}

function buildFinancialSection(analysis: PropertyCaseFinancialAnalysis): PropertyCaseVisualSection {
  const metrics: Array<[string, boolean]> = [
    ["總承諾金額", analysis.totalCommitment.status === "available"],
    ["初期所需現金", analysis.cashNeeded.status === "available"],
    ["每月月付", analysis.monthlyPayment.status === "available"],
    ["每月總負擔", analysis.monthlyBurden.status === "available"],
  ];
  return section("financial", "財務", metrics);
}

function buildStatusSection(
  id: string,
  label: string,
  rows: Array<[string, PropertyCaseStatus]>,
): PropertyCaseVisualSection {
  const completedCount = rows.filter(([, status]) => status === "completed").length;
  const missingItems = rows.filter(([, status]) => status !== "completed").map(([name, status]) => `${name}：${statusLabel(status)}`);
  const unavailable = rows.some(([, status]) => status === "unavailable");
  return {
    id,
    label,
    state: unavailable ? (completedCount > 0 ? "partial" : "not_assessed") : stateFromCounts(completedCount, rows.length),
    completedCount,
    totalCount: rows.length,
    missingItems,
  };
}

function buildDueDiligenceSection(
  readiness: DueDiligenceReadinessResult,
  items: DueDiligenceItem[],
): PropertyCaseVisualSection {
  const completedCount = readiness.confirmed_count;
  const missingItems = items
    .filter((item) => item.status !== "confirmed" && item.status !== "not_applicable")
    .map((item) => `${item.label}：${item.status}`);
  return {
    id: "due_diligence",
    label: "盡職調查",
    state: readiness.blocked_count > 0
      ? "blocked"
      : readiness.readiness === "completed"
        ? "completed"
        : readiness.readiness === "partial"
          ? "partial"
          : "not_assessed",
    completedCount,
    totalCount: readiness.item_count,
    missingItems,
  };
}

function buildViewingSection(readiness: ViewingOfferReadinessResult): PropertyCaseVisualSection {
  const checks: Array<[string, boolean]> = [
    ["完成看屋紀錄", readiness.completed_viewing_count > 0],
    ["待問問題已處理", readiness.open_question_count === 0 && readiness.viewing_count > 0],
    ["出價方案", readiness.offer_plan_count > 0],
  ];
  const item = section("viewing_offer", "看屋與出價", checks);
  return {
    ...item,
    state: readiness.readiness === "not_provided" ? "not_assessed" : item.state,
    missingItems: [
      ...item.missingItems,
      ...(readiness.next_step_count > 0 ? [`尚有 ${readiness.next_step_count} 項手動下一步`] : []),
    ],
  };
}

function buildDecisionSection(draft: PropertyCaseDraft): PropertyCaseVisualSection {
  return section("decision", "決策摘要", [
    ["決策狀態", Boolean(draft.decision_status)],
    ["人工審查摘要或下一步", Boolean(draft.decision_review_summary || draft.decision_next_step)],
  ]);
}

function buildTimelineSection(readiness: TimelineReadinessResult, milestoneCount: number): PropertyCaseVisualSection {
  const completedCount = readiness.milestone_done_count + (readiness.event_count > 0 ? 1 : 0);
  const totalCount = milestoneCount + 1;
  return {
    id: "timeline",
    label: "時間軸",
    state: readiness.readiness === "completed" ? "completed" : readiness.readiness === "partial" ? "partial" : "not_assessed",
    completedCount,
    totalCount,
    missingItems: [
      ...(readiness.event_count === 0 ? ["尚無已輸入事件"] : []),
      ...(readiness.milestone_done_count < milestoneCount ? ["仍有未完成里程碑"] : []),
    ],
  };
}

function section(id: string, label: string, checks: Array<[string, boolean]>): PropertyCaseVisualSection {
  const completedCount = checks.filter(([, complete]) => complete).length;
  return {
    id,
    label,
    state: stateFromCounts(completedCount, checks.length),
    completedCount,
    totalCount: checks.length,
    missingItems: checks.filter(([, complete]) => !complete).map(([name]) => name),
  };
}

function stateFromCounts(completedCount: number, totalCount: number): PropertyCaseVisualState {
  if (totalCount === 0) return "not_assessed";
  if (completedCount === totalCount) return "completed";
  if (completedCount === 0) return "missing";
  return "partial";
}

function statusLabel(status: PropertyCaseStatus): string {
  return {
    completed: "已完成",
    missing: "尚未評估",
    incomplete: "資料不完整",
    unavailable: "暫時不可用",
  }[status];
}

function positiveOrZero(value: number | null): boolean {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}
