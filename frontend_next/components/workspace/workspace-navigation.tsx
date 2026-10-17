"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { NavigationItem, WorkspaceNavigation as DesignSystemNavigation } from "@/components/design-system/navigation";
import { WORKSPACE_SECTIONS } from "@/lib/workspace/workspace-model";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { scenarioEntryCopy } from "@/lib/workspace/scenario-entry-copy";
import { workspaceNavigationCopy } from "@/lib/workspace/workspace-navigation-copy";
import { placesEntryCopy } from "@/lib/my-places-entry-copy";
import { navigationCopy } from "@/lib/navigation/copy";
import { documentEvidenceCopy } from "@/lib/workspace/document-evidence-copy";

export function WorkspaceNavigation({ caseId }: { caseId: string }) {
  const pathname = usePathname();
  const { copyFrom } = useExperienceLocale();
  return <DesignSystemNavigation label={copyFrom(workspaceNavigationCopy, "label")} className="workspace-navigation">
    <span className="workspace-navigation__label text-meta">{copyFrom(navigationCopy, "analysis")}</span>
    {WORKSPACE_SECTIONS.map((section) => {
      const href = `/cases/${encodeURIComponent(caseId)}/${section}`;
      return <NavigationItem key={section} href={href} current={pathname === href}>{copyFrom(workspaceNavigationCopy, section)}</NavigationItem>;
    })}
    <span className="workspace-navigation__label text-meta">{copyFrom(navigationCopy, "decisions")}</span>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/scenarios`} current={pathname.endsWith("/scenarios")}>{copyFrom(scenarioEntryCopy, "nav")}</NavigationItem>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/commute-planner`} current={pathname.endsWith("/commute-planner")}>{copyFrom(placesEntryCopy, "planner")}</NavigationItem>
    <Link className="ds-navigation-item" href={`/cases/${encodeURIComponent(caseId)}/decision-room`} aria-current={pathname.endsWith("/decision-room") ? "page" : undefined}>{copyFrom(workspaceNavigationCopy, "decisionRoom")}</Link>
    <span className="workspace-navigation__label text-meta">{copyFrom(workspaceNavigationCopy, "outputs")}</span>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/evidence`} current={pathname.endsWith("/evidence")}>{copyFrom(documentEvidenceCopy, "nav")}</NavigationItem>
    <NavigationItem href={`/compare?cases=${encodeURIComponent(caseId)}`}>{copyFrom(workspaceNavigationCopy, "compare")}</NavigationItem>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/report`} current={pathname.endsWith("/report")}>{copyFrom(workspaceNavigationCopy, "report")}</NavigationItem>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/planning`} current={pathname.endsWith("/planning")}>{copyFrom(workspaceNavigationCopy, "planning")}</NavigationItem>
  </DesignSystemNavigation>;
}
