"use client";
import Link from "next/link";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { Citation } from "@/lib/workspace/document-evidence";
import { documentEvidenceCopy } from "@/lib/workspace/document-evidence-copy";
import type { ExecutiveAttention, ExecutiveKeyNumber, ExecutiveRef, ReportExecutiveSummary } from "@/lib/workspace/report-executive";
import { reportExecutiveCopy, type ReportExecutiveCopyKey } from "@/lib/workspace/report-executive-copy";
import { EvidenceCitation } from "./citation";
import styles from "./evidence.module.css";

/** Page-one summary. Numbers resolve to the report's existing citation list; it adds no references of its own. */
export function ReportExecutive({ summary, citations }: { summary: ReportExecutiveSummary; citations: Citation[] }) {
  const { copyFrom, formatDate, formatNumber } = useExperienceLocale();
  const t = (key: ReportExecutiveCopyKey, values?: Record<string, string | number>) => copyFrom(reportExecutiveCopy, key, values);
  const n = (value: number) => formatNumber(value);
  const stateText = (states: ExecutiveRef["state"][]) => [...new Set(states)].map((state) => copyFrom(documentEvidenceCopy, state)).join(" / ");
  /** One shared state is stated once per list; mixed states stay on each item. */
  const sharedState = (groups: ExecutiveRef[][]) => { if (groups.some((refs) => !refs.length)) return null; const states = new Set(groups.flat().map((ref) => ref.state)); return states.size === 1 ? [...states][0] : null; };
  const numbersState = sharedState(summary.keyNumbers.map((item) => item.refs));
  const attentionState = sharedState(summary.attention.map((item) => item.refs));
  const refs = (items: ExecutiveRef[], derived = false, shared: ExecutiveRef["state"] | null = null) => {
    const resolved = items.map((ref) => ({ ref, citation: citations.find((citation) => citation.id === ref.citationId) })).filter((item): item is { ref: ExecutiveRef; citation: Citation } => Boolean(item.citation));
    if (!resolved.length) return null;
    return <p className={styles.executiveRefs}>
      <span>{t(derived ? "inputs" : "references")}:</span>
      {resolved.map(({ citation }) => <EvidenceCitation key={citation.id} citation={citation} number={citations.indexOf(citation) + 1} report />)}
      {!shared && <span>· {t("evidenceState")}: {stateText(resolved.map(({ ref }) => ref.state))}</span>}
    </p>;
  };
  const keyNumber = (item: ExecutiveKeyNumber) => <li key={item.id} data-testid={`executive-key-${item.id}`} data-trust={item.trust}>
    <span className={styles.executiveLabel}>{item.id === "asking_unit" ? t("asking_unit") : item.label}</span>
    <strong className={styles.numeric} data-numeric>{n(item.value)} {item.unit}</strong>
    <span className={styles.tag}>{t(item.trust)}</span>
    {item.id === "selected" && item.context[0] && <p>{t("basis", { basis: item.context[0] })}</p>}
    {item.id === "commute" && <p>{item.context.join(" · ")} · {t("commuteCaveat")}</p>}
    {item.id === "asking_unit" && <p>{t("askingUnitMethod")}</p>}
    {item.id === "asking_unit" && item.position && item.band && <p><strong>{t(item.position, { low: n(item.band.low), high: n(item.band.high), unit: item.band.unit })}</strong> · {t("bandCaveat")}</p>}
    {item.id === "market" && <p>{[item.context[0], item.band && t("band", { low: n(item.band.low), high: n(item.band.high), unit: item.band.unit }), item.samples !== null && t("samples", { count: n(item.samples) }), item.period && t("period", { period: item.period })].filter(Boolean).join(" · ")} · {t("marketCaveat")}</p>}
    {item.id === "housing" && <p>{t("housingCaveat")}</p>}
    {refs(item.refs, item.trust === "derived", numbersState)}
  </li>;
  const attentionText = (item: ExecutiveAttention) => {
    switch (item.id) {
      case "conflicting_price": return t("conflicting_price", { finance: n(item.finance), selected: n(item.selected), unit: item.unit });
      case "stale": return t("stale", { count: item.count, labels: item.labels.join(t("sep")) });
      case "risk_match": return t("risk_match", { labels: item.labels.join(t("sep")) });
      case "risk_unresolved": return t("risk_unresolved", { count: item.count, total: item.total, labels: item.labels.join(t("sep")) + (item.count > item.labels.length ? "…" : "") });
      case "affordability_not_assessed": return t("affordability_not_assessed");
    }
  };
  return <section aria-labelledby="report-executive-title" className={styles.executive} data-testid="report-executive">
    <h2 id="report-executive-title" className="text-section">{t("title")}</h2>
    <p className="text-meta">{t("intro")}</p>
    <div className={styles.executiveContext}>
      <section aria-labelledby="executive-property" data-testid="executive-property">
        <h3 id="executive-property" className="text-subsection">{t("property")}</h3>
        {/* Title and address lead the report header directly above; repeated here for screen readers that jump to this section. */}
        <p className="sr-only">{summary.property.title} · {summary.property.address}</p>
        <p>{t(summary.property.identity === "confirmed" ? "identity" : "identityPending")}</p>
      </section>
      <section aria-labelledby="executive-snapshot" data-testid="executive-snapshot">
        <h3 id="executive-snapshot" className="text-subsection">{t("snapshot")}</h3>
        <p>{t("saved", { saved: formatDate(summary.snapshot.savedAt), generated: formatDate(summary.snapshot.generatedAt) })}</p>
        <p>{t("frozen")}</p>
      </section>
    </div>
    <section aria-labelledby="executive-key-numbers" data-testid="executive-key-numbers">
      <h3 id="executive-key-numbers" className="text-subsection">{t("keyNumbers")}</h3>
      {numbersState && <p className="text-meta" data-testid="executive-key-state">{t("evidenceState")}: {stateText([numbersState])}</p>}
      {summary.keyNumbers.length ? <ul className={styles.executiveNumbers}>{summary.keyNumbers.map(keyNumber)}</ul> : <p>{t("noKeyNumbers")}</p>}
    </section>
    <section aria-labelledby="executive-attention" data-testid="executive-attention">
      <h3 id="executive-attention" className="text-subsection">{t("attention")}</h3>
      {attentionState && <p className="text-meta">{t("evidenceState")}: {stateText([attentionState])}</p>}
      {summary.attention.length ? <ul className={styles.executiveList}>{summary.attention.map((item) => <li key={item.id} data-testid={`executive-attention-${item.id}`}>
        <p>{attentionText(item)}</p>
        {refs(item.refs, false, attentionState)}
        {item.gapIds.length > 0 && <p className={`${styles.executiveRefs} ${styles.screenOnly}`}><a href="#report-limits">{t("gapRefs")}</a></p>}
      </li>)}</ul> : <p>{t("noAttention")}</p>}
    </section>
    <section aria-labelledby="executive-open" data-testid="executive-open">
      <h3 id="executive-open" className="text-subsection">{t("open")}</h3>
      <p>{t("openTotal", { count: summary.open.total })}</p>
      <ul className={styles.executiveList}>{summary.open.areas.map((area) => {
        const name = copyFrom(documentEvidenceCopy, area.domain);
        return <li key={area.domain} data-testid={`executive-open-${area.domain}`}>
          <p><strong>{t("openArea", { area: name, count: area.count })}</strong>: {area.items.map((item) => t("openItem", { label: item.label, reason: t(item.reason === "stale" ? "stale_reason" : item.reason) })).join(t("sep"))}{area.more > 0 && ` · ${t("more", { count: area.more })}`}</p>
          <p className={styles.screenOnly}><Link href={area.href}>{t("workspace", { area: name })}</Link></p>
        </li>;
      })}</ul>
      <p className={`${styles.executiveRefs} ${styles.screenOnly}`}><a href="#report-limits">{t("gapRefs")}</a></p>
    </section>
    <section aria-labelledby="executive-limitation" data-testid="executive-limitation">
      <h3 id="executive-limitation" className="text-subsection">{t("limitation")}</h3>
      <p>{t("limitationText")}</p>
    </section>
    <p className="text-meta">{t("detail")}</p>
  </section>;
}
