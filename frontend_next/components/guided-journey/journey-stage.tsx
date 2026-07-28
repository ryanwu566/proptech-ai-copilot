import type { ReactNode } from "react";
import type { JourneyStepDefinition } from "@/lib/guided-journey";
import { JourneyNavigation } from "@/components/guided-journey/journey-navigation";

export function JourneyStage({ step, active, children, onPrevious, onNext, hasPrevious, hasNext }: { step: JourneyStepDefinition; active: boolean; children: ReactNode; onPrevious: () => void; onNext: () => void; hasPrevious: boolean; hasNext: boolean }) {
  const headingId = "journey-stage-heading-" + step.id;
  return <section id={"journey-stage-" + step.id} hidden={!active} aria-hidden={!active} aria-labelledby={headingId} className="min-w-0 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm sm:p-6">
    <div className="border-b border-stone-100 pb-4"><p className="text-[10px] font-bold tracking-wider text-cyan-700">第 {step.number} 步</p><h2 id={headingId} className="mt-1 text-2xl font-black tracking-tight text-slate-950">{step.title}</h2><p className="mt-3 text-base font-bold leading-6 text-slate-800">{step.question}</p><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{step.description}</p><p className="mt-3 text-[11px] text-slate-500">專業工具：{step.toolLabels.join("、")}</p></div>
    <div className="mt-5">{children}</div>
    <JourneyNavigation previousLabel={step.previousLabel} nextLabel={step.nextLabel} onPrevious={onPrevious} onNext={onNext} hasPrevious={hasPrevious} hasNext={hasNext} />
  </section>;
}
