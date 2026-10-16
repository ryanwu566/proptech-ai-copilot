"use client";
import Link from "next/link";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { Citation } from "@/lib/workspace/document-evidence";
import { documentEvidenceCopy, type DocumentEvidenceCopyKey } from "@/lib/workspace/document-evidence-copy";
import styles from "./document-evidence.module.css";

export function EvidenceCitation({ citation, number, report = false }: { citation: Citation; number?: number; report?: boolean }) {
  const { copyFrom } = useExperienceLocale();
  const label = `${copyFrom(documentEvidenceCopy, "reference")}: ${citation.label}`;
  return <span className={styles.citation} data-citation-id={citation.id}>
    <a href={report ? `#report-${citation.id}` : citation.href} aria-label={label}>[{number ?? citation.observationId}]</a>
    {report && <span className={styles.printReference}>{citation.id}</span>}
  </span>;
}

export function EvidenceProvenance({ citation, report = false }: { citation: Citation; report?: boolean }) {
  const { copyFrom, formatDate, formatNumber } = useExperienceLocale();
  const text = (key: DocumentEvidenceCopyKey) => copyFrom(documentEvidenceCopy, key);
  const date = (value: string | null) => value ? formatDate(value) : text("unknownDate");
  return <dl className={styles.provenance}>
    <dt>{text("source")}</dt><dd>{text(citation.source.kind === "document" ? "document" : "snapshot")} · {citation.source.label}</dd>
    <dt>{text("original")}</dt><dd>{citation.label}</dd>
    <dt>{text("observed")}</dt><dd>{date(citation.observedAt)}</dd>
    <dt>{text("effective")}</dt><dd>{date(citation.effectiveAt)}</dd>
    <dt>{text("updated")}</dt><dd>{date(citation.sourceUpdatedAt)}</dd>
    <dt>{text("verification")}</dt><dd>{text(citation.verification)}</dd>
    <dt>{text("state")}</dt><dd data-evidence-state={citation.state}>{text(citation.state)}</dd>
    <dt>{text("relation")}</dt><dd>{text(citation.relation)}</dd>
    <dt>{text("version")}</dt><dd><code>{citation.versionId}</code></dd>
    <dt>{text("limitation")}</dt><dd>{citation.limitation}</dd>
    {citation.document && <>
      <dt>{text("class")}</dt><dd>{text(citation.document.documentClass)}</dd>
      <dt>{text("document")}</dt><dd>{citation.document.mediaType} · {formatNumber(citation.document.byteLength)} B</dd>
      <dt>SHA-256</dt><dd><code>{citation.document.sha256}</code></dd>
      <dt>{text("extraction")}</dt><dd>{text(citation.document.extraction)}</dd>
      <dt>{text("scan")}</dt><dd>{text(citation.document.scan)}</dd>
      <dt>{text("expires")}</dt><dd>{date(citation.document.expiresAt)}</dd>
    </>}
    <dt>{text("reference")}</dt><dd><Link href={report ? `#report-${citation.id}` : citation.href}>{citation.id}</Link></dd>
    {citation.canonicalUrl && <><dt>{text("sources")}</dt><dd><a href={citation.canonicalUrl} rel="noopener noreferrer" target="_blank">{citation.canonicalUrl}</a></dd></>}
  </dl>;
}

export function ReportCitationReferences({ citations }: { citations: Citation[] }) {
  const { copyFrom } = useExperienceLocale();
  if (!citations.length) return null;
  return <section aria-label={copyFrom(documentEvidenceCopy, "sources")} className={styles.references} data-testid="report-citation-references">
    <h2 className="text-section">{copyFrom(documentEvidenceCopy, "sources")}</h2>
    <ol>{citations.map((citation, index) => <li key={citation.id} id={`report-${citation.id}`}>
      <EvidenceCitation citation={citation} number={index + 1} report /><EvidenceProvenance citation={citation} report />
    </li>)}</ol>
  </section>;
}
