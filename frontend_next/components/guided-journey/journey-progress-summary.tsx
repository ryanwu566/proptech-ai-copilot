import type { JourneyStepId } from "@/lib/guided-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function JourneyProgressSummary({ visitedSteps, totalSteps }: { visitedSteps: readonly JourneyStepId[]; totalSteps: number }) {
  const { t } = useExperienceLocale();
  const count = t("journey.progressCount").replace("{visited}", String(visitedSteps.length)).replace("{total}", String(totalSteps));
  return <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-3 text-xs text-cyan-950">
    <p className="font-bold">{t("journey.progressTitle")}</p>
    <p className="mt-1">{count}</p>
    <p className="mt-1 text-[11px] leading-5 text-cyan-800">{t("journey.progressNote")}</p>
  </div>;
}

// 流程瀏覽進度 · 已瀏覽 · 瀏覽進度不代表資料完整度或決策完成度
