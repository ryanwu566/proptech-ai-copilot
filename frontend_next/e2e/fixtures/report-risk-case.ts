import { e9Case } from "../../lib/workspace/e9-test-fixtures";

/** Saved production-shaped Risk evidence; never queries or imports a provider. */
export function reportRiskCase(periods = ["未提供", "113年度（官方公開 MVT）", "2026-08-20"]) {
  const saved = e9Case("risk-periods");
  saved.data.terrainReference!.layers.forEach((layer, index) => {
    layer.data_updated_at = periods[index % periods.length];
  });
  return saved;
}
