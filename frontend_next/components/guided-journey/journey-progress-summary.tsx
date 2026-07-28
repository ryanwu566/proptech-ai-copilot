import type { JourneyStepId } from "@/lib/guided-journey";

export function JourneyProgressSummary({ visitedSteps, totalSteps }: { visitedSteps: readonly JourneyStepId[]; totalSteps: number }) {
  return <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-3 text-xs text-cyan-950">
    <p className="font-bold">流程瀏覽進度</p>
    <p className="mt-1">已瀏覽 {visitedSteps.length} / {totalSteps} 個步驟</p>
    <p className="mt-1 text-[11px] leading-5 text-cyan-800">瀏覽進度不代表資料完整度或決策完成度。</p>
  </div>;
}
