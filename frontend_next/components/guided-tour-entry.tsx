"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const OnboardingTour = dynamic(() => import("@/components/onboarding-tour").then((module) => module.OnboardingTour), { ssr: false });
const GuidedCaseSimulation = dynamic(() => import("@/components/guided-case-simulation").then((module) => module.GuidedCaseSimulation), { ssr: false });

/**
 * Visible "Start tour" entry. It never opens by itself and never requests data.
 * `create` ends on Home's address field; `demo` ends in the zero-provider example case.
 */
export function GuidedTourEntry({ cta, className = "commercial-text-action" }: { cta: "create" | "demo"; className?: string }) {
  const { copy } = useExperienceLocale();
  const [open, setOpen] = useState<"tour" | "demo" | null>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const focusAfterClose = useRef(false);
  // Runs after the modal's own cleanup has returned focus to the opener.
  useEffect(() => {
    if (open !== null || !focusAfterClose.current) return;
    focusAfterClose.current = false;
    document.getElementById("commercial-address")?.focus();
  }, [open]);
  return <>
    <button ref={opener} type="button" data-testid="tour-start" className={className} onClick={() => setOpen("tour")}>{copy("guide.start")}</button>
    {open === "tour" && <OnboardingTour opener={opener.current} onClose={() => setOpen(null)} cta={cta === "create"
      ? { label: copy("guide.ctaCreate"), onSelect: () => { focusAfterClose.current = true; } }
      : { label: copy("guide.ctaDemo"), onSelect: () => setOpen("demo") }} />}
    {open === "demo" && <GuidedCaseSimulation opener={opener.current} onClose={() => setOpen(null)} />}
  </>;
}
