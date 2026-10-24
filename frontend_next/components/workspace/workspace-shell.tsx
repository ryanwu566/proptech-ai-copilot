"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useWorkspace } from "./workspace-provider";
import { WorkspaceNavigation } from "./workspace-navigation";
import styles from "./workspace-shell.module.css";
import { CaseWorkflowHandoff } from "@/components/navigation/case-workflow-handoff";
import { CopilotEntry } from "./copilot/copilot-entry";
import { DemoCaseNotice } from "./demo-case-notice";

// Last case path that finished rendering; null until the first case page has mounted in this document.
let settledPath: string | null = null;

/** Content enters with a short reveal only on in-app navigation; first load renders still. */
function RouteEnter({ path, children }: { path: string; children: ReactNode }) {
  const [animate] = useState(() => settledPath !== null && settledPath !== path);
  useEffect(() => { settledPath = path; }, [path]);
  return <div className={animate ? `${styles.page} ${styles.enter}` : styles.page} data-case-route-content>{children}</div>;
}

/**
 * One frame for every case route: case bar, then a rail (sections and pulse) beside the content column.
 * Snapshot-writing and standalone routes supply their own case bar and content; the geometry never changes.
 * On phones the rail becomes a section strip above the content and the pulse follows the content.
 */
export function CaseFrame({ caseId, header, pulse, children }: { caseId: string; header: ReactNode; pulse: ReactNode; children: ReactNode }) {
  const pathname = usePathname();
  const rail = useRef<HTMLDivElement>(null);
  const pulseSlot = useRef<HTMLDivElement>(null);
  // On narrow screens the rail is a horizontal strip; keep the current section in view.
  useEffect(() => {
    const strip = rail.current;
    if (!strip) return;
    const keepCurrentVisible = () => {
      const current = strip.querySelector<HTMLElement>("[aria-current='page']");
      if (!current || strip.scrollWidth <= strip.clientWidth) return;
      strip.scrollLeft = current.offsetLeft - (strip.clientWidth - current.offsetWidth) / 2;
    };
    keepCurrentVisible();
    const observer = new ResizeObserver(keepCurrentVisible);
    observer.observe(strip);
    if (strip.firstElementChild) observer.observe(strip.firstElementChild);
    return () => observer.disconnect();
  }, [pathname]);
  // Mirror each pulse state onto the matching section link as a dot. Presentation only: the pulse stays the source.
  useEffect(() => {
    const strip = rail.current;
    const slot = pulseSlot.current;
    if (!strip) return;
    const sync = () => {
      const states = new Map<string, string>();
      slot?.querySelectorAll<HTMLAnchorElement>("[data-pulse-state]").forEach((link) => states.set(link.getAttribute("href") ?? "", link.dataset.pulseState ?? ""));
      strip.querySelectorAll<HTMLAnchorElement>("a.ds-navigation-item").forEach((link) => {
        const state = states.get(link.getAttribute("href") ?? "");
        if (state) link.dataset.pulseState = state; else delete link.dataset.pulseState;
      });
    };
    sync();
    if (!slot) return;
    const observer = new MutationObserver(sync);
    observer.observe(slot, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-pulse-state", "href"] });
    return () => observer.disconnect();
  }, [caseId]);
  return <div className={styles.shell} data-case-frame>
    {header}
    <div className={styles.body}>
      <div className={styles.side}>
        <div ref={rail} className={styles.rail} data-case-rail><WorkspaceNavigation caseId={caseId} /></div>
        <div ref={pulseSlot} className={styles.pulse}>{pulse}</div>
      </div>
      <div className={styles.content} data-case-content>
        <div className={styles.demoNotice}><DemoCaseNotice key={caseId} caseIds={[caseId]} /></div>
        <RouteEnter key={pathname} path={pathname}>{children}</RouteEnter>
      </div>
    </div>
  </div>;
}

export function WorkspaceContent({ children }: { children: ReactNode }) {
  const workspace = useWorkspace();
  // The assistant entry follows the route content so each section opens on its own title.
  return <main className={styles.main} id="main-content" tabIndex={-1}>{children}<CopilotEntry /><CaseWorkflowHandoff caseId={workspace.caseId} /></main>;
}
