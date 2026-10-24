"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { navigationCopy } from "@/lib/navigation/copy";
import { caseDestination, nextCaseStep } from "@/lib/navigation/model";

/** Navigation only: no repository writes, readiness inference or provider requests. */
export function CaseWorkflowHandoff({ caseId, marketStarted = true }: { caseId: string; marketStarted?: boolean }) {
  const pathname = usePathname();
  const { copyFrom } = useExperienceLocale();
  const section = pathname.split("/").at(-1) ?? "overview";
  const next = nextCaseStep(section, marketStarted);
  const href = next === "compare" ? `/compare?cases=${encodeURIComponent(caseId)}` : caseDestination(caseId, next);
  return <nav className="case-workflow-handoff" data-testid="case-workflow-handoff" aria-label={copyFrom(navigationCopy, "next")}>
    <div><strong>{copyFrom(navigationCopy, "next")}</strong><p className="text-meta">{copyFrom(navigationCopy, next === "compare" ? "compareHint" : "nextHint")}</p></div>
    <Link prefetch={false} className="ds-button ds-button--secondary" href={href}>{copyFrom(navigationCopy, next)}</Link>
    {section !== "report" && <Link prefetch={false} className="commercial-text-action" href={caseDestination(caseId, "report")}>{copyFrom(navigationCopy, "report")}</Link>}
  </nav>;
}
