"use client";

import { usePathname } from "next/navigation";
import { NavigationItem, WorkspaceNavigation as DesignSystemNavigation } from "@/components/design-system/navigation";
import { WORKSPACE_SECTIONS, type WorkspaceSection } from "@/lib/workspace/workspace-model";

const labels: Record<WorkspaceSection, string> = {
  overview: "物件總覽",
  market: "價格與市場",
  location: "區位與通勤",
  risk: "風險與環境",
  finance: "資金與持有成本",
};

export function WorkspaceNavigation({ caseId }: { caseId: string }) {
  const pathname = usePathname();
  return <DesignSystemNavigation label="案件工作區" className="workspace-navigation">
    {WORKSPACE_SECTIONS.map((section) => {
      const href = `/cases/${encodeURIComponent(caseId)}/${section}`;
      return <NavigationItem key={section} href={href} current={pathname === href}>{labels[section]}</NavigationItem>;
    })}
    <span className="workspace-navigation__label text-meta">輸出與方法</span>
    <NavigationItem href={`/compare?cases=${encodeURIComponent(caseId)}`}>比較案件</NavigationItem>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/report`}>案件報告</NavigationItem>
    <NavigationItem href={`/cases/${encodeURIComponent(caseId)}/planning`} current={pathname.endsWith("/planning")}>進階案件規劃</NavigationItem>
  </DesignSystemNavigation>;
}
