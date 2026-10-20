// The one fixture behind the guided tour demo and the competition demo.
// Presentation-only identity: deliberately incompatible with SavedCase/workspace models,
// so it can never be saved, analysed or shown as live property evidence.
export const DEMO_CASE = Object.freeze({
  demoId: "demo:guided-case:v2",
  synthetic: true,
  priceTwd: 18_000_000,
  areaPing: 30,
  comparablesWan: Object.freeze([1740, 1860, 1800]),
  // Evidence the example case holds once the location is confirmed, and the gaps it keeps.
  known: Object.freeze(["location", "price", "comparables"] as const),
  unknown: Object.freeze(["flood", "slope"] as const),
  questions: Object.freeze(["question1", "question2", "question3"] as const),
} as const);
