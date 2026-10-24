"use client";

import { useCallback, useEffect, useRef, useState, type ComponentType, type RefObject } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { commandPaletteTriggerCopy } from "@/lib/command-palette-trigger-copy";

export type CommandPaletteRuntimeProps = {
  open: boolean;
  onClose: () => void;
  opener: HTMLElement | null;
  trigger: RefObject<HTMLButtonElement | null>;
};

/** Global shell only. No palette runtime requests before a click or shortcut. */
export function CommandPaletteLauncher() {
  const { locale } = useExperienceLocale();
  const [Runtime, setRuntime] = useState<ComponentType<CommandPaletteRuntimeProps> | null>(null);
  const [open, setOpen] = useState(false);
  const [shortcut, setShortcut] = useState("Ctrl K");
  const trigger = useRef<HTMLButtonElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const runtimeRequested = useRef(false);
  const intent = useRef(false); // Native key events can precede React's commit.

  const close = useCallback(() => {
    intent.current = false;
    setOpen(false);
    if (!Runtime && opener.current?.isConnected) opener.current.focus({ preventScroll: true });
  }, [Runtime]);

  const show = useCallback(() => {
    if (document.querySelector("dialog[open], [role='dialog'][aria-modal='true']")) return;
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    intent.current = true;
    setOpen(true);
    if (Runtime || runtimeRequested.current) return;
    runtimeRequested.current = true;
    // Deliberately inside user intent: no dynamic component/preload boundary at entry.
    void import("./command-palette-host").then((module) => {
      // A different modal may have opened while its chunk was in flight.
      if (document.querySelector("dialog[open], [role='dialog'][aria-modal='true']")) { intent.current = false; setOpen(false); }
      setRuntime(() => module.CommandPaletteHost);
    }).catch(() => {
      runtimeRequested.current = false;
      intent.current = false;
      setOpen(false);
      if (opener.current?.isConnected) opener.current.focus({ preventScroll: true });
    });
  }, [Runtime]);

  useEffect(() => { setShortcut(/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘ K" : "Ctrl K"); }, []);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.isComposing && event.key.toLowerCase() === "k") {
        if (!intent.current && document.querySelector("dialog[open], [role='dialog'][aria-modal='true']")) return;
        event.preventDefault();
        if (intent.current) close(); else show();
      } else if (intent.current && !event.isComposing && event.key === "Escape") {
        event.preventDefault();
        close();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close, show]);

  return <>
    <button ref={trigger} type="button" className="case-command-trigger" data-testid="command-palette-trigger" aria-haspopup="dialog" aria-expanded={open}
      aria-busy={open && !Runtime} aria-keyshortcuts="Control+K Meta+K" onClick={show}>
      <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><circle cx="7" cy="7" r="4.75" /><path d="m10.5 10.5 3.25 3.25" /></svg>
      <span className="case-command-trigger__label">{commandPaletteTriggerCopy[locale]}</span><kbd aria-hidden="true">{shortcut}</kbd>
    </button>
    {Runtime && <Runtime open={open} onClose={close} opener={opener.current} trigger={trigger} />}
  </>;
}
