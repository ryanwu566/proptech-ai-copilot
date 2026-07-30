import type { ReactNode } from "react";
import { getJourneyStepCopy, type JourneyStepDefinition } from "@/lib/guided-journey";
import { JourneyNavigation } from "@/components/guided-journey/journey-navigation";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function JourneyStage({ step, active, children, onPrevious, onNext, hasPrevious, hasNext }: { step: JourneyStepDefinition; active: boolean; children: ReactNode; onPrevious: () => void; onNext: () => void; hasPrevious: boolean; hasNext: boolean }) {
  const { t } = useExperienceLocale();
  const copy = getJourneyStepCopy(step, t);
  const headingId = `journey-stage-heading-${step.id}`;
  return <section id={`journey-stage-${step.id}`} hidden={!active} aria-hidden={!active} aria-labelledby={headingId} data-action-contract="one-primary-per-view" data-primary-action-id={step.primaryActionId} className="min-w-0 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm sm:p-6">
    <div className="min-w-0 border-b border-stone-100 pb-4"><p className="text-[10px] font-bold tracking-wider text-cyan-700">{t("journey.step")} {step.number}</p><h2 id={headingId} className="mt-1 break-words text-2xl font-black tracking-tight text-slate-950">{copy.title}</h2><p className="mt-3 max-w-3xl text-base font-bold leading-6 text-slate-800">{copy.question}</p><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{copy.description}</p><p className="mt-3 break-words text-[11px] text-slate-500">{t("journey.tools")}: {copy.toolLabels.join(" · ")}</p></div>
    <div className="mt-5 min-w-0">{children}</div>
    <JourneyNavigation previousLabel={copy.previousLabel} nextLabel={copy.nextLabel} onPrevious={onPrevious} onNext={onNext} hasPrevious={hasPrevious} hasNext={hasNext} />
  </section>;
}
