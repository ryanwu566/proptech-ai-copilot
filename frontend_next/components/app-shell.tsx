"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AppPage, Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { hasSeenOnboarding, OnboardingTour } from "@/components/onboarding-tour";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { VoiceAction } from "@/lib/voice-input";

export function AppShell({ page, onNavigate, onTourAction, onVoiceAction, children }: { page: AppPage; onNavigate: (page: AppPage) => void; onTourAction: (action: "tax-low" | "map" | "explore") => void; onVoiceAction?: (action: VoiceAction) => void; children: ReactNode }) {
  const { t } = useExperienceLocale();
  const [menuOpen, setMenuOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  useEffect(() => { setTourOpen(!hasSeenOnboarding()); }, []);
  const navigate = (next: AppPage) => { onNavigate(next); setMenuOpen(false); };
  return <div className="min-h-screen overflow-x-hidden bg-canvas"><Sidebar page={page} onNavigate={navigate} open={menuOpen} onClose={() => setMenuOpen(false)} /><main className="min-w-0 lg:pl-48"><Topbar page={page} onMenu={() => setMenuOpen(true)} onTour={() => setTourOpen(true)} onVoiceAction={onVoiceAction} /><p role="note" className="border-b border-amber-100 bg-amber-50/70 px-4 py-2 text-[10px] leading-5 text-amber-900 sm:px-5 lg:px-7">{t("hero.limitation")}</p><div className="mx-auto max-w-[1440px] min-w-0 px-4 py-5 sm:px-5 lg:px-7 lg:py-6">{children}</div></main><OnboardingTour open={tourOpen} onClose={() => setTourOpen(false)} onAction={onTourAction} /></div>;
}
