import type { JourneyStepDefinition, JourneyStepId } from "@/lib/guided-journey";

type JourneyStepperProps = {
  steps: readonly JourneyStepDefinition[];
  activeStep: JourneyStepId;
  visitedSteps: readonly JourneyStepId[];
  onSelect: (step: JourneyStepId) => void;
};

type StepButtonProps = Omit<JourneyStepperProps, "steps"> & { step: JourneyStepDefinition };

function StepButton({ step, activeStep, visitedSteps, onSelect }: StepButtonProps) {
  const active = step.id === activeStep;
  const visited = visitedSteps.includes(step.id);
  return <button type="button" aria-current={active ? "step" : undefined} onClick={() => onSelect(step.id)} className={"w-full rounded-xl border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 " + (active ? "border-cyan-400 bg-cyan-50 shadow-sm" : "border-stone-200 bg-white hover:border-cyan-200")}>
    <span className="flex items-start gap-3"><span className={"grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-black " + (active ? "bg-cyan-700 text-white" : visited ? "bg-cyan-100 text-cyan-900" : "bg-stone-100 text-slate-500")}>{step.number}</span><span className="min-w-0"><strong className="block text-sm text-slate-900">{step.title}</strong><span className="mt-1 block text-[11px] text-slate-500">{active ? "目前步驟" : visited ? "已瀏覽" : "尚未瀏覽"}</span></span></span>
  </button>;
}

export function JourneyStepper({ steps, activeStep, visitedSteps, onSelect }: JourneyStepperProps) {
  return <nav aria-label="購屋判斷流程" className="space-y-3">
    <div className="hidden space-y-2 lg:block">{steps.map((step) => <StepButton key={step.id} step={step} activeStep={activeStep} visitedSteps={visitedSteps} onSelect={onSelect} />)}</div>
    <details className="rounded-xl border border-stone-200 bg-white lg:hidden">
      <summary className="cursor-pointer px-3 py-3 text-sm font-bold text-slate-900">查看全部步驟</summary>
      <div className="space-y-2 border-t border-stone-100 p-3">{steps.map((step) => <StepButton key={step.id} step={step} activeStep={activeStep} visitedSteps={visitedSteps} onSelect={onSelect} />)}</div>
    </details>
  </nav>;
}
