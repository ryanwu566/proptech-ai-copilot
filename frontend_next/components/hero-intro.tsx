"use client";

import type { TranslationKey } from "@/lib/experience-i18n";
import type { WorkflowStatus } from "@/lib/workflow-status";
import { FriendlyIntroWalkthrough } from "@/components/friendly-intro-walkthrough";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const capabilities: TranslationKey[] = [
  "hero.capability.location",
  "hero.capability.valuation",
  "hero.capability.risk",
  "hero.capability.market",
  "hero.capability.decision",
];

const trustItems: TranslationKey[] = [
  "hero.trust.sources",
  "hero.trust.traceability",
  "hero.trust.multiSource",
  "hero.trust.privacy",
];

export function HeroIntro({ onStart, onWorkspace, reportReady = false, onReport, workflowStatus }: { onStart: () => void; onWorkspace: () => void; reportReady?: boolean; onReport: () => void; workflowStatus?: WorkflowStatus }) {
  const { t } = useExperienceLocale();
  const primaryLabel = workflowStatus?.completedSteps.length ? `${t("hero.continue")}: ${t("hero.primary")}` : t("hero.primary");
  return (
    <section id="hero" className="relative min-w-0 overflow-hidden rounded-3xl border border-cyan-200/70 bg-slate-950 px-4 py-8 text-white shadow-xl sm:px-7 sm:py-10 lg:px-10 lg:py-12">
      <div className="hero-grid pointer-events-none absolute inset-0 opacity-35" />
      <div className="hero-orb pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-cyan-400/25 blur-3xl motion-reduce:animate-none" />

      <div className="relative grid min-w-0 gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.95fr)] xl:items-center">
        {/* Left: Copy and CTAs */}
        <div className="min-w-0 hero-reveal motion-reduce:animate-none">
          {/* Brand kicker */}
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_4px_rgba(103,232,249,.65)]" />
            <p className="text-[10px] font-bold tracking-[0.22em] text-cyan-200">{t("hero.kicker")}</p>
          </div>

          {/* Headline */}
          <h1 className="mt-5 max-w-2xl text-3xl font-black leading-tight tracking-tight sm:text-4xl lg:text-[2.75rem] lg:leading-[1.15]">
            {t("hero.title")}
          </h1>

          {/* Subheadline */}
          <p className="mt-4 max-w-xl text-sm leading-7 text-slate-300 sm:text-base sm:leading-7">
            {t("hero.description")}
          </p>

          {/* Capability strip */}
          <div className="mt-5 flex flex-wrap gap-2" aria-label={t("hero.capabilityLabel")}>
            {capabilities.map((key) => (
              <span
                key={key}
                className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1.5 text-[10px] font-bold text-cyan-100"
              >
                {t(key)}
              </span>
            ))}
          </div>

          {/* CTAs */}
          <div className="mt-7 grid gap-3 sm:flex sm:flex-wrap">
            <button
              type="button"
              data-action-kind="primary"
              data-primary-action-id="property-finder"
              onClick={onStart}
              className="rounded-xl bg-cyan-400 px-6 py-3.5 text-sm font-extrabold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 motion-reduce:transition-none"
            >
              {primaryLabel}
            </button>
            <button
              type="button"
              data-action-kind="secondary"
              onClick={onWorkspace}
              className="rounded-xl border border-white/25 bg-white/10 px-6 py-3.5 text-sm font-bold text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white/40 motion-reduce:transition-none"
            >
              {t("hero.secondaryCta")}
            </button>
          </div>

          {/* Trust strip */}
          <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2">
            {trustItems.map((key) => (
              <span key={key} className="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
                <span className="h-1 w-1 rounded-full bg-cyan-400/60" />
                {t(key)}
              </span>
            ))}
          </div>
        </div>

        {/* Right: Walkthrough panel */}
        <FriendlyIntroWalkthrough />
      </div>

      {/* Disclaimer */}
      <p className="relative mt-8 border-t border-white/10 pt-5 text-[10px] leading-5 text-slate-400">
        {t("hero.disclaimer")}
      </p>
    </section>
  );
}
