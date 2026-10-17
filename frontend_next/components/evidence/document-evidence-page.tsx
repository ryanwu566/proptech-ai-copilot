"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserCaseRepository, type WorkspaceReadDiagnostic } from "@/lib/workspace/case-repository";
import { projectCaseEvidence } from "@/lib/workspace/case-evidence";
import { buildCaseEvidenceGraph, type EvidenceGraph } from "@/lib/workspace/document-evidence";
import { documentEvidenceCopy, type DocumentEvidenceCopyKey } from "@/lib/workspace/document-evidence-copy";
import { EvidenceCitation, EvidenceProvenance } from "./citation";
import styles from "./document-evidence.module.css";

export function DocumentEvidencePage({ caseId }: { caseId: string }) {
  const repository = useMemo(createBrowserCaseRepository, []);
  const [read, setRead] = useState<WorkspaceReadDiagnostic | null>(null);
  const [hash, setHash] = useState("");
  const { copyFrom } = useExperienceLocale();
  const text = (key: DocumentEvidenceCopyKey) => copyFrom(documentEvidenceCopy, key);
  useEffect(() => {
    const load = () => setRead(repository.readDiagnostic());
    const updateHash = () => { setHash(window.location.hash.slice(1)); };
    load(); updateHash(); const unsubscribe = repository.subscribe(load);
    window.addEventListener("hashchange", updateHash);
    return () => { unsubscribe(); window.removeEventListener("hashchange", updateHash); };
  }, [repository]);
  const invalid = read && (["parse_error", "invalid_storage", "storage_unavailable"].includes(read.status) || read.issues.some(issue => issue.caseId === caseId));
  const workspace = invalid ? null : read?.cases.find(item => item.caseId === caseId);
  const graph = useMemo(() => workspace ? buildCaseEvidenceGraph(projectCaseEvidence(workspace)) : null, [workspace]);
  useEffect(() => {
    if (!hash || !graph) return;
    const element = document.getElementById(hash);
    if (element instanceof HTMLDetailsElement) { element.open = true; element.scrollIntoView({ block: "start" }); }
  }, [hash, graph]);
  return <main id="main-content" className={styles.page} data-testid="document-evidence-page">
    <header><h1 className="text-page">{text("title")}</h1><p>{text("intro")}</p></header>
    <nav aria-label={text("nav")}><Link href={`/cases/${encodeURIComponent(caseId)}/overview`}>{text("back")}</Link><Link href={`/cases/${encodeURIComponent(caseId)}/report`}>{text("report")}</Link></nav>
    {!read ? <p role="status">…</p> : invalid ? <p role="alert">{text("error")}</p> : !graph ? <p role="status">{text("empty")}</p> : <EvidenceGraphView graph={graph} hash={hash} />}
  </main>;
}

/** Shared view for saved snapshots and future authorized document graph reads. */
export function EvidenceGraphView({ graph, hash = "" }: { graph: EvidenceGraph; hash?: string }) {
  const { copyFrom, formatNumber } = useExperienceLocale();
  const text = (key: DocumentEvidenceCopyKey) => copyFrom(documentEvidenceCopy, key);
  return <>
      {hash && !graph.citations.some(c => c.id === hash) && <p role="alert">{text("missing")}</p>}
      <section aria-label={text("graph")}><h2 className="text-section">{text("graph")}</h2>
        {graph.decisions.map(decision => <div className={styles.flow} key={decision.id}>
          <div><h3 className="text-subsection">{text("decision")}</h3><Link href={decision.href}>{text(decision.domain as DocumentEvidenceCopyKey)}</Link></div>
          <span aria-hidden="true" className={styles.arrow}>←</span>
          <div><h3 className="text-subsection">{text("claim")} → {text("observation")} → {text("source")}</h3><ul>
            {graph.claims.filter(claim => claim.decisionId === decision.id).map(claim => <li key={claim.id}>
              <span>{claim.label}</span>{claim.citationIds.map(id => { const citation = graph.citations.find(c => c.id === id)!; return <EvidenceCitation key={id} citation={citation} />; })}
            </li>)}
          </ul></div>
        </div>)}
      </section>
      <section aria-label={text("detail")}><h2 className="text-section">{text("detail")}</h2>{graph.citations.map(citation => <details key={citation.id} id={citation.id} className={styles.detail} data-testid="evidence-detail">
        <summary>{citation.label} · {text(citation.state)}</summary>
        {graph.observations.filter(o => o.id === citation.observationId && o.versionId === citation.versionId).map(o => {
          const value = o.value ?? o.historicalValue;
          return <p key={o.id}>{text("observation")}: {value === null ? text("unknownDate") : typeof value === "number" ? formatNumber(value) : value} {o.unit}{o.value === null && o.historicalValue !== null && <> · {text("stale")}</>}</p>;
        })}
        <h3 className="text-subsection">{text("provenance")}</h3><EvidenceProvenance citation={citation} />
        <nav aria-label={text("decision")}>{graph.decisions.filter(d => citation.decisionIds.includes(d.id)).map(d => <span key={d.id}><Link href={d.href}>{text("decision")}: {text(d.domain as DocumentEvidenceCopyKey)}</Link> · <Link href={d.analysisHref}>{text(d.domain as DocumentEvidenceCopyKey)}</Link></span>)}</nav>
      </details>)}</section>
    </>;
}
