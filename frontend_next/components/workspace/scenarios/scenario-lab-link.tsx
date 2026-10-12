"use client";

import Link from "next/link";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { scenarioEntryCopy } from "@/lib/workspace/scenario-entry-copy";

export function ScenarioLabLink({ caseId }: { caseId: string }) {
  const { copyFrom } = useExperienceLocale();
  return <Link prefetch={false} className="ds-button ds-button--secondary" href={`/cases/${encodeURIComponent(caseId)}/scenarios`}>{copyFrom(scenarioEntryCopy, "nav")}</Link>;
}
