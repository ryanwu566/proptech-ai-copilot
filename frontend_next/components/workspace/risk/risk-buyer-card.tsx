"use client";

import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { buyerStateCopy, hazardBuyerCopy, riskBuyerCopy } from "@/lib/workspace/risk-buyer-copy";
import { buyerState, type RiskBuyerCardModel } from "@/lib/workspace/risk-buyer-model";
import type { RiskEvidenceRow } from "@/lib/workspace/risk-evidence-model";
import styles from "./risk-environment.module.css";

export function RiskBuyerCard({ card }: { card: RiskBuyerCardModel }) {
  const { locale } = useExperienceLocale();
  const c = riskBuyerCopy(locale);
  const state = buyerStateCopy(card.state, locale);
  const hazard = hazardBuyerCopy(card.actionKey, locale);
  // A saved finding is a record of an earlier query, not a fresh provider finding.
  const meaning = card.freshness === "saved_summary" && card.evidence
    ? savedFinding(card.state, locale)
    : state.meaning;
  return <article data-buyer-card data-testid={`risk-buyer-card-${card.key}`} className={`ds-panel ${styles.buyerCard}`}>
    <DetailsDisclosure className={styles.buyerDisclosure} summary={<span className={styles.cardSummary}>
      <span className="text-subsection">{hazard.name}</span>
      <span className={styles.buyerMeaning}>{meaning}</span>
      <span className={styles.cardMeta}><code>{card.state}</code><span>{c[card.freshness]}</span></span>
      <span className={styles.cardAction}>{c.openCard} <span aria-hidden="true">↕</span></span>
    </span>}>
      <div className={styles.buyerSections}>
        <section><h3 className="text-subsection">{c.known}</h3><p>{meaning}</p></section>
        <section><h3 className="text-subsection">{c.limits}</h3><p>{state.limits}</p></section>
        <section><h3 className="text-subsection">{c.next}</h3><p>{state.next}</p><ul className={styles.buyerActions}>{hazard.actions.map((action) => <li key={action}>{action}</li>)}</ul></section>
        <DetailsDisclosure summary={c.sourceDetails} variant="compact"><RiskSourceEvidence row={card.evidence} checkedAt={card.checkedAt} /></DetailsDisclosure>
      </div>
    </DetailsDisclosure>
  </article>;
}

function savedFinding(state: RiskBuyerCardModel["state"], locale: ReturnType<typeof useExperienceLocale>["locale"]) {
  if (state === "MATCHED") return riskBuyerCopy(locale).savedMatched;
  if (state === "NO MATCH") return riskBuyerCopy(locale).savedNoMatch;
  return `${riskBuyerCopy(locale).saved_summary}：${buyerStateCopy(state, locale).meaning}`;
}

export function RiskSourceEvidence({ row, checkedAt }: { row?: Readonly<RiskEvidenceRow>; checkedAt: string | null }) {
  const { locale } = useExperienceLocale();
  const c = riskBuyerCopy(locale);
  const value = (text?: string | null) => !text || ["未提供", "未知", "未設定"].includes(text) ? c.unknown : text;
  const entries = [
    [c.source, value(row?.source)],
    [c.evidenceType, value(row?.label)],
    [c.agency, value(row?.sourceAgency)],
    [c.classification, row?.categories?.map((category) => `${category.official} (${category.canonical})`).join(" / ") || value(row?.sourceClassification)],
    [c.coverage, row ? c[row.coverage] : c.unknown],
    [c.version, value(row?.datasetVersion)],
    [c.period, value(row?.effectivePeriod)],
    [c.checked, value(checkedAt)],
    [c.condition, value(row?.queryCondition)],
    [c.limitations, value(row?.limitation)],
    [c.next, value(row?.nextVerification)],
    [c.topicIdentity, row?.key ?? c.unknown],
    [c.reference, value(row?.sourceUrl)],
  ];
  return <div className={styles.sourceEvidence}>
    <dl className={styles.provenance}>{entries.map(([label, text]) => <div key={label}><dt>{label}</dt><dd>{text}</dd></div>)}</dl>
    {row && <p className="text-meta">{c.status}: <code>{buyerState(row)}</code></p>}
    {row?.sourceUrl && /^https?:\/\//i.test(row.sourceUrl) && <a className="ds-button ds-button--tertiary" href={row.sourceUrl} target="_blank" rel="noreferrer">{c.official}</a>}
  </div>;
}
