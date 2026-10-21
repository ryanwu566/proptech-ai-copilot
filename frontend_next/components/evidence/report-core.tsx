"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { StatusLabel } from "@/components/design-system/status-label";
import type { EvidenceField } from "@/lib/workspace/case-evidence";
import type { Citation } from "@/lib/workspace/document-evidence";
import type { ExecutiveKeyNumber } from "@/lib/workspace/report-executive";
import type { ReportCore, ReportCoreGroup } from "@/lib/workspace/report-core";
import { checklistIdForEvidence } from "@/lib/workspace/evidence-checklist";
import type { DecisionRoomReport } from "@/lib/decision-room-report";
import type { ReportRoomUi } from "./report-decision-room-entry";
import { reportCoreCopy, type ReportCoreCopyKey } from "@/lib/workspace/report-core-copy";
import { EvidenceCitation } from "./citation";
import styles from "./evidence.module.css";

function useCoreCopy() {
  const { copyFrom, formatNumber } = useExperienceLocale();
  return { t: (key: ReportCoreCopyKey, values?: Record<string, string | number>) => copyFrom(reportCoreCopy, key, values), n: formatNumber };
}

/**
 * Optional advisor/firm header seam. Nothing is stored or uploaded and no branding is
 * invented: absent values print as ruled fill-in lines and are omitted on screen.
 */
export type ReportBranding = { preparedBy: string | null; preparedFor: string | null };
export const EMPTY_REPORT_BRANDING: ReportBranding = { preparedBy: null, preparedFor: null };

export function ReportPreparedBy({ branding }: { branding: ReportBranding }) {
  const { t } = useCoreCopy();
  const row = (key: "advisor" | "client", value: string | null) => <div className={value ? undefined : styles.printOnly}>
    <dt>{t(key)}</dt><dd>{value ?? <span className={styles.fillLine} aria-hidden="true" />}</dd>
  </div>;
  return <dl className={styles.preparedBy} data-testid="report-prepared-by">{row("advisor", branding.preparedBy)}{row("client", branding.preparedFor)}</dl>;
}

export function ReportAppendixHeading() {
  const { t } = useCoreCopy();
  return <h2 id="report-appendix" className="text-section">{t("appendix")}</h2>;
}

const SAVED = new Set<EvidenceField<string | number>["status"]>(["available", "limited"]);

function fieldCitations(field: EvidenceField<string | number>, citations: Citation[]) {
  return citations.filter((citation) => citation.observationId === field.id).map((citation) => <EvidenceCitation key={citation.id} citation={citation} number={citations.indexOf(citation) + 1} report />);
}

/** Values with state and [n] references only; each field's full provenance prints once, in the appendix. */
function CoreFacts({ group, citations, room, roomUi }: { group: ReportCoreGroup; citations: Citation[]; room?: DecisionRoomReport | null; roomUi?: ReportRoomUi | null }) {
  const { t, n } = useCoreCopy();
  // Each linked Decision Room action is referenced once, on the first evidence row it belongs to.
  const shown = new Set<string>();
  const linked = (field: EvidenceField<string | number>) => {
    const key = room ? checklistIdForEvidence(field.id) : null;
    if (!room || !roomUi || !key || shown.has(key)) return null;
    // Completed actions print once, on page three; page two points only at open work.
    const action = room.outstanding.find((item) => item.sourceKey === key);
    if (!action) return null;
    shown.add(key);
    return <roomUi.RoomActionRef action={action} />;
  };
  // Saved values and units stay as saved; only missing-state wording is interface copy.
  const value = (field: EvidenceField<string | number>) => field.value === null
    ? field.id === "poi-risk" ? t("unknownFacility") : t(`gap_${field.missingReason ?? "not_preserved"}`)
    : `${typeof field.value === "number" ? n(field.value) : field.value}${field.unit ? ` ${field.unit}` : ""}`;
  // A saved value's ordinary saved state is stated once per page (ReportCorePages); every other
  // state keeps its label unless the missing-value text already says the same thing.
  const label = (field: EvidenceField<string | number>) => {
    if (field.value !== null && SAVED.has(field.status)) return null;
    const text = t(`status_${field.status}`);
    return text === value(field) ? null : text;
  };
  return <dl className={styles.coreFacts}>{group.facts.map((field) => <div key={field.id} data-testid={`core-fact-${field.id}`} data-evidence-status={field.status}>
    <dt>{field.label}</dt>
    <dd><strong className={typeof field.value === "number" ? styles.numeric : undefined} data-numeric={typeof field.value === "number" || undefined}>{value(field)}</strong>
      {label(field) && <StatusLabel semanticRole="neutral">{label(field)}</StatusLabel>}
      {fieldCitations(field, citations)}{linked(field)}</dd>
  </div>)}</dl>;
}

/** Drawn only from the executive's cited asking-unit derivation; nothing renders without a saved band. */
export function MarketPositionMarker({ item, citations }: { item: ExecutiveKeyNumber | undefined; citations: Citation[] }) {
  const { t, n } = useCoreCopy();
  if (!item || item.id !== "asking_unit" || !item.band || !item.position) return null;
  const { low, high, unit } = item.band;
  const lo = Math.min(low, item.value); const hi = Math.max(high, item.value);
  const pad = (hi - lo) * 0.15 || 1; const min = lo - pad; const max = hi + pad;
  const pct = (x: number) => `${((x - min) / (max - min)) * 100}%`;
  const label = t(({ below: "markerBelow", within: "markerWithin", above: "markerAbove" } as const)[item.position], { value: n(item.value), unit: item.unit, low: n(low), high: n(high), bandUnit: unit });
  const refs = item.refs.map((ref) => citations.find((citation) => citation.id === ref.citationId)).filter((citation): citation is Citation => Boolean(citation));
  return <figure className={styles.marketMarker} data-testid="core-market-marker" data-position={item.position}>
    <div className={styles.markerTrack} role="img" aria-label={label}>
      <span className={styles.markerBand} style={{ left: pct(low), width: `calc(${pct(high)} - ${pct(low)})` }} />
      <span className={styles.markerPoint} style={{ left: pct(item.value) }} />
    </div>
    <div className={styles.markerScale} aria-hidden="true"><span style={{ left: pct(low) }}>P25 {n(low)}</span><span style={{ left: pct(high) }}>P75 {n(high)}</span></div>
    <figcaption><strong>{label}</strong> · {t("markerCaveat")}{refs.map((citation) => <EvidenceCitation key={citation.id} citation={citation} number={citations.indexOf(citation) + 1} report />)}</figcaption>
  </figure>;
}

function CoreGroup({ group, citations, room, roomUi, children }: { group: ReportCoreGroup; citations: Citation[]; room?: DecisionRoomReport | null; roomUi?: ReportRoomUi | null; children?: ReactNode }) {
  const { t } = useCoreCopy();
  return <section aria-labelledby={`core-${group.id}`} className={styles.coreGroup} data-testid={`core-group-${group.id}`}>
    <h3 id={`core-${group.id}`} className="text-subsection">{t(group.id)}</h3>
    {/* One limitation per area, stated once instead of after every value. */}
    <p className="text-meta">{t(`${group.id}Note`)}</p>
    {children}
    <CoreFacts group={group} citations={citations} room={room} roomUi={roomUi} />
  </section>;
}

export function ReportCorePages({ core, citations, askingUnit, room = null, roomUi = null }: { core: ReportCore; citations: Citation[]; askingUnit: ExecutiveKeyNumber | undefined; room?: DecisionRoomReport | null; roomUi?: ReportRoomUi | null }) {
  const { t } = useCoreCopy();
  const [, page2, page3] = core.pages;
  const roomLeads = Boolean(room && room.counts.outstanding > 0);
  return <>
    <section aria-labelledby="core-page-2" className={styles.corePage} data-testid="report-core-page-2" data-report-page="2">
      <h2 id="core-page-2" className="text-section">{t("page2")}</h2>
      <p className="text-meta">{t("savedState")}</p>
      {page2.groups.map((group) => <CoreGroup key={group.id} group={group} citations={citations} room={room} roomUi={roomUi}>
        {group.id === "market" && <MarketPositionMarker item={askingUnit} citations={citations} />}
      </CoreGroup>)}
    </section>
    <section aria-labelledby="core-page-3" className={styles.corePage} data-testid="report-core-page-3" data-report-page="3">
      <h2 id="core-page-3" className="text-section">{t("page3")}</h2>
      <p className="text-meta">{t("savedState")}</p>
      {page3.groups.map((group) => <CoreGroup key={group.id} group={group} citations={citations} room={room} roomUi={roomUi} />)}
      {room && roomUi && <roomUi.RoomNextActions report={room} caseId={core.caseId} />}
      <section aria-labelledby="core-next-steps" className={styles.coreGroup} data-testid="core-next-steps">
        <h3 id="core-next-steps" className="text-subsection">{t("checklist")}</h3>
        <p className="text-meta">{t("checklistIntro", { count: page3.gapTotal })}</p>
        {page3.nextSteps.length ? <ol className={styles.coreSteps}>{page3.nextSteps.map((step) => <li key={step.domain} data-testid={`core-step-${step.domain}`}>
          {/* Gap labels and next actions are saved evidence text and stay as saved. */}
          <p><strong>{t("checklistArea", { area: t(step.domain), count: step.count })}</strong>: {step.items.map((item) => `${item.label} (${t(`gap_${item.reason}`)})`).join(t("sep"))}{step.more > 0 && ` · ${t("more", { count: step.more })}`}</p>
          {/* With open Decision Room actions, print gives page three to them; per-item next steps still print in the appendix. */}
          <ul className={roomLeads ? styles.screenOnly : undefined}>{step.actions.map((action) => <li key={action}>{action}</li>)}</ul>
          <p className={styles.screenOnly}><Link href={step.href}>{t("workspace", { area: t(step.domain) })}</Link></p>
        </li>)}</ol> : <p>{t("checklistEmpty")}</p>}
        <p className="text-meta">{t("checklistFooter")}</p>
      </section>
    </section>
  </>;
}
