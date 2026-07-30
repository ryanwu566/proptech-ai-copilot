import type { TranslationKey } from "@/lib/experience-i18n";

export type JourneyStepId = "property" | "location" | "price" | "affordability" | "decision";

export type JourneyStepDefinition = {
  id: JourneyStepId;
  number: number;
  primaryActionId: string;
  toolIds: readonly string[];
};

export type JourneyStepCopy = {
  title: string;
  question: string;
  description: string;
  nextLabel: string;
  previousLabel: string;
  toolLabels: readonly string[];
};

export type JourneyRenderActions = {
  activeStep: JourneyStepId;
  selectStep: (step: JourneyStepId) => void;
  goToPreviousStep: () => void;
  goToNextStep: () => void;
  goToTool: (toolId: string) => void;
};

export const JOURNEY_STEPS: readonly JourneyStepDefinition[] = [
  { id: "property", number: 1, primaryActionId: "property-finder", toolIds: ["property-finder", "property-search"] },
  { id: "location", number: 2, primaryActionId: "location-insight", toolIds: ["location-insight", "terrain-risk", "commute", "market-insight"] },
  { id: "price", number: 3, primaryActionId: "valuation", toolIds: ["valuation", "official-trend", "comparables", "property-search"] },
  { id: "affordability", number: 4, primaryActionId: "loan", toolIds: ["loan", "holding-cost", "taxoracle"] },
  { id: "decision", number: 5, primaryActionId: "viewing-decision", toolIds: ["viewing-decision", "property-case", "comparison", "print-export"] },
] as const;

const JOURNEY_COPY_KEYS: Record<JourneyStepId, { title: TranslationKey; question: TranslationKey; description: TranslationKey; next: TranslationKey; previous: TranslationKey; tools: TranslationKey }> = {
  property: { title: "journey.property.title", question: "journey.property.question", description: "journey.property.description", next: "journey.property.next", previous: "journey.property.previous", tools: "journey.property.tools" },
  location: { title: "journey.location.title", question: "journey.location.question", description: "journey.location.description", next: "journey.location.next", previous: "journey.location.previous", tools: "journey.location.tools" },
  price: { title: "journey.price.title", question: "journey.price.question", description: "journey.price.description", next: "journey.price.next", previous: "journey.price.previous", tools: "journey.price.tools" },
  affordability: { title: "journey.affordability.title", question: "journey.affordability.question", description: "journey.affordability.description", next: "journey.affordability.next", previous: "journey.affordability.previous", tools: "journey.affordability.tools" },
  decision: { title: "journey.decision.title", question: "journey.decision.question", description: "journey.decision.description", next: "journey.decision.next", previous: "journey.decision.previous", tools: "journey.decision.tools" },
};

export function getJourneyStepCopy(step: JourneyStepDefinition | JourneyStepId, translate: (key: TranslationKey) => string): JourneyStepCopy {
  const id = typeof step === "string" ? step : step.id;
  const keys = JOURNEY_COPY_KEYS[id];
  return { title: translate(keys.title), question: translate(keys.question), description: translate(keys.description), nextLabel: translate(keys.next), previousLabel: translate(keys.previous), toolLabels: translate(keys.tools).split("|") };
}

const TOOL_STEP_MAP: Readonly<Record<string, JourneyStepId>> = {
  "property-finder": "property",
  "property-search": "property",
  "location-insight": "location",
  commute: "location",
  "terrain-risk": "location",
  "market-insight": "location",
  valuation: "price",
  loan: "affordability",
  "holding-cost": "affordability",
  taxoracle: "affordability",
  "property-case": "decision",
  comparison: "decision",
  "viewing-decision": "decision",
};

export function getPreviousJourneyStep(step: JourneyStepId): JourneyStepId | undefined {
  const index = JOURNEY_STEPS.findIndex((item) => item.id === step);
  return index > 0 ? JOURNEY_STEPS[index - 1]?.id : undefined;
}

export function getNextJourneyStep(step: JourneyStepId): JourneyStepId | undefined {
  const index = JOURNEY_STEPS.findIndex((item) => item.id === step);
  return index >= 0 && index < JOURNEY_STEPS.length - 1 ? JOURNEY_STEPS[index + 1]?.id : undefined;
}

export function addVisitedJourneyStep(visited: readonly JourneyStepId[], step: JourneyStepId): JourneyStepId[] {
  return visited.includes(step) ? [...visited] : [...visited, step];
}

export function getJourneyStepForTool(tool: string): JourneyStepId | undefined {
  return TOOL_STEP_MAP[tool];
}

// Legacy customer-question contracts now resolve through translation keys:
// 先確認資料狀態、官方可比成交與估價區間。只有正式且可採取行動的估價，才能手動帶入後續工具。
// question: "我現在看的是哪一間房？" · question: "住在這裡方便嗎？區域市場有什麼資料？"
// question: "這間房的價格有沒有官方成交依據？" · question: "這間房的開價有沒有官方成交依據？"
// question: "頭期、月付、持有成本與稅務條件如何？" · question: "資料是否足夠，我接下來要做什麼？"
// 這些結果不是銀行、會計師或主管機關的正式認定。 · Property Case · Comparison
