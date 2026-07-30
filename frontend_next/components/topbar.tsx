"use client";

import type { AppPage } from "@/components/sidebar";
import { ViewModeToggle } from "@/components/view-mode-toggle";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ReadAloudControls } from "@/components/read-aloud-controls";
import { VoiceInputControls } from "@/components/voice-input-controls";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createSafeSpeechSummary } from "@/lib/safe-speech";
import type { VoiceAction } from "@/lib/voice-input";

export function Topbar({ page, onMenu, onTour, onVoiceAction }: { page: AppPage; onMenu: () => void; onTour: () => void; onVoiceAction?: (action: VoiceAction) => void }) {
  const { t, locale } = useExperienceLocale();
  const summary = createSafeSpeechSummary([t("app.currentView"), String(page), t("hero.limitation")], locale);
  return <header className="sticky top-0 z-10 flex min-h-12 flex-wrap items-center justify-between gap-2 border-b border-stone-200 bg-[#f7f5f0]/90 px-4 py-1 backdrop-blur sm:px-5 lg:px-7"><div className="flex min-w-0 items-center gap-3"><button onClick={onMenu} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-stone-200 bg-white text-sm text-slate-600 lg:hidden" aria-label={t("app.openMenu")}>☰</button><p className="truncate text-xs font-bold text-slate-600">{page}</p></div><div className="flex min-w-0 shrink-0 flex-wrap items-center justify-end gap-1.5 text-[9px] font-semibold text-slate-500 sm:gap-2 sm:text-[10px]"><LocaleSwitcher /><ReadAloudControls summary={summary} /><VoiceInputControls onAction={onVoiceAction} /><ViewModeToggle compact /><button onClick={onTour} className="hidden rounded-md border border-cyan-200 bg-cyan-50 px-2.5 py-1.5 font-bold text-cyan-800 sm:block">{t("app.tour")}</button></div></header>;
}
