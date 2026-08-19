"use client";

import { ExperienceStatePanel } from "@/components/experience-state-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function ChartUnavailableState() {
  const { copy } = useExperienceLocale();
  return <ExperienceStatePanel state="unavailable" title={copy("viz.chartUnavailableTitle")} explanation={copy("viz.chartUnavailableExplanation")} />;
}
