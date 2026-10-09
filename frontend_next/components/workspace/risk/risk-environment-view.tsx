"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { SatelliteEvidence } from "@/components/satellite-evidence";
import { CommercialButton } from "@/components/design-system/button";
import { DataTable, DataTableCell, DataTableHeader } from "@/components/design-system/data-table";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { MapFrame } from "@/components/design-system/map-frame";
import { Message } from "@/components/design-system/message";
import { EvidenceSection, Panel, Section } from "@/components/design-system/section";
import { StatusLabel } from "@/components/design-system/status-label";
import { MetricItem, SummaryStrip } from "@/components/design-system/summary-strip";
import { useWorkspace } from "@/components/workspace/workspace-provider";
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
import { riskSummaryCounts } from "@/lib/workspace/risk-presentation";
import styles from "./risk-environment.module.css";

const UNKNOWN_USABILITY = new Set(["limited", "unavailable", "stale", "unsupported", "no_coverage"]);
const when = (value: string | null | undefined) => value || "未提供";
const defaultSelection = (model: RiskEvidenceModel | null) => model?.rows.find((row) => row.matched)?.key ?? model?.rows[0]?.key;
const evidenceContract = (row: RiskEvidenceRow) => resolveCommercialState("evidence", row.usability);
const riskContract = (row: RiskEvidenceRow) => resolveCommercialState("risk", row.interpretation);

function RowStatuses({ row }: { row: RiskEvidenceRow }) {
  const evidence = evidenceContract(row);
  const risk = riskContract(row);
  return <div className={styles.statusStack}>
    <StatusLabel semanticRole={evidence.role}>{evidence.label["zh-TW"]}</StatusLabel>
    <StatusLabel semanticRole={risk.role}>{risk.label["zh-TW"]}</StatusLabel>
  </div>;
}

export function RiskEnvironmentView() {
  const workspace = useWorkspace();
  const queryContext = useMemo(() => buildRiskQueryContext(workspace), [workspace]);
  const latestContext = useRef<RiskQueryContext | null>(queryContext);
  latestContext.current = queryContext;
  const requestId = useRef(0);
  const activeRequest = useRef<string | null>(null);
  const [storedResult, setResult] = useState<{ fingerprint: string; value: TerrainRiskResult } | null>(null);
  const result = storedResult?.fingerprint === queryContext?.fingerprint ? storedResult?.value ?? null : null;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
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
  const summaryCounts = riskSummaryCounts(model);

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
          updateSavedCaseRiskEvidence(workspace.caseId, { ...buildStoredRiskEvidenceSnapshot(model), checked_at: model.freshness.checkedAt }, {
            journeyAnchorId: anchor.journey_anchor_id,
            normalizedAddress: anchor.normalized_address,
            coordinates: anchor.coordinates,
          });
        }
        setResult({ fingerprint: responseContext.fingerprint, value: next });
      }
    } catch {
      const current = latestContext.current;
      if (requestId.current === responseId && current && canCommitRiskResponse(current, responseContext)) setError("目前無法完成風險證據查詢；已保留其他可用內容，請稍後重試。");
    } finally {
      const current = latestContext.current;
      if (requestId.current === responseId && current && canCommitRiskResponse(current, responseContext)) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }

  const unknownRows = model?.rows.filter((row) => row.interpretation === "unknown" || UNKNOWN_USABILITY.has(row.usability)) ?? [];

  return <div className={styles.page}>
    <header className={styles.heading}>
      <h1 className="text-page">風險與環境</h1>
      <p className="text-body">在繼續評估此物件前，哪些環境或災害證據需要查證？</p>
      <p className="text-meta">本頁提供逐項證據與待確認事項，不回答物件是否安全，也不形成購買建議。</p>
      <div className={styles.headingActions}>
        <CommercialButton size="touch" loading={loading} loadingLabel="查詢中" disabled={!queryContext} onClick={() => void refreshEvidence()}>查詢目前物件風險證據</CommercialButton>
        {!queryContext && <span className="text-helper">物件資料已變更，需重新確認後再查詢。</span>}
      </div>
    </header>

    <Section title="重要風險證據" description="摘要只計數已符合的來源證據與仍未知的項目，不合併成安全分數。">
      <SummaryStrip label="風險證據摘要">
        <MetricItem label="符合來源定義" value={summaryCounts.material} unit={model ? "項" : undefined} note="逐項判讀，不跨圖層比較嚴重度" />
        <MetricItem label="未知／無法取得" value={summaryCounts.unknown} unit={model ? "項" : undefined} note="保持可見，待後續查證" />
        <MetricItem label="證據時間" value={when(model?.freshness.checkedAt)} note={freshModel ? "本次查詢" : savedModel ? "已儲存摘要" : "尚未查詢"} />
      </SummaryStrip>
      {savedModel && !freshModel && <Message variant={workspace.identity.state === "revalidation_required" ? "warning" : "information"} title="已儲存的摘要證據">
        {workspace.identity.state === "revalidation_required" ? "此摘要屬於先前物件狀態，不能作為目前證據。" : "需重新查詢才能檢視完整結果；摘要不會被重建成即時證據。"}
      </Message>}
      {error && <Message variant="error" title="查詢未完成" action={<CommercialButton variant="secondary" onClick={() => void refreshEvidence()}>重試此項查詢</CommercialButton>}>{error}</Message>}
    </Section>

    <EvidenceTable model={model} selectedKey={selectedRow?.key} onSelect={setSelectedKey} />

    {coordinates && <Section title="風險／環境地圖" description="位置、查詢半徑與來源提供的幾何是分析脈絡，不以裝飾漸層推測風險。">
      <div className={styles.mapGrid}>
        <MapFrame title="風險與環境圖" description="物件位置、500 公尺查詢範圍與可用證據圖層" attribution="OpenStreetMap；其他圖層依各證據來源" detail={<span>點位／半徑不等於地籍或工程界線</span>}>
          <RiskEvidenceMap center={coordinates} radiusM={500} hazardGeometries={result?.hazard_geometries} selectedKey={selectedRow?.key} />
        </MapFrame>
        <Panel className={styles.mapDetail} aria-live="polite">
          <h3 className="text-subsection">選取證據詳情</h3>
          {selectedRow ? <><RowStatuses row={selectedRow} /><dl>
            <div><dt>證據</dt><dd>{selectedRow.label}</dd></div><div><dt>結果</dt><dd>{selectedRow.result}</dd></div>
            <div><dt>重要限制</dt><dd>{selectedRow.limitation}</dd></div><div><dt>下一步</dt><dd>{selectedRow.nextVerification}</dd></div>
          </dl></> : <p className="text-body">尚未有可選取的證據列。</p>}
        </Panel>
      </div>
    </Section>}

    <UnknownEvidence rows={unknownRows} />
    <VerificationActions actions={model?.verificationActions ?? []} />

    <Section title="證據時間">
      <p className="text-body">最後查詢／保存時間：<span data-numeric>{when(model?.freshness.checkedAt)}</span></p>
      <p className="text-meta">來源有效期間以證據表為準；查詢時間不等於資料發布時間。</p>
    </Section>

    {freshModel && coordinates && <SourceDetails key={`${workspace.caseId}|${queryContext?.fingerprint}`} model={freshModel} result={result!} coordinates={coordinates} />}
  </div>;
}

function EvidenceTable({ model, selectedKey, onSelect }: { model: RiskEvidenceModel | null; selectedKey?: string; onSelect: (key: string) => void }) {
  return <Section title="證據表" description="各圖層保留自己的來源分類與限制；查詢完成不等於風險較低。">
    {model?.rows.length ? <DataTable caption="風險證據表" regionLabel="風險證據表"><thead><tr>
      <DataTableHeader>來源／證據類型</DataTableHeader><DataTableHeader>狀態</DataTableHeader><DataTableHeader>結果</DataTableHeader>
      <DataTableHeader>涵蓋範圍</DataTableHeader><DataTableHeader>有效期間／版本</DataTableHeader><DataTableHeader>限制與下一步</DataTableHeader>
    </tr></thead><tbody>{model.rows.map((row) => <tr key={row.key}>
      <DataTableCell className={styles.sourceCell}><p className="text-meta">{row.sourceAgency ?? row.source}</p><button type="button" className={styles.tableButton} aria-pressed={row.key === selectedKey} onClick={() => onSelect(row.key)}>{row.label}</button></DataTableCell>
      <DataTableCell><RowStatuses row={row} /></DataTableCell>
      <DataTableCell className={styles.resultCell}>{row.result}{row.categories && <ul className={styles.categoryList}>{row.categories.map((category) => <li key={`${category.official}-${category.canonical}`}>{category.official}</li>)}</ul>}</DataTableCell>
      <DataTableCell className={styles.metadataCell}>{row.coverage === "covered" ? "本次範圍已涵蓋" : row.coverage === "not_covered" ? "不在涵蓋範圍" : "涵蓋狀態未知"}</DataTableCell>
      <DataTableCell className={styles.metadataCell}>{row.datasetVersion ?? row.effectivePeriod}</DataTableCell>
      <DataTableCell className={styles.resultCell}>{row.limitation}<br /><strong>{row.nextVerification}</strong></DataTableCell>
    </tr>)}</tbody></DataTable> : <Message title="尚未查詢風險證據">確認目前物件後，使用上方按鈕查詢各項來源；未查詢不代表沒有風險。</Message>}
  </Section>;
}

function UnknownEvidence({ rows }: { rows: RiskEvidenceRow[] }) {
  return <Section title="未知或目前無法取得" description="缺少、未涵蓋、過期或不支援的項目不會被隱藏。"><EvidenceSection>
    <div className={styles.unknownList}>{rows.length ? rows.map((row) => <div className={styles.unknownItem} key={row.key}><strong>{row.label}</strong><p>{row.result}</p><p>{row.limitation}</p></div>) : <p className="text-body">目前沒有額外未知項目；仍應依證據限制完成現場與官方查證。</p>}</div>
  </EvidenceSection></Section>;
}

function VerificationActions({ actions }: { actions: string[] }) {
  const visible = actions.length ? actions : ["確認物件身分與座標後，逐項查詢官方風險來源。"];
  return <Section title="下一步查證" description="以下是來源與現場查證行動，不是購買或投資建議。"><ol className={styles.actionList}>
    {visible.map((action, index) => <li className={styles.actionItem} key={action}><strong>{index + 1}.</strong> {action}</li>)}
  </ol></Section>;
}

function SourceDetails({ model, result, coordinates }: { model: RiskEvidenceModel; result: TerrainRiskResult; coordinates: { latitude: number; longitude: number } }) {
  const [satelliteOpen, setSatelliteOpen] = useState(false);
  return <Section title="方法與輔助證據">
    <DetailsDisclosure summary="來源與方法詳情"><div className={styles.sourceList}>
      {model.rows.map((row) => <div className={styles.sourceItem} key={row.key}>
        <strong>{row.label}：{row.source}</strong>
        <p>涵蓋：{row.coverage === "covered" ? "本次查詢範圍已涵蓋" : row.coverage === "not_covered" ? "不在涵蓋範圍" : "涵蓋狀態未知"}；有效期間／版本：{row.datasetVersion ?? row.effectivePeriod}</p>
        <p>{row.limitation}</p>
        {row.sourceUrl && <a className="ds-button ds-button--tertiary" href={row.sourceUrl} target="_blank" rel="noreferrer">查看官方來源</a>}
      </div>)}
      {result.official_data_sources?.map((source) => <div className={styles.sourceItem} key={`${source.agency}-${source.dataset_name}`}>
        <strong>{source.dataset_name}</strong><p>{source.agency}；涵蓋：{source.coverage}；發布版本：{source.published_version ?? "未設定"}；生效日：{source.effective_date ?? "未提供"}</p><p>{source.limitation_summary}</p>
      </div>)}
    </div></DetailsDisclosure>
    <DetailsDisclosure summary="衛星影像參考（輔助證據）" onToggle={(event) => setSatelliteOpen(event.currentTarget.open)}><div className={styles.supportingEvidence}>{satelliteOpen && <SatelliteEvidence coordinate={{ ...coordinates, accepted: true }} />}</div></DetailsDisclosure>
  </Section>;
}
