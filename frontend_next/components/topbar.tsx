"use client";
import { getPageLabelKey, type AppPage } from "@/components/sidebar";
import { CommercialGlobalHeader } from "@/components/commercial-global-header";
import { ViewModeToggle } from "@/components/view-mode-toggle";
import { ReadAloudControls } from "@/components/read-aloud-controls";
import { VoiceInputControls } from "@/components/voice-input-controls";
import { AssistiveNarrationControls } from "@/components/assistive-narration-controls";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createSafeSpeechSummary } from "@/lib/safe-speech";
import type { VoiceAction } from "@/lib/voice-input";
export function Topbar({ page, onNavigate, onTour, onVoiceAction }: { page: AppPage; onNavigate: (page: AppPage) => void; onTour: () => void; onVoiceAction?: (action: VoiceAction) => void }) {
  const { t, locale } = useExperienceLocale();
  const summary = createSafeSpeechSummary([t("app.currentView"), t(getPageLabelKey(page)), t("hero.limitation")], locale);
  return <CommercialGlobalHeader page={page} onNavigate={onNavigate}>
    <details className="ds-disclosure"><summary className="ds-disclosure__summary">{t("commercial.accessibility")}</summary>
      <div className="commercial-accessibility-controls"><AssistiveNarrationControls /><ReadAloudControls summary={summary} /><VoiceInputControls onAction={onVoiceAction} /><ViewModeToggle compact /><button type="button" className="ds-button ds-button--tertiary" onClick={onTour}>{t("app.tour")}</button></div>
    </details>
  </CommercialGlobalHeader>;
}
