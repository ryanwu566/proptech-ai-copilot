import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";

export type RiskSummary = {
  overallSignal: "green" | "yellow" | "red" | "unknown";
  overallLabel: string;
  overallScore: number | null;
  decisionSuggestion: string;
  priceReasonableness: {
    status: "undervalued" | "reasonable" | "overpriced" | "unknown";
    label: string;
    explanation: string;
  };
  riskFactors: Array<{ key: string; level: "low" | "medium" | "high"; title: string; message: string }>;
  positiveFactors: Array<{ key: string; title: string; message: string }>;
  missingChecks: string[];
  nextActions: string[];
  dataConfidence: "high" | "medium" | "low" | "unknown";
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
  const { propertySearch, valuation, trend, loan, holding, location, terrainRisk } = inputs;
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
  addTerrainRisk(terrainRisk, riskFactors, positiveFactors, missingChecks);

  if (!valuation) missingChecks.push("完成估價，確認估價區間與資料信心");
  if (comparisonPrice === undefined) missingChecks.push("帶入物件開價或成交樣本總價");
  if (!loan) missingChecks.push("完成貸款月付試算");
  else if (loan.income_burden_ratio === null) missingChecks.push("補入月收入，確認貸款負擔率");
  if (!holding) missingChecks.push("完成每月持有成本試算");
  else if (holding.income_burden_ratio === null) missingChecks.push("補入月收入，確認總持有成本負擔率");
  if (!location) missingChecks.push("完成區位分析並實地確認生活圈");
  if (!trend) missingChecks.push("補查市場趨勢與價格波動");
  if (!propertySearch) missingChecks.push("使用找房雷達比較其他可負擔路段");
  if (!location || location.data_quality.missing_sources.some((source) => /risk|嫌惡|風險/i.test(source))) {
    missingChecks.push("補查嫌惡設施與周邊環境風險");
  }
  if (location?.data_quality.status !== "good") missingChecks.push("確認區位資料限制與定位結果");

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
  const overallSignal = signalFor(overallScore);
  const overallLabel = { green: "可進一步看屋", yellow: "需謹慎評估", red: "暫不建議", unknown: "資料不足" }[overallSignal];
  const decisionSuggestion = {
    green: "目前條件相對健康，可安排實地看屋並確認屋況。",
    yellow: "可進一步看屋，但建議補查風險並保留議價空間。",
    red: "目前負擔或價格風險偏高，建議先比較其他路段。",
    unknown: "資料尚不足，請先完成估價、貸款或區位分析。",
  }[overallSignal];

  if (overallSignal === "green") nextActions.push("安排實地看屋，確認屋況、噪音與社區管理");
  if (overallSignal === "yellow") nextActions.push("針對主要風險補查，並保留議價空間");
  if (overallSignal === "red") nextActions.push("先比較其他路段或降低總價與負擔條件");
  if (overallSignal === "unknown") nextActions.push(...missingChecks.slice(0, 3));
  if (priceReasonableness.status === "overpriced") nextActions.push("以估價區間與可比成交作為議價依據");
  if (location) nextActions.push("實地確認交通尖峰、噪音與嫌惡設施");

  return {
    overallSignal, overallLabel, overallScore, decisionSuggestion, priceReasonableness,
    riskFactors: uniqueByKey(riskFactors),
    positiveFactors: uniqueByKey(positiveFactors),
    missingChecks: [...new Set(missingChecks)],
    nextActions: [...new Set(nextActions)],
    dataConfidence,
  };
}

function assessPrice(price: number | undefined, valuation?: ValuationResult): RiskSummary["priceReasonableness"] {
  if (price === undefined || !valuation) return { status: "unknown", label: "尚未完成", explanation: "需要物件開價與估價區間才能比較。" };
  if (price < valuation.price_range.low * 0.95) return { status: "undervalued", label: "低於估價區間", explanation: `帶入價格 ${price.toLocaleString()} 萬，低於估價下緣 5% 以上，仍需確認屋況與交易條件。` };
  if (price > valuation.price_range.high * 1.05) return { status: "overpriced", label: "高於估價區間", explanation: `帶入價格 ${price.toLocaleString()} 萬，高於估價上緣 5% 以上，建議保留議價空間。` };
  return { status: "reasonable", label: "接近合理區間", explanation: `帶入價格 ${price.toLocaleString()} 萬，位於估價區間內或接近區間邊界。` };
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
  const title = kind === "loan" ? "貸款負擔" : "持有成本負擔";
  if (ratio <= lowLimit) {
    positives.push({ key: kind, title, message: `負擔率 ${(ratio * 100).toFixed(1)}%，目前在較健康範圍。` });
    return 90;
  }
  if (ratio <= mediumLimit) {
    risks.push({ key: kind, level: "medium", title, message: `負擔率 ${(ratio * 100).toFixed(1)}%，需保留生活與緊急預備金。` });
    return 65;
  }
  risks.push({ key: kind, level: "high", title, message: `負擔率 ${(ratio * 100).toFixed(1)}%，目前負擔偏重。` });
  return 25;
}

function assessLocation(location: LocationInsightResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"]): number {
  if (!location || location.location_score === null) return 45;
  if (location.location_score >= 75) positives.push({ key: "location", title: "區位條件", message: `區位總分 ${location.location_score}，生活圈條件具支持性。` });
  else if (location.location_score < 55) risks.push({ key: "location", level: "high", title: "區位條件", message: `區位總分 ${location.location_score}，建議確認是否符合日常需求。` });
  else risks.push({ key: "location", level: "medium", title: "區位條件", message: `區位總分 ${location.location_score}，優缺點需實地確認。` });
  if (location.poi_summary.risk_facility_count > 0) risks.push({ key: "risk-facilities", level: "high", title: "周邊風險設施", message: `生活圈資料顯示 ${location.poi_summary.risk_facility_count} 個風險設施，需實地確認。` });
  return location.location_score;
}

function addPriceFactors(price: RiskSummary["priceReasonableness"], risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"]) {
  if (price.status === "overpriced") risks.push({ key: "price", level: "high", title: "開價合理性", message: price.explanation });
  if (price.status === "reasonable") positives.push({ key: "price", title: "開價合理性", message: price.explanation });
  if (price.status === "undervalued") positives.push({ key: "price", title: "價格低於估價區間", message: price.explanation });
}

function addConfidenceFactors(confidence: RiskSummary["dataConfidence"], valuation: ValuationResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"]) {
  if (confidence === "high") positives.push({ key: "confidence", title: "估價資料信心", message: `估價信心 ${valuation?.confidence_score} 分且採官方資料。` });
  if (confidence === "low") risks.push({ key: "confidence", level: "high", title: "估價資料信心", message: "估價信心偏低或含展示樣本，價格判斷需保守。" });
  if (confidence === "medium") risks.push({ key: "confidence", level: "medium", title: "估價資料信心", message: "估價信心中等，建議補看可比成交與資料限制。" });
}

function addLocationPriceSupport(location: LocationInsightResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"], missing: string[]) {
  if (!location || location.valuation_context.supports_price_reasonableness === "unknown") {
    missing.push("確認區位條件是否支持目前開價");
    return;
  }
  if (location.valuation_context.supports_price_reasonableness) {
    positives.push({ key: "location-price", title: "區位支持價格", message: location.valuation_context.explanation });
  } else {
    risks.push({ key: "location-price", level: "medium", title: "區位未支持價格", message: location.valuation_context.explanation });
  }
}

function addTerrainRisk(terrainRisk: TerrainRiskResult | undefined, risks: RiskSummary["riskFactors"], positives: RiskSummary["positiveFactors"], missing: string[]) {
  if (!terrainRisk) {
    missing.push("尚未完成地勢與災害風險分析");
    return;
  }
  if (terrainRisk.overall.level === "unknown" || terrainRisk.data_quality.status === "unavailable") {
    missing.push("地勢與災害風險資料不足，需至官方圖台確認");
    return;
  }
  if (terrainRisk.overall.level === "high") {
    risks.push({ key: "terrain-risk", level: "high", title: "地勢與災害風險", message: terrainRisk.overall.summary });
  } else if (terrainRisk.overall.level === "medium") {
    risks.push({ key: "terrain-risk", level: "medium", title: "地勢與災害風險", message: terrainRisk.overall.summary });
  } else {
    positives.push({ key: "terrain-risk", title: "地勢與災害風險", message: "可用官方圖資目前未比對到明確風險，仍需實地確認。" });
  }
}

function signalFor(score: number | null): RiskSummary["overallSignal"] {
  if (score === null) return "unknown";
  if (score >= 75) return "green";
  if (score >= 55) return "yellow";
  return "red";
}

function uniqueByKey<T extends { key: string }>(items: T[]): T[] {
  return [...new Map(items.map((item) => [item.key, item])).values()];
}
