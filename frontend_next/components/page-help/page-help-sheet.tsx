"use client";

import Link from "next/link";
import { useEffect, useId, useRef } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { helpNextSteps } from "@/lib/help/page-help";
import { pageGuides, pageHelpChrome, pageHelpNextLabels } from "@/lib/help/page-help-copy";
import type { PageHelpSheetProps } from "./page-help-launcher";
import styles from "./page-help.module.css";

/**
 * The page guide: a modal side sheet on wide screens and a bottom sheet on phones. Native <dialog> keeps the page
 * inert behind it and closes on Escape; focus starts on the title and returns to whatever opened the guide.
 */
export function PageHelpSheet({ topic, pathname, opener, onClose }: PageHelpSheetProps) {
  const { locale } = useExperienceLocale();
  const guide = pageGuides[locale][topic];
  const chrome = pageHelpChrome[locale];
  const labels = pageHelpNextLabels[locale];
  const next = helpNextSteps(topic, pathname);
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  // A "focus" next step hands focus to a page control instead of back to the opener.
  const focusAfterClose = useRef<string | null>(null);
  const id = useId();

  useEffect(() => {
    const element = dialog.current;
    const overflow = document.body.style.overflow;
    element?.showModal();
    document.body.style.overflow = "hidden";
    title.current?.focus({ preventScroll: true });
    return () => {
      element?.close();
      document.body.style.overflow = overflow;
      const target = focusAfterClose.current ? document.querySelector<HTMLElement>(focusAfterClose.current) : null;
      if (target) { target.scrollIntoView({ block: "center" }); target.focus({ preventScroll: true }); }
      else if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, [opener]);

  return <dialog ref={dialog} className={styles.sheet} data-testid="page-help" data-help-topic={topic}
    aria-modal="true" aria-labelledby={`${id}-title`} aria-describedby={`${id}-role`}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => {
      if (event.target !== event.currentTarget) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
    }}
    onKeyDown={(event) => {
      // Keep Tab inside the sheet: wrap between its first and last control (the title counts as the start).
      if (event.key !== "Tab") return;
      const controls = [...event.currentTarget.querySelectorAll<HTMLElement>("a[href], button:not(:disabled)")];
      const first = controls[0];
      const last = controls[controls.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === title.current)) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && active === last) { event.preventDefault(); first?.focus(); }
    }}>
    <header className={styles.head}>
      <div>
        <p className={styles.eyebrow}>{chrome.eyebrow}</p>
        <h2 ref={title} id={`${id}-title`} tabIndex={-1}>{guide.title}</h2>
      </div>
      <button type="button" className={styles.close} data-testid="page-help-close" aria-label={chrome.close} onClick={onClose}>
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><path d="m4 4 8 8M12 4l-8 8" /></svg>
      </button>
    </header>
    <div className={styles.body}>
      <section className={styles.block} aria-labelledby={`${id}-role-heading`}>
        <h3 id={`${id}-role-heading`}>{chrome.role}</h3>
        <p id={`${id}-role`} className={styles.lead}>{guide.role}</p>
      </section>
      <section className={styles.block} aria-labelledby={`${id}-see`}>
        <h3 id={`${id}-see`}>{chrome.see}</h3>
        <ol className={styles.see}>{guide.see.map((item) => <li key={item}>{item}</li>)}</ol>
      </section>
      <section className={styles.block} aria-labelledby={`${id}-read`}>
        <h3 id={`${id}-read`}>{chrome.read}</h3>
        <dl className={styles.legend}>
          {(["known", "unknown", "caution"] as const).map((state) => <div key={state} data-state={state}>
            <dt><span className={styles.marker} aria-hidden="true" />{chrome[state]}</dt>
            <dd>{guide[state]}</dd>
          </div>)}
        </dl>
      </section>
      <section className={styles.block} aria-labelledby={`${id}-next`}>
        <h3 id={`${id}-next`}>{chrome.next}</h3>
        <p>{guide.next}</p>
        {next.length > 0 && <div className={styles.actions}>
          {next.map((step, index) => step.kind === "route"
            ? <Link key={step.href} prefetch={false} href={step.href} className={`ds-button ds-button--compact ${index === 0 ? "ds-button--secondary" : "ds-button--tertiary"}`} data-testid="page-help-next" onClick={onClose}>{labels[step.label]}<span aria-hidden="true">→</span></Link>
            : <button key={step.selector} type="button" className="ds-button ds-button--compact ds-button--secondary" data-testid="page-help-next" onClick={() => { focusAfterClose.current = step.selector; onClose(); }}>{labels[step.label]}</button>)}
        </div>}
      </section>
    </div>
    <footer className={styles.foot}><p>{chrome.footnote}</p></footer>
  </dialog>;
}
