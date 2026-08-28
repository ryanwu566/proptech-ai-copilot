import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { buildTerrainReferenceEvidence } from "@/lib/terrain-reference-evidence";
import { classifyTerrainSafety } from "@/lib/terrain-safety-gate";

export type RiskSummary = {
  overallSignal: "green" | "yellow" | "red" | "unknown";
  overallLabel: string;
  overallScore: number | null;
  decisionSuggestion: string;
  priceReasonableness: {
    status: "undervalued" | "reasonable" | "overpriced" | "unknown";
    label: string;
    explanation: string;
    params?: Record<string, string | number>;
  };
  riskFactors: Array<{ key: string; level: "low" | "medium" | "high"; title: string; message: string; params?: Record<string, string | number> }>;
  positiveFactors: Array<{ key: string; title: string; message: string; params?: Record<string, string | number> }>;
  missingChecks: string[];
  nextActions: string[];
  dataConfidence: "high" | "medium" | "low" | "unknown";
  referenceNotes: string[];
};

export type RiskSummaryInputs = {
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holding?: HoldingCostResult;
  location?: LocationInsightResult;
  terrainRisk?: TerrainRiskResult;
};

export function buildRiskSummary(inputs: RiskSummaryInputs): RiskSummary {
  const { propertySearch, valuation, trend, loan, holding, location } = inputs;
  const comparisonPrice = loan?.property_price_wan ?? holding?.property_price_wan;
  const priceReasonableness = assessPrice(comparisonPrice, valuation);
  const dataConfidence = assessDataConfidence(valuation);
  const riskFactors: RiskSummary["riskFactors"] = [];
  const positiveFactors: RiskSummary["positiveFactors"] = [];
  const missingChecks: string[] = [];
  const nextActions: string[] = [];

  addPriceFactors(priceReasonableness, riskFactors, positiveFactors);
  addConfidenceFactors(dataConfidence, valuation, riskFactors, positiveFactors);
  const loanScore = assessBurden("loan", loan?.income_burden_ratio, riskFactors, positiveFactors);
  const holdingScore = assessBurden("holding", holding?.income_burden_ratio, riskFactors, positiveFactors);
  const locationScore = assessLocation(location, riskFactors, positiveFactors);
  addLocationPriceSupport(location, riskFactors, positiveFactors, missingChecks);
  const terrainReference = buildTerrainReferenceEvidence(inputs.terrainRisk);
  const terrainSafety = classifyTerrainSafety(inputs.terrainRisk);

  if (!valuation) missingChecks.push("riskSummary.missingValuation");
  if (comparisonPrice === undefined) missingChecks.push("riskSummary.missingPrice");
  if (!loan) missingChecks.push("riskSummary.missingLoan");
  else if (loan.income_burden_ratio === null) missingChecks.push("riskSummary.missingIncome");
  if (!holding) missingChecks.push("riskSummary.missingHolding");
  else if (holding.income_burden_ratio === null) missingChecks.push("riskSummary.missingHoldingIncome");
  if (!location) missingChecks.push("riskSummary.missingLocation");
  if (!trend) missingChecks.push("riskSummary.missingTrend");
  if (!propertySearch) missingChecks.push("riskSummary.missingPropertySearch");
  if (!location || location.data_quality.missing_sources.some((source) => /risk|嫌惡|風險/i.test(source))) {
    missingChecks.push("riskSummary.missingRiskFacility");
  }
  if (location?.data_quality.status !== "good") missingChecks.push("riskSummary.missingLocationQuality");
  // Terrain evidence completeness: surface a gap whenever terrain evidence is
  // not a positively-established all-clear (known low + sufficient quality).
  // This includes unknown/unavailable/error/not_assessed/absent (incomplete)
  // and partial/limited/no_match/medium (caution). Known high is a risk, not a
  // gap, and is handled by the signal gate below.
  if (terrainSafety === "incomplete" || terrainSafety === "absent" || terrainSafety === "caution") {
    missingChecks.push("riskSummary.missingTerrain");
  }

  const completedCoreModules = [loan, holding, location].filter(Boolean).length;
  const hasEnoughData = Boolean(valuation) && completedCoreModules >= 2;
  const completenessScore = [propertySearch, valuation, trend, loan, holding, location].filter(Boolean).length / 6 * 100;
  const valuationScore = valuation?.confidence_score ?? 0;
  const priceScore = { undervalued: 90, reasonable: 80, overpriced: 30, unknown: 45 }[priceReasonableness.status];
  const weightedScore = Math.round(
    valuationScore * 0.25
    + priceScore * 0.25
    + loanScore * 0.15
    + holdingScore * 0.15
    + locationScore * 0.15
    + completenessScore * 0.05,
  );
  const overallScore = hasEnoughData ? weightedScore : null;
  // Numeric score is preserved conceptually (valuation/price/loan/holding/
  // location/completeness). The user-facing qualitative signal is then gated on
  // terrain evidence: known-high terrain forces a risk (red); materially
  // incomplete or non-all-clear terrain (incomplete/absent/caution) prevents an
  // unrestricted green by downgrading it to yellow (caution). Known-low terrain
  // leaves the numeric signal untouched.
  const overallSignal = gateSignalForTerrain(signalFor(overallScore), terrainSafety);
  const overallLabel = `riskSummary.label${capitalize(overallSignal)}`;
  const decisionSuggestion = `riskSummary.suggestion${capitalize(overallSignal)}`;

  if (overallSignal === "green") nextActions.push("riskSummary.nextGreen");
  if (overallSignal === "yellow") nextActions.push("riskSummary.nextYellow");
  if (overallSignal === "red") nextActions.push("riskSummary.nextRed");
  if (overallSignal === "unknown") nextActions.push(...missingChecks.slice(0, 3));
  if (priceReasonableness.status === "overpriced") nextActions.push("riskSummary.nextOverpriced");
  if (location) nextActions.push("riskSummary.nextLocation");

  return {
    overallSignal, overallLabel, overallScore, decisionSuggestion, priceReasonableness,
    riskFactors: uniqueByKey(riskFactors),
    positiveFactors: uniqueByKey(positiveFactors),
    missingChecks: [...new Set(missingChecks)],
    nextActions: [...new Set(nextActions)],
    dataConfidence,
    referenceNotes: [terrainReference.summary, terrainReference.notice],
  };
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function assessPrice(price: number | undefined, valuation?: ValuationResult): RiskSummary["priceReasonableness"] {
  if (price === undefined || !valuation) return { status: "unknown", label: "riskSummary.priceUnknown", explanation: "riskSummary.priceUnknownExplanation" };
  if (price < valuation.price_range.low * 0.95) return { status: "undervalued", label: "riskSummary.priceUndervalued", explanation: "riskSummary.priceUndervaluedExplanation", params: { price: price.toLocaleString() } };
  if (price > valuation.price_range.high * 1.05) return { status: "overpriced", label: "riskSummary.priceOverpriced", explanation: "riskSummary.priceOverpricedExplanation", params: { price: price.toLocaleString() } };
  return { status: "reasonable", label: "riskSummary.priceReasonable", explanation: "riskSummary.priceReasonableExplanation", params: { price: price.toLocaleString() } };
}

function assessDataConfidence(valuation?: ValuationResult): RiskSummary["dataConfidence"] {
  if (!valuation) return "unknown";
  const official = valuation.estimate_data_composition.startsWith("official");
  if (valuation.confidence_score >= 80 && official) return "high";
  if (valuation.confidence_score >= 60) return "medium";
  return "low";
}

function assessBurden(
  kind: "loan" | "holding",
  ratio: number | null | undefined,
  risks: RiskSummary["riskFactors"],
  positives: RiskSummary["positiveFactors"],
): number {
  if (ratio === null || ratio === undefined) return 45;
  const lowLimit = kind === "loan" ? 0.3 : 0.35;
  const mediumLimit = kind === "loan" ? 0.4 : 0.45;
  const title = kind === "loan" ? "riskSummary.titleLoan" : "riskSummary.titleHolding";
  const ratioPercent = (ratio * 100).toFixed(1);
  if (ratio <= lowLimit) {
    positives.push({ key: kind, title, message: "riskSummary.burdenHealthy", params: { ratio: ratioPercent } });
    return 90;
  }
  if (ratio <= mediumLimit) {
    risks.push({ key: kind, level: "medium", title, message: "riskSummary.burdenCaution", params: { ratio: ratioPercent } });
    return 65;
  }
  risks.push({ key: kind, level: "high", title, message: "riskSummary.burdenHigh", params: { ratio: ratioPercent } });
  return 25;
}

function assessLocation(location: LocationInsightResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"]): number {
  if (!location || location.location_score === null) return 45;
  if (location.location_score >= 75) positives.push({ key: "location", title: "riskSummary.titleLocation", message: "riskSummary.locationGood", params: { score: location.location_score } });
  else if (location.location_score < 55) risks.push({ key: "location", level: "high", title: "riskSummary.titleLocation", message: "riskSummary.locationLow", params: { score: location.location_score } });
  else risks.push({ key: "location", level: "medium", title: "riskSummary.titleLocation", message: "riskSummary.locationMedium", params: { score: location.location_score } });
  if (location.poi_summary.risk_facility_count > 0) risks.push({ key: "risk-facilities", level: "high", title: "riskSummary.titleRiskFacilities", message: "riskSummary.riskFacilityWarning", params: { count: location.poi_summary.risk_facility_count } });
  return location.location_score;
}

function addPriceFactors(price: RiskSummary["priceReasonableness"], risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"]) {
  if (price.status === "overpriced") risks.push({ key: "price", level: "high", title: "riskSummary.titlePrice", message: price.explanation, params: { ...price.params, _messageKey: price.explanation } });
  if (price.status === "reasonable") positives.push({ key: "price", title: "riskSummary.titlePrice", message: price.explanation, params: { ...price.params, _messageKey: price.explanation } });
  if (price.status === "undervalued") positives.push({ key: "price", title: "riskSummary.titlePrice", message: price.explanation, params: { ...price.params, _messageKey: price.explanation } });
}

function addConfidenceFactors(confidence: RiskSummary["dataConfidence"], valuation: ValuationResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"]) {
  if (confidence === "high") positives.push({ key: "confidence", title: "riskSummary.titleConfidence", message: "riskSummary.confidenceHighMessage", params: { confidence: valuation?.confidence_score ?? 0 } });
  if (confidence === "low") risks.push({ key: "confidence", level: "high", title: "riskSummary.titleConfidence", message: "riskSummary.confidenceLowMessage" });
  if (confidence === "medium") risks.push({ key: "confidence", level: "medium", title: "riskSummary.titleConfidence", message: "riskSummary.confidenceMediumMessage" });
}

function addLocationPriceSupport(location: LocationInsightResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"], missing: string[]) {
  if (!location || location.valuation_context.supports_price_reasonableness === "unknown") {
    missing.push("riskSummary.missingLocationQuality");
    return;
  }
  if (location.valuation_context.supports_price_reasonableness) {
    positives.push({ key: "location-price", title: "riskSummary.titleLocationSupportsPrice", message: location.valuation_context.explanation });
  } else {
    risks.push({ key: "location-price", level: "medium", title: "riskSummary.titleLocationNotSupportsPrice", message: location.valuation_context.explanation });
  }
}

function signalFor(score: number | null): RiskSummary["overallSignal"] {
  if (score === null) return "unknown";
  if (score >= 75) return "green";
  if (score >= 55) return "yellow";
  return "red";
}

// Terrain evidence gate for the qualitative signal. Priority: known-high
// terrain is material risk (red, unless already red). Materially incomplete or
// non-all-clear terrain must not present an unrestricted all-clear, so a green
// numeric signal is downgraded to yellow (caution); it never upgrades a
// weaker signal. Known-low terrain and the null/unknown signal pass through.
function gateSignalForTerrain(
  signal: RiskSummary["overallSignal"],
  terrainSafety: import("@/lib/terrain-safety-gate").TerrainSafetyClass,
): RiskSummary["overallSignal"] {
  if (terrainSafety === "known_high") {
    return signal === "unknown" ? "unknown" : "red";
  }
  if (terrainSafety === "known_low") {
    return signal;
  }
  // incomplete / absent / caution: prevent unrestricted green only.
  if (signal === "green") return "yellow";
  return signal;
}

function uniqueByKey<T extends { key: string }>(items: T[]): T[] {
  return [...new Map(items.map((item) => [item.key, item])).values()];
}
