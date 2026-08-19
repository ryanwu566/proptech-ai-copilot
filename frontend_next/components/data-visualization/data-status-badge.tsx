"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";
import { visualStateLabel } from "@/lib/visual-storytelling-copy";

type Status = "available" | "no_data" | "unavailable" | "fresh" | "aging" | "stale" | "unknown" | "partial" | "covered" | "not_covered";

export function DataStatusBadge({ status }: { status: Status }) {
  const { copy } = useExperienceLocale();
  const labels: Record<Status, string> = {
    available: visualStateLabel("available"),
    no_data: visualStateLabel("no_data"),
    unavailable: visualStateLabel("unavailable"),
    fresh: copy("viz.dataStatusFresh"),
    aging: copy("viz.dataStatusAging"),
    stale: visualStateLabel("stale"),
    unknown: visualStateLabel("unknown"),
    partial: visualStateLabel("partial"),
    covered: copy("viz.freshnessCovered"),
    not_covered: copy("viz.freshnessNotCovered"),
  };
  return <span role="status" aria-label={labels[status]} className="inline-flex rounded-full border border-slate-300 bg-slate-50 px-2 py-1 text-[11px] font-bold text-slate-700">{labels[status]}</span>;
}
