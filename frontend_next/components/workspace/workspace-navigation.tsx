"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import type { ReactNode } from "react";
import { WorkspaceNavigation as DesignSystemNavigation } from "@/components/design-system/navigation";
import { WORKSPACE_SECTIONS } from "@/lib/workspace/workspace-model";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { scenarioEntryCopy } from "@/lib/workspace/scenario-entry-copy";
import { workspaceNavigationCopy } from "@/lib/workspace/workspace-navigation-copy";
import { placesEntryCopy } from "@/lib/my-places-entry-copy";
import { documentEvidenceCopy } from "@/lib/workspace/document-evidence-copy";
import { DetailsDisclosure } from "@/components/design-system/disclosure";

// Brief, evidence and outputs form the judge journey. Deeper tools remain discoverable on demand.
// The legacy planning route (/cases/:id/planning) remains for direct URLs only.
export function WorkspaceNavigation({ caseId }: { caseId: string }) {
  const pathname = usePathname();
  const { copyFrom } = useExperienceLocale();
  const base = `/cases/${encodeURIComponent(caseId)}`;
  const toolActive = ["decision-room", "scenarios", "commute-planner", "evidence"].some((section) => pathname === `${base}/${section}`);
  return <DesignSystemNavigation label={copyFrom(workspaceNavigationCopy, "label")} className="workspace-navigation">
    <CaseNavLink href={`${base}/overview`} current={pathname === `${base}/overview`}>{copyFrom(workspaceNavigationCopy, "overview")}</CaseNavLink>
    <span className="workspace-navigation__label text-meta">{copyFrom(workspaceNavigationCopy, "groupCase")}</span>
    {WORKSPACE_SECTIONS.filter((section) => section !== "overview").map((section) => <CaseNavLink key={section} href={`${base}/${section}`} current={pathname === `${base}/${section}`}>{copyFrom(workspaceNavigationCopy, section)}</CaseNavLink>)}
    <span className="workspace-navigation__label text-meta">{copyFrom(workspaceNavigationCopy, "groupDecide")}</span>
    <CaseNavLink href={`/compare?cases=${encodeURIComponent(caseId)}`}>{copyFrom(workspaceNavigationCopy, "compare")}</CaseNavLink>
    <CaseNavLink href={`${base}/report`} current={pathname.endsWith("/report")}>{copyFrom(workspaceNavigationCopy, "report")}</CaseNavLink>
    <DetailsDisclosure key={pathname} summary={copyFrom(workspaceNavigationCopy, "groupTools")} className="workspace-navigation__tools" data-testid="workspace-tools" open={toolActive}>
    <CaseNavLink className="workspace-navigation__secondary" href={`${base}/decision-room`} current={pathname.endsWith("/decision-room")}>{copyFrom(workspaceNavigationCopy, "decisionRoom")}</CaseNavLink>
    <CaseNavLink className="workspace-navigation__secondary" href={`${base}/scenarios`} current={pathname.endsWith("/scenarios")}>{copyFrom(scenarioEntryCopy, "nav")}</CaseNavLink>
    <CaseNavLink className="workspace-navigation__secondary" href={`${base}/commute-planner`} current={pathname.endsWith("/commute-planner")}>{copyFrom(placesEntryCopy, "planner")}</CaseNavLink>
    <CaseNavLink className="workspace-navigation__secondary" href={`${base}/evidence`} current={pathname.endsWith("/evidence")}>{copyFrom(documentEvidenceCopy, "nav")}</CaseNavLink>
    </DetailsDisclosure>
  </DesignSystemNavigation>;
}

/** Design-system navigation item as a client-side link: the case frame stays mounted, and prefetch stays off so hover or viewport never loads a route. */
function CaseNavLink({ href, current = false, className, children }: { href: string; current?: boolean; className?: string; children: ReactNode }) {
  return <Link href={href} prefetch={false} className={className ? `ds-navigation-item ${className}` : "ds-navigation-item"} aria-current={current ? "page" : undefined}><span>{children}</span></Link>;
}
