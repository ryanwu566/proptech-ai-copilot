"use client";

import type { JourneyDecisionContext } from "@/lib/decision-case-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function DecisionCaseStatusStrip({ context }: { context: JourneyDecisionContext }) {
  const { copy } = useExperienceLocale();
  const items: [string, string][] = [
    [copy("journey.caseStatusProperty"), context.propertyContext.selectionStatus === "not_selected" ? copy("journey.caseStatusNotProvided") : context.propertyContext.selectionStatus === "partial" ? copy("journey.caseStatusPartial") : copy("journey.caseStatusEntered")],
    [copy("journey.caseStatusPrice"), context.officialValuationAvailable ? copy("journey.caseStatusOfficialAvailable") : context.priceStatus === "demo" ? copy("journey.caseStatusDemoNotTransferable") : context.priceStatus === "unavailable" ? copy("journey.caseStatusDataUnavailable") : copy("journey.caseStatusInsufficient")],
    [copy("journey.caseStatusAfford"), context.affordabilityStatus === "available" ? copy("journey.caseStatusCalculated") : context.affordabilityStatus === "partial" ? copy("journey.caseStatusPartialData") : context.taxStatus === "not_eligible" ? copy("journey.caseStatusNeedReview") : copy("journey.caseStatusNotCalculated")],
    [copy("journey.caseStatusDueDiligence"), copy("journey.caseStatusNotStarted")],
    [copy("journey.caseStatusViewing"), copy("journey.caseStatusNoRecords")],
  ];
  return <section aria-label={copy("journey.caseActionTitle")} className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">{items.map(([label, value]) => <div key={label} className="min-w-0 rounded-lg border border-stone-200 bg-stone-50 p-3"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className="mt-1 break-words text-xs font-black text-slate-900">{value}</p></div>)}</div></section>;
}
