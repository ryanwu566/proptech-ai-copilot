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
import { CommandPaletteDialog } from "./command-palette-dialog";
import type { CommandPaletteRuntimeProps } from "./command-palette-launcher";

const OnboardingTour = dynamic(() => import("@/components/onboarding-tour").then((module) => module.OnboardingTour), { ssr: false });

/** Loaded only after explicit intent. Retains navigation/tour handoff after closing. */
export function CommandPaletteHost({ open, onClose, opener, trigger }: CommandPaletteRuntimeProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { copy } = useExperienceLocale();
  const [tour, setTour] = useState(false);
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
  }, [open, tour, pathname, trigger]);

  function navigate(href: string, address = false) {
    navigationFocus.current = { pathname: new URL(href, window.location.origin).pathname, address };
    router.push(href);
  }
  function select(command: CaseCommand) {
    onClose();
    if (command.action === "tour") setTour(true);
    else if (command.href) navigate(command.href, command.id === "new");
  }
  return <>
    {open && <CommandPaletteSession pathname={pathname} opener={opener} onClose={onClose} onSelect={select} />}
    {tour && <OnboardingTour opener={opener} onClose={() => setTour(false)} cta={{ label: copy("guide.ctaCreate"), onSelect: () => navigate("/#commercial-address", true) }} />}
  </>;
}

/** Mounted only while open: fresh diagnostic reads, event subscriptions, no polling. */
function CommandPaletteSession({ pathname, opener, onClose, onSelect }: {
  pathname: string; opener: HTMLElement | null; onClose: () => void; onSelect: (command: CaseCommand) => void;
}) {
  const caseId = caseIdFromPath(pathname);
  const { locale } = useExperienceLocale();
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const rooms = useMemo(() => createBrowserDecisionRoomRepository(), []);
  const [snapshot, setSnapshot] = useState<{ workspace: PropertyCaseWorkspace | null; room: RoomRead | null }>(() => {
    const workspace = caseId ? repository.getCase(caseId) : null;
    return { workspace, room: workspace ? rooms.read(workspace.caseId) : null };
  });

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

  return <CommandPaletteDialog commands={buildCaseCommands({ pathname, ...snapshot, locale })} opener={opener} onClose={onClose} onSelect={onSelect} />;
}
