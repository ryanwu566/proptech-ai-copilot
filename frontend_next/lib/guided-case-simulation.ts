import { TOUR_STEPS } from "@/lib/guided-tour";

// Presentation-only identity: deliberately incompatible with SavedCase/workspace models.
export const DEMO_CASE = Object.freeze({
  demoId: "demo:guided-case:v1",
  synthetic: true,
  priceTwd: 18_000_000,
  areaPing: 30,
  comparablesWan: Object.freeze([1740, 1860, 1800]),
  walkMinutes: 8,
  commuteMinutes: 35,
  risk: "unknown",
  downPaymentPercent: 30,
  ratePercent: 2.5,
  loanYears: 30,
} as const);
export const DEMO_STAGES = TOUR_STEPS;
