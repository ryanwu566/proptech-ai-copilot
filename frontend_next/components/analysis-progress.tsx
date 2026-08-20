"use client";

export type AnalysisProgressPhase = "idle" | "accepted" | "dispatched" | "waiting" | "received" | "rendering" | "complete";

const PHASE_VALUE: Record<AnalysisProgressPhase, number> = {
  idle: 0,
  accepted: 8,
  dispatched: 18,
  waiting: 45,
  received: 90,
  rendering: 97,
  complete: 100,
};

export type AnalysisProgressLabels = {
  title: string;
  accepted: string;
  dispatched: string;
  waiting: string;
  received: string;
  rendering: string;
  complete: string;
};

export function AnalysisProgress({ phase, labels, testId }: { phase: AnalysisProgressPhase; labels: AnalysisProgressLabels; testId: string }) {
  if (phase === "idle") return null;
  const value = PHASE_VALUE[phase];
  const status = labels[phase];
  return <div data-testid={testId} data-progress-phase={phase} className="min-w-0 rounded-xl border border-cyan-200 bg-gradient-to-r from-slate-950 via-cyan-950 to-slate-950 p-3 text-white shadow-lg shadow-cyan-950/10">
    <div className="flex min-w-0 items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-200">{labels.title}</p>
        <p className="mt-1 truncate text-xs font-semibold text-white" aria-live="polite">{status}</p>
      </div>
      <span className="shrink-0 font-mono text-sm font-black text-cyan-100">{value}%</span>
    </div>
    <div
      role="progressbar"
      aria-label={labels.title}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      aria-valuetext={status}
      className="mt-3 h-2 overflow-hidden rounded-full bg-white/15"
    >
      <div className="relative h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-300 transition-[width] duration-200 motion-reduce:transition-none" style={{ width: `${value}%` }}>
        {phase !== "complete" && <span aria-hidden="true" className="absolute inset-y-0 right-0 w-8 animate-pulse bg-white/30 motion-reduce:animate-none" />}
      </div>
    </div>
  </div>;
}
