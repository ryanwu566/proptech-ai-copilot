"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Field } from "@/components/design-system/field";
import { Section } from "@/components/design-system/section";
import { AsyncState } from "@/components/design-system/async-state";
import { StatusLabel } from "@/components/design-system/status-label";
import { RepositoryNotice, storageBlocked } from "@/components/evidence/evidence-view";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { formatExactDate } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { useStartGuidedExample } from "@/components/app-shell";

export function CommercialHome({ onStart, onFinder }: { onStart: (address: string) => void; onFinder: () => void }) {
  const { t, copy, locale } = useExperienceLocale();
  const startDemo = useStartGuidedExample();
  const [address, setAddress] = useState("");
  const repository = useMemo(createBrowserCaseRepository, []);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  useEffect(() => { const load = () => setRead(repository.readDiagnostic()); load(); return repository.subscribe(load); }, [repository]);
  function start(event: FormEvent) { event.preventDefault(); if (address.trim()) onStart(address.trim()); }
  const recent = read?.cases.slice().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).slice(0, 3) ?? [];
  return <div className="commercial-home">
    <section className="commercial-home__start" aria-labelledby="commercial-home-heading">
      <header data-page-heading tabIndex={-1}><p className="text-meta">{t("commercial.workspace")}</p><h1 id="commercial-home-heading" className="text-page">{t("commercial.homeTitle")}</h1><p className="text-body">{t("commercial.homeDescription")}</p></header>
      <form onSubmit={start} className="commercial-home__form">
        <Field required label={t("commercial.address")} helperText={t("commercial.addressHint")}><input id="commercial-address" className="ds-control" required value={address} onChange={(event) => setAddress(event.target.value)} autoComplete="street-address" placeholder={t("commercial.addressPlaceholder")} /></Field>
        <CommercialButton type="submit" size="touch">{t("commercial.start")}</CommercialButton>
      </form>
      <button type="button" className="commercial-text-action" onClick={onFinder}>{t("commercial.finder")}</button>
      <button type="button" data-testid="demo-start" className="ds-button ds-button--secondary" onClick={(event) => startDemo?.(event.currentTarget)}>{copy("guide.demoStart")}</button>
    </section>
    <Section title={t("commercial.recent")} description={t("commercial.localNote")}>
      {read && <RepositoryNotice read={read} />}
      {!read ? <AsyncState kind="loading" title={t("commercial.loadingCases")} /> : storageBlocked(read) ? null : recent.length ? <ul className="commercial-recent-cases">
        {recent.map((workspace) => { const identity = resolveCommercialState("identity", workspace.identity.state); return <li key={workspace.caseId}>
          <div><h3 className="text-subsection">{workspace.title}</h3><p className="text-dense">{workspace.displayAddress}</p><p className="text-meta">{t("commercial.snapshot")} · {formatExactDate(workspace.updatedAt)}</p></div>
          <StatusLabel semanticRole={identity.role}>{identity.label[locale]}</StatusLabel>
          <Link className="ds-button ds-button--secondary" href={`/cases/${encodeURIComponent(workspace.caseId)}/overview`} aria-label={`${t("commercial.continue")}${workspace.title}`}>{t("commercial.continue")}</Link>
        </li>; })}
      </ul> : <p className="text-body">{read.issues.length ? t("commercial.invalidCases") : t("commercial.emptyCases")}</p>}
      <Link className="commercial-text-action" href="/cases">{t("commercial.allCases")}</Link>
    </Section>
    <p role="note" className="commercial-home__trust text-meta">{t("commercial.trust")}</p>
  </div>;
}
