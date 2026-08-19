"use client";

import type { ViewingOfferReadinessResult } from "@/lib/property-case-viewing-offer";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertyCaseViewingReadiness({ readiness }: { readiness: ViewingOfferReadinessResult }) {
  const { copy } = useExperienceLocale();
  const readinessLabel = (value: string): string => value === "completed" ? copy("viz.viewingReadinessCompleted") : value === "partial" ? copy("viz.viewingReadinessPartial") : copy("viz.viewingReadinessNotProvided");
  return <section className="rounded-2xl border border-stone-200 bg-white p-4" aria-label={copy("viz.viewingTitle")}><div><p className="text-xs font-bold text-slate-500">{copy("viz.viewingKicker")}</p><h3 className="mt-1 text-sm font-black text-slate-900">{copy("viz.viewingTitle")}</h3><p className="mt-1 text-xs text-slate-600">{copy("viz.viewingDesc")}</p></div><div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-5"><Stat label={copy("viz.viewingRecords")} value={readiness.viewing_count} /><Stat label={copy("viz.viewingCompleted")} value={readiness.completed_viewing_count} /><Stat label={copy("viz.viewingQuestions")} value={readiness.open_question_count} /><Stat label={copy("viz.viewingOfferPlans")} value={readiness.offer_plan_count} /><Stat label={copy("viz.viewingNextSteps")} value={readiness.next_step_count} /></div><div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-3 text-xs leading-5 text-amber-900"><strong>{copy("viz.viewingReadinessLabel")}: {readinessLabel(readiness.readiness)}</strong><p className="mt-1">{copy("viz.viewingReadinessNote")}</p></div></section>;
}

function Stat({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-stone-50 p-2 text-center"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 text-lg font-black text-slate-900">{value}</p></div>; }
