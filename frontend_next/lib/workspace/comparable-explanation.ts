/** Versioned public evidence only. No selection reconstruction or I/O. */
export type DecisionDimension = {
  target: string | number | null; comparable: string | number | null;
  difference: number | null; role: "scope" | "ranking" | "weight" | "outlier" | "context";
  threshold: [number, number] | null;
};
export const DECISION_DIMENSIONS = ["location", "building_type", "area", "age", "distance", "recency", "unit_price", "floor", "parking", "community_distance"] as const;
export const DECISION_REASONS = ["selected", "time_window", "official_source", "required_metrics", "scope", "price_outlier", "rank_limit", "insufficient_samples", "community_distance", "community_distance_unknown"] as const;
export type DecisionReason = typeof DECISION_REASONS[number];
export type DecisionCandidate = {
  candidate_id: string; status: "included" | "excluded"; reasons: DecisionReason[];
  transaction_period: string | null; dimensions: Record<typeof DECISION_DIMENSIONS[number], DecisionDimension>;
};
export type ComparableExplanation = {
  version: "comparable-explanation-v1"; selection_version: "deterministic-valuation-v1";
  coverage: "returned_candidates_only"; reference_period: string; recency_reference_period: string;
  window_start: string | null; scope: "none" | "community" | "road" | "district" | "city" | "fallback";
  considered_count: number; selected_count: number; excluded_count: number; provider_excluded_count: null;
  reason_counts: Partial<Record<DecisionReason, number>>; excluded_example_bound: 5;
  outlier_bounds: [number, number] | null; outlier_fallback: boolean;
  selected: DecisionCandidate[]; excluded_examples: DecisionCandidate[];
};

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}
function count(value: unknown): value is number { return typeof value === "number" && Number.isSafeInteger(value) && value >= 0; }
function scalar(value: unknown): string | number | null {
  return typeof value === "string" ? value.slice(0, 160) : typeof value === "number" && Number.isFinite(value) ? value : null;
}
function bounds(value: unknown): [number, number] | null {
  return Array.isArray(value) && value.length === 2 && value.every((v) => typeof v === "number" && Number.isFinite(v)) && value[0] <= value[1] ? [value[0], value[1]] : null;
}
function period(value: unknown): value is string { return typeof value === "string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(value); }
function candidate(value: unknown, status: DecisionCandidate["status"]): DecisionCandidate | null {
  const row = object(value); const data = object(row?.dimensions);
  if (!row || !data || row.status !== status || typeof row.candidate_id !== "string" || !/^candidate-\d+$/.test(row.candidate_id) || !Array.isArray(row.reasons) || row.reasons.length === 0 || row.reasons.length > DECISION_REASONS.length || !row.reasons.every((r) => DECISION_REASONS.includes(r))) return null;
  if (status === "included" ? row.reasons.length !== 1 || row.reasons[0] !== "selected" : row.reasons.includes("selected")) return null;
  const dimensions = {} as DecisionCandidate["dimensions"];
  for (const key of DECISION_DIMENSIONS) {
    const d = object(data[key]);
    if (!d || !["scope", "ranking", "weight", "outlier", "context"].includes(String(d.role))) return null;
    dimensions[key] = { target: scalar(d.target), comparable: scalar(d.comparable), difference: typeof d.difference === "number" && Number.isFinite(d.difference) ? d.difference : null, role: d.role as DecisionDimension["role"], threshold: bounds(d.threshold) };
    if (dimensions[key].target === null || dimensions[key].comparable === null) dimensions[key].difference = null;
    if (key === "parking") dimensions[key] = { target: null, comparable: null, difference: null, role: "context", threshold: null };
  }
  return { candidate_id: row.candidate_id.slice(0, 40), status, reasons: [...new Set(row.reasons)] as DecisionReason[], transaction_period: typeof row.transaction_period === "string" ? row.transaction_period.slice(0, 16) : null, dimensions };
}

/** Malformed or incomplete trace is unavailable. Whitelist all persisted fields. */
export function compactComparableExplanation(value: unknown): ComparableExplanation | undefined {
  const trace = object(value);
  if (!trace || trace.version !== "comparable-explanation-v1" || trace.selection_version !== "deterministic-valuation-v1" || trace.coverage !== "returned_candidates_only" || !period(trace.reference_period) || !period(trace.recency_reference_period) || !(trace.window_start === null || period(trace.window_start)) || !["none", "community", "road", "district", "city", "fallback"].includes(String(trace.scope)) || !count(trace.considered_count) || !count(trace.selected_count) || !count(trace.excluded_count) || trace.selected_count + trace.excluded_count !== trace.considered_count || trace.selected_count > 10 || trace.excluded_example_bound !== 5 || !Array.isArray(trace.selected) || trace.selected.length !== trace.selected_count || !Array.isArray(trace.excluded_examples) || trace.excluded_examples.length > 5 || trace.excluded_examples.length > trace.excluded_count || typeof trace.outlier_fallback !== "boolean") return undefined;
  const selected = trace.selected.map((row) => candidate(row, "included"));
  const excluded = trace.excluded_examples.map((row) => candidate(row, "excluded"));
  if (selected.some((row) => !row) || excluded.some((row) => !row)) return undefined;
  const all = [...selected, ...excluded] as DecisionCandidate[];
  if (new Set(all.map((row) => row.candidate_id)).size !== all.length) return undefined;
  const rawCounts = object(trace.reason_counts); if (!rawCounts) return undefined;
  const reason_counts: ComparableExplanation["reason_counts"] = {};
  for (const reason of DECISION_REASONS) {
    const n = rawCounts[reason];
    if (n === undefined) continue;
    if (!count(n) || n > trace.excluded_count || reason === "selected") return undefined;
    reason_counts[reason] = n;
  }
  if (Object.values(reason_counts).reduce((sum, n) => sum + n, 0) < trace.excluded_count) return undefined;
  for (const reason of DECISION_REASONS) {
    const observed = (excluded as DecisionCandidate[]).filter((row) => row.reasons.includes(reason)).length;
    if (observed > (reason_counts[reason] ?? 0)) return undefined;
  }
  return {
    version: trace.version, selection_version: trace.selection_version, coverage: trace.coverage,
    reference_period: trace.reference_period, recency_reference_period: trace.recency_reference_period,
    window_start: trace.window_start, scope: trace.scope as ComparableExplanation["scope"],
    considered_count: trace.considered_count, selected_count: trace.selected_count, excluded_count: trace.excluded_count,
    provider_excluded_count: null, reason_counts, excluded_example_bound: 5,
    outlier_bounds: bounds(trace.outlier_bounds), outlier_fallback: trace.outlier_fallback,
    selected: selected as DecisionCandidate[], excluded_examples: excluded as DecisionCandidate[],
  };
}
