export function riskSummaryCounts(model: { materialEvidenceCount: number; unknownEvidenceCount: number } | null): {
  material: number | "尚未查詢";
  unknown: number | "尚未查詢";
} {
  return model
    ? { material: model.materialEvidenceCount, unknown: model.unknownEvidenceCount }
    : { material: "尚未查詢", unknown: "尚未查詢" };
}
