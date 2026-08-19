"use client";

import type { JourneyDecisionContext } from "@/lib/decision-case-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function DecisionReadinessSummary({ context }: { context: JourneyDecisionContext }) {
  const { copy } = useExperienceLocale();
  const known = [context.propertyContext.selectionStatus !== "not_selected", context.officialValuationAvailable, context.loanKnown, context.holdingKnown, context.taxStatus !== "not_started"].filter(Boolean).length;
  return <section aria-labelledby="decision-readiness-summary-heading" className="min-w-0 rounded-xl border border-violet-100 bg-violet-50/50 p-4"><h3 id="decision-readiness-summary-heading" className="text-base font-black text-slate-950">{copy("journey.readinessTitle")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{copy("journey.readinessDesc")} ({copy("journey.readinessKnown")}: {known})</p><ul className="mt-3 grid gap-2 text-xs text-slate-700 sm:grid-cols-2"><li className="rounded-lg bg-white p-3">{copy("journey.readinessPrice")}: {context.officialValuationAvailable ? copy("journey.readinessPriceAvailable") : copy("journey.readinessPriceNotAvailable")}</li><li className="rounded-lg bg-white p-3">{copy("journey.readinessFunding")}: {context.loanKnown ? copy("journey.readinessFundingAvailable") : copy("journey.readinessFundingStart")}</li><li className="rounded-lg bg-white p-3">{copy("journey.readinessCase")}: {context.candidateCaseId ? copy("journey.readinessCaseContinue") : copy("journey.readinessCaseDecide")}</li><li className="rounded-lg bg-white p-3">{copy("journey.readinessNext")}: {context.missingDataLabels[0] || copy("journey.missingNoData")}</li></ul></section>;
}
