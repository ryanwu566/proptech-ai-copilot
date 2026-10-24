"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { SatelliteEvidence } from "@/components/satellite-evidence";
import { CommercialButton } from "@/components/design-system/button";
import { DataTable, DataTableCell, DataTableHeader } from "@/components/design-system/data-table";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { MapFrame } from "@/components/design-system/map-frame";
import { Message } from "@/components/design-system/message";
import { Panel, Section } from "@/components/design-system/section";
import { StatusLabel } from "@/components/design-system/status-label";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { identityConfirmationCopy, identityConfirmationKind } from "@/lib/workspace/identity-confirmation-copy";
import { api, type TerrainRiskResult } from "@/lib/api";
import { readSavedCases, updateSavedCaseRiskEvidence } from "@/lib/case-storage";
import { resolveCommercialState } from "@/lib/commercial/state";
import {
  buildRiskEvidenceModel,
  buildRiskQueryContext,
  buildStoredRiskEvidenceModel,
  buildStoredRiskEvidenceSnapshot,
  canCommitRiskResponse,
  type RiskEvidenceModel,
  type RiskEvidenceRow,
  type RiskQueryContext,
} from "@/lib/workspace/risk-evidence-model";
import { RiskEvidenceMap } from "./risk-evidence-map";
import { ExplicitMap } from "@/components/map/explicit-map";
import { buildRiskBuyerModel } from "@/lib/workspace/risk-buyer-model";
import { formatEvidenceDate } from "@/lib/workspace/evidence-date";
import { hazardBuyerCopy, riskBuyerCopy, riskBuyerSummary } from "@/lib/workspace/risk-buyer-copy";
import { RiskBuyerCard, RiskSourceEvidence } from "./risk-buyer-card";
import styles from "./risk-environment.module.css";

const defaultSelection = (model: RiskEvidenceModel | null) => model?.rows.find((row) => row.matched)?.key ?? model?.rows[0]?.key;
const evidenceContract = (row: RiskEvidenceRow) => resolveCommercialState("evidence", row.usability);
const riskContract = (row: RiskEvidenceRow) => resolveCommercialState("risk", row.interpretation);

function RowStatuses({ row }: { row: RiskEvidenceRow }) {
  const { locale } = useExperienceLocale();
  const evidence = evidenceContract(row);
  const risk = riskContract(row);
  return <div className={styles.statusStack}>
    <StatusLabel semanticRole={evidence.role}>{evidence.label[locale]}</StatusLabel>
    <StatusLabel semanticRole={risk.role}>{risk.label[locale]}</StatusLabel>
  </div>;
}

export function RiskEnvironmentView() {
  const workspace = useWorkspace();
  const { locale, formatDate } = useExperienceLocale();
  const queryContext = useMemo(() => buildRiskQueryContext(workspace), [workspace]);
  const latestContext = useRef<RiskQueryContext | null>(queryContext);
  latestContext.current = queryContext;
  const requestId = useRef(0);
  const activeRequest = useRef<string | null>(null);
  const [storedResult, setResult] = useState<{ fingerprint: string; value: TerrainRiskResult } | null>(null);
  const result = storedResult?.fingerprint === queryContext?.fingerprint ? storedResult?.value ?? null : null;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<"saveError" | "queryError" | "">("");
  const [selectedKey, setSelectedKey] = useState<string>();
  const saved = readSavedCases().find((item) => item.id === workspace.caseId);
  const savedModel = useMemo(() => saved?.data.terrainReference ? buildStoredRiskEvidenceModel(saved.data.terrainReference, {
    stale: workspace.identity.state === "revalidation_required",
    checkedAt: saved.data.riskEvidenceCheckedAt ?? null,
  }) : null, [saved?.data.terrainReference, saved?.data.riskEvidenceCheckedAt, workspace.identity.state]);
  const freshModel = useMemo(() => result ? buildRiskEvidenceModel(result) : null, [result]);
  const model = freshModel ?? savedModel;
  const selectedRow = model?.rows.find((row) => row.key === selectedKey) ?? model?.rows[0];
  const coordinates = workspace.identity.anchor?.coordinates;


  useEffect(() => {
    requestId.current += 1;
    activeRequest.current = null;
    setResult(null); setError(""); setLoading(false);
  }, [queryContext?.fingerprint]);
  useEffect(() => () => { requestId.current += 1; activeRequest.current = null; }, []);
  useEffect(() => { setSelectedKey(defaultSelection(model)); }, [model]);

  async function refreshEvidence() {
    if (!queryContext || activeRequest.current === queryContext.fingerprint) return;
    const responseContext = queryContext;
    const responseId = ++requestId.current;
    activeRequest.current = responseContext.fingerprint;
    setLoading(true); setError("");
    try {
      const next = await api.terrainRiskAnalyze(responseContext.payload);
      const current = latestContext.current;
      if (requestId.current === responseId && current && canCommitRiskResponse(current, responseContext)) {
        const model = buildRiskEvidenceModel(next);
        const anchor = workspace.identity.anchor;
        if (anchor?.coordinates) {
          const persisted = await updateSavedCaseRiskEvidence(workspace.caseId, { ...buildStoredRiskEvidenceSnapshot(model), checked_at: model.freshness.checkedAt }, {
            journeyAnchorId: anchor.journey_anchor_id,
            normalizedAddress: anchor.normalized_address,
            coordinates: anchor.coordinates,
            snapshotVersion: workspace.storageVersion,
          }, () => {
            const latest = latestContext.current;
            return requestId.current === responseId && Boolean(latest && canCommitRiskResponse(latest, responseContext));
          });
          const latest = latestContext.current;
          if (requestId.current !== responseId || !latest || !canCommitRiskResponse(latest, responseContext)) return;
          if (!persisted) { setError("saveError"); return; }
        }
        setResult({ fingerprint: responseContext.fingerprint, value: next });
      }
    } catch {
      const current = latestContext.current;
      if (requestId.current === responseId && current && canCommitRiskResponse(current, responseContext)) setError("queryError");
    } finally {
      const current = latestContext.current;
      if (requestId.current === responseId && current && canCommitRiskResponse(current, responseContext)) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }

  const buyer = buildRiskBuyerModel(model);
  const c = riskBuyerCopy(locale);

  return <div className={styles.page}>
    <header className={styles.heading}>
      <h1 className="text-page">{c.title}</h1>
      <p className="text-body">{c.intro}</p>
    </header>

    <Panel className={styles.buyerSummary} data-testid="risk-buyer-summary">
      <h2 className="text-section">{riskBuyerSummary(buyer.verificationCount, locale)}</h2>
      <p className="text-body"><strong>{c.principle}</strong> · {c.caution}</p>
      <p className="text-meta">{c.countNote}</p>
      {model && <p className="text-meta">{c[model.freshness.status]} · {c.checked}: <span data-numeric>{formatEvidenceDate(model.freshness.checkedAt, formatDate, c.unknown)}</span></p>}
      <div className={styles.headingActions}>
        <CommercialButton size="touch" loading={loading} loadingLabel={c.loading} disabled={!queryContext} onClick={() => void refreshEvidence()}>{c.query}</CommercialButton>
        {!queryContext && <span className="text-helper" data-testid="risk-identity-gate">{identityConfirmationCopy[locale][identityConfirmationKind(workspace.identity) === "reconfirmation" ? "reconfirmationRisk" : "pendingRisk"]}</span>}
      </div>
    </Panel>

    {savedModel && !freshModel && <Message variant={workspace.identity.state === "revalidation_required" ? "warning" : "information"} title={c.savedTitle}>
      {workspace.identity.state === "revalidation_required" ? c.staleNotice : c.savedNotice}
    </Message>}
    {error && <Message variant="error" title={c.errorTitle} action={<CommercialButton variant="secondary" onClick={() => void refreshEvidence()}>{c.retry}</CommercialButton>}>{c[error]}</Message>}

    <Section title={c.cards} description={c.guidance}>
      <div className={styles.buyerGrid}>{buyer.cards.map((card) => <RiskBuyerCard key={card.key} card={card} />)}</div>
    </Section>

    <Message title={c.buildingTitle}>{c.buildingNote}</Message>

    {coordinates && <Section title={c.mapTitle} description={c.mapNote}>
      <MapFrame title={c.mapRegion} description={c.mapNote} attribution={c.mapAttribution}>
        <ExplicitMap key={`${workspace.caseId}:${coordinates.latitude}:${coordinates.longitude}`} kind="risk"><RiskEvidenceMap center={coordinates} radiusM={500} hazardGeometries={result?.hazard_geometries} selectedKey={selectedRow?.key} /></ExplicitMap>
      </MapFrame>
    </Section>}

    <DetailsDisclosure summary={c.details} data-testid="risk-details">
      <EvidenceTable model={model} selectedKey={selectedRow?.key} onSelect={setSelectedKey} />
      <p className="text-meta">{c.timeNote}</p>
    </DetailsDisclosure>

    {freshModel && coordinates && <SourceDetails key={`${workspace.caseId}|${queryContext?.fingerprint}`} result={result!} coordinates={coordinates} />}
  </div>;
}

function EvidenceTable({ model, selectedKey, onSelect }: { model: RiskEvidenceModel | null; selectedKey?: string; onSelect: (key: string) => void }) {
  const { locale, formatDate } = useExperienceLocale();
  const c = riskBuyerCopy(locale);
  return <Section title={c.table} description={c.tableNote}>
    {model?.rows.length ? <DataTable caption={c.table} regionLabel={c.table}><thead><tr>
      <DataTableHeader>{c.source} / {c.evidenceType}</DataTableHeader><DataTableHeader>{c.status}</DataTableHeader><DataTableHeader>{c.result}</DataTableHeader>
      <DataTableHeader>{c.coverage}</DataTableHeader><DataTableHeader>{c.version}</DataTableHeader><DataTableHeader>{c.sourceDetails}</DataTableHeader>
    </tr></thead><tbody>{model.rows.map((row) => <tr key={row.key}>
      <DataTableCell className={styles.sourceCell}><p className="text-meta">{row.sourceAgency ?? row.source}</p><button type="button" className={styles.tableButton} aria-pressed={row.key === selectedKey} onClick={() => onSelect(row.key)}>{row.key === "terrain" ? c.terrain : hazardBuyerCopy(row.key, locale).name}</button></DataTableCell>
      <DataTableCell><RowStatuses row={row} /></DataTableCell>
      <DataTableCell className={styles.resultCell}>{row.result}{row.categories && <ul className={styles.categoryList}>{row.categories.map((category) => <li key={`${category.official}-${category.canonical}`}>{category.official}</li>)}</ul>}</DataTableCell>
      <DataTableCell className={styles.metadataCell}>{c[row.coverage]}</DataTableCell>
      <DataTableCell className={styles.metadataCell}>{row.datasetVersion ?? formatEvidenceDate(row.effectivePeriod, formatDate, c.unknown, "source")}</DataTableCell>
      <DataTableCell className={styles.resultCell}><DetailsDisclosure summary={c.sourceDetails}><RiskSourceEvidence row={row} checkedAt={model.freshness.checkedAt} /></DetailsDisclosure></DataTableCell>
    </tr>)}</tbody></DataTable> : <Message title={c.not_queried}>{c.preQuery}</Message>}
  </Section>;
}

function SourceDetails({ result, coordinates }: { result: TerrainRiskResult; coordinates: { latitude: number; longitude: number } }) {
  const { locale } = useExperienceLocale();
  const c = riskBuyerCopy(locale);
  const [satelliteOpen, setSatelliteOpen] = useState(false);
  return <Section>
    <DetailsDisclosure summary={c.methods}>
      <p className="text-meta">{c.sourceOriginal}</p>
      <pre className={styles.sourceRecords} data-testid="risk-source-records">{JSON.stringify({
        official_data_sources: result.official_data_sources,
        source_transparency: result.source_transparency,
        input: result.input,
        sources: { terrain: result.terrain.source, ...Object.fromEntries(Object.entries(result.hazards).map(([key, hazard]) => [key, hazard.source])) },
      }, null, 2)}</pre>
    </DetailsDisclosure>
    <DetailsDisclosure summary={c.satellite} onToggle={(event) => setSatelliteOpen(event.currentTarget.open)}><div className={styles.supportingEvidence}>{satelliteOpen && <SatelliteEvidence coordinate={{ ...coordinates, accepted: true }} />}</div></DetailsDisclosure>
  </Section>;
}
