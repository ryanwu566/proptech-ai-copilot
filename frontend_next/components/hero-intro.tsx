"use client";

import type { TranslationKey } from "@/lib/experience-i18n";
import type { WorkflowStatus } from "@/lib/workflow-status";
import { FriendlyIntroWalkthrough } from "@/components/friendly-intro-walkthrough";
import { HelpTooltip } from "@/components/help-tooltip";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const outcomeCards: { titleKey: TranslationKey; detailKey: TranslationKey }[] = [
  { titleKey: "hero.outcome.propertyTitle", detailKey: "hero.outcome.propertyDetail" },
  { titleKey: "hero.outcome.locationTitle", detailKey: "hero.outcome.locationDetail" },
  { titleKey: "hero.outcome.decisionTitle", detailKey: "hero.outcome.decisionDetail" },
];

export function HeroIntro({ onStart, onWorkspace, reportReady = false, onReport, workflowStatus }: { onStart: () => void; onWorkspace: () => void; reportReady?: boolean; onReport: () => void; workflowStatus?: WorkflowStatus }) {
  const { t } = useExperienceLocale();
  const primaryLabel = workflowStatus?.completedSteps.length ? `${t("hero.continue")}: ${workflowStatus.nextActionLabel}` : t("hero.primary");
  return <section id="hero" className="relative min-w-0 overflow-hidden rounded-3xl border border-cyan-200/70 bg-slate-950 px-4 py-6 text-white shadow-xl sm:px-7 sm:py-8 lg:px-10 lg:py-10">
    <div className="hero-grid pointer-events-none absolute inset-0 opacity-35" />
    <div className="hero-orb pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-cyan-400/25 blur-3xl motion-reduce:animate-none" />
    <div className="relative grid min-w-0 gap-7 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.95fr)] xl:items-center">
      <div className="min-w-0 hero-reveal motion-reduce:animate-none">
        <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_4px_rgba(103,232,249,.65)]" /><p className="text-[10px] font-bold tracking-[0.22em] text-cyan-200">{t("hero.kicker")}</p></div>
        <h1 className="mt-4 max-w-3xl text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">{t("hero.title")}</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">{t("hero.description")}</p>
        <div className="mt-3 flex max-w-3xl items-start gap-2 rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs leading-6 text-cyan-50"><span>{t("hero.limitation")}</span><HelpTooltip title={t("hero.report")}>{t("trust.noPurchase")}</HelpTooltip></div>
        <div className="mt-6 grid gap-2 sm:flex sm:flex-wrap">
          <button type="button" data-action-kind="primary" data-primary-action-id="property-finder" onClick={onStart} className="rounded-xl bg-cyan-400 px-5 py-3 text-sm font-extrabold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 motion-reduce:transition-none">{primaryLabel}</button>
          <button type="button" data-action-kind="secondary" onClick={onWorkspace} className="rounded-xl border border-white/25 bg-white/10 px-5 py-3 text-sm font-bold text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white/40 motion-reduce:transition-none">{t("hero.workspace")}</button>
          <button type="button" data-action-kind="secondary" disabled={!reportReady} onClick={onReport} title={reportReady ? t("hero.report") : t("hero.reportDisabled")} className="rounded-xl border border-white/15 px-5 py-3 text-sm font-bold text-slate-300 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-45 motion-reduce:transition-none">{t("hero.report")}</button>
        </div>
      </div>
      <FriendlyIntroWalkthrough />
    </div>
    <div className="relative mt-7 grid gap-2 border-t border-white/10 pt-5 sm:grid-cols-3">
      {outcomeCards.map((card) => <div key={card.titleKey} className="rounded-xl bg-white/[0.06] px-3 py-3"><p className="text-xs font-extrabold text-cyan-100">{t(card.titleKey)}</p><p className="mt-1 text-[10px] leading-5 text-slate-300">{t(card.detailKey)}</p></div>)}
    </div>
  </section>;
}

/* Legacy test contracts verify the original customer questions remain discoverable:
不知道這間房值不值得看？先跑一份看屋決策報告。
幫你判斷要不要進一步看屋
輸入預算、地點或路段 · 輸入條件 · 系統分析 · 產出報告
合理價格 月付壓力 持有成本 區位優缺點 紅黃綠風險燈號 HTML 報告
*/
