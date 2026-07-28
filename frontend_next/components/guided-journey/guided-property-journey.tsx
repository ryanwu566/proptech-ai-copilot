"use client";

import { useState, type ReactNode } from "react";
import { JOURNEY_STEPS, addVisitedJourneyStep, getNextJourneyStep, getPreviousJourneyStep, type JourneyStepId } from "@/lib/guided-journey";
import { JourneyExpertTools } from "@/components/guided-journey/journey-expert-tools";
import { JourneyProgressSummary } from "@/components/guided-journey/journey-progress-summary";
import { JourneyStage } from "@/components/guided-journey/journey-stage";
import { JourneyStepper } from "@/components/guided-journey/journey-stepper";

export function GuidedPropertyJourney({ renderStep, renderExpertTools }: { renderStep: (step: JourneyStepId) => ReactNode; renderExpertTools: () => ReactNode }) {
  const [activeStep, setActiveStep] = useState<JourneyStepId>("property");
  const [visitedSteps, setVisitedSteps] = useState<JourneyStepId[]>(["property"]);

  function selectStep(step: JourneyStepId) {
    setVisitedSteps((current) => addVisitedJourneyStep(current, step));
    setActiveStep(step);
  }

  function moveTo(step: JourneyStepId | undefined) {
    selectStep(step ?? "property");
  }

  return <section aria-label="購屋判斷旅程" className="space-y-5">
    <header className="rounded-2xl border border-cyan-200 bg-slate-950 px-4 py-6 text-white shadow-lg sm:px-6 sm:py-8">
      <p className="text-[10px] font-bold tracking-[0.2em] text-cyan-200">GUIDED PROPERTY DECISION JOURNEY</p>
      <h1 className="mt-3 max-w-3xl text-3xl font-black tracking-tight sm:text-4xl">從一間房開始，逐步完成購屋判斷</h1>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">先確認物件，再依序查看地點、價格、資金與案件完整度。每個結果都可以展開查看資料來源與計算依據。</p>
      <p className="mt-4 text-xs leading-5 text-cyan-100">目前步驟：{JOURNEY_STEPS.find((step) => step.id === activeStep)?.title}</p>
    </header>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[240px_minmax(0,1fr)] lg:items-start">
      <aside className="space-y-3 lg:sticky lg:top-16">
        <JourneyProgressSummary visitedSteps={visitedSteps} totalSteps={JOURNEY_STEPS.length} />
        <JourneyStepper steps={JOURNEY_STEPS} activeStep={activeStep} visitedSteps={visitedSteps} onSelect={selectStep} />
        <JourneyExpertTools renderTools={renderExpertTools} />
      </aside>
      <main className="min-w-0 space-y-4">
        {JOURNEY_STEPS.filter((step) => visitedSteps.includes(step.id)).map((step) => <JourneyStage key={step.id} step={step} active={activeStep === step.id} onPrevious={() => moveTo(getPreviousJourneyStep(step.id))} onNext={() => moveTo(getNextJourneyStep(step.id))} hasPrevious={Boolean(getPreviousJourneyStep(step.id))} hasNext={Boolean(getNextJourneyStep(step.id))}>{renderStep(step.id)}</JourneyStage>)}
      </main>
    </div>
  </section>;
}
