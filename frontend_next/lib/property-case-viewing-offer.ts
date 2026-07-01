import {
  buildPropertyCaseFinancialAnalysis,
  type PropertyCaseFinancialAnalysis,
  type PropertyCaseFinancialInputs,
} from "@/lib/property-case-financials";

export type ViewingLogStatus = "planned" | "completed" | "cancelled";
export type ViewingQuestionCategory = "property" | "building" | "community" | "financing_tax" | "contract_negotiation" | "location_reference" | "other";
export type ViewingQuestionStatus = "open" | "awaiting_response" | "user_recorded_response" | "resolved_by_user" | "no_longer_needed";
export type OfferPlanStatus = "draft" | "discussed" | "submitted_by_user" | "withdrawn" | "not_pursuing";
export type ViewingOfferReadiness = "completed" | "partial" | "not_provided";

export type ViewingLog = {
  id: string;
  viewed_on: string;
  participant_note: string;
  summary: string;
  positive_observations: string;
  concerns: string;
  follow_up_action: string;
  status: ViewingLogStatus;
};

export type ViewingQuestion = {
  id: string;
  category: ViewingQuestionCategory;
  question: string;
  recorded_response: string;
  response_source_note: string;
  follow_up_action: string;
  target_date: string;
  status: ViewingQuestionStatus;
};

export type OfferPlan = {
  id: string;
  scenario_name: string;
  proposed_price: number | null;
  reservation_or_earnest_amount: number | null;
  intended_response_date: string;
  conditions_note: string;
  negotiation_note: string;
  status: OfferPlanStatus;
};

export type ViewingOfferReadinessResult = {
  readiness: ViewingOfferReadiness;
  viewing_count: number;
  completed_viewing_count: number;
  open_question_count: number;
  user_recorded_response_count: number;
  offer_plan_count: number;
  active_offer_plan_count: number;
  next_step_count: number;
};

export type OfferPlanFinancialPreview = {
  offer_plan_id: string;
  scenario_name: string;
  analysis: PropertyCaseFinancialAnalysis;
};

export const MAX_OFFER_PLANS = 3;

export const VIEWING_LOG_STATUS_LABELS: Record<ViewingLogStatus, string> = {
  planned: "預計看屋",
  completed: "已完成看屋",
  cancelled: "已取消",
};

export const VIEWING_QUESTION_STATUS_LABELS: Record<ViewingQuestionStatus, string> = {
  open: "待確認",
  awaiting_response: "等待回覆",
  user_recorded_response: "已記錄回覆",
  resolved_by_user: "已由使用者確認",
  no_longer_needed: "不再需要",
};

export const OFFER_PLAN_STATUS_LABELS: Record<OfferPlanStatus, string> = {
  draft: "草稿",
  discussed: "已討論",
  submitted_by_user: "使用者已送出",
  withdrawn: "已撤回",
  not_pursuing: "不追蹤",
};

export const VIEWING_LOG_STATUS_OPTIONS: ViewingLogStatus[] = ["planned", "completed", "cancelled"];
export const VIEWING_QUESTION_CATEGORY_OPTIONS: ViewingQuestionCategory[] = ["property", "building", "community", "financing_tax", "contract_negotiation", "location_reference", "other"];
export const VIEWING_QUESTION_STATUS_OPTIONS: ViewingQuestionStatus[] = ["open", "awaiting_response", "user_recorded_response", "resolved_by_user", "no_longer_needed"];
export const OFFER_PLAN_STATUS_OPTIONS: OfferPlanStatus[] = ["draft", "discussed", "submitted_by_user", "withdrawn", "not_pursuing"];

export function normalizeViewingLogs(logs?: Partial<ViewingLog>[] | null): ViewingLog[] {
  return (logs ?? []).map((log, index) => ({
    id: safeText(log.id) || `viewing-${index + 1}`,
    viewed_on: normalizeDate(log.viewed_on),
    participant_note: safeText(log.participant_note),
    summary: safeText(log.summary),
    positive_observations: safeText(log.positive_observations),
    concerns: safeText(log.concerns),
    follow_up_action: safeText(log.follow_up_action),
    status: normalizeViewingStatus(log.status),
  }));
}

export function normalizeViewingQuestions(questions?: Partial<ViewingQuestion>[] | null): ViewingQuestion[] {
  return (questions ?? []).map((question, index) => ({
    id: safeText(question.id) || `question-${index + 1}`,
    category: normalizeQuestionCategory(question.category),
    question: safeText(question.question),
    recorded_response: safeText(question.recorded_response),
    response_source_note: safeText(question.response_source_note),
    follow_up_action: safeText(question.follow_up_action),
    target_date: normalizeDate(question.target_date),
    status: normalizeQuestionStatus(question.status),
  })).filter((question) => question.question);
}

export function normalizeOfferPlans(plans?: Partial<OfferPlan>[] | null): OfferPlan[] {
  return (plans ?? []).slice(0, MAX_OFFER_PLANS).map((plan, index) => ({
    id: safeText(plan.id) || `offer-${index + 1}`,
    scenario_name: safeText(plan.scenario_name),
    proposed_price: positiveNumber(plan.proposed_price),
    reservation_or_earnest_amount: nonNegativeNumber(plan.reservation_or_earnest_amount),
    intended_response_date: normalizeDate(plan.intended_response_date),
    conditions_note: safeText(plan.conditions_note),
    negotiation_note: safeText(plan.negotiation_note),
    status: normalizeOfferStatus(plan.status),
  })).filter((plan) => plan.scenario_name);
}

export function buildViewingOfferReadiness(
  logs: ViewingLog[],
  questions: ViewingQuestion[],
  offers: OfferPlan[],
): ViewingOfferReadinessResult {
  const normalizedLogs = normalizeViewingLogs(logs);
  const normalizedQuestions = normalizeViewingQuestions(questions);
  const normalizedOffers = normalizeOfferPlans(offers);
  const completedViewingCount = normalizedLogs.filter((log) => log.status === "completed").length;
  const unresolvedQuestions = normalizedQuestions.filter((question) => question.status !== "resolved_by_user" && question.status !== "no_longer_needed");
  const userRecordedResponses = normalizedQuestions.filter((question) => question.status === "user_recorded_response" || question.status === "resolved_by_user");
  const activeOffers = normalizedOffers.filter((offer) => offer.status !== "withdrawn" && offer.status !== "not_pursuing");
  const hasAnyInput = normalizedLogs.length > 0 || normalizedQuestions.length > 0 || normalizedOffers.length > 0;
  const nextStepCount = [
    ...normalizedLogs.map((log) => log.follow_up_action),
    ...normalizedQuestions.map((question) => question.follow_up_action),
    ...normalizedOffers.map((offer) => offer.negotiation_note),
  ].filter((value) => value.trim()).length;

  let readiness: ViewingOfferReadiness = "not_provided";
  if (completedViewingCount > 0 && unresolvedQuestions.length === 0 && activeOffers.length > 0) readiness = "completed";
  else if (hasAnyInput) readiness = "partial";

  return {
    readiness,
    viewing_count: normalizedLogs.length,
    completed_viewing_count: completedViewingCount,
    open_question_count: unresolvedQuestions.length,
    user_recorded_response_count: userRecordedResponses.length,
    offer_plan_count: normalizedOffers.length,
    active_offer_plan_count: activeOffers.length,
    next_step_count: nextStepCount,
  };
}

export function buildOfferPlanFinancialPreviews(
  base: PropertyCaseFinancialInputs,
  offers: OfferPlan[],
): OfferPlanFinancialPreview[] {
  return normalizeOfferPlans(offers).map((offer) => ({
    offer_plan_id: offer.id,
    scenario_name: offer.scenario_name,
    analysis: buildPropertyCaseFinancialAnalysis({
      ...base,
      listingPrice: offer.proposed_price,
    }),
  }));
}

function normalizeViewingStatus(status: unknown): ViewingLogStatus {
  return VIEWING_LOG_STATUS_OPTIONS.includes(status as ViewingLogStatus) ? status as ViewingLogStatus : "planned";
}

function normalizeQuestionCategory(category: unknown): ViewingQuestionCategory {
  return VIEWING_QUESTION_CATEGORY_OPTIONS.includes(category as ViewingQuestionCategory) ? category as ViewingQuestionCategory : "other";
}

function normalizeQuestionStatus(status: unknown): ViewingQuestionStatus {
  return VIEWING_QUESTION_STATUS_OPTIONS.includes(status as ViewingQuestionStatus) ? status as ViewingQuestionStatus : "open";
}

function normalizeOfferStatus(status: unknown): OfferPlanStatus {
  return OFFER_PLAN_STATUS_OPTIONS.includes(status as OfferPlanStatus) ? status as OfferPlanStatus : "draft";
}

function normalizeDate(value: unknown): string {
  const text = safeText(value);
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : "";
}

function positiveNumber(value: unknown): number | null {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function nonNegativeNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function safeText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
