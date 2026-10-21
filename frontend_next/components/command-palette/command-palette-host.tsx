"use client";

import dynamic from "next/dynamic";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { CASE_CLEARED_EVENT } from "@/lib/case-storage";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { createBrowserDecisionRoomRepository, type RoomRead } from "@/lib/decision-room-store";
import { caseIdFromPath } from "@/lib/navigation/model";
import { buildCaseCommands, type CaseCommand } from "@/lib/command-palette";
import { commandPaletteCopy } from "@/lib/command-palette-copy";
import { CommandPaletteDialog } from "./command-palette-dialog";
import styles from "./command-palette.module.css";

const OnboardingTour = dynamic(() => import("@/components/onboarding-tour").then((module) => module.OnboardingTour), { ssr: false });

/** Root-layout host: local diagnostic reads and subscriptions only; never starts evidence work. */
export function CommandPaletteHost() {
  const pathname = usePathname();
  const router = useRouter();
  const caseId = caseIdFromPath(pathname);
  const { locale, copyFrom, copy } = useExperienceLocale();
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const rooms = useMemo(() => createBrowserDecisionRoomRepository(), []);
  const [snapshot, setSnapshot] = useState<{ workspace: PropertyCaseWorkspace | null; room: RoomRead | null }>({ workspace: null, room: null });
  const [open, setOpen] = useState(false);
  const [tour, setTour] = useState(false);
  const [shortcut, setShortcut] = useState("Ctrl K");
  const opener = useRef<HTMLElement | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const navigationFocus = useRef<{ pathname: string; address: boolean } | null>(null);

  useEffect(() => {
    const intent = navigationFocus.current;
    if (open || tour || !intent || intent.pathname !== pathname) return;
    const frame = requestAnimationFrame(() => {
      if (intent.address) document.getElementById("commercial-address")?.focus({ preventScroll: true });
      else if (document.activeElement === document.body) trigger.current?.focus({ preventScroll: true });
      navigationFocus.current = null;
    });
    return () => cancelAnimationFrame(frame);
  }, [open, tour, pathname]);

  useEffect(() => {
    const refresh = () => {
      const workspace = caseId ? repository.getCase(caseId) : null;
      setSnapshot({ workspace, room: workspace ? rooms.read(workspace.caseId) : null });
    };
    refresh();
    const unsubscribe = repository.subscribe(refresh);
    const unsubscribeRoom = caseId ? rooms.subscribe(caseId, refresh) : () => {};
    window.addEventListener(CASE_CLEARED_EVENT, refresh);
    return () => { unsubscribe(); unsubscribeRoom(); window.removeEventListener(CASE_CLEARED_EVENT, refresh); };
  }, [caseId, repository, rooms]);
  useEffect(() => { setShortcut(/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘ K" : "Ctrl K"); }, []);

  function show() {
    if (document.querySelector("dialog[open], [role='dialog'][aria-modal='true']")) return;
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setOpen(true);
  }
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.isComposing && event.key.toLowerCase() === "k") {
        if (!open && document.querySelector("dialog[open], [role='dialog'][aria-modal='true']")) return;
        event.preventDefault();
        if (open) setOpen(false); else show();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const commands = buildCaseCommands({ pathname, ...snapshot, locale });
  function navigate(href: string, address = false) {
    navigationFocus.current = { pathname: new URL(href, window.location.origin).pathname, address };
    router.push(href);
  }
  function select(command: CaseCommand) {
    setOpen(false);
    if (command.action === "tour") setTour(true);
    else if (command.href) navigate(command.href, command.id === "new");
  }
  return <>
    <button ref={trigger} type="button" className={styles.trigger} data-testid="command-palette-trigger" aria-haspopup="dialog" aria-expanded={open}
      aria-keyshortcuts="Control+K Meta+K" onClick={show}>
      <span>{copyFrom(commandPaletteCopy, "trigger")}</span><kbd aria-hidden="true">{shortcut}</kbd>
    </button>
    {open && <CommandPaletteDialog commands={commands} onClose={() => setOpen(false)} onSelect={select} />}
    {tour && <OnboardingTour opener={opener.current} onClose={() => setTour(false)} cta={{ label: copy("guide.ctaCreate"), onSelect: () => navigate("/#commercial-address", true) }} />}
  </>;
}
