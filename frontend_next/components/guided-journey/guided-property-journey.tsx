"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getJourneyStepCopy, JOURNEY_STEPS, addVisitedJourneyStep, getJourneyStepForTool, getNextJourneyStep, getPreviousJourneyStep, type JourneyRenderActions, type JourneyStepId } from "@/lib/guided-journey";
import { JourneyProgressSummary } from "@/components/guided-journey/journey-progress-summary";
import { JourneyStage } from "@/components/guided-journey/journey-stage";
import { JourneyStepper } from "@/components/guided-journey/journey-stepper";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function GuidedPropertyJourney({ renderStep }: { renderStep: (step: JourneyStepId, actions: JourneyRenderActions) => ReactNode }) {
  const [activeStep, setActiveStep] = useState<JourneyStepId>("property");
  const [visitedSteps, setVisitedSteps] = useState<JourneyStepId[]>(["property"]);
  const { t } = useExperienceLocale();

  useEffect(() => {
    const onVoiceStep = (event: Event) => {
      const step = (event as CustomEvent<JourneyStepId>).detail;
      if (JOURNEY_STEPS.some((item) => item.id === step)) selectStep(step);
    };
    window.addEventListener("proptech:select-journey-step", onVoiceStep);
    return () => window.removeEventListener("proptech:select-journey-step", onVoiceStep);
  }, []);

  function selectStep(step: JourneyStepId) {
    setVisitedSteps((current) => addVisitedJourneyStep(current, step));
    setActiveStep(step);
  }

  function moveTo(step: JourneyStepId | undefined) {
    selectStep(step ?? "property");
  }

  const actions: JourneyRenderActions = {
    activeStep,
    selectStep,
    goToPreviousStep: () => moveTo(getPreviousJourneyStep(activeStep)),
    goToNextStep: () => moveTo(getNextJourneyStep(activeStep)),
    goToTool: (toolId) => {
      const step = getJourneyStepForTool(toolId);
      if (step) selectStep(step);
    },
  };

  const activeCopy = getJourneyStepCopy(activeStep, t);
  return <section aria-label={t("journey.title")} className="space-y-5">
    <header className="rounded-2xl border border-cyan-200 bg-slate-950 px-4 py-6 text-white shadow-lg sm:px-6 sm:py-8">
      <p className="text-[10px] font-bold tracking-[0.2em] text-cyan-200">{t("journey.eyebrow")}</p>
      <h1 className="mt-3 max-w-3xl text-3xl font-black tracking-tight sm:text-4xl">{t("journey.title")}</h1>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">{t("journey.description")}</p>
      <p className="mt-4 text-xs leading-5 text-cyan-100">{t("journey.current")}: {activeCopy.title}</p>
    </header>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[240px_minmax(0,1fr)] lg:items-start">
      <aside className="space-y-3 lg:sticky lg:top-16">
        <JourneyProgressSummary visitedSteps={visitedSteps} totalSteps={JOURNEY_STEPS.length} />
        <JourneyStepper steps={JOURNEY_STEPS} activeStep={activeStep} visitedSteps={visitedSteps} onSelect={selectStep} />
      </aside>
      <main className="min-w-0 space-y-4">
        {JOURNEY_STEPS.filter((step) => visitedSteps.includes(step.id)).map((step) => <JourneyStage key={step.id} step={step} active={activeStep === step.id} onPrevious={() => moveTo(getPreviousJourneyStep(step.id))} onNext={() => moveTo(getNextJourneyStep(step.id))} hasPrevious={Boolean(getPreviousJourneyStep(step.id))} hasNext={Boolean(getNextJourneyStep(step.id))}>{renderStep(step.id, actions)}</JourneyStage>)}
      </main>
    </div>
  </section>;
}
