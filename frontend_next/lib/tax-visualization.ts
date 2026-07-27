import type { TaxResult } from "./api";

export type TaxOutcomeKey = "passed" | "manual_review" | "failed" | "other";
export type TaxVisualModel = {
  state: "available" | "unavailable";
  eligibility: { key: TaxResult["eligibility_status"]; label: string; message: string };
  riskScore: number | null;
  signal: { key: TaxResult["signal_color"]; label: string };
  counts: { passed: number; manualReview: number; failed: number; other: number; missingDocs: number };
  outcomes: { key: TaxOutcomeKey; label: string; count: number }[];
  keyRules: { code: string; title: string; outcome: string; detail: string }[];
  missingDocs: string[];
  reminderTimeline: string[];
  entersFiveYearMonitoring: boolean | null;
  evidence: { key: string; label: string; value: string }[];
};

const validScore = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100;
const eligibilityLabels: Record<TaxResult["eligibility_status"], { label: string; message: string }> = {
  eligible: { label: "目前未發現阻擋項目", message: "依本次輸入條件，快篩規則目前未發現阻擋項目，仍須以正式文件與主管機關認定為準。" },
  manual_review: { label: "需要人工複核", message: "本案有條件需要補件或人工複核，尚不能視為符合資格。" },
  not_eligible: { label: "目前有阻擋項目", message: "依本次輸入條件，快篩規則出現阻擋項目；正式結果仍以主管機關與專業人員審查為準。" },
};
const signalLabels: Record<TaxResult["signal_color"], string> = { green: "綠色訊號", yellow: "黃色訊號", red: "紅色訊號" };

function emptyModel(): TaxVisualModel {
  return { state: "unavailable", eligibility: { key: "manual_review", label: "未評估", message: "尚未取得稅務快篩結果。" }, riskScore: null, signal: { key: "yellow", label: "未評估" }, counts: { passed: 0, manualReview: 0, failed: 0, other: 0, missingDocs: 0 }, outcomes: [], keyRules: [], missingDocs: [], reminderTimeline: [], entersFiveYearMonitoring: null, evidence: [] };
}

export function buildTaxVisualModel(result: TaxResult | undefined): TaxVisualModel {
  if (!result) return emptyModel();
  const passed = result.rule_traces.filter((row) => row.outcome === "passed").length;
  const manualReview = result.rule_traces.filter((row) => row.outcome === "manual_review").length;
  const failed = result.rule_traces.filter((row) => row.outcome === "failed" || row.outcome === "hard_fail").length;
  const other = result.rule_traces.filter((row) => !["passed", "manual_review", "failed", "hard_fail"].includes(row.outcome)).length;
  const outcomes = [
    { key: "passed" as const, label: "通過", count: passed },
    { key: "manual_review" as const, label: "需複核", count: manualReview },
    { key: "failed" as const, label: "阻擋／未通過", count: failed },
    { key: "other" as const, label: "其他／未辨識", count: other },
  ].filter((item) => item.count > 0);
  const eligibility = eligibilityLabels[result.eligibility_status];
  return {
    state: "available",
    eligibility: { key: result.eligibility_status, ...eligibility },
    riskScore: validScore(result.risk_score) ? result.risk_score : null,
    signal: { key: result.signal_color, label: signalLabels[result.signal_color] },
    counts: { passed, manualReview, failed, other, missingDocs: result.missing_docs.length },
    outcomes,
    keyRules: result.rule_traces.filter((row) => row.outcome !== "passed").slice(0, 3).map((row) => ({ code: row.code, title: row.title, outcome: row.outcome, detail: row.detail })),
    missingDocs: result.missing_docs,
    reminderTimeline: result.reminder_timeline,
    entersFiveYearMonitoring: typeof result.case_input.enters_five_year_monitoring === "boolean" ? result.case_input.enters_five_year_monitoring : null,
    evidence: [
      ["source", "判定來源", "TaxOracle 規則引擎 TX001–TX009"],
      ["risk_score", "風險分數", validScore(result.risk_score) ? `${result.risk_score} / 100` : "目前無法顯示"],
      ["missing_docs", "缺少文件", result.missing_docs.length ? `${result.missing_docs.length} 項` : "目前沒有回傳補件項目"],
      ["monitoring", "五年列管", typeof result.case_input.enters_five_year_monitoring === "boolean" ? (result.case_input.enters_five_year_monitoring ? "本案結果標示為是" : "本案結果標示為否") : "未評估"],
      ["disclaimer", "使用提醒", result.disclaimer],
    ].map(([key, label, value]) => ({ key, label, value })),
  };
}

export { validScore as isValidTaxRiskScore };
