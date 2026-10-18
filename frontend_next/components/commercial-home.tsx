"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Field } from "@/components/design-system/field";
import { Message } from "@/components/design-system/message";
import { Section } from "@/components/design-system/section";
import { AsyncState } from "@/components/design-system/async-state";
import { StatusLabel } from "@/components/design-system/status-label";
import { RepositoryNotice, storageBlocked } from "@/components/evidence/evidence-view";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { MAX_DRAFT_ADDRESS_LENGTH, type AddressDraftFailure } from "@/lib/workspace/case-draft";
import { createAddressDraftCase } from "@/lib/case-storage";
import { formatExactDate } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { useStartGuidedExample } from "@/components/app-shell";
import { navigationCopy } from "@/lib/navigation/copy";
import { caseDestination } from "@/lib/navigation/model";
import { homeStartCopy } from "@/lib/home-start-copy";

/** Primary start is local case creation only: no geocoding, provider call or analysis. */
export function CommercialHome({ onFinder }: { onFinder: () => void }) {
  const { t, copyFrom, locale } = useExperienceLocale();
  const router = useRouter();
  const startDemo = useStartGuidedExample();
  const [address, setAddress] = useState("");
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<AddressDraftFailure | null>(null);
  const submitting = useRef(false);
  const repository = useMemo(createBrowserCaseRepository, []);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  useEffect(() => { const load = () => setRead(repository.readDiagnostic()); load(); return repository.subscribe(load); }, [repository]);
  // If the case navigation is interrupted (e.g. Back mid-push), Home stays mounted; re-enable the start.
  useEffect(() => { const reset = () => { submitting.current = false; setPending(false); }; window.addEventListener("popstate", reset); return () => window.removeEventListener("popstate", reset); }, []);
  async function start(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setPending(true);
    setFailure(null);
    const result = await createAddressDraftCase(address).catch(() => ({ status: "blocked", reason: "write_failed" }) as const);
    if (result.status === "blocked") {
      submitting.current = false;
      setPending(false);
      setFailure(result.reason);
      return;
    }
    router.push(caseDestination(result.caseId, "location"));
  }
  const recent = read?.cases.slice().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).slice(0, 3) ?? [];
  return <div className="commercial-home">
    <section className="commercial-home__start" aria-labelledby="commercial-home-heading">
      <header data-page-heading tabIndex={-1}><p className="text-meta">{t("commercial.workspace")}</p><h1 id="commercial-home-heading" className="text-page">{t("commercial.homeTitle")}</h1><p className="text-body">{t("commercial.homeDescription")}</p></header>
      <form onSubmit={start} className="commercial-home__form" aria-busy={pending || undefined}>
        <Field required label={t("commercial.address")} helperText={t("commercial.addressHint")}><input id="commercial-address" className="ds-control" required maxLength={MAX_DRAFT_ADDRESS_LENGTH} value={address} onChange={(event) => { setAddress(event.target.value); setFailure(null); }} autoComplete="street-address" placeholder={t("commercial.addressPlaceholder")} /></Field>
        <CommercialButton type="submit" size="touch" loading={pending} loadingLabel={copyFrom(homeStartCopy, "creating")}>{t("commercial.start")}</CommercialButton>
      </form>
      <div data-testid="home-start-status">{failure && <Message variant="error" title={copyFrom(homeStartCopy, "failedTitle")} action={failure === "limit_reached" || failure === "storage_invalid" ? <Link prefetch={false} className="commercial-text-action" href="/cases">{copyFrom(homeStartCopy, "manageCases")}</Link> : undefined}>{copyFrom(homeStartCopy, failure)}</Message>}</div>
      <div className="commercial-home__secondary">
        {recent.length > 0 && <Link prefetch={false} className="ds-button ds-button--secondary ds-button--touch" href="/cases">{copyFrom(homeStartCopy, "resume")}</Link>}
        <button type="button" className="commercial-text-action" onClick={onFinder}>{t("commercial.finder")}</button>
        <button type="button" data-testid="demo-start" className="commercial-text-action" onClick={(event) => startDemo?.(event.currentTarget)}>{copyFrom(homeStartCopy, "example")}</button>
      </div>
    </section>
    <Section title={t("commercial.recent")} description={t("commercial.localNote")}>
      {read && <RepositoryNotice read={read} />}
      {!read ? <AsyncState kind="loading" title={t("commercial.loadingCases")} /> : storageBlocked(read) ? null : recent.length ? <ul className="commercial-recent-cases">
        {recent.map((workspace) => { const identity = resolveCommercialState("identity", workspace.identity.state); return <li key={workspace.caseId}>
          <div><h3 className="text-subsection">{workspace.title}</h3>{workspace.displayAddress !== workspace.title && <p className="text-dense">{workspace.displayAddress}</p>}<p className="text-meta">{t("commercial.snapshot")} · {formatExactDate(workspace.updatedAt)}</p></div>
          <StatusLabel semanticRole={identity.role}>{identity.label[locale]}</StatusLabel>
          <Link className="ds-button ds-button--secondary" href={`/cases/${encodeURIComponent(workspace.caseId)}/overview`} aria-label={`${t("commercial.continue")}${workspace.title}`}>{t("commercial.continue")}</Link>
        </li>; })}
      </ul> : <p className="text-body">{read.issues.length ? t("commercial.invalidCases") : copyFrom(navigationCopy, "emptyHint")}</p>}
      <Link className="commercial-text-action" href="/cases">{t("commercial.allCases")}</Link>
    </Section>
    <section className="commercial-home__what" aria-labelledby="commercial-home-what">
      <h2 id="commercial-home-what" className="text-subsection">{copyFrom(homeStartCopy, "whatTitle")}</h2>
      <p className="text-body">{copyFrom(homeStartCopy, "what")}</p>
      <p role="note" className="commercial-home__trust text-meta">{copyFrom(homeStartCopy, "trust")} {copyFrom(homeStartCopy, "boundary")}</p>
    </section>
  </div>;
}
