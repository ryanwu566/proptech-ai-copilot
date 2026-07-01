import type { PropertyCaseDraft } from "@/lib/property-case";

export type TimelineEventType =
  | "created"
  | "viewing"
  | "question"
  | "due_diligence"
  | "financial_review"
  | "offer"
  | "decision_review"
  | "status_change"
  | "custom";

export type TimelineRelatedSection =
  | "basic"
  | "financial"
  | "due_diligence"
  | "viewing_offer"
  | "market_reference"
  | "location_reference"
  | "decision"
  | "other";

export type TimelineReadiness = "completed" | "partial" | "not_provided";

export type TimelineEvent = {
  id: string;
  event_date: string;
  event_type: TimelineEventType;
  title: string;
  summary: string;
  related_section: TimelineRelatedSection;
  note: string;
};

export type CaseMilestoneId =
  | "basic_info_reviewed"
  | "first_viewing_recorded"
  | "financial_review_started"
  | "due_diligence_started"
  | "questions_tracked"
  | "offer_plan_created"
  | "decision_review_written"
  | "report_ready_for_print";

export type CaseMilestone = {
  milestone_id: CaseMilestoneId;
  is_done: boolean;
  done_date: string;
  note: string;
};

export type ExecutiveDecisionSummary = {
  headline: string;
  decision_status: string;
  basic_data_complete: boolean;
  financial_summary_available: boolean;
  due_diligence_available: boolean;
  viewing_offer_available: boolean;
  open_questions_count: number;
  blocked_due_diligence_count: number;
  active_next_actions_count: number;
  offer_plan_count: number;
  manual_decision_review_present: boolean;
  report_ready: boolean;
  missing_sections: string[];
};

export type TimelineReadinessResult = {
  readiness: TimelineReadiness;
  event_count: number;
  milestone_done_count: number;
  active_next_actions_count: number;
};

export const TIMELINE_EVENT_TYPE_OPTIONS: TimelineEventType[] = [
  "created",
  "viewing",
  "question",
  "due_diligence",
  "financial_review",
  "offer",
  "decision_review",
  "status_change",
  "custom",
];

export const TIMELINE_RELATED_SECTION_OPTIONS: TimelineRelatedSection[] = [
  "basic",
  "financial",
  "due_diligence",
  "viewing_offer",
  "market_reference",
  "location_reference",
  "decision",
  "other",
];

export const CASE_MILESTONE_TEMPLATE: Array<{ milestone_id: CaseMilestoneId; label: string }> = [
  { milestone_id: "basic_info_reviewed", label: "基本資料已檢視" },
  { milestone_id: "first_viewing_recorded", label: "已記錄第一次看屋" },
  { milestone_id: "financial_review_started", label: "財務檢視已開始" },
  { milestone_id: "due_diligence_started", label: "盡職調查已開始" },
  { milestone_id: "questions_tracked", label: "提問追蹤已建立" },
  { milestone_id: "offer_plan_created", label: "出價規劃已建立" },
  { milestone_id: "decision_review_written", label: "決策審查摘要已填寫" },
  { milestone_id: "report_ready_for_print", label: "目前摘要可列印" },
];

export function buildDefaultMilestones(): CaseMilestone[] {
  return CASE_MILESTONE_TEMPLATE.map((milestone) => ({
    milestone_id: milestone.milestone_id,
    is_done: false,
    done_date: "",
    note: "",
  }));
}

export function normalizeTimelineEvents(events?: Partial<TimelineEvent>[] | null): TimelineEvent[] {
  return (events ?? []).map((event, index) => ({
    id: safeText(event.id) || `timeline-${index + 1}`,
    event_date: normalizeDate(event.event_date),
    event_type: normalizeEventType(event.event_type),
    title: safeText(event.title),
    summary: safeText(event.summary),
    related_section: normalizeRelatedSection(event.related_section),
    note: safeText(event.note),
  })).filter((event) => event.event_date && event.title);
}

export function normalizeCaseMilestones(milestones?: Partial<CaseMilestone>[] | null): CaseMilestone[] {
  const byId = new Map((milestones ?? []).map((milestone) => [milestone.milestone_id, milestone]));
  return CASE_MILESTONE_TEMPLATE.map((template) => {
    const input = byId.get(template.milestone_id);
    return {
      milestone_id: template.milestone_id,
      is_done: Boolean(input?.is_done),
      done_date: normalizeDate(input?.done_date),
      note: safeText(input?.note),
    };
  });
}

export function buildTimelineReadiness(
  events: TimelineEvent[],
  milestones: CaseMilestone[],
  executiveSummaryNote?: string,
  finalReviewNote?: string,
): TimelineReadinessResult {
  const normalizedEvents = normalizeTimelineEvents(events);
  const normalizedMilestones = normalizeCaseMilestones(milestones);
  const milestoneDoneCount = normalizedMilestones.filter((milestone) => milestone.is_done).length;
  const hasExecutiveNotes = Boolean(safeText(executiveSummaryNote) || safeText(finalReviewNote));
  let readiness: TimelineReadiness = "not_provided";
  if (normalizedEvents.length > 0 && milestoneDoneCount > 0 && hasExecutiveNotes) readiness = "completed";
  else if (normalizedEvents.length > 0 || milestoneDoneCount > 0 || hasExecutiveNotes) readiness = "partial";
  return {
    readiness,
    event_count: normalizedEvents.length,
    milestone_done_count: milestoneDoneCount,
    active_next_actions_count: 0,
  };
}

export function buildExecutiveDecisionSummary(draft: PropertyCaseDraft): ExecutiveDecisionSummary {
  const missingSections: string[] = [];
  if (!draft.readiness.draft_ready) missingSections.push("basic");
  if (!draft.financial_input.loan_amount && !draft.financial_input.estimated_holding_cost) missingSections.push("financial");
  if (draft.readiness.due_diligence !== "completed") missingSections.push("due_diligence");
  if (draft.readiness.viewing_offer !== "completed") missingSections.push("viewing_offer");
  if (draft.readiness.timeline_summary !== "completed") missingSections.push("timeline_summary");
  if (!draft.decision_review_summary && !draft.decision_next_step) missingSections.push("decision_review");

  const openQuestionsCount = draft.viewing_questions.filter((question) => question.status !== "resolved_by_user" && question.status !== "no_longer_needed").length;
  const blockedDueDiligenceCount = draft.due_diligence_items.filter((item) => item.status === "blocked").length;
  const timelineActionCount = draft.timeline_events.filter((event) => event.related_section === "decision" && event.note).length;
  const activeNextActionsCount = [
    draft.decision_next_step,
    ...draft.due_diligence_items.map((item) => item.next_action),
    ...draft.viewing_logs.map((log) => log.follow_up_action),
    ...draft.viewing_questions.map((question) => question.follow_up_action),
    ...draft.offer_plans.map((offer) => offer.negotiation_note),
  ].filter((value) => value.trim()).length + timelineActionCount;

  return {
    headline: draft.case_name || "待補案件名稱",
    decision_status: draft.decision_status,
    basic_data_complete: draft.readiness.draft_ready,
    financial_summary_available: Boolean(draft.financial_input.loan_amount || draft.financial_input.estimated_holding_cost),
    due_diligence_available: draft.readiness.due_diligence !== "not_provided",
    viewing_offer_available: draft.readiness.viewing_offer !== "not_provided",
    open_questions_count: openQuestionsCount,
    blocked_due_diligence_count: blockedDueDiligenceCount,
    active_next_actions_count: activeNextActionsCount,
    offer_plan_count: draft.offer_plans.length,
    manual_decision_review_present: Boolean(draft.decision_review_summary || draft.decision_next_step),
    report_ready: draft.readiness.print_ready,
    missing_sections: missingSections,
  };
}

function normalizeEventType(type: unknown): TimelineEventType {
  return TIMELINE_EVENT_TYPE_OPTIONS.includes(type as TimelineEventType) ? type as TimelineEventType : "custom";
}

function normalizeRelatedSection(section: unknown): TimelineRelatedSection {
  return TIMELINE_RELATED_SECTION_OPTIONS.includes(section as TimelineRelatedSection) ? section as TimelineRelatedSection : "other";
}

function normalizeDate(value: unknown): string {
  const text = safeText(value);
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : "";
}

function safeText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
