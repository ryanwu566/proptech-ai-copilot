"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import dynamic from "next/dynamic";
import { AppPage } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import type { VoiceAction } from "@/lib/voice-input";

const OnboardingTour = dynamic(() => import("@/components/onboarding-tour").then((module) => module.OnboardingTour), { ssr: false });

export function AppShell({ page, onNavigate, onVoiceAction, children }: { page: AppPage; onNavigate: (page: AppPage) => void; onVoiceAction?: (action: VoiceAction) => void; children: ReactNode }) {
  const [tourOpen, setTourOpen] = useState(false);
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>("[data-page-heading]")?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [page]);
  return <div className="min-h-screen bg-canvas"><Topbar page={page} onNavigate={onNavigate} onTour={() => setTourOpen(true)} onVoiceAction={onVoiceAction} /><main id="main-content" tabIndex={-1} className="commercial-app-content outline-none">{children}</main>{tourOpen && <OnboardingTour onClose={() => setTourOpen(false)} />}</div>;
}
