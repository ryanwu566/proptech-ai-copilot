"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AsyncState } from "@/components/design-system/async-state";
import { Panel, Section } from "@/components/design-system/section";
import { StatusLabel } from "@/components/design-system/status-label";
import { formatExactDate, formatWan } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { RepositoryNotice, storageBlocked } from "@/components/evidence/evidence-view";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { buildWorkspaceOverview } from "@/lib/workspace/overview-model";
import styles from "./saved-cases-entry.module.css";
import { CopilotLink } from "./copilot/copilot-link";
import { useSearchParams } from "next/navigation";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { navigationCopy } from "@/lib/navigation/copy";
import { caseDestination, parseCaseDestination, type CaseDestination } from "@/lib/navigation/model";

export function SavedCasesLoading() {
  const { copyFrom } = useExperienceLocale();
  return <main className={styles.page} id="main-content" tabIndex={-1} aria-busy="true"><AsyncState kind="loading" title={copyFrom(navigationCopy, "loading")} /></main>;
}

export function SavedCasesEntry() {
  const { copyFrom } = useExperienceLocale();
  const search = useSearchParams();
  const destination = parseCaseDestination(search.get("next"));
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const [cases, setCases] = useState<PropertyCaseWorkspace[] | null>(null);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  useEffect(() => {
    const load = () => { const next = repository.readDiagnostic(); setRead(next); setCases(next.cases); };
    load();
    return repository.subscribe(load);
  }, [repository]);

  return <main className={styles.page} id="main-content" tabIndex={-1}>
    <header className={styles.heading}>
      <p className="text-meta">{copyFrom(navigationCopy, "local")}</p>
      <h1 className="text-page">{copyFrom(navigationCopy, "cases")}</h1>
      <p className="text-body">{copyFrom(navigationCopy, "resumeHint")}</p>
      {search.has("next") && <p data-testid="case-destination-hint" role="status">{copyFrom(navigationCopy, "chooseHint", { destination: copyFrom(navigationCopy, destination) })}</p>}
      <Link prefetch={false} className="ds-button ds-button--secondary" href="/compare">{copyFrom(navigationCopy, "compare")}</Link>
    </header>
    {read && <RepositoryNotice read={read} />}
    <Section title={copyFrom(navigationCopy, "choose")}>
      {cases === null
        ? <AsyncState kind="loading" title={copyFrom(navigationCopy, "loading")} />
        : read && storageBlocked(read) ? <Link prefetch={false} className="ds-button ds-button--secondary" href="/?workflow=property">{copyFrom(navigationCopy, "property")}</Link> : cases.length === 0 && read?.issues.length ? <><p>{copyFrom(navigationCopy, "invalid")}</p><Link prefetch={false} className="ds-button ds-button--secondary" href="/?workflow=property">{copyFrom(navigationCopy, "property")}</Link></> : cases.length === 0
          ? <AsyncState kind="not_started" title={copyFrom(navigationCopy, "empty")} detail={copyFrom(navigationCopy, "emptyHint")} action={<Link prefetch={false} className="ds-button ds-button--primary" href="/?workflow=property">{copyFrom(navigationCopy, "property")}</Link>} />
          : <div className={styles.grid}>{cases.map((workspace) => <SavedCaseRow key={workspace.caseId} workspace={workspace} destination={destination} />)}</div>}
    </Section>
  </main>;
}

function SavedCaseRow({ workspace, destination }: { workspace: PropertyCaseWorkspace; destination: CaseDestination }) {
  const { locale, copyFrom } = useExperienceLocale();
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const overview = buildWorkspaceOverview(workspace);
  return <article aria-label={workspace.title} className={styles.caseArticle}><Panel variant="plain">
    <div className={styles.rowHeading}>
      <div><h2 className="text-subsection">{workspace.title}</h2><p className="text-dense">{workspace.displayAddress}</p></div>
      <StatusLabel semanticRole={identity.role}>{identity.label[locale]}</StatusLabel>
    </div>
    <p className="text-meta">{workspace.assumptions.activePriceWan ? formatWan(workspace.assumptions.activePriceWan) : copyFrom(navigationCopy, "unknownPrice")} · {copyFrom(navigationCopy, "snapshot")} {formatExactDate(workspace.updatedAt)}</p>
    <p className="text-dense">{overview.unresolvedCount > 0 ? copyFrom(navigationCopy, "gaps", { count: overview.unresolvedCount }) : copyFrom(navigationCopy, "noGaps")}</p>
    <div className={styles.actions}><Link prefetch={false} className="ds-button ds-button--secondary" href={caseDestination(workspace.caseId, destination)}>{copyFrom(navigationCopy, "open")}{workspace.title}</Link>
    {destination !== "report" && <Link prefetch={false} className="ds-button ds-button--tertiary" href={caseDestination(workspace.caseId, "report")}>{copyFrom(navigationCopy, "report")}</Link>}<CopilotLink caseId={workspace.caseId} /></div>
  </Panel></article>;
}
