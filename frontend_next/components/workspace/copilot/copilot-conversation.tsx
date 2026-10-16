"use client";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useWorkspace } from "../workspace-provider";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserDecisionRoomRepository } from "@/lib/decision-room-store";
import { SCENARIO_STORAGE_KEY } from "@/lib/workspace/scenario-model";
import { assembleCopilotContext, answerQuestion, createResponseGate, type CopilotAnswer, type CopilotContext, type CopilotEvidence, type CopilotTopic } from "@/lib/workspace/grounded-copilot";
import { copilotCopy, copilotTopicLabel, copilotStatusLabel, copilotEvidenceLabel } from "@/lib/workspace/copilot-copy";
import styles from "./copilot.module.css";

export function CopilotConversation() {
  const workspace = useWorkspace();
  const repository = useMemo(createBrowserDecisionRoomRepository, []);
  const [snapshot, setSnapshot] = useState<{ workspace: typeof workspace; context: CopilotContext } | null>(null);
  useEffect(() => {
    function read() {
      let scenarioRaw: string | null = null;
      try { scenarioRaw = localStorage.getItem(`${SCENARIO_STORAGE_KEY}:${workspace.caseId}`); } catch { /* Missing evidence stays missing. */ }
      setSnapshot({ workspace, context: assembleCopilotContext(workspace, { scenarioRaw, roomRead: repository.read(workspace.caseId) }) });
    }
    read();
    const stop = repository.subscribe(workspace.caseId, read);
    const onStorage = (event: StorageEvent) => { if (event.key === null || event.key === `${SCENARIO_STORAGE_KEY}:${workspace.caseId}`) read(); };
    window.addEventListener("storage", onStorage);
    window.addEventListener("proptech:scenarios-changed", read);
    return () => { stop(); window.removeEventListener("storage", onStorage); window.removeEventListener("proptech:scenarios-changed", read); };
  }, [workspace, repository]);
  // Never display the previous property's context while its effect is being replaced.
  if (!snapshot || snapshot.workspace !== workspace) return null;
  return <Conversation key={snapshot.context.key} context={snapshot.context} />;
}

function Conversation({ context }: { context: CopilotContext }) {
  const { locale } = useExperienceLocale();
  const c = copilotCopy(locale);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Array<{ question: string; answer: CopilotAnswer }>>([]);
  const [pending, setPending] = useState(false);
  const gate = useRef(createResponseGate());
  useEffect(() => { const active = gate.current; return () => active.cancel(); }, []);
  const latest = turns.at(-1)?.answer;
  async function ask(value: string) {
    if (!value.trim() || pending) return;
    const ticket = gate.current.begin(context.key);
    setPending(true);
    const answer = await Promise.resolve(answerQuestion(context, value, latest));
    if (!gate.current.accepts(ticket, context.key)) return;
    setTurns(previous => [...previous, { question: value.slice(0, 1000), answer }].slice(-12));
    setQuestion(""); setPending(false);
  }
  function submit(event: FormEvent) { event.preventDefault(); void ask(question); }
  const askTopic = (topic: CopilotTopic) => void ask(copilotTopicLabel(topic, locale));
  return <section className={styles.panel} aria-label={c.title} data-testid="copilot-conversation">
    <header><h2>{c.title}</h2><p>{c.intro}</p><p className={styles.muted}>{c.mode}</p></header>
    <div className={styles.context} data-testid="copilot-context"><strong>{c.context}</strong><p>{context.title} · {context.address}</p><p>{context.caseId} · {context.savedAt}</p><div className={styles.chips}><span>{c.saved}</span><span>{c.live}</span></div></div>
    <p>{c.boundary}</p><p className={styles.muted}>{c.scope}</p>
    <nav className={styles.actions} aria-label={c.suggestions}>
      <button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} onClick={() => void ask(c.summary)}>{c.summary}</button>
      {(["market", "finance", "commute", "risk", "scenario", "decision"] as const).map(topic => <button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} key={topic} onClick={() => askTopic(topic)}>{copilotTopicLabel(topic, locale)}</button>)}
    </nav>
    <div role="log" aria-live="polite" aria-relevant="additions" className={styles.turns}>
      {turns.map((turn, i) => <article key={i} className={styles.turn} data-testid="copilot-turn"><p className={styles.question}>{turn.question}</p><Answer answer={turn.answer} index={i} pending={pending} onFollowup={(value) => void ask(value)} /></article>)}
    </div>
    <form onSubmit={submit} className={styles.form} aria-busy={pending}>
      <label htmlFor="copilot-question">{c.question}</label>
      <textarea id="copilot-question" value={question} maxLength={1000} rows={3} onChange={event => setQuestion(event.target.value)} required />
      <div className={styles.actions}><button className="ds-button ds-button--primary" disabled={pending || !question.trim()} type="submit">{c.send}</button><button className="ds-button ds-button--secondary" type="button" onClick={() => { gate.current.cancel(); setTurns([]); setPending(false); setQuestion(""); }}>{c.reset}</button></div>
    </form>
    <p className={styles.muted}>{c.refresh}</p>
  </section>;
}

function Answer({ answer, index, pending, onFollowup }: { answer: CopilotAnswer; index: number; pending: boolean; onFollowup: (question: string) => void }) {
  const { locale } = useExperienceLocale(); const c = copilotCopy(locale);
  const limitation = (value: string) => value === "user_record" ? c.decisionNote : ["known_subtotal", "scenario_assumptions"].includes(value) ? c.scenarioNote : value || c.boundary;
  const source = (row: CopilotEvidence) => row.source === "scenarios" || row.source === "decision-room" ? copilotTopicLabel(row.topic, locale) : row.source;
  return <div data-testid="copilot-answer" data-answer-status={answer.status}>
    <strong className={styles.status}>{copilotStatusLabel(answer.status, locale)}</strong>
    <p>{answer.conflicts.length ? c.conflict : answer.used.length ? c.partial : c.empty}</p>
    {answer.insights.map(insight => <p key={insight.kind}>{insight.kind === "asking_vs_market" ? c.difference : c.housing}: <strong>{new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(insight.kind === "asking_vs_market" ? insight.values.differenceWan : insight.values.monthlyTwd)}</strong> {insight.refs.map(ref => { const position = answer.used.findIndex(item => item.ref === ref); const row = answer.used[position]; return <a key={ref} href={`#copilot-${index}-${encodeURIComponent(row.id)}`}>[{position + 1}] </a>; })}</p>)}
    {answer.topics.includes("market") && <p>{c.marketNote}</p>}
    {answer.topics.includes("finance") && <p>{c.financeNote}</p>}
    {answer.topics.includes("commute") && <p>{c.commuteNote}</p>}
    {answer.topics.includes("scenario") && <p>{c.scenarioNote}</p>}
    {answer.topics.includes("decision") && <p>{c.decisionNote}</p>}
    <p className={styles.muted}>{c.numeric}</p>
    <h3>{c.used}</h3>
    {!answer.used.length && <p>{c.empty}</p>}
    <ul className={styles.used}>{answer.used.map((row, position) => <li key={row.ref}><a href={`#copilot-${index}-${encodeURIComponent(row.id)}`} data-citation-ref={row.ref}>[{position + 1}] {copilotEvidenceLabel(row.id, row.label, locale)}</a>: <EvidenceValue row={row} /><span className={styles.chip}>{c.saved}</span><span className={styles.chip}>{source(row)}</span></li>)}</ul>
    <details open={!answer.used.length}><summary>{c.missing} ({answer.missing.length})</summary><ul className={styles.evidence}>{answer.missing.map(row => <li key={row.ref}><a href={row.href}>{copilotEvidenceLabel(row.id, row.label, locale)}</a> · {copilotStatusLabel(row.status, locale)}<p>{c.unknown}</p><p>{row.limitation}</p></li>)}</ul></details>
    <details><summary>{c.provenance}</summary><ul className={styles.evidence}>{answer.used.map(row => <li id={`copilot-${index}-${encodeURIComponent(row.id)}`} key={row.ref} data-evidence-ref={row.ref} tabIndex={-1}>
      <strong>{copilotEvidenceLabel(row.id, row.label, locale)}</strong> · <EvidenceValue row={row} />
      <p className={styles.chips}><span>{source(row)}</span><span>{c.saved}</span><span>{copilotStatusLabel(row.status, locale)}</span></p>
      <p>{row.checkedAt || c.unknown} / {row.updatedAt || c.unknown}</p><p>{c.limitation}: {limitation(row.limitation)}</p><a href={row.href}>{c.inspect}</a>
    </li>)}</ul></details>
    <nav className={styles.actions} aria-label={c.followup}><button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} onClick={() => onFollowup(c.nextMissing)}>{c.nextMissing}</button>{answer.followups.map(topic => <button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} key={topic} onClick={() => onFollowup(copilotTopicLabel(topic, locale))}>{copilotTopicLabel(topic, locale)}</button>)}</nav>
  </div>;
}
function EvidenceValue({ row }: { row: CopilotEvidence }) {
  const { locale } = useExperienceLocale();
  const unit = ({ "萬元": "TWD × 10,000", "萬元／坪": "TWD × 10,000 / ping", "元／月": "TWD / month", "分鐘": "min", "公尺": "m", "年": "year", "坪": "ping" } as Record<string, string>)[row.unit] ?? row.unit;
  return <span className={styles.value}>{typeof row.value === "number" ? new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(row.value) : row.value} {unit}</span>;
}
