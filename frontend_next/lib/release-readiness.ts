export type ReleaseReadinessState = "ready" | "partial" | "blocked";

export type ReleaseReadinessInput = {
  backendReachable: boolean;
  frontendBuildVerified: boolean;
  testsVerified: boolean;
  marketCoverageFull: boolean;
  officialValuationAvailable: boolean;
  productionUiVerified: boolean;
};

export type ReleaseReadinessSummary = {
  state: ReleaseReadinessState;
  label: string;
  detail: string;
};

export function buildReleaseReadinessSummary(input: ReleaseReadinessInput): ReleaseReadinessSummary {
  const blocked = !input.backendReachable || !input.testsVerified || !input.frontendBuildVerified;
  if (blocked) {
    return { state: "blocked", label: "Blocked", detail: "必要的服務、測試或建置驗證尚未通過。" };
  }
  const ready = input.marketCoverageFull && input.officialValuationAvailable && input.productionUiVerified;
  if (ready) {
    return { state: "ready", label: "Ready", detail: "品質閘門與正式驗收條件皆已確認。" };
  }
  return { state: "partial", label: "Partial", detail: "技術驗證已完成，但仍有正式資料或人工驗收項目待確認。" };
}
