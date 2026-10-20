"use client";

import Link from "next/link";
import { cloneElement, useEffect, useId, useMemo, useRef, useState, type ReactElement, type FormEvent } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import { createDecisionRoomCaseAdapter, type DecisionRoomCaseRead, type DecisionRoomCaseContext } from "@/lib/decision-room-case-adapter";
import { addEvidenceAction, createBrowserDecisionRoomRepository, decisionRoomGaps, findEvidenceAction, mergeRoomRecord, WORK_STATUSES, type DecisionRoom, type RoomError, type RoomRead, type ViewingNote, type WorkItem, type WorkKind, type ManualCheck, type AskingPrice } from "@/lib/decision-room-store";
import { decisionRoomCopy, type DecisionRoomCopy } from "@/lib/decision-room-copy";
import { projectDecisionRoomReport } from "@/lib/decision-room-report";
import { decisionRoomReportCopy, type DecisionRoomReportCopyKey } from "@/lib/decision-room-report-copy";
import { resolveCommercialState } from "@/lib/commercial/state";
import { WorkspaceNavigation } from "@/components/workspace/workspace-navigation";
import { documentEvidenceCopy } from "@/lib/workspace/document-evidence-copy";
import styles from "./decision-room.module.css";
import { CopilotLink } from "@/components/workspace/copilot/copilot-link";

type Save = (change: (room: DecisionRoom) => DecisionRoom | null) => Promise<boolean>;
type EditorError = RoomError | "case_unreadable" | "record_removed";
const button = "ds-button ds-button--secondary ds-button--compact";
const primary = "ds-button ds-button--primary ds-button--compact";
const uuid = () => crypto.randomUUID();
function Field({ label, children }: { label: string; children: ReactElement<{ id?: string }> }) {
  const id = useId();
  return <div className={styles.field}><label htmlFor={id}>{label}</label>{cloneElement(children, { id })}</div>;
}
function submit(event: FormEvent, action: () => void) { event.preventDefault(); action(); }
function SourceLink({ url, c }: { url: string; c: DecisionRoomCopy }) { return url ? <a href={url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">{c.openSource}</a> : null; }
function Empty({ c }: { c: DecisionRoomCopy }) { return <p className={styles.muted}>{c.empty}</p>; }

export function DecisionRoomPage({ caseId }: { caseId: string }) {
  const { locale, formatDate, formatNumber } = useExperienceLocale();
  const c = decisionRoomCopy(locale);
  const repository = useMemo(createBrowserDecisionRoomRepository, []);
  const adapter = useMemo(() => createDecisionRoomCaseAdapter(createBrowserCaseRepository()), []);
  const [caseRead, setCaseRead] = useState<DecisionRoomCaseRead | null>(null);
  const [roomRead, setRoomRead] = useState<RoomRead | null>(null);
  const [error, setError] = useState<EditorError | null>(null);
  const [savedAt, setSavedAt] = useState("");
  const [pending, setPending] = useState(false);
  const roomRef = useRef<DecisionRoom | null>(null);
  const saving = useRef(false);
  const notice = useRef<HTMLDivElement>(null);
  function load() {
    const nextCase = adapter.read(caseId);
    if (nextCase.status !== "ready" && roomRef.current) { setError("case_unreadable"); return; }
    setCaseRead(nextCase);
    if (nextCase.status === "ready") {
      const nextRoom = repository.read(caseId);
      if (nextRoom.status !== "ready" && nextRoom.status !== "empty" && roomRef.current) { setError(nextRoom.status); return; }
      setRoomRead(nextRoom);
      roomRef.current = nextRoom.status === "ready" || nextRoom.status === "empty" ? nextRoom.room : null;
    }
    setError(null);
    setSavedAt("");
  }
  useEffect(() => {
    const context = adapter.read(caseId);
    setCaseRead(context);
    const room = context.status === "ready" ? repository.read(caseId) : null;
    setRoomRead(room);
    roomRef.current = room?.status === "ready" || room?.status === "empty" ? room.room : null;
    const stopCase = adapter.subscribe(() => {
      const nextCase = adapter.read(caseId);
      if (nextCase.status === "ready") setCaseRead(nextCase);
      else { setError("case_unreadable"); setSavedAt(""); }
    });
    const stopRoom = repository.subscribe(caseId, () => {
      if (saving.current) return;
      const latest = repository.read(caseId);
      if ((latest.status === "ready" || latest.status === "empty") && latest.room.revision === roomRef.current?.revision) return;
      setError("conflict");
      setSavedAt("");
    });
    return () => { stopCase(); stopRoom(); };
  }, [adapter, repository, caseId]);
  const save: Save = async (change) => {
    const current = roomRef.current;
    if (!current || saving.current || error === "conflict") return false;
    const currentCase = adapter.read(caseId);
    if (currentCase.status !== "ready") { setError("case_unreadable"); setSavedAt(""); return false; }
    const next = change(current);
    if (!next) { setError("record_removed"); setSavedAt(""); return false; }
    saving.current = true;
    setPending(true);
    const result = await repository.save(next, current.revision, () => adapter.read(caseId).status === "ready");
    saving.current = false;
    setPending(false);
    if (result.status !== "saved") {
      setError(result.status);
      setSavedAt("");
      requestAnimationFrame(() => notice.current?.scrollIntoView({ block: "center", behavior: "smooth" }));
      return false;
    }
    roomRef.current = result.room;
    setRoomRead({ status: "ready", room: result.room });
    setError(null);
    setSavedAt(result.room.updatedAt);
    return true;
  };

  const loading = caseRead === null || (caseRead.status === "ready" && roomRead === null);
  const context = caseRead?.status === "ready" ? caseRead.context : null;
  const room = roomRead?.status === "ready" || roomRead?.status === "empty" ? roomRead.room : null;
  return <main id="main-content" className={styles.room} data-testid="decision-room">
    <div className={styles.breadcrumb}><Link href="/cases">{c.cases}</Link><span aria-hidden="true">/</span><Link href={`/cases/${encodeURIComponent(caseId)}/overview`}>{c.overview}</Link></div>
    <header className={styles.hero}>
      {context && <p data-testid="room-case-context" className={styles.eyebrow}>{context.title} · {context.address}</p>}
      <h1 id="room-title" data-testid="room-heading">{c.title}</h1>
      <p>{c.subtitle}</p>
      <p className={styles.boundary}>{c.boundary}</p>
      <p className={styles.muted}>{c.localOnly}</p>
    </header>
    {context && <><WorkspaceNavigation caseId={caseId} /><CopilotLink caseId={caseId} /></>}
    {loading && <p aria-busy="true">{c.loading}</p>}
    {caseRead && caseRead.status !== "ready" && <div className={styles.error} role="alert"><p>{c[caseRead.status]}</p><Link href="/cases">{c.cases}</Link><button className={button} onClick={load}>{c.retry}</button></div>}
    {context && roomRead && !room && <div className={styles.error} role="alert"><p>{c[roomRead.status as RoomError]}</p><button className={button} onClick={load}>{c.retry}</button></div>}
    {context && room && <>
      <div ref={notice} className={styles.notice}>
        {error && <div role="alert" className={styles.error}><p>{c[error]}</p>{error === "conflict" && <button className={button} onClick={load}>{c.reload}</button>}</div>}
        <p role="status" aria-live="polite">{pending ? c.saving : savedAt ? `${c.saved} · ${formatDate(savedAt)}` : ""}</p>
      </div>
      <ActionSummary room={room} c={c} />
      <nav className={styles.sections} aria-label={c.title}>
        {[["verification-items", c.verifications], ["evidence-actions", c.evidenceActions], ["viewing-notes", c.notes], ["checklist-items", c.checklist], ["question-items", c.questions], ["task-items", c.tasks], ["manual-checks", c.manual], ["evidence-gaps", c.gaps]].map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}
      </nav>
      <fieldset disabled={pending} aria-busy={pending} className={styles.columns}>
        <div className={styles.primary}>
          <WorkList room={room} kind="verification" save={save} c={c} />
          <Notes room={room} save={save} c={c} />
          <WorkList room={room} kind="checklist" save={save} c={c} />
          <WorkList room={room} kind="question" save={save} c={c} />
          <WorkList room={room} kind="task" save={save} c={c} />
          <Checks room={room} save={save} c={c} />
        </div>
        <aside className={styles.secondary} aria-label={c.gaps}>
          <EvidenceActions room={room} context={context} save={save} c={c} />
          <section className={styles.panel} id="asking-price" aria-labelledby="asking-heading">
            <h2 id="asking-heading">{c.asking}</h2><p className={styles.muted}>{c.priceHint}</p>
            <p className={styles.snapshot}>{c.savedPrice}: <strong>{context.savedAskingPriceWan === null ? c.unknown : formatNumber(context.savedAskingPriceWan)}</strong></p>
            <PriceForm key={caseId} initial={room.askingPrice} save={(value) => save((r) => ({ ...r, askingPrice: value }))} c={c} />
          </section>
          <Gaps room={room} context={context} c={c} />
          <Evidence context={context} c={c} />
        </aside>
      </fieldset>
      <section id="activity-history" data-testid="activity-history" className={styles.panel} aria-labelledby="history-heading">
        <h2 id="history-heading">{c.history}</h2><p className={styles.muted}>{c.historyHint}</p>
        {!room.history.length ? <Empty c={c} /> : <ol className={styles.history}>{[...room.history].reverse().map((event) => <li key={event.id}><span><strong>{c[event.kind]}</strong>{event.subject && <span className={styles.userText}> · {event.subject}</span>}</span><time dateTime={event.at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(event.at))}</time></li>)}</ol>}
      </section>
    </>}
  </main>;
}

function Notes({ room, save, c }: { room: DecisionRoom; save: Save; c: DecisionRoomCopy }) {
  const { formatDate } = useExperienceLocale();
  const [editing, setEditing] = useState<ViewingNote | null>(null);
  return <section id="viewing-notes" data-testid="viewing-notes" className={styles.panel} aria-labelledby="notes-heading">
    <h2 id="notes-heading">{c.notes}</h2>
    {!room.notes.length && <Empty c={c} />}
    <ul className={styles.records}>{room.notes.map((note) => <li key={note.id} className={styles.record}>
        <p className={styles.userText}>{note.text}</p><p className={styles.muted}>{note.date ? formatDate(`${note.date}T12:00:00`) : c.noDate}</p>
        <div className={styles.actions}><button className={button} disabled={Boolean(editing)} onClick={() => setEditing(note)}>{c.edit}</button><button className={button} onClick={() => save((r) => ({ ...r, notes: r.notes.filter((n) => n.id !== note.id) }))}>{c.remove}</button></div>
    </li>)}</ul>
    {editing && <NoteForm key={editing.id} initial={editing} c={c} cancel={() => setEditing(null)} onSave={async (value) => {
      const ok = await save((r) => {
        const merged = mergeRoomRecord(editing, value, r.notes.find((n) => n.id === value.id));
        return merged ? { ...r, notes: r.notes.map((n) => n.id === value.id ? merged : n) } : null;
      });
      if (ok) setEditing(null);
      return ok;
    }} />}
    <NoteForm c={c} onSave={(value) => save((r) => ({ ...r, notes: [...r.notes, value] }))} />
  </section>;
}
function NoteForm({ initial, c, onSave, cancel }: { initial?: ViewingNote; c: DecisionRoomCopy; onSave: (note: ViewingNote) => Promise<boolean>; cancel?: () => void }) {
  const [text, setText] = useState(initial?.text ?? "");
  const [date, setDate] = useState(initial?.date ?? "");
  return <form data-testid={initial ? "note-edit-form" : "new-note-form"} className={styles.form} onSubmit={(e) => submit(e, async () => { if (await onSave({ id: initial?.id ?? uuid(), date, text }) && !initial) { setText(""); setDate(""); } })}>
    <Field label={c.noteText}><textarea required maxLength={4000} rows={3} value={text} onChange={(e) => setText(e.target.value)} /></Field>
    <Field label={c.viewedDate}><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
    <div className={styles.actions}><button className={primary} type="submit">{c.save}</button>{cancel && <button className={button} type="button" onClick={cancel}>{c.cancel}</button>}</div>
  </form>;
}
function WorkList({ room, kind, save, c }: { room: DecisionRoom; kind: WorkKind; save: Save; c: DecisionRoomCopy }) {
  const { formatDate } = useExperienceLocale();
  const [editing, setEditing] = useState<WorkItem | null>(null);
  const [adding, setAdding] = useState(false);
  const items = room.items.filter((r) => r.kind === kind);
  const { copyFrom } = useExperienceLocale();
  const r = (key: DecisionRoomReportCopyKey) => copyFrom(decisionRoomReportCopy, key);
  const title = kind === "checklist" ? c.checklist : kind === "question" ? c.questions : kind === "verification" ? c.verifications : c.tasks;
  return <section id={`${kind}-items`} data-testid={`${kind}-items`} className={styles.panel} aria-labelledby={`${kind}-heading`}>
    <div className={styles.sectionHeading}><h2 id={`${kind}-heading`}>{title}</h2><button className={button} onClick={() => setAdding(true)}>{c.add}</button></div>
    {kind === "verification" && <p className={styles.muted}>{c.verificationsHint}</p>}
    {!items.length && <Empty c={c} />}
    <ul className={styles.records}>{items.map((item) => <li key={item.id} className={styles.record} data-testid="room-action" data-status={item.status} data-origin={item.origin ?? "manual"} data-source-key={item.sourceKey || undefined}>
        <div className={styles.sectionHeading}><strong className={styles.userText}>{item.title}</strong><span className={styles.tag} data-status={item.status}>{c[item.status]}</span></div>
        <p className={styles.muted}><span className={styles.origin} data-testid="room-action-origin">{r("origin")}: {r(`origin_${item.origin ?? "manual"}`)}{item.sourceKey ? ` · ${r("linked")}` : ""}</span></p>
        <p className={styles.muted}>{c.owner}: {item.owner || c.unassigned} · {c.dueDate}: {item.dueDate ? formatDate(`${item.dueDate}T12:00:00`) : c.noDate}</p>
        {item.note && <p className={`${styles.userText} ${styles.muted}`}>{item.note}</p>}
        {item.resolution && <p className={styles.userText}>{c.resolution}: {item.resolution}</p>}
        <div className={styles.actions}><button className={button} disabled={Boolean(editing)} onClick={() => setEditing(item)}>{c.edit}</button><button className={button} onClick={() => save((r) => ({ ...r, items: r.items.filter((row) => row.id !== item.id) }))}>{c.remove}</button></div>
    </li>)}</ul>
    {editing && <WorkForm key={editing.id} initial={editing} kind={kind} c={c} cancel={() => setEditing(null)} onSave={async (value) => {
      const ok = await save((r) => {
        const merged = mergeRoomRecord(editing, value, r.items.find((row) => row.id === value.id));
        return merged ? { ...r, items: r.items.map((row) => row.id === value.id ? merged : row) } : null;
      });
      if (ok) setEditing(null);
      return ok;
    }} />}
    {adding && <WorkForm kind={kind} c={c} cancel={() => setAdding(false)} onSave={async (value) => { const ok = await save((r) => ({ ...r, items: [...r.items, value] })); if (ok) setAdding(false); return ok; }} />}
  </section>;
}
function WorkForm({ initial, kind, c, onSave, cancel }: { initial?: WorkItem; kind: WorkKind; c: DecisionRoomCopy; onSave: (item: WorkItem) => Promise<boolean>; cancel: () => void }) {
  const [draft, setDraft] = useState<Omit<WorkItem, "id">>(initial ?? { kind, title: "", owner: "", dueDate: "", status: "open", resolution: "", origin: "manual", sourceKey: "", note: "" });
  const owners = useId();
  const field = (key: keyof typeof draft, value: string) => setDraft((r) => ({ ...r, [key]: value }));
  return <form data-testid={initial ? "item-edit-form" : `new-${kind}-form`} className={styles.form} onSubmit={(e) => submit(e, () => onSave({ ...draft, id: initial?.id ?? uuid() }))}>
    <Field label={c.itemTitle}><input required maxLength={300} value={draft.title} onChange={(e) => field("title", e.target.value)} /></Field>
    <div className={styles.fieldRow}><Field label={c.owner}><input maxLength={100} list={owners} value={draft.owner} onChange={(e) => field("owner", e.target.value)} /></Field><Field label={c.dueDate}><input type="date" value={draft.dueDate} onChange={(e) => field("dueDate", e.target.value)} /></Field></div>
    <datalist id={owners}>{[c.owner_buyer, c.owner_agent, c.owner_scrivener, c.owner_management, c.owner_seller].map((name) => <option key={name} value={name} />)}</datalist>
    <Field label={c.status}><select value={draft.status} onChange={(e) => field("status", e.target.value)}>{WORK_STATUSES.map((status) => <option key={status} value={status}>{c[status]}</option>)}</select></Field>
    <Field label={c.note}><textarea maxLength={2000} rows={2} value={draft.note ?? ""} onChange={(e) => field("note", e.target.value)} /></Field>
    <Field label={c.resolution}><textarea required={draft.status === "done" && kind !== "checklist"} maxLength={2000} rows={2} value={draft.resolution} onChange={(e) => field("resolution", e.target.value)} /></Field>
    <p className={styles.muted}>{c.resolutionHint}</p>
    <div className={styles.actions}><button className={primary} type="submit">{c.save}</button><button className={button} type="button" onClick={cancel}>{c.cancel}</button></div>
  </form>;
}
function Checks({ room, save, c }: { room: DecisionRoom; save: Save; c: DecisionRoomCopy }) {
  const { formatDate } = useExperienceLocale();
  const [editing, setEditing] = useState<ManualCheck | null>(null);
  const [adding, setAdding] = useState(false);
  return <section id="manual-checks" data-testid="manual-checks" className={styles.panel} aria-labelledby="manual-heading">
    <div className={styles.sectionHeading}><h2 id="manual-heading">{c.manual}</h2><button className={button} onClick={() => setAdding(true)}>{c.add}</button></div><p className={styles.muted}>{c.manualHint}</p>
    {!room.verifications.length && <Empty c={c} />}
    <ul className={styles.records}>{room.verifications.map((check) => <li key={check.id} className={styles.record}>
        <strong className={styles.userText}>{check.topic}</strong><p className={styles.tag}>{c[check.outcome]}</p>
        <p className={styles.userText}>{check.sourceNote}</p><p className={styles.muted}>{c.checkedBy}: {check.checkedBy} · {formatDate(`${check.checkedDate}T12:00:00`)}</p>
        <SourceLink url={check.sourceUrl} c={c} />
        <div className={styles.actions}><button className={button} disabled={Boolean(editing)} onClick={() => setEditing(check)}>{c.edit}</button><button className={button} onClick={() => save((r) => ({ ...r, verifications: r.verifications.filter((row) => row.id !== check.id) }))}>{c.remove}</button></div>
    </li>)}</ul>
    {editing && <CheckForm key={editing.id} initial={editing} c={c} cancel={() => setEditing(null)} onSave={async (value) => {
      const ok = await save((r) => {
        const merged = mergeRoomRecord(editing, value, r.verifications.find((row) => row.id === value.id));
        return merged ? { ...r, verifications: r.verifications.map((row) => row.id === value.id ? merged : row) } : null;
      });
      if (ok) setEditing(null);
      return ok;
    }} />}
    {adding && <CheckForm c={c} cancel={() => setAdding(false)} onSave={async (value) => { const ok = await save((r) => ({ ...r, verifications: [...r.verifications, value] })); if (ok) setAdding(false); return ok; }} />}
  </section>;
}
function CheckForm({ initial, c, onSave, cancel }: { initial?: ManualCheck; c: DecisionRoomCopy; onSave: (check: ManualCheck) => Promise<boolean>; cancel: () => void }) {
  const [draft, setDraft] = useState<Omit<ManualCheck, "id">>(initial ?? { topic: "", outcome: "needs_follow_up", sourceUrl: "", sourceNote: "", checkedDate: "", checkedBy: "" });
  const field = (key: keyof typeof draft, value: string) => setDraft((r) => ({ ...r, [key]: value }));
  return <form data-testid={initial ? "check-edit-form" : "new-check-form"} className={styles.form} onSubmit={(e) => submit(e, () => onSave({ ...draft, id: initial?.id ?? uuid() }))}>
    <Field label={c.topic}><input required maxLength={300} value={draft.topic} onChange={(e) => field("topic", e.target.value)} /></Field>
    <Field label={c.outcome}><select value={draft.outcome} onChange={(e) => field("outcome", e.target.value)}><option value="needs_follow_up">{c.needs_follow_up}</option><option value="user_checked">{c.user_checked}</option></select></Field>
    <Field label={c.sourceUrl}><input type="url" maxLength={2048} value={draft.sourceUrl} onChange={(e) => field("sourceUrl", e.target.value)} /></Field>
    <Field label={c.sourceNote}><textarea required maxLength={2000} rows={3} value={draft.sourceNote} onChange={(e) => field("sourceNote", e.target.value)} /></Field>
    <div className={styles.fieldRow}><Field label={c.checkedBy}><input required maxLength={100} value={draft.checkedBy} onChange={(e) => field("checkedBy", e.target.value)} /></Field><Field label={c.checkedDate}><input required type="date" value={draft.checkedDate} onChange={(e) => field("checkedDate", e.target.value)} /></Field></div>
    <div className={styles.actions}><button className={primary} type="submit">{c.save}</button><button className={button} type="button" onClick={cancel}>{c.cancel}</button></div>
  </form>;
}
function PriceForm({ initial, c, save }: { initial: AskingPrice; c: DecisionRoomCopy; save: (price: AskingPrice) => Promise<boolean> }) {
  const [price, setPrice] = useState(initial.priceWan === null ? "" : String(initial.priceWan));
  const [url, setUrl] = useState(initial.sourceUrl);
  const [note, setNote] = useState(initial.sourceNote);
  const [date, setDate] = useState(initial.checkedDate);
  const [dirty, setDirty] = useState(false);
  const base = useRef(initial);
  useEffect(() => {
    if (dirty) return;
    base.current = initial;
    setPrice(initial.priceWan === null ? "" : String(initial.priceWan));
    setUrl(initial.sourceUrl); setNote(initial.sourceNote); setDate(initial.checkedDate);
  }, [initial, dirty]);
  return <form data-testid="asking-price-form" className={styles.form} onChange={() => setDirty(true)} onSubmit={(e) => submit(e, async () => {
    const merged = mergeRoomRecord(base.current, { priceWan: price.trim() ? Number(price) : null, sourceUrl: url, sourceNote: note, checkedDate: date }, initial)!;
    if (await save(merged)) setDirty(false);
  })}>
    <Field label={c.price}><input type="number" min="0.0001" max="1000000000" step="any" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} /></Field>
    <Field label={c.sourceUrl}><input type="url" maxLength={2048} value={url} onChange={(e) => setUrl(e.target.value)} /></Field>
    <Field label={c.sourceNote}><textarea maxLength={2000} rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
    <Field label={c.checkedDate}><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
    <SourceLink url={initial.sourceUrl} c={c} />
    <div className={styles.actions}><button className={primary} type="submit">{c.save}</button></div>
  </form>;
}
function Gaps({ room, context, c }: { room: DecisionRoom; context: DecisionRoomCaseContext; c: DecisionRoomCopy }) {
  const { locale } = useExperienceLocale();
  const gaps = decisionRoomGaps(room, context.evidence);
  return <section id="evidence-gaps" data-testid="evidence-gaps" className={styles.panel} aria-labelledby="gaps-heading">
    <h2 id="gaps-heading">{c.gaps}</h2><p className={styles.muted}>{c.gapsHint}</p>
    {gaps.length ? <ul className={styles.gaps}>{gaps.map((gap) => <li key={gap.id}><a href={`#${gap.target}`}>{c[gap.reason]}</a>{gap.subject && <span className={styles.userText}> · {gap.reason === "saved_evidence" ? c[gap.subject as keyof DecisionRoomCopy] ?? c.unknown : gap.subject}</span>}{gap.state && <small>{resolveCommercialState("evidence", gap.state).recognized ? resolveCommercialState("evidence", gap.state).label[locale] : c.unknown}</small>}</li>)}</ul> : <p>{c.noGaps}</p>}
  </section>;
}
function Evidence({ context, c }: { context: DecisionRoomCaseContext; c: DecisionRoomCopy }) {
  const { locale, formatDate, copyFrom } = useExperienceLocale();
  const identity = resolveCommercialState("identity", context.identityState);
  const manualStatus = (status: string) => status === "manual_confirmed" ? c.user_checked : status === "candidate" ? c.open : c.unknown;
  return <section id="saved-evidence" data-testid="saved-evidence" className={styles.panel} aria-labelledby="evidence-heading">
    <h2 id="evidence-heading">{c.evidence}</h2><p className={styles.muted}>{c.evidenceHint}</p><p className={styles.muted}>{c.snapshot}: {formatDate(context.snapshotDate)}</p>
    <p><Link href={`/cases/${encodeURIComponent(context.caseId)}/evidence`}>{copyFrom(documentEvidenceCopy, "nav")}</Link></p>
    <dl className={styles.evidence}>
      <div><dt>{c.identity}</dt><dd>{identity.label[locale]}</dd></div>
      <div><dt>{c.parcel}</dt><dd>{manualStatus(context.parcelStatus)}</dd></div>
      <div><dt>{c.building}</dt><dd>{manualStatus(context.buildingStatus)}</dd></div>
      {context.evidence.map((row) => <div key={row.key}><dt>{c[row.key as keyof DecisionRoomCopy] ?? row.key}</dt><dd>{resolveCommercialState("query", row.query).label[locale]}<br />{row.usability && <>{resolveCommercialState("evidence", row.usability).label[locale]}<br /></>}{resolveCommercialState("completeness", row.completeness).label[locale]}</dd></div>)}
    </dl>
  </section>;
}

/** Counts of the buyer's own actions. The same projection feeds Report page one; it is not a score. */
function ActionSummary({ room, c }: { room: DecisionRoom; c: DecisionRoomCopy }) {
  const { copyFrom } = useExperienceLocale();
  const r = (key: DecisionRoomReportCopyKey, values?: Record<string, string | number>) => copyFrom(decisionRoomReportCopy, key, values);
  const report = projectDecisionRoomReport({ status: "ready", room });
  const { counts } = report;
  const sentence = report.readiness === "none" ? r("readinessNone") : report.readiness === "clear" ? r("readinessClear", { done: counts.done }) : r("readinessOutstanding", { count: counts.outstanding, verification: counts.verification });
  return <section className={`${styles.panel} ${styles.summary}`} data-testid="room-action-summary" data-readiness={report.readiness} aria-labelledby="summary-heading">
    <h2 id="summary-heading">{c.actionSummary}</h2>
    <p data-testid="room-readiness">{sentence}</p>
    <dl className={styles.counts}>
      <div data-testid="room-count-open"><dt>{c.open}</dt><dd>{counts.open + counts.blocked}{counts.blocked > 0 && <small> · {c.blockedCount} {counts.blocked}</small>}</dd></div>
      <div data-testid="room-count-in_progress"><dt>{c.in_progress}</dt><dd>{counts.inProgress}</dd></div>
      <div data-testid="room-count-done"><dt>{c.done}</dt><dd>{counts.done}</dd></div>
    </dl>
    <p className={styles.muted}>{r("readinessCaveat")}</p>
  </section>;
}
/** Saved-evidence checks the buyer can turn into verification actions; one action per evidence key. */
function EvidenceActions({ room, context, save, c }: { room: DecisionRoom; context: DecisionRoomCaseContext; save: Save; c: DecisionRoomCopy }) {
  const { copyFrom } = useExperienceLocale();
  const r = (key: DecisionRoomReportCopyKey, values?: Record<string, string | number>) => copyFrom(decisionRoomReportCopy, key, values);
  return <section id="evidence-actions" data-testid="evidence-actions" className={styles.panel} aria-labelledby="evidence-actions-heading">
    <h2 id="evidence-actions-heading">{c.evidenceActions}</h2><p className={styles.muted}>{c.evidenceActionsHint}</p>
    {!context.evidenceActions.length ? <p>{c.noEvidenceActions}</p> : <ul className={styles.candidates}>{context.evidenceActions.map((candidate) => {
      const existing = findEvidenceAction(room, candidate.sourceKey);
      return <li key={candidate.sourceKey} data-testid={`evidence-action-${candidate.sourceKey}`}>
        <span><strong className={styles.userText}>{candidate.title}</strong><small>{r(`origin_${candidate.origin}`)}</small></span>
        {existing ? <span className={styles.tag} data-testid="evidence-action-in-room">{r("inRoom", { status: c[existing.status] })}</span>
          : <button className={button} onClick={() => save((latest) => addEvidenceAction(latest, candidate, uuid).room)}>{r("addToRoom")}</button>}
      </li>;
    })}</ul>}
  </section>;
}
