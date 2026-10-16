"use client";
import Link from "next/link";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { copilotEntryLabel } from "@/lib/workspace/copilot-entry-copy";
export function CopilotLink({ caseId }: { caseId: string }) {
  const { locale } = useExperienceLocale();
  return <Link className="ds-button ds-button--secondary ds-button--compact" href={`/cases/${encodeURIComponent(caseId)}/overview?copilot=1`}>{copilotEntryLabel(locale)}</Link>;
}
