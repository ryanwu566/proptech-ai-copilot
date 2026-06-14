"use client";

import type { WorkflowStatus } from "@/lib/workflow-status";
import { OPEN_TAXORACLE_EVENT } from "@/lib/workflow-status";

export function WorkflowCommandCenter({ status }: { status: WorkflowStatus }) {
  function go(target: string) {
    if (target === "taxoracle") {
      window.dispatchEvent(new Event(OPEN_TAXORACLE_EVENT));
      return;
    }
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  return <section className="min-w-0 rounded-2xl border border-cyan-200 bg-white p-4 shadow-sm" aria-label="流程指揮中心">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0"><p className="text-[10px] font-bold tracking-wider text-cyan-700">WORKFLOW COMMAND CENTER</p><h2 className="mt-1 font-bold text-slate-950">目前進度 {status.overallProgress}% · {status.currentStep}</h2><p className="mt-1 text-xs text-slate-500">下一步：{status.nextStep}</p></div>
      <button type="button" onClick={() => go(status.nextActionTargetId)} className="w-full rounded-xl bg-cyan-700 px-5 py-3 text-sm font-bold text-white transition hover:bg-cyan-800 sm:w-auto">{status.nextActionLabel}</button>
    </div>
    <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-100"><div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all" style={{ width: `${status.overallProgress}%` }} /></div>
    <div className="mt-3 flex max-w-full gap-2 overflow-x-auto pb-1">{workflowTargets.map(([label,target]) => <button key={target} type="button" onClick={() => go(target)} className={`shrink-0 rounded-full border px-3 py-1.5 text-[10px] font-bold ${status.completedSteps.includes(label) ? "border-emerald-200 bg-emerald-50 text-emerald-800" : status.nextStep === label ? "border-cyan-300 bg-cyan-50 text-cyan-800" : "border-stone-200 bg-white text-slate-400"}`}>{status.completedSteps.includes(label) ? "✓ " : ""}{label}</button>)}</div>
    {status.missingItems.length > 0 && <p className="mt-3 text-[10px] leading-5 text-slate-500">尚待完成：{status.missingItems.join("、")}</p>}
  </section>;
}

const workflowTargets: [string, string][] = [
  ["找房雷達", "property-finder"], ["估價與趨勢", "valuation-calculator"], ["貸款與持有成本", "loan-calculator"],
  ["區位分析", "location-insight-calculator"], ["風險總評", "risk-summary"], ["看屋決策報告", "decision-report"], ["TaxOracle 稅務快篩", "taxoracle"],
];
