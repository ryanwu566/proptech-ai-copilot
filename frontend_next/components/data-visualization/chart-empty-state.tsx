"use client";

import { ExperienceStatePanel } from "@/components/experience-state-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function ChartEmptyState({ title }: { title?: string }) {
  const { copy } = useExperienceLocale();
  return <ExperienceStatePanel state="partial" title={title ?? copy("viz.chartEmptyTitle")} explanation={copy("viz.chartEmptyExplanation")} nextAction={copy("viz.chartEmptyNextAction")} />;
}
