"use client";

import { DataStatusBadge } from "./data-status-badge";
import type { VisualFreshnessStatus } from "@/lib/market-insight-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function FreshnessIndicator({ status }: { status: VisualFreshnessStatus }) {
  const { copy } = useExperienceLocale();
  return <div aria-label={copy("viz.freshnessLabel")} className="flex items-center gap-2"><DataStatusBadge status={status} /><span className="text-xs text-slate-500">{copy("viz.freshnessHint")}</span></div>;
}
