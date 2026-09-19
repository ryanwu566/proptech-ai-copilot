"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import type { PropertyDTO, PropertyEvidenceDTO, PropertyGraphDTO } from "@/lib/vnext-identity-contract";
import { VNextContractError } from "@/lib/vnext-identity-contract";
import {
  VNextApiError, VNextOutcomeUnknownError, VNextSessionError, newIdempotencyKey,
  type vnextIdentityClient,
} from "@/lib/vnext-identity-client";
import type { BuildingComponents, ParcelComponents } from "@/lib/vnext-manual-identity";
import styles from "./property-identity-review.module.css";

export type PropertyIdentityReviewApi = Pick<typeof vnextIdentityClient,
  "graphByStatus" | "evidence" | "createParcelHypothesis" | "createBuildingHypothesis" | "createParcelBuildingRelation">;

type GraphStatus = "confirmed" | "disputed" | "proposed";
type Reference = { id: string; label: string; kind: "parcel" | "building" };
type Attempt = { fingerprint: string; key: string };
type Command = "parcel" | "building" | "relation";
type GraphPages = Record<GraphStatus, PropertyGraphDTO[]>;

const initialGraph: GraphPages = { confirmed: [], disputed: [], proposed: [] };
const emptyParcel: ParcelComponents = { county_city: "", district_township: "", section: "", subsection: null, land_number: "" };
const emptyBuilding: BuildingComponents = {
  county_city: "", district_township: "", section: "", subsection_status: "not_applicable", subsection: null, building_number: "",
};

function statusLabel(status: PropertyGraphDTO["relations"][number]["status"], sourceType: string): string {
  if (status === "confirmed") return "已確認關係（人工確認；非官方地籍證明）";
  if (status === "disputed") return "有爭議 · 需再查證";
  if (status === "proposed") return `待確認 · proposed · ${sourceType === "user" ? "手動輸入 · " : ""}未驗證 · 非官方地籍確認`;
  return status === "rejected" ? "已排除關係" : "已由其他關係取代";
}

function sourceLabel(sourceType: string): string {
  if (sourceType === "user") return "使用者提供";
  if (sourceType === "official") return "官方來源";
  if (sourceType === "partner") return "合作來源";
  if (sourceType === "document") return "文件";
  if (sourceType === "demo" || sourceType === "test") return "示範或測試來源";
  if (sourceType === "deterministic") return "系統推定";
  return "其他來源";
}

function evidenceLabel(status: string): string {
  if (status === "user_provided") return "使用者提供 · 未驗證";
  if (status === "unverified") return "未驗證";
  if (status === "available") return "可查閱";
  if (status === "limited") return "資料有限";
  if (status === "conflicting") return "有衝突";
  if (status === "stale") return "可能過期";
  return "目前不可用或狀態未知";
}

function referenceStatusLabel(status: string | null): string {
  if (status === "unverified") return "參照本身未驗證";
  if (status === "disputed") return "參照本身有爭議";
  if (status === "rejected") return "參照已排除";
  if (status === "superseded") return "參照已被取代";
  if (status === "limited") return "參照資料有限";
  return "參照已記錄，仍須查證來源";
}

function readableError(caught: unknown, reading = false): string {
  if (caught instanceof VNextOutcomeUnknownError) return reading ? "載入失敗，請重試。" : "送出結果尚未確定。請重試；系統會沿用同一請求識別碼。";
  if (caught instanceof VNextSessionError) return "目前沒有可用的登入工作階段。";
  if (caught instanceof VNextContractError) return "資料格式無法確認，請重新載入後再試。";
  if (caught instanceof VNextApiError) {
    if (caught.code === "permission_denied") return "此工作空間沒有新增權限。";
    if (caught.code === "conflicting_evidence" || caught.code === "idempotency_conflict") return "已有相同或衝突的資料，請重新載入確認。";
    if (caught.code === "validation_failed") return "輸入格式不符，請檢查地號或建號。";
    return `操作失敗（${caught.code}；參照 ${caught.requestId}）。`;
  }
  return "載入失敗或操作未完成，請重試。";
}

type ReviewProps = {
  property: PropertyDTO;
  role: "owner" | "admin" | "manager" | "member" | "viewer";
  api: PropertyIdentityReviewApi;
  preview?: boolean;
};

export function PropertyIdentityReview(props: ReviewProps) {
  return <PropertyIdentityReviewContent key={`${props.property.workspace_id}:${props.property.property_entity_id}`} {...props} />;
}

function PropertyIdentityReviewContent({ property, role, api, preview = false }: ReviewProps) {
  const propertyId = property.property_entity_id;
  const workspaceId = property.workspace_id;
  const canWrite = role !== "viewer" && property.lifecycle_state !== "archived";
  const attempts = useRef<Partial<Record<Command, Attempt>>>({});
  const [graph, setGraph] = useState<GraphPages>(initialGraph);
  const [evidencePages, setEvidencePages] = useState<PropertyEvidenceDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [proposedLoaded, setProposedLoaded] = useState(false);
  const [showProposed, setShowProposed] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [parcel, setParcel] = useState<ParcelComponents>(emptyParcel);
  const [building, setBuilding] = useState<BuildingComponents>(emptyBuilding);
  const [parcelResult, setParcelResult] = useState<string | null>(null);
  const [buildingResult, setBuildingResult] = useState<string | null>(null);
  const [relationResult, setRelationResult] = useState(false);
  const [createdRefs, setCreatedRefs] = useState<Reference[]>([]);
  const [parcelRef, setParcelRef] = useState("");
  const [buildingRef, setBuildingRef] = useState("");

  const checkPage = useCallback((page: PropertyGraphDTO | PropertyEvidenceDTO) => {
    if (page.property.property_entity_id !== propertyId || page.property.workspace_id !== workspaceId) {
      throw new VNextContractError("review.property");
    }
  }, [propertyId, workspaceId]);

  const reload = useCallback(async () => {
    setLoading(true); setError(null);
    setLoaded(false); setGraph(initialGraph); setEvidencePages([]); setShowProposed(false); setProposedLoaded(false);
    try {
      const [confirmed, disputed, evidence] = await Promise.all([
        api.graphByStatus(propertyId, "confirmed"),
        api.graphByStatus(propertyId, "disputed"),
        api.evidence(propertyId),
      ]);
      checkPage(confirmed); checkPage(disputed); checkPage(evidence);
      setGraph({ confirmed: [confirmed], disputed: [disputed], proposed: [] });
      setEvidencePages([evidence]);
      setShowProposed(false); setProposedLoaded(false); setLoaded(true);
    } catch (caught: unknown) { setError(readableError(caught, true)); }
    finally { setLoading(false); }
  }, [api, checkPage, propertyId]);

  useEffect(() => { void reload(); }, [reload]);

  async function toggleProposed(checked: boolean) {
    setShowProposed(checked);
    if (!checked || proposedLoaded) return;
    setBusy("proposed"); setError(null);
    try {
      const page = await api.graphByStatus(propertyId, "proposed");
      checkPage(page);
      setGraph((current) => ({ ...current, proposed: [page] }));
      setProposedLoaded(true);
    } catch (caught: unknown) { setError(readableError(caught, true)); }
    finally { setBusy(null); }
  }

  async function loadMoreGraph(status: GraphStatus) {
    const cursor = graph[status].at(-1)?.next_cursor;
    if (!cursor || busy) return;
    setBusy(`graph-${status}`); setError(null);
    try {
      const page = await api.graphByStatus(propertyId, status, cursor);
      checkPage(page);
      setGraph((current) => ({ ...current, [status]: [...current[status], page] }));
    } catch (caught: unknown) { setError(readableError(caught, true)); }
    finally { setBusy(null); }
  }

  async function loadMoreEvidence() {
    const cursor = evidencePages.at(-1)?.next_cursor;
    if (!cursor || busy) return;
    setBusy("evidence"); setError(null);
    try {
      const page = await api.evidence(propertyId, cursor);
      checkPage(page);
      setEvidencePages((current) => [...current, page]);
    } catch (caught: unknown) { setError(readableError(caught, true)); }
    finally { setBusy(null); }
  }

  async function command<T>(kind: Command, fingerprint: string, send: (key: string) => Promise<T>, saved: (value: T) => void) {
    if (busy || !canWrite) return;
    const prior = attempts.current[kind];
    const attempt = prior?.fingerprint === fingerprint ? prior : { fingerprint, key: newIdempotencyKey(kind) };
    attempts.current[kind] = attempt;
    setBusy(kind); setError(null); setNotice(null);
    try {
      const result = await send(attempt.key);
      saved(result);
      delete attempts.current[kind];
      setNotice("已記錄為待確認假設；這不是官方確認結果。");
      try {
        const [newEvidence, newProposed] = await Promise.all([
          api.evidence(propertyId),
          showProposed ? api.graphByStatus(propertyId, "proposed") : Promise.resolve(null),
        ]);
        checkPage(newEvidence);
        setEvidencePages([newEvidence]);
        if (newProposed) {
          checkPage(newProposed);
          setGraph((current) => ({ ...current, proposed: [newProposed] }));
          setProposedLoaded(true);
        }
      } catch { setError("已儲存，但無法更新關係與證據；請重新載入。"); }
    } catch (caught: unknown) {
      if (!(caught instanceof VNextOutcomeUnknownError || caught instanceof VNextContractError)) delete attempts.current[kind];
      setError(readableError(caught));
    } finally { setBusy(null); }
  }

  function saveParcel(event: FormEvent) {
    event.preventDefault();
    const fingerprint = JSON.stringify({ propertyId, workspaceId, parcel });
    void command("parcel", fingerprint,
      (key) => api.createParcelHypothesis(propertyId, workspaceId, parcel, key),
      (result) => {
        setParcelResult(result.display_value);
        setCreatedRefs((current) => [...current, { id: result.identity_reference_id, label: result.display_value, kind: "parcel" }]);
      });
  }

  function saveBuilding(event: FormEvent) {
    event.preventDefault();
    const fingerprint = JSON.stringify({ propertyId, workspaceId, building });
    void command("building", fingerprint,
      (key) => api.createBuildingHypothesis(propertyId, workspaceId, building, key),
      (result) => {
        setBuildingResult(result.display_value);
        setCreatedRefs((current) => [...current, { id: result.identity_reference_id, label: result.display_value, kind: "building" }]);
      });
  }

  function saveRelation(event: FormEvent) {
    event.preventDefault();
    if (!parcelRef || !buildingRef || !parcelRefs.some((ref) => ref.id === parcelRef) || !buildingRefs.some((ref) => ref.id === buildingRef)) return;
    const fingerprint = JSON.stringify({ workspaceId, parcelRef, buildingRef });
    void command("relation", fingerprint,
      (key) => api.createParcelBuildingRelation(workspaceId, parcelRef, buildingRef, key),
      () => setRelationResult(true));
  }

  const visibleStatuses: GraphStatus[] = showProposed ? ["confirmed", "disputed", "proposed"] : ["confirmed", "disputed"];
  const pages = visibleStatuses.flatMap((status) => graph[status]);
  const nodes = useMemo(() => new Map(pages.flatMap((page) => page.nodes.map((node) => [node.node_id, node] as const))), [pages]);
  const graphRelations = visibleStatuses.flatMap((status) => graph[status].flatMap((page) => page.relations));
  const propertyNodeIds = new Set([...nodes.values()].filter((node) => node.node_type === "property" && node.record_id === propertyId).map((node) => node.node_id));
  const referenceRows = graphRelations.filter((relation) => {
    const expectedNodeType = relation.relation_type === "property_parcel" ? "parcel" : relation.relation_type === "property_building" ? "building" : null;
    if (!expectedNodeType) return false;
    return (propertyNodeIds.has(relation.from_node_id) && nodes.get(relation.to_node_id)?.node_type === expectedNodeType)
      || (propertyNodeIds.has(relation.to_node_id) && nodes.get(relation.from_node_id)?.node_type === expectedNodeType);
  });
  const referenceNodeIds = new Set(referenceRows.map((relation) => propertyNodeIds.has(relation.from_node_id) ? relation.to_node_id : relation.from_node_id));
  const bridgeRows = graphRelations.filter((relation) => relation.relation_type === "parcel_building"
    && referenceNodeIds.has(relation.from_node_id) && referenceNodeIds.has(relation.to_node_id));
  const visibleRelations = [...referenceRows, ...bridgeRows];
  const graphRefs: Reference[] = referenceRows.flatMap((relation) => {
    const nodeId = propertyNodeIds.has(relation.from_node_id) ? relation.to_node_id : relation.from_node_id;
    const node = nodes.get(nodeId);
    return node && (node.node_type === "parcel" || node.node_type === "building")
      ? [{ id: node.record_id, label: node.display_label, kind: node.node_type }] : [];
  });
  const availableReferences = [...new Map([...graphRefs, ...createdRefs].map((ref) => [ref.id, ref] as const)).values()];
  const parcelRefs = availableReferences.filter((ref) => ref.kind === "parcel");
  const buildingRefs = availableReferences.filter((ref) => ref.kind === "building");
  const evidence = evidencePages.flatMap((page) => page.evidence);

  return <main className={styles.page}>
    <header className={styles.hero}>
      <p className={styles.kicker}>PROPERTY IDENTITY / REVIEW</p>
      <h1>這筆房產的地籍身分</h1>
      <p>先看可查到的地號與地籍建號參照，再補充您的線索。手動輸入只會建立待確認假設。</p>
      {preview && <strong className={styles.preview}>示範資料，非真實地籍結果</strong>}
    </header>

    {error && <div role="alert" className={styles.error}>{error} <button type="button" onClick={() => void reload()}>重新載入</button></div>}
    {notice && <p role="status" className={styles.notice}>{notice}</p>}
    {loading && <p role="status" className={styles.loading}>正在載入地籍關係與證據摘要…</p>}

    <section className={styles.panel} data-testid="identity-status-summary" aria-labelledby="identity-summary-heading">
      <div className={styles.sectionTitle}><div><p className={styles.step}>01 / 目前狀態</p><h2 id="identity-summary-heading">房產身分摘要</h2></div><span className={styles.tag}>{property.lifecycle_state === "disputed" ? "房產身分有爭議" : property.confirmation_summary.human_confirmed ? "PropertyEntity 已人工確認" : "PropertyEntity 尚未確認"}</span></div>
      <p className={styles.propertyName}>{property.display_label}</p>
      <p className={styles.muted}>PropertyEntity 是這筆房產的工作空間紀錄；它的人工確認不會自動確認下列地號或建號。</p>
      <div className={styles.metrics}>
        <div><strong data-testid="confirmed-count">{visibleRelations.filter((relation) => relation.status === "confirmed").length}</strong><span>已載入的已確認關係</span></div>
        <div><strong>{visibleRelations.filter((relation) => relation.status === "disputed").length}</strong><span>已載入的有爭議關係</span></div>
        <div><strong>{showProposed ? visibleRelations.filter((relation) => relation.status === "proposed").length : "—"}</strong><span>已載入的待確認關係{showProposed ? "" : "（已隱藏）"}</span></div>
        <div><strong data-testid="evidence-count">{evidence.length}</strong><span>可見證據摘要</span></div>
      </div>
      <details><summary>查看紀錄識別碼與確認來源</summary><p>PropertyEntity ID：{propertyId}</p><p>工作空間 ID：{workspaceId}</p><p>房產確認時間：{property.confirmation_summary.confirmed_at ?? "無"}</p></details>
    </section>

    <section className={styles.panel} aria-labelledby="graph-heading">
      <div className={styles.sectionTitle}><div><p className={styles.step}>02 / 關係檢視</p><h2 id="graph-heading">地號、建號與關係</h2></div><label className={styles.toggle}><input type="checkbox" checked={showProposed} disabled={loading || busy !== null} onChange={(event) => void toggleProposed(event.target.checked)} />顯示待確認關係</label></div>
      <p className={styles.muted}>已確認表示系統中的人工確認；正式地籍仍須向主管機關或授權來源查證。</p>
      {loaded && visibleRelations.length === 0 && <p className={styles.empty}>{showProposed ? "目前沒有可顯示的地籍關係" : "目前沒有已確認或有爭議的地籍關係"}</p>}
      {busy === "proposed" && <p role="status">正在載入待確認關係…</p>}
      {referenceRows.length > 0 && <div className={styles.referenceGrid}>{referenceRows.map((relation) => {
        const node = nodes.get(propertyNodeIds.has(relation.from_node_id) ? relation.to_node_id : relation.from_node_id);
        return <article key={relation.relation_id} className={`${styles.relationCard} ${styles[relation.status]}`} data-testid={relation.status === "proposed" ? "proposed-relation" : "identity-reference-row"}>
          <p className={styles.cardType}>{relation.relation_type === "property_parcel" ? "地號參照" : "地籍建號參照"}</p>
          <h3>{node?.display_label ?? "參照資料暫不可讀"}</h3>
          <strong>{statusLabel(relation.status, relation.source.source_type)}</strong>
          <p>{referenceStatusLabel(node?.status ?? null)}</p>
          <p>來源：{sourceLabel(relation.source.source_type)} · 證據{relation.evidence_id ? "可追溯" : "未附"}</p>
          <details><summary>識別碼與資料來源</summary><p>參照 ID：{node?.record_id ?? "未知"}</p><p>來源：{relation.source.source_id}</p><p>關係 ID：{relation.relation_id}</p><p>證據 ID：{relation.evidence_id ?? "未附"}</p></details>
        </article>;
      })}</div>}
      {bridgeRows.map((relation) => <article key={relation.relation_id} className={`${styles.relationCard} ${styles[relation.status]}`} data-testid={relation.status === "proposed" ? "proposed-relation" : undefined}>
        <p className={styles.cardType}>地號 ↔ 地籍建號</p><h3>雙向關係</h3><strong>{statusLabel(relation.status, relation.source.source_type)}</strong>
        <p>{nodes.get(relation.from_node_id)?.display_label ?? "地號"} ↔ {nodes.get(relation.to_node_id)?.display_label ?? "建號"}</p>
        <details><summary>識別碼與資料來源</summary><p>關係 ID：{relation.relation_id}</p><p>來源：{relation.source.source_id}</p><p>證據 ID：{relation.evidence_id ?? "未附"}</p></details>
      </article>)}
      {visibleStatuses.map((status) => graph[status].at(-1)?.next_cursor && <button key={status} type="button" className={styles.secondary} disabled={busy !== null} onClick={() => void loadMoreGraph(status)}>載入更多{status === "proposed" ? "待確認" : status === "disputed" ? "爭議" : "已確認"}關係</button>)}
    </section>

    <section className={styles.panel} aria-labelledby="evidence-heading">
      <p className={styles.step}>03 / 依據</p><h2 id="evidence-heading">資料與證據</h2>
      <p className={styles.muted}>來源與可用狀態供您判斷；原始資料及私人內容不會在此展開。</p>
      {loaded && evidence.length === 0 && <p className={styles.empty}>目前沒有可顯示的證據摘要</p>}
      {evidence.map((item) => <article key={item.evidence_id} className={styles.evidence}>
        <strong>{sourceLabel(item.source.source_type)} · {evidenceLabel(item.status)}</strong>
        <span>涵蓋狀態：{item.coverage_status === "known" ? "已知" : item.coverage_status === "partial" ? "部分" : "未知或不可用"} · 品質：{item.quality_status === "passed" ? "已檢查" : item.quality_status === "failed" ? "檢查未通過" : item.quality_status === "limited" ? "檢查有限" : "尚未檢查"}</span>
        <details><summary>查看來源與時間</summary><p>資料類型：{item.fact_type}</p><p>來源：{item.source.source_id}</p><p>取得時間：{item.source.retrieved_at ?? "未知"}</p><p>證據 ID：{item.evidence_id}</p></details>
      </article>)}
      {evidencePages.at(-1)?.next_cursor && <button type="button" className={styles.secondary} disabled={busy !== null} onClick={() => void loadMoreEvidence()}>載入更多證據</button>}
    </section>

    <section className={styles.panel} aria-labelledby="manual-heading">
      <p className={styles.step}>04 / 補充線索</p><h2 id="manual-heading">手動提出地籍假設</h2>
      <p className={styles.caution}>手動輸入 · 未驗證 · proposed · 非官方確認結果。送出不會把這些資料變成已確認或官方資料。</p>
      {!canWrite && <p className={styles.empty}>此工作空間角色只能檢視，無法新增假設。</p>}
      <div className={styles.formGrid}>
        <form onSubmit={saveParcel} className={styles.formCard}>
          <h3>可能的地號</h3><p>填入地籍地號組件，作為這筆房產的待確認參照。</p>
          <label>縣市（地號）<input required maxLength={160} value={parcel.county_city} onChange={(e) => setParcel({ ...parcel, county_city: e.target.value })} /></label>
          <label>鄉鎮市區（地號）<input required maxLength={160} value={parcel.district_township} onChange={(e) => setParcel({ ...parcel, district_township: e.target.value })} /></label>
          <label>段（地號）<input required maxLength={160} value={parcel.section} onChange={(e) => setParcel({ ...parcel, section: e.target.value })} /></label>
          <label>小段（地號，可留空）<input maxLength={160} value={parcel.subsection ?? ""} onChange={(e) => setParcel({ ...parcel, subsection: e.target.value || null })} /></label>
          <label>地號<input required maxLength={160} value={parcel.land_number} onChange={(e) => setParcel({ ...parcel, land_number: e.target.value })} /></label>
          <button type="submit" data-testid="submit-parcel" disabled={!canWrite || busy !== null}>記錄地號假設</button>
          {parcelResult && <p data-testid="parcel-result" className={styles.result}>手動輸入 · 未驗證 · proposed · 非官方確認結果<br />{parcelResult}</p>}
        </form>
        <form onSubmit={saveBuilding} className={styles.formCard}>
          <h3>可能的地籍建號</h3><p>地籍建號不等於實體建物、社區、戶別或刊登物件</p>
          <label>縣市（建號）<input required maxLength={160} value={building.county_city} onChange={(e) => setBuilding({ ...building, county_city: e.target.value })} /></label>
          <label>鄉鎮市區（建號）<input required maxLength={160} value={building.district_township} onChange={(e) => setBuilding({ ...building, district_township: e.target.value })} /></label>
          <label>段（建號）<input required maxLength={160} value={building.section} onChange={(e) => setBuilding({ ...building, section: e.target.value })} /></label>
          <label>小段狀態<select value={building.subsection_status} onChange={(e) => setBuilding({ ...building, subsection_status: e.target.value as BuildingComponents["subsection_status"], subsection: null })}><option value="not_applicable">無小段</option><option value="specified">有小段</option></select></label>
          {building.subsection_status === "specified" && <label>小段（建號）<input required maxLength={160} value={building.subsection ?? ""} onChange={(e) => setBuilding({ ...building, subsection: e.target.value })} /></label>}
          <label>建號<input required maxLength={160} value={building.building_number} onChange={(e) => setBuilding({ ...building, building_number: e.target.value })} /></label>
          <button type="submit" data-testid="submit-building" disabled={!canWrite || busy !== null}>記錄地籍建號假設</button>
          {buildingResult && <p data-testid="building-result" className={styles.result}>地籍建號 · 手動輸入 · 未驗證 · proposed · 非官方確認結果<br />{buildingResult}</p>}
        </form>
      </div>
    </section>

    <section className={styles.panel} aria-labelledby="relation-heading">
      <p className={styles.step}>05 / 連結線索</p><h2 id="relation-heading">這筆地號可能對應哪個建號？</h2>
      <p className={styles.caution}>只可選擇已存在的地號與地籍建號參照。新增後是雙向、未驗證手動關係 · proposed · 非官方地籍確認。</p>
      <form onSubmit={saveRelation} className={styles.relationForm}>
        <label>既有地號參照<select required value={parcelRef} onChange={(e) => setParcelRef(e.target.value)}><option value="">請選擇</option>{parcelRefs.map((ref) => <option value={ref.id} key={ref.id}>{ref.label}</option>)}</select></label>
        <span aria-hidden="true" className={styles.linkSymbol}>↔</span>
        <label>既有建號參照<select required value={buildingRef} onChange={(e) => setBuildingRef(e.target.value)}><option value="">請選擇</option>{buildingRefs.map((ref) => <option value={ref.id} key={ref.id}>{ref.label}</option>)}</select></label>
        <button type="submit" data-testid="submit-relation" disabled={!canWrite || busy !== null || !parcelRef || !buildingRef}>記錄可能關係</button>
      </form>
      {(!parcelRefs.length || !buildingRefs.length) && <p className={styles.empty}>請先建立地號與建號假設，或顯示待確認關係以選取既有參照。</p>}
      {relationResult && <p data-testid="relation-result" className={styles.result}>雙向 · 未驗證手動關係 · proposed · 非官方地籍確認</p>}
    </section>
  </main>;
}
