"use client";

import { useCallback, useEffect, useRef, useState, type ComponentType } from "react";
import { usePathname } from "next/navigation";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { helpTopicForPath, type HelpTopic } from "@/lib/help/page-help";
import { pageHelpTriggerCopy } from "@/lib/help/page-help-trigger-copy";

export type PageHelpSheetProps = { topic: HelpTopic; pathname: string; opener: HTMLElement | null; onClose: () => void };

const modalOpen = () => document.querySelector("dialog[open], [role='dialog'][aria-modal='true']") !== null;
const editable = (target: EventTarget | null) => target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));

/**
 * Global "?" entry for the contextual page guide. It shows only on pages that have a guide, reads nothing but the
 * pathname, and loads the guide (copy and sheet) only after a click or the "?" key, so routes ship no help payload.
 */
export function PageHelpLauncher() {
  const pathname = usePathname();
  const topic = helpTopicForPath(pathname);
  const { locale } = useExperienceLocale();
  const [Sheet, setSheet] = useState<ComponentType<PageHelpSheetProps> | null>(null);
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const requested = useRef(false);

  const close = useCallback(() => setOpen(false), []);
  const show = useCallback(() => {
    if (modalOpen()) return;
    opener.current = document.activeElement instanceof HTMLElement && document.activeElement !== document.body ? document.activeElement : trigger.current;
    setOpen(true);
    if (requested.current) return;
    requested.current = true;
    void import("./page-help-sheet").then((module) => {
      // Another dialog may have opened while the chunk was in flight.
      if (modalOpen()) setOpen(false);
      setSheet(() => module.PageHelpSheet);
    }).catch(() => {
      requested.current = false;
      setOpen(false);
    });
  }, []);

  // A route change closes the guide: it describes the page it was opened on.
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!topic) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "?" || event.ctrlKey || event.metaKey || event.altKey || event.isComposing || event.defaultPrevented || editable(event.target)) return;
      event.preventDefault();
      show();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [topic, show]);

  if (!topic) return null;
  const label = pageHelpTriggerCopy[locale];
  return <>
    <button ref={trigger} type="button" className="page-help-trigger" data-testid="page-help-trigger" data-help-topic={topic}
      aria-label={label} title={label} aria-haspopup="dialog" aria-expanded={open} aria-busy={open && !Sheet || undefined} aria-keyshortcuts="Shift+?" onClick={show}>
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="9" r="7.25" /><path d="M6.9 6.9a2.15 2.15 0 1 1 3 1.98c-.55.24-.9.78-.9 1.38v.34" /><circle cx="9" cy="12.9" r=".35" fill="currentColor" /></svg>
    </button>
    {open && Sheet && <Sheet topic={topic} pathname={pathname} opener={opener.current} onClose={close} />}
  </>;
}
