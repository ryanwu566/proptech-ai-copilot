"use client";

import type { WorkflowStatus } from "@/lib/workflow-status";
import { FriendlyIntroWalkthrough } from "@/components/friendly-intro-walkthrough";
import { HelpTooltip } from "@/components/help-tooltip";
import { HELP_CONTENT } from "@/lib/help-content";

const outcomeCards = [
  { title: "1. 輸入條件", detail: "預算、地點、坪數、建物型態" },
  { title: "2. 系統分析", detail: "合理價格、月付、持有成本、區位與風險" },
  { title: "3. 產出報告", detail: "紅黃綠燈號、補查清單、HTML 報告與案件比較" },
];

export function HeroIntro({ onStart, onWorkspace, reportReady = false, onReport, workflowStatus }: { onStart: () => void; onWorkspace: () => void; reportReady?: boolean; onReport: () => void; workflowStatus?: WorkflowStatus }) {
  return <section id="hero" className="relative min-w-0 overflow-hidden rounded-3xl border border-cyan-200/70 bg-slate-950 px-4 py-6 text-white shadow-xl sm:px-7 sm:py-8 lg:px-10 lg:py-10">
    <div className="hero-grid pointer-events-none absolute inset-0 opacity-35" />
    <div className="hero-orb pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-cyan-400/25 blur-3xl motion-reduce:animate-none" />
    <div className="relative grid min-w-0 gap-7 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.95fr)] xl:items-center">
      <div className="min-w-0 hero-reveal motion-reduce:animate-none">
        <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_4px_rgba(103,232,249,.65)]" /><p className="text-[10px] font-bold tracking-[0.22em] text-cyan-200">買房前的看屋初篩助手</p></div>
        <h1 className="mt-4 max-w-3xl text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">不知道這間房值不值得看？先跑一份看屋決策報告。</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">輸入預算、地點或路段，系統會整理實價登錄、合理價格、貸款、持有成本、區位與風險燈號，幫你判斷要不要進一步看屋。</p>
        <div className="mt-3 flex max-w-3xl items-start gap-2 rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs leading-6 text-cyan-50"><span>最後你會拿到：合理價格、月付壓力、區位優缺點、紅黃綠風險燈號，以及可分享的 HTML 報告。</span><HelpTooltip title={HELP_CONTENT.decisionReport.title}>{HELP_CONTENT.decisionReport.body}</HelpTooltip></div>
        <div className="mt-6 grid gap-2 sm:flex sm:flex-wrap">
          <button type="button" onClick={onStart} className="rounded-xl bg-cyan-400 px-5 py-3 text-sm font-extrabold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 motion-reduce:transition-none">{workflowStatus?.completedSteps.length ? `繼續完成：${workflowStatus.nextActionLabel}` : "開始做看屋初篩"}</button>
          <button type="button" onClick={onWorkspace} className="rounded-xl border border-white/25 bg-white/10 px-5 py-3 text-sm font-bold text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white/40 motion-reduce:transition-none">查看目前分析進度</button>
          <button type="button" disabled={!reportReady} onClick={onReport} title={reportReady ? "查看看屋報告" : "完成估價後即可查看報告"} className="rounded-xl border border-white/15 px-5 py-3 text-sm font-bold text-slate-300 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-45 motion-reduce:transition-none">查看看屋報告</button>
        </div>
      </div>
      <FriendlyIntroWalkthrough />
    </div>
    <div className="relative mt-7 grid gap-2 border-t border-white/10 pt-5 sm:grid-cols-3">
      {outcomeCards.map((card) => <div key={card.title} className="rounded-xl bg-white/[0.06] px-3 py-3"><p className="text-xs font-extrabold text-cyan-100">{card.title}</p><p className="mt-1 text-[10px] leading-5 text-slate-300">{card.detail}</p></div>)}
    </div>
  </section>;
}
