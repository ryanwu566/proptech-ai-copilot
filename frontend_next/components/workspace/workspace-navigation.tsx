"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { NavigationItem, WorkspaceNavigation as DesignSystemNavigation } from "@/components/design-system/navigation";
import { WORKSPACE_SECTIONS } from "@/lib/workspace/workspace-model";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { scenarioEntryCopy } from "@/lib/workspace/scenario-entry-copy";
import { workspaceNavigationCopy } from "@/lib/workspace/workspace-navigation-copy";
import { placesEntryCopy } from "@/lib/my-places-entry-copy";
import { documentEvidenceCopy } from "@/lib/workspace/document-evidence-copy";

// Primary: the seven-step case workflow. Secondary pages stay reachable but de-emphasized.
// The legacy planning route (/cases/:id/planning) remains for direct URLs only.
export function WorkspaceNavigation({ caseId }: { caseId: string }) {
  const pathname = usePathname();
  const { copyFrom } = useExperienceLocale();
  const base = `/cases/${encodeURIComponent(caseId)}`;
  return <DesignSystemNavigation label={copyFrom(workspaceNavigationCopy, "label")} className="workspace-navigation">
    <span className="workspace-navigation__label text-meta">{copyFrom(workspaceNavigationCopy, "primary")}</span>
    {WORKSPACE_SECTIONS.map((section) => <NavigationItem key={section} href={`${base}/${section}`} current={pathname === `${base}/${section}`}>{copyFrom(workspaceNavigationCopy, section)}</NavigationItem>)}
    <Link className="ds-navigation-item" href={`${base}/decision-room`} aria-current={pathname.endsWith("/decision-room") ? "page" : undefined}>{copyFrom(workspaceNavigationCopy, "decisionRoom")}</Link>
    <NavigationItem href={`${base}/report`} current={pathname.endsWith("/report")}>{copyFrom(workspaceNavigationCopy, "report")}</NavigationItem>
    <span className="workspace-navigation__label text-meta">{copyFrom(workspaceNavigationCopy, "secondary")}</span>
    <NavigationItem className="workspace-navigation__secondary" href={`${base}/scenarios`} current={pathname.endsWith("/scenarios")}>{copyFrom(scenarioEntryCopy, "nav")}</NavigationItem>
    <NavigationItem className="workspace-navigation__secondary" href={`${base}/commute-planner`} current={pathname.endsWith("/commute-planner")}>{copyFrom(placesEntryCopy, "planner")}</NavigationItem>
    <NavigationItem className="workspace-navigation__secondary" href={`${base}/evidence`} current={pathname.endsWith("/evidence")}>{copyFrom(documentEvidenceCopy, "nav")}</NavigationItem>
    <NavigationItem className="workspace-navigation__secondary" href={`/compare?cases=${encodeURIComponent(caseId)}`}>{copyFrom(workspaceNavigationCopy, "compare")}</NavigationItem>
  </DesignSystemNavigation>;
}
