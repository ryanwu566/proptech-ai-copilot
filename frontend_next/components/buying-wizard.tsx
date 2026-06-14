"use client";

import { BUYING_WIZARD_STEPS, getActiveWizardStep, isWizardStepCompleted, type BuyingWizardStep } from "@/lib/buying-wizard-status";
import { OPEN_TAXORACLE_EVENT, type WorkflowStatus } from "@/lib/workflow-status";

export type WizardStepSummary = Partial<Record<BuyingWizardStep, string[]>>;

export function BuyingWizard({ status, summaries = {} }: { status: WorkflowStatus; summaries?: WizardStepSummary }) {
  const active = getActiveWizardStep(status);
  function go(targetId: string) {
    if (targetId === "taxoracle") return window.dispatchEvent(new Event(OPEN_TAXORACLE_EVENT));
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  return <section className="min-w-0 rounded-2xl border border-cyan-200 bg-white p-4 shadow-sm" aria-label="看房分析 Wizard">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-[10px] font-bold tracking-[0.18em] text-cyan-700">BUYING WIZARD</p><h2 className="mt-1 text-lg font-extrabold text-slate-950">第 {BUYING_WIZARD_STEPS.indexOf(active) + 1} 步：{active.label}</h2><p className="mt-1 text-xs leading-5 text-slate-600">{active.guide}</p></div><div className="shrink-0 text-left sm:text-right"><strong className="text-2xl text-cyan-800">{status.overallProgress}%</strong><p className="text-[10px] text-slate-500">分析進度</p></div></div>
    <ol className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7">{BUYING_WIZARD_STEPS.map((step, index) => {
      const completed = isWizardStepCompleted(status, step); const current = step.id === active.id; const enabled = completed || current;
      return <li key={step.id}><button type="button" disabled={!enabled} title={enabled ? `前往${step.label}` : "請先完成目前步驟"} onClick={() => go(step.targetId)} className={`flex min-h-16 w-full items-center gap-2 rounded-xl border px-3 py-2 text-left text-xs font-bold transition disabled:cursor-not-allowed disabled:opacity-45 ${current ? "border-cyan-400 bg-cyan-50 text-cyan-900 ring-2 ring-cyan-100" : completed ? "border-emerald-200 bg-emerald-50 text-emerald-900 hover:border-emerald-400" : "border-stone-200 bg-stone-50 text-slate-500"}`}><span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-[10px] ${completed ? "bg-emerald-600 text-white" : current ? "bg-cyan-700 text-white" : "bg-stone-200 text-slate-500"}`}>{completed ? "✓" : index + 1}</span><span>{step.label}</span></button></li>;
    })}</ol>
    {Object.values(summaries).some((lines) => lines?.length) && <details className="mt-4 rounded-xl border border-stone-200 bg-stone-50"><summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">查看已完成步驟摘要</summary><div className="grid gap-3 border-t border-stone-200 p-3 sm:grid-cols-2">{BUYING_WIZARD_STEPS.filter((step) => isWizardStepCompleted(status, step) && summaries[step.id]?.length).map((step) => <article key={step.id} className="rounded-xl border border-stone-200 bg-white p-3"><div className="flex items-center justify-between gap-2"><h3 className="text-xs font-bold text-slate-900">{step.label}已完成</h3><button type="button" onClick={() => go(step.targetId)} className="rounded-lg border border-stone-200 px-2 py-1 text-[10px] font-bold text-slate-600 hover:border-cyan-300">返回修改</button></div><ul className="mt-2 space-y-1 text-[11px] leading-5 text-slate-600">{summaries[step.id]?.map((line) => <li key={line}>{line}</li>)}</ul></article>)}</div></details>}
    <button type="button" onClick={() => go(status.nextActionTargetId)} className="mt-4 w-full rounded-xl bg-cyan-700 px-5 py-3 text-sm font-bold text-white transition hover:bg-cyan-800">{status.nextActionLabel}</button>
  </section>;
}
