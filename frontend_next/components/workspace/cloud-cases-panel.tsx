"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { cloudCases } from "@/lib/cloud-case-client";
import { previewLocalImport, type CloudActivity, type CloudCase, type CloudErrorCode, type CloudResult, type CloudSummary, type ImportPreview } from "@/lib/cloud-case-contract";
import { getVNextAuthClient } from "@/lib/vnext-auth-session";
import styles from "./cloud-cases-panel.module.css";

const errors: Record<CloudErrorCode, string> = {
  sign_in_required: "請登入帳號後再操作；本機案件仍保留。",
  persistence_pending: "Cloud 儲存尚未啟用；本機原始案件與筆記仍保留。",
  unavailable: "Cloud 暫時無法使用；未確認儲存成功。本機原始資料仍保留，請手動重試。",
  offline: "目前離線；可繼續開啟本機案件。重新連線後請手動重試。",
  conflict: "版本衝突：帳號中的案件已變更。草稿仍保留；請先讀取最新版本並比較，再決定是否儲存。",
  forbidden: "無法存取此案件，或權限已變更。請重新讀取帳號案件。",
  invalid: "資料不符合保存邊界，或包含憑證欄位。未上傳成功；請檢查原始資料。",
};

export function CloudCasesPanel({ localCases }: { localCases: { caseId: string; title: string }[] }) {
  const controlId = useId();
  const [localId, setLocalId] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [summaries, setSummaries] = useState<CloudSummary[]>([]);
  const [scope, setScope] = useState<"owned" | "shared">("owned");
  const [offset, setOffset] = useState(0);
  const [row, setRow] = useState<CloudCase | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [cadence, setCadence] = useState<"off" | "daily" | "weekly">("off");
  const [member, setMember] = useState("");
  const [memberRole, setMemberRole] = useState<"editor" | "viewer">("viewer");
  const [activity, setActivity] = useState<CloudActivity[]>([]);
  const [activityOffset, setActivityOffset] = useState(0);
  const [message, setMessage] = useState("本機案件只在你預覽並確認後才會儲存到帳號；登入不會自動上傳。");
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);
  const requestEpoch = useRef(0);
  const previewEpoch = useRef(0);
  const locked = useRef(false);

  useEffect(() => {
    const online = () => setOffline(!navigator.onLine);
    online();
    window.addEventListener("online", online); window.addEventListener("offline", online);
    const subscription = getVNextAuthClient()?.auth.onAuthStateChange(event => {
      if (!["SIGNED_OUT", "SIGNED_IN", "USER_UPDATED"].includes(event)) return;
      requestEpoch.current++;
      previewEpoch.current++;
      setRow(null); setPreview(null); setSummaries([]); setActivity([]); setTitle(""); setNotes(""); setMember(""); setMemberRole("viewer");
      setConflict(false); setMessage("帳號狀態已變更；請手動重新讀取 Cloud 案件。本機案件仍保留。");
    });
    return () => { requestEpoch.current++; previewEpoch.current++; subscription?.data.subscription.unsubscribe(); window.removeEventListener("online", online); window.removeEventListener("offline", online); };
  }, []);

  async function run<T>(operation: () => Promise<CloudResult<T>>, success: (value: T) => void) {
    if (locked.current) return;
    locked.current = true; setBusy(true);
    const epoch = requestEpoch.current;
    try {
      const result = await operation();
      if (epoch !== requestEpoch.current) return;
      if (result.status === "ready") success(result.value);
      else {
        setMessage(errors[result.status]);
        if (result.status === "conflict") setConflict(true);
        if (["forbidden", "sign_in_required"].includes(result.status)) { setRow(null); setSummaries([]); setActivity([]); setTitle(""); setNotes(""); }
      }
    } catch { if (epoch === requestEpoch.current) setMessage(errors.unavailable); }
    finally { locked.current = false; setBusy(false); }
  }

  function accept(next: CloudCase, keepDraft = false) {
    if (next.id !== row?.id) { setMember(""); setMemberRole("viewer"); }
    setRow(next); setActivity([]); setActivityOffset(0); setCadence(next.monitoring.cadence);
    if (keepDraft) {
      // Keep intentionally edited fields; adopt newer untouched metadata.
      setTitle(current => row && current !== row.title ? current : next.title);
      setNotes(current => row && current !== row.notes ? current : next.notes);
    } else { setTitle(next.title); setNotes(next.notes); }
    setConflict(false);
  }

  async function prepare() {
    const epoch = requestEpoch.current;
    const selected = ++previewEpoch.current;
    const next = await previewLocalImport(window.localStorage, localId);
    if (epoch !== requestEpoch.current || selected !== previewEpoch.current) return;
    setPreview(next);
    setMessage(next ? "請確認：會保存這份原始快照與此案件的決策室筆記；原本本機副本繼續保留。" : "無法安全預覽：原始紀錄可能已損壞、過大、重複或包含憑證。未上傳任何資料。");
  }

  async function migrate() {
    if (!preview) return;
    const confirmed = preview;
    const epoch = requestEpoch.current;
    await run(async () => {
      const latest = await previewLocalImport(window.localStorage, String(confirmed.snapshot.id));
      if (epoch !== requestEpoch.current) return { status: "sign_in_required" as const };
      if (!latest || latest.import_key !== confirmed.import_key) {
        setPreview(null);
        return { status: "conflict" as const };
      }
      return cloudCases.create(confirmed, () => epoch === requestEpoch.current);
    }, next => { accept(next); setPreview(null); setMessage("已儲存 Cloud 快照；本機原始案件與筆記仍保留。後續本機變更不會自動同步。"); });
  }

  function list(nextScope = scope, nextOffset = 0) {
    void run(() => cloudCases.list(nextScope, nextOffset), values => {
      setSummaries(values); setScope(nextScope); setOffset(nextOffset);
      setMessage(values.length ? "已讀取 Cloud 清單；開啟案件不會更新資料來源。" : "這一頁沒有 Cloud 案件。");
    });
  }

  return <section className={styles.panel} aria-label="Cloud 案件" data-testid="cloud-cases-panel" aria-busy={busy}>
    <h2 className="text-section-title">Cloud 案件 · 跨裝置保存</h2>
    <p>本機（Local）只在此瀏覽器。Cloud 保存到登入帳號，僅擁有者與明確授權成員可存取。</p>
    <p role="status" data-testid="cloud-status">{offline ? errors.offline : message}</p>
    <Link href="/account">帳號與登入</Link>
    <fieldset disabled={busy || offline}>
      <legend>明確保存到帳號</legend>
      <label>本機案件<select aria-label="選擇要保存的本機案件" value={localId} onChange={e => { previewEpoch.current++; setLocalId(e.target.value); setPreview(null); }}>
        <option value="">選擇本機案件</option>{localCases.map(c => <option key={c.caseId} value={c.caseId}>{c.title} · Local</option>)}
      </select></label>
      <button className="ds-button ds-button--secondary" disabled={!localId} onClick={() => void prepare()}>預覽保存到帳號</button>
      {preview && <div className={styles.preview}>
        <h3>確認上傳：{String(preview.snapshot.title)}</h3>
        <p>原始建立：{String(preview.snapshot.createdAt)} · 原始更新：{String(preview.snapshot.updatedAt)}</p>
        <p>{preview.user_authored.decision_room ? "包含決策室原始筆記與活動紀錄。" : "此案件沒有另存的決策室筆記。"}保留證據來源、失敗與未知狀態；不重新分析。</p>
        <button className="ds-button ds-button--primary" onClick={() => void migrate()}>確認儲存到我的帳號</button>
        <button className="ds-button ds-button--tertiary" onClick={() => { previewEpoch.current++; setPreview(null); }}>取消上傳</button>
      </div>}
    </fieldset>
    <fieldset disabled={busy || offline}>
      <legend>帳號案件</legend>
      <div className={styles.actions}>
        <button className="ds-button ds-button--secondary" onClick={() => list("owned")}>讀取我的 Cloud 案件</button>
        <button className="ds-button ds-button--secondary" onClick={() => list("shared")}>讀取受邀案件</button>
      </div>
      <ul>{summaries.map(c => <li key={c.id}><button className="ds-button ds-button--tertiary" onClick={() => void run(() => cloudCases.open(c.id), next => { accept(next); setMessage("已開啟保存快照；未呼叫分析供應商。同步狀態代表最後一次讀取，請手動檢查最新版本。"); })}>{c.title} · Cloud · {c.role} · v{c.revision}</button></li>)}</ul>
      <div className={styles.actions}>
        {offset > 0 && <button onClick={() => list(scope, Math.max(0, offset - 20))}>上一頁案件</button>}
        {summaries.length === 20 && <button onClick={() => list(scope, offset + 20)}>下一頁案件</button>}
      </div>
    </fieldset>
    {row && <div className={styles.detail} data-testid="cloud-case-detail">
      <h3>{row.title} · Cloud</h3>
      <p>權限：{row.role} · {row.sharing === "private" ? "私人" : "僅授權成員"} · 版本 {row.revision}</p>
      <p>上次讀取的更新時間：{row.updated_at}。離線或其他裝置更新後，請手動讀取最新版本。</p>
      <p>原始證據快照：{String(row.snapshot.title)} · {String(row.snapshot.updatedAt)}</p>
      <CloudSnapshot row={row} />
      <details><summary>檢視原始證據與筆記（不重新分析）</summary><pre className={styles.snapshot}>{JSON.stringify({ snapshot: row.snapshot, user_authored: row.user_authored }, null, 2)}</pre></details>
      <fieldset disabled={busy || offline}>
        <legend>同步與使用者資料</legend>
        <button className="ds-button ds-button--secondary" onClick={() => void run(() => cloudCases.open(row.id), next => { const keep = conflict || title !== row.title || notes !== row.notes; accept(next, keep); setMessage(keep ? "已讀取最新版本，草稿仍保留。請比較以下帳號版本，再儲存你的草稿。" : "已手動檢查最新版本；未重新分析。"); })}>讀取最新版本</button>
        {conflict && <p role="alert">{errors.conflict}</p>}
        <p>帳號版本標題：{row.title} · 帳號版本筆記：{row.notes || "（空白）"}</p>
        <label htmlFor={`${controlId}-title`}>Cloud 標題</label><input id={`${controlId}-title`} maxLength={500} disabled={row.role === "viewer"} value={title} onChange={e => setTitle(e.target.value)} />
        <label htmlFor={`${controlId}-notes`}>Cloud 使用者筆記</label><textarea id={`${controlId}-notes`} maxLength={8000} disabled={row.role === "viewer"} value={notes} onChange={e => setNotes(e.target.value)} />
        <button className="ds-button ds-button--primary" disabled={conflict || row.role === "viewer" || !title.trim()} onClick={() => void run(() => cloudCases.metadata(row, title, notes), next => { accept(next); setMessage("使用者資料已儲存；歷史證據未變更。"); })}>儲存 Cloud 使用者資料</button>
      </fieldset>
      <fieldset disabled={busy || offline || conflict || row.role !== "owner"}>
        <legend>協作 · 僅擁有者管理</legend>
        <p>邀請只授權指定 Auth 帳號 UUID；不產生公開連結，也不寄出通知。owner/editor/viewer 與工作區角色分開。</p>
        <label htmlFor={`${controlId}-member`}>成員 Auth UUID</label><input id={`${controlId}-member`} value={member} maxLength={36} onChange={e => setMember(e.target.value)} />
        <label htmlFor={`${controlId}-role`}>案件權限</label><select id={`${controlId}-role`} value={memberRole} onChange={e => setMemberRole(e.target.value as "editor" | "viewer")}><option value="viewer">viewer · 唯讀</option><option value="editor">editor · 編輯標題與筆記</option></select>
        <button className="ds-button ds-button--secondary" disabled={!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(member)} onClick={() => void run(() => cloudCases.membership(row, member, memberRole), next => { accept(next, true); setMessage("成員授權已更新；沒有公開分享連結。"); })}>授權成員</button>
        <ul>{Object.entries(row.members).map(([id, role]) => <li key={id}>{id} · {role} <button onClick={() => void run(() => cloudCases.membership(row, id, null), next => { accept(next, true); setMessage("成員存取權已撤銷。"); })}>撤銷 {id}</button></li>)}</ul>
      </fieldset>
      <fieldset disabled={busy || offline || conflict || row.role !== "owner"}>
        <legend>監控偏好 · 僅擁有者管理</legend>
        <label htmlFor={`${controlId}-cadence`}>檢查頻率</label><select id={`${controlId}-cadence`} value={cadence} onChange={e => setCadence(e.target.value as typeof cadence)}><option value="off">關閉</option><option value="daily">每日</option><option value="weekly">每週</option></select>
        <p>僅手動更新供應商資料。排程執行與 email／SMS 通知尚未配置；儲存偏好不代表監控已啟動。</p>
        <button className="ds-button ds-button--secondary" onClick={() => void run(() => cloudCases.monitoring(row, cadence), next => { accept(next, true); setMessage("監控偏好已儲存；排程與通知尚未啟用。"); })}>儲存監控偏好</button>
      </fieldset>
      <fieldset disabled={busy || offline}>
        <legend>活動紀錄</legend>
        <button className="ds-button ds-button--secondary" onClick={() => void run(() => cloudCases.activity(row.id), values => { setActivity(values); setActivityOffset(0); })}>讀取最近活動</button>
        <ol>{activity.map(event => <li key={event.revision}>v{event.revision} · {event.kind} · {event.occurred_at}</li>)}</ol>
        {activity.length === 20 && <button onClick={() => void run(() => cloudCases.activity(row.id, activityOffset + 20), values => { setActivity(values); setActivityOffset(activityOffset + 20); })}>較早活動</button>}
      </fieldset>
    </div>}
  </section>;
}

function CloudSnapshot({ row }: { row: CloudCase }) {
  const object = (v: unknown): Record<string, unknown> => v && typeof v === "object" && !Array.isArray(v) ? v as Record<string, unknown> : {};
  const data = object(row.snapshot.data);
  const address = object(row.snapshot.inputSummary);
  const room = object(row.user_authored.decision_room);
  const viewingNotes = Array.isArray(room.notes) ? room.notes.filter((v): v is { text: string; date?: string } => Boolean(v && typeof v === "object" && typeof v.text === "string")) : [];
  const sources = [
    ["marketInsight", "市場"], ["valuation", "估值"], ["financeEvidence", "財務"],
    ["locationInsight", "生活圈"], ["commuteRoute", "通勤"], ["commuteTransit", "大眾運輸"], ["terrainReference", "環境風險"],
  ];
  const text = (v: unknown): string | null => typeof v === "string" || typeof v === "number" ? String(v) : null;
  return <section aria-label="Cloud 歷史快照摘要" className={styles.detail}>
    <h4>歷史快照摘要</h4>
    <p>{[address.city, address.district, address.road].map(text).filter(Boolean).join(" ") || "原始地址未提供"}</p>
    <p>建立時間：{String(row.snapshot.createdAt)}。以下為保存時的來源狀態，不代表目前資料已更新或驗證。</p>
    <dl>{sources.map(([key, label]) => {
      const evidence = object(data[key]);
      const quality = object(evidence.data_quality);
      const state = text(evidence.status) ?? text(evidence.data_status) ?? text(quality.status) ?? text(object(evidence.calculation).query);
      const source = text(evidence.source_name) ?? text(evidence.source) ?? text(evidence.source_provider);
      const time = text(evidence.checked_at) ?? text(evidence.calculated_at) ?? text(evidence.source_updated_at) ?? text(evidence.snapshot_generated_at);
      return <div key={key}><dt>{label}</dt><dd>{data[key] === undefined ? "未保存" : `原始狀態：${state ?? "未記錄／未知"}`}{source ? ` · ${source}` : ""}{time ? ` · ${time}` : ""}</dd></div>;
    })}</dl>
    <h4>原始看屋筆記</h4>
    {viewingNotes.length ? <ul>{viewingNotes.map((note, index) => <li key={index}>{text(note.date) ?? ""} {note.text}</li>)}</ul> : <p>此快照沒有另存的看屋筆記。</p>}
  </section>;
}
