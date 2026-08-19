"use client";

import { ExperienceStatePanel } from "@/components/experience-state-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function JourneyMissingDataPanel({ title, items, state = "partial", nextAction, onAction }: { title: string; items: readonly string[]; state?: "empty" | "partial" | "limited" | "unknown" | "not_assessed" | "no_official_data"; nextAction?: string; onAction?: () => void }) {
  const { copy } = useExperienceLocale();
  return <ExperienceStatePanel state={state} title={title} nextAction={nextAction} onAction={onAction}>
    {items.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-900">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-xs leading-5 text-amber-900">{copy("journey.missingNoData")}</p>}
  </ExperienceStatePanel>;
}
