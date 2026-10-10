"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { TOUR_STEPS, writeTourStatus, type TourStatus, type TourStepId } from "@/lib/guided-tour";

// Mount only when requested. A new mount intentionally restarts the guide.
export type TourPresentation = {
  title: string; disclosure: string; exit: string; restart: string; completed: string;
  heading?: (id: TourStepId) => string;
  description: (id: TourStepId) => string;
  renderStage: (id: TourStepId) => ReactNode;
  onRestart: () => void;
};
export function OnboardingTour({ onClose, presentation, opener }: { onClose: () => void; presentation?: TourPresentation; opener?: HTMLElement | null }) {
  const { copy } = useExperienceLocale();
  const [stepId, setStepId] = useState<TourStepId>("propertyCase");
  const [run, setRun] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const returnFocus = useRef(opener);
  const step = TOUR_STEPS.findIndex((item) => item.id === stepId);
  const current = TOUR_STEPS[step];
  const progress = copy("guide.progress", { current: step + 1, total: TOUR_STEPS.length });

  useEffect(() => {
    const element = dialog.current;
    const restore = returnFocus.current ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    const previousOverflow = document.body.style.overflow;
    element?.showModal();
    document.body.style.overflow = "hidden";
    heading.current?.focus({ preventScroll: true });
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
      if (restore?.isConnected) restore.focus({ preventScroll: true });
    };
  }, []);

  // Locale changes update copy without moving focus, resetting the step or replaying motion.
  useEffect(() => {
    if (body.current) body.current.scrollTop = 0;
    heading.current?.focus({ preventScroll: true });
  }, [stepId, run]);

  function close(status: TourStatus) {
    try { writeTourStatus(window.localStorage, status); }
    catch { /* Access to localStorage itself can be denied by the browser. */ }
    onClose();
  }

  return <dialog ref={dialog} className={`onboarding-dialog${presentation ? " simulation-dialog" : ""}`} data-step-id={stepId} data-demo={presentation ? "true" : undefined}
    aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-context"
    onKeyDown={(event) => {
      if (event.key !== "Tab") return;
      const controls = event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), select, input:not(:disabled)');
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && (document.activeElement === first || document.activeElement === heading.current)) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }}
    onCancel={(event) => { event.preventDefault(); if (presentation) onClose(); else close("skipped"); }}>
    <div className="onboarding-card">
      <header className="onboarding-header">
        <p id="tour-title" className="onboarding-title">{presentation?.title ?? copy("guide.title")}</p>
        <LocaleSwitcher />
      </header>
      <div className="onboarding-progress" aria-hidden="true"><span style={{ width: `${((step + 1) / TOUR_STEPS.length) * 100}%` }} /></div>
      <div ref={body} className="onboarding-body">
        <ol className="onboarding-path" aria-label={copy("guide.path")}>
          {TOUR_STEPS.map((item, index) => <li key={item.id} aria-current={item.id === stepId ? "step" : undefined} data-explored={index < step || undefined}>
            <span aria-hidden="true">{index + 1}</span>{copy(item.label)}
            {presentation && index < step && <span className="sr-only">{presentation.completed}</span>}
          </li>)}
        </ol>
        <section className="onboarding-context">
          <p id="tour-progress" className="onboarding-step-count" role="status" aria-live="polite" aria-atomic="true">{progress}</p>
          <div key={`${stepId}:${run}`} className="onboarding-step">
            <h2 ref={heading} tabIndex={-1} aria-describedby="tour-progress tour-description">{presentation?.heading?.(stepId) ?? copy(current.heading)}</h2>
            <p id="tour-description" className="onboarding-description">{presentation?.description(stepId) ?? copy(current.description)}</p>
            {presentation?.renderStage(stepId)}
          </div>
          {!presentation && <><p id="tour-context" data-testid="tour-context-note" className="onboarding-context-note">{copy("guide.context")}</p>
          <p className="onboarding-boundary">{copy("guide.boundary")}</p></>}
        </section>
      </div>
      {presentation && <p id="tour-context" data-testid="demo-disclosure" className="simulation-disclosure" role="note">{presentation.disclosure}</p>}
      <footer className="onboarding-footer">
        <button type="button" data-testid="tour-skip" className="ds-button ds-button--tertiary" onClick={() => close("skipped")}>{copy("guide.skip")}</button>
        {presentation && <><button type="button" data-testid="demo-exit" className="ds-button ds-button--tertiary" onClick={onClose}>{presentation.exit}</button>
          <button type="button" data-testid="demo-restart" className="ds-button ds-button--tertiary" onClick={() => { presentation.onRestart(); setStepId("propertyCase"); setRun((value) => value + 1); }}>{presentation.restart}</button></>}
        <div className="onboarding-actions">
          <button type="button" data-testid="tour-back" className="ds-button ds-button--secondary" disabled={step === 0} onClick={() => setStepId(TOUR_STEPS[step - 1].id)}>{copy("guide.back")}</button>
          <button type="button" data-testid="tour-next" className="ds-button ds-button--primary" onClick={() => {
            if (step === TOUR_STEPS.length - 1) close("completed");
            else setStepId(TOUR_STEPS[step + 1].id);
          }}>{copy(step === TOUR_STEPS.length - 1 ? "guide.finish" : "guide.next")}</button>
        </div>
      </footer>
    </div>
  </dialog>;
}
