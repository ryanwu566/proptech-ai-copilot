/**
 * Localizers for dynamic user-visible copy produced by business logic modules.
 * These map semantic codes/IDs to runtime copy keys, keeping business logic
 * free of locale-specific strings while ensuring all rendered copy goes through
 * the unified runtime-copy.ts translation system.
 */
import type { ExperienceLocale } from "@/lib/experience-i18n";
import { translateRuntimeCopy, type RuntimeCopyKey } from "@/lib/runtime-copy";

// ─── Viewing Decision ───────────────────────────────────────────────────────

export type ViewingDecisionStatus = "ready_to_view" | "needs_more_data" | "clarify_risk_first";

const STATUS_LABEL_KEYS: Record<ViewingDecisionStatus, RuntimeCopyKey> = {
  ready_to_view: "decision.readyToView",
  needs_more_data: "decision.needsMoreData",
  clarify_risk_first: "decision.clarifyRiskFirst",
};

export function localizeViewingDecisionLabel(status: ViewingDecisionStatus, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, STATUS_LABEL_KEYS[status]);
}

const CRITICAL_CHECK_KEYS: Record<string, { label: RuntimeCopyKey; action: RuntimeCopyKey }> = {
  valuation: { label: "decision.criticalValuation", action: "decision.actionValuation" },
  loan: { label: "decision.criticalLoan", action: "decision.actionLoan" },
  holding: { label: "decision.criticalHolding", action: "decision.actionHolding" },
  location: { label: "decision.criticalLocation", action: "decision.actionLocation" },
};

export function localizeCriticalCheckLabel(key: string, locale: ExperienceLocale): string {
  return CRITICAL_CHECK_KEYS[key] ? translateRuntimeCopy(locale, CRITICAL_CHECK_KEYS[key].label) : key;
}

export function localizeCriticalCheckAction(key: string, locale: ExperienceLocale): string {
  return CRITICAL_CHECK_KEYS[key] ? translateRuntimeCopy(locale, CRITICAL_CHECK_KEYS[key].action) : key;
}

const NEXT_ACTION_KEYS: Record<string, RuntimeCopyKey> = {
  view_report: "decision.actionViewReport",
  check_location: "decision.actionCheckLocation",
  check_loan: "decision.actionCheckLoan",
  check_holding: "decision.actionCheckHolding",
  check_risk: "decision.actionCheckRisk",
};

export function localizeNextActionLabel(actionId: string, locale: ExperienceLocale): string {
  return NEXT_ACTION_KEYS[actionId] ? translateRuntimeCopy(locale, NEXT_ACTION_KEYS[actionId]) : actionId;
}

const RISK_SOURCE_KEYS: Record<string, RuntimeCopyKey> = {
  red_signal: "decision.riskRedSignal",
  loan_risky: "decision.riskLoanRisky",
  holding_risky: "decision.riskHoldingRisky",
  location_facility: "decision.riskLocationFacility",
  tax_high: "decision.riskTaxHigh",
};

export function localizeRiskSource(sourceId: string, locale: ExperienceLocale, params?: Record<string, string | number>): string {
  if (RISK_SOURCE_KEYS[sourceId]) return translateRuntimeCopy(locale, RISK_SOURCE_KEYS[sourceId], params);
  if (sourceId === "high_item" && params) return translateRuntimeCopy(locale, "decision.riskHighItem", params);
  return sourceId;
}

export function localizeDecisionReasons(status: ViewingDecisionStatus, locale: ExperienceLocale, missingItems?: string[]): string[] {
  switch (status) {
    case "clarify_risk_first":
      return [translateRuntimeCopy(locale, "decision.reasonHighRisk")];
    case "needs_more_data":
      return [
        translateRuntimeCopy(locale, "decision.reasonMissingData", { items: missingItems?.join(", ") ?? "" }),
        translateRuntimeCopy(locale, "decision.reasonMissingNotLowRisk"),
      ];
    case "ready_to_view":
      return [
        translateRuntimeCopy(locale, "decision.reasonReadyNoHighRisk"),
        translateRuntimeCopy(locale, "decision.reasonReadyOnSite"),
      ];
  }
}

export function localizeRuleNotes(locale: ExperienceLocale): string[] {
  return [
    translateRuntimeCopy(locale, "decision.ruleCheckRisk"),
    translateRuntimeCopy(locale, "decision.ruleCheckData"),
    translateRuntimeCopy(locale, "decision.ruleUnknownNotLow"),
  ];
}

// ─── Buying Wizard Steps ────────────────────────────────────────────────────

export type BuyingWizardStepId = "property_search" | "valuation" | "affordability" | "location" | "risk" | "report" | "tax";

const STEP_KEYS: Record<BuyingWizardStepId, { label: RuntimeCopyKey; title: RuntimeCopyKey; guide: RuntimeCopyKey }> = {
  property_search: { label: "wizardStep.propertySearch", title: "wizardStep.propertySearchTitle", guide: "wizardStep.propertySearchGuide" },
  valuation: { label: "wizardStep.valuation", title: "wizardStep.valuationTitle", guide: "wizardStep.valuationGuide" },
  affordability: { label: "wizardStep.affordability", title: "wizardStep.affordabilityTitle", guide: "wizardStep.affordabilityGuide" },
  location: { label: "wizardStep.location", title: "wizardStep.locationTitle", guide: "wizardStep.locationGuide" },
  risk: { label: "wizardStep.risk", title: "wizardStep.riskTitle", guide: "wizardStep.riskGuide" },
  report: { label: "wizardStep.report", title: "wizardStep.reportTitle", guide: "wizardStep.reportGuide" },
  tax: { label: "wizardStep.tax", title: "wizardStep.taxTitle", guide: "wizardStep.taxGuide" },
};

export function localizeWizardStepLabel(stepId: BuyingWizardStepId, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, STEP_KEYS[stepId].label);
}

export function localizeWizardStepTitle(stepId: BuyingWizardStepId, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, STEP_KEYS[stepId].title);
}

export function localizeWizardStepGuide(stepId: BuyingWizardStepId, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, STEP_KEYS[stepId].guide);
}


// ─── Risk Summary ───────────────────────────────────────────────────────────

export type RiskSignal = "green" | "yellow" | "red" | "unknown";

const SIGNAL_LABEL_KEYS: Record<RiskSignal, RuntimeCopyKey> = {
  green: "riskSummary.labelGreen",
  yellow: "riskSummary.labelYellow",
  red: "riskSummary.labelRed",
  unknown: "riskSummary.labelUnknown",
};

const SIGNAL_SUGGESTION_KEYS: Record<RiskSignal, RuntimeCopyKey> = {
  green: "riskSummary.suggestionGreen",
  yellow: "riskSummary.suggestionYellow",
  red: "riskSummary.suggestionRed",
  unknown: "riskSummary.suggestionUnknown",
};

export function localizeRiskSignalLabel(signal: RiskSignal, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, SIGNAL_LABEL_KEYS[signal]);
}

export function localizeRiskSuggestion(signal: RiskSignal, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, SIGNAL_SUGGESTION_KEYS[signal]);
}

type PriceStatus = "undervalued" | "reasonable" | "overpriced" | "unknown";
const PRICE_LABEL_KEYS: Record<PriceStatus, RuntimeCopyKey> = {
  unknown: "riskSummary.priceUnknown",
  undervalued: "riskSummary.priceUndervalued",
  overpriced: "riskSummary.priceOverpriced",
  reasonable: "riskSummary.priceReasonable",
};
const PRICE_EXPLANATION_KEYS: Record<PriceStatus, RuntimeCopyKey> = {
  unknown: "riskSummary.priceUnknownExplanation",
  undervalued: "riskSummary.priceUndervaluedExplanation",
  overpriced: "riskSummary.priceOverpricedExplanation",
  reasonable: "riskSummary.priceReasonableExplanation",
};

export function localizePriceLabel(status: PriceStatus, locale: ExperienceLocale): string {
  return translateRuntimeCopy(locale, PRICE_LABEL_KEYS[status]);
}

export function localizePriceExplanation(status: PriceStatus, locale: ExperienceLocale, params?: Record<string, string | number>): string {
  return translateRuntimeCopy(locale, PRICE_EXPLANATION_KEYS[status], params);
}

const FACTOR_TITLE_KEYS: Record<string, RuntimeCopyKey> = {
  loan: "riskSummary.titleLoan",
  holding: "riskSummary.titleHolding",
  location: "riskSummary.titleLocation",
  "risk-facilities": "riskSummary.titleRiskFacilities",
  price: "riskSummary.titlePrice",
  confidence: "riskSummary.titleConfidence",
  "location-price": "riskSummary.titleLocation",
};

export function localizeFactorTitle(key: string, locale: ExperienceLocale, titleKey?: string): string {
  // If the producer provided a specific title key, use it directly
  if (titleKey && titleKey.startsWith("riskSummary.")) {
    return translateRuntimeCopy(locale, titleKey as RuntimeCopyKey);
  }
  return FACTOR_TITLE_KEYS[key] ? translateRuntimeCopy(locale, FACTOR_TITLE_KEYS[key]) : translateRuntimeCopy(locale, "common.noData");
}

export function localizeFactorMessage(key: string, level: string, locale: ExperienceLocale, params?: Record<string, string | number>): string {
  // Loan and holding: burden ratio messages
  if ((key === "loan" || key === "holding") && params?.ratio !== undefined) {
    if (level === "high") return translateRuntimeCopy(locale, "riskSummary.burdenHigh", params);
    if (level === "medium") return translateRuntimeCopy(locale, "riskSummary.burdenCaution", params);
    return translateRuntimeCopy(locale, "riskSummary.burdenHealthy", params);
  }
  // Location: location score messages
  if (key === "location" && params?.score !== undefined) {
    if (level === "high") return translateRuntimeCopy(locale, "riskSummary.locationLow", params);
    if (level === "medium") return translateRuntimeCopy(locale, "riskSummary.locationMedium", params);
    return translateRuntimeCopy(locale, "riskSummary.locationGood", params);
  }
  // Risk facilities: warning with count
  if (key === "risk-facilities" && params?.count !== undefined) {
    return translateRuntimeCopy(locale, "riskSummary.riskFacilityWarning", params);
  }
  // Confidence: confidence-specific messages (never burden)
  if (key === "confidence") {
    if (level === "positive" || level === "low" || level === "medium" || level === "high") {
      if (params?.confidence !== undefined) return translateRuntimeCopy(locale, "riskSummary.confidenceHighMessage", params);
      if (level === "high") return translateRuntimeCopy(locale, "riskSummary.confidenceLowMessage", params);
      if (level === "medium") return translateRuntimeCopy(locale, "riskSummary.confidenceMediumMessage", params);
    }
    // For positive factors with confidence param
    if (params?.confidence !== undefined) return translateRuntimeCopy(locale, "riskSummary.confidenceHighMessage", params);
    return translateRuntimeCopy(locale, "riskSummary.confidenceMediumMessage", params);
  }
  // Price: use price explanation keys
  if (key === "price" && params?.price !== undefined) {
    const messageKey = params._messageKey as string | undefined;
    if (messageKey && messageKey.startsWith("riskSummary.")) {
      return translateRuntimeCopy(locale, messageKey as RuntimeCopyKey, params);
    }
    if (level === "high") return translateRuntimeCopy(locale, "riskSummary.priceOverpricedExplanation", params);
    return translateRuntimeCopy(locale, "riskSummary.priceReasonableExplanation", params);
  }
  // Location-price: the message is a raw explanation from the API
  if (key === "location-price") {
    // The message field is the API explanation string — pass through safely
    // Title localization handles the distinction (supports/not supports)
    return params?.message as string ?? translateRuntimeCopy(locale, "riskSummary.titleLocation");
  }
  // Generic fallback: try treating message as a runtime copy key
  if (params?.message && typeof params.message === "string" && params.message.startsWith("riskSummary.")) {
    return translateRuntimeCopy(locale, params.message as RuntimeCopyKey, params);
  }
  // Safe generic fallback: return translated title rather than raw key
  return translateRuntimeCopy(locale, "common.noData");
}
