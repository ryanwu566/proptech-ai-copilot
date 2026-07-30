"use client";

import type { ReactNode } from "react";
import { getExperienceStatePresentation, type ExperienceState } from "@/lib/experience-architecture";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function ExperienceStatePanel({ state, title, explanation, nextAction, sourceNote, onAction, children, className = "" }: { state: ExperienceState; title?: string; explanation?: string; nextAction?: string; sourceNote?: string; onAction?: () => void; children?: ReactNode; className?: string }) {
  const { t } = useExperienceLocale();
  const copy = getExperienceStatePresentation(state, t);
  const action = nextAction ?? copy.nextAction;
  const note = sourceNote ?? copy.sourceNote;
  return <section role="status" aria-live="polite" data-experience-state={state} className={`rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-amber-950 ${className}`}>
    <h3 className="text-sm font-black">{title ?? copy.heading}</h3>
    <p className="mt-1 text-xs leading-5">{explanation ?? copy.explanation}</p>
    {note ? <p className="mt-2 text-[11px] leading-5 text-amber-900">{note}</p> : null}
    {children}
    {action ? onAction ? <button type="button" onClick={onAction} className="mt-3 rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-bold text-amber-950 transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-600 focus:ring-offset-2">{action}</button> : <p className="mt-2 text-xs font-bold">{action}</p> : null}
  </section>;
}
