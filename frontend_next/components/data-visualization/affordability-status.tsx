"use client";

import type { HoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import type { LoanVisualModel } from "@/lib/loan-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type Affordability = LoanVisualModel["affordability"] | HoldingCostVisualModel["affordability"];

export function AffordabilityStatus({ value }: { value: Affordability }) {
  const { copy } = useExperienceLocale();
  return <section role="status" aria-label={`${copy("viz.affordabilityStatusLabel")}${value.label}`} className="rounded-xl border border-amber-200 bg-amber-50 p-3">
    <p className="text-xs font-bold text-amber-900">{copy("viz.affordabilityStatusPrefix")}{value.label}</p>
    <p className="mt-1 text-xs leading-5 text-amber-800">{value.message}</p>
  </section>;
}
