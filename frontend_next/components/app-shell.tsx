"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AppPage } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { OnboardingTour } from "@/components/onboarding-tour";
import type { VoiceAction } from "@/lib/voice-input";

export function AppShell({ page, onNavigate, onTourAction, onVoiceAction, children }: { page: AppPage; onNavigate: (page: AppPage) => void; onTourAction: (action: "tax-low" | "map" | "explore") => void; onVoiceAction?: (action: VoiceAction) => void; children: ReactNode }) {
  const [tourOpen, setTourOpen] = useState(false);
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>("[data-page-heading]")?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [page]);
  return <div className="min-h-screen bg-canvas"><Topbar page={page} onNavigate={onNavigate} onTour={() => setTourOpen(true)} onVoiceAction={onVoiceAction} /><main id="main-content" tabIndex={-1} className="commercial-app-content outline-none">{children}</main><OnboardingTour open={tourOpen} onClose={() => setTourOpen(false)} onAction={onTourAction} /></div>;
}
