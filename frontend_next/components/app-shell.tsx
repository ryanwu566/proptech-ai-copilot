"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import dynamic from "next/dynamic";
import { AppPage } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import type { VoiceAction } from "@/lib/voice-input";

const OnboardingTour = dynamic(() => import("@/components/onboarding-tour").then((module) => module.OnboardingTour), { ssr: false });
const GuidedCaseSimulation = dynamic(() => import("@/components/guided-case-simulation").then((module) => module.GuidedCaseSimulation), { ssr: false });
const GuidedExampleContext = createContext<((opener: HTMLElement) => void) | null>(null);
export function useStartGuidedExample() { return useContext(GuidedExampleContext); }

export function AppShell({ page, onNavigate, onVoiceAction, children }: { page: AppPage; onNavigate: (page: AppPage) => void; onVoiceAction?: (action: VoiceAction) => void; children: ReactNode }) {
  const [tourOpen, setTourOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const demoOpener = useRef<HTMLElement | null>(null);
  const previousPage = useRef(page);
  useEffect(() => {
    const changed = previousPage.current !== page;
    previousPage.current = page;
    const frame = window.requestAnimationFrame(() => {
      if (changed || document.activeElement === document.body) document.querySelector<HTMLElement>("[data-page-heading]")?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [page]);
  return <GuidedExampleContext.Provider value={(opener) => { demoOpener.current = opener; setTourOpen(false); setDemoOpen(true); }}><div className="min-h-screen bg-canvas"><Topbar page={page} onNavigate={onNavigate} onTour={() => setTourOpen(true)} onVoiceAction={onVoiceAction} /><main id="main-content" tabIndex={-1} className="commercial-app-content outline-none">{children}</main>{tourOpen && <OnboardingTour onClose={() => setTourOpen(false)} />}{demoOpen && <GuidedCaseSimulation opener={demoOpener.current} onClose={() => setDemoOpen(false)} />}</div></GuidedExampleContext.Provider>;
}
