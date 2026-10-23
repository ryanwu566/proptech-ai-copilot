"use client";
import { useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent } from "react";
import { useWorkspace } from "../workspace-provider";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { createBrowserDecisionRoomRepository } from "@/lib/decision-room-store";
import { SCENARIO_STORAGE_KEY } from "@/lib/workspace/scenario-model";
import { assembleCopilotContext, answerQuestion, createResponseGate, type CopilotAnswer, type CopilotContext, type CopilotEvidence, type CopilotTopic } from "@/lib/workspace/grounded-copilot";
import { copilotCopy, copilotTopicLabel, copilotStatusLabel, copilotEvidenceLabel } from "@/lib/workspace/copilot-copy";
import { composeAnswer, type KeyFact } from "@/lib/workspace/copilot-compose";
import { answerCopy, answerText, formatQuantity, formatRange, headlineText, nextActionLabel, originLabel, travelMode } from "@/lib/workspace/copilot-answer-copy";
import { formatEvidenceDate } from "@/lib/workspace/evidence-date";
import styles from "./copilot.module.css";

export function CopilotConversation() {
  const workspace = useWorkspace();
  const repository = useMemo(createBrowserDecisionRoomRepository, []);
  const [snapshot, setSnapshot] = useState<{ workspace: typeof workspace; context: CopilotContext } | null>(null);
  useEffect(() => {
    function read() {
      let scenarioRaw: string | null = null;
      try { scenarioRaw = localStorage.getItem(`${SCENARIO_STORAGE_KEY}:${workspace.caseId}`); } catch { /* Missing evidence stays missing. */ }
      const context = assembleCopilotContext(workspace, { scenarioRaw, roomRead: repository.read(workspace.caseId) });
      // An unchanged evidence key keeps the same context object, so earlier answers still cite its own rows.
      setSnapshot(previous => previous && previous.workspace === workspace && previous.context.key === context.key ? previous : { workspace, context });
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
  const { locale, formatDate } = useExperienceLocale();
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
    <div className={styles.context} data-testid="copilot-context"><strong>{c.context}</strong><p>{context.title} · {context.address}</p><p>{c.savedAt}: {formatEvidenceDate(context.savedAt, formatDate, c.unknown)}</p><div className={styles.chips}><span>{c.saved}</span><span>{c.live}</span></div></div>
    <p>{c.boundary}</p><p className={styles.muted}>{c.scope}</p>
    <nav className={styles.actions} aria-label={c.suggestions}>
      <button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} onClick={() => void ask(c.summary)}>{c.summary}</button>
      {(["market", "finance", "commute", "risk", "scenario", "decision"] as const).map(topic => <button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} key={topic} onClick={() => askTopic(topic)}>{copilotTopicLabel(topic, locale)}</button>)}
    </nav>
    <div role="log" aria-live="polite" aria-relevant="additions" className={styles.turns}>
      {turns.map((turn, i) => <article key={i} className={styles.turn} data-testid="copilot-turn"><p className={styles.question}>{turn.question}</p><Answer answer={turn.answer} context={context} index={i} pending={pending} onFollowup={(value) => void ask(value)} /></article>)}
    </div>
    <form onSubmit={submit} className={styles.form} aria-busy={pending}>
      <label htmlFor="copilot-question">{c.question}</label>
      <textarea id="copilot-question" value={question} maxLength={1000} rows={3} onChange={event => setQuestion(event.target.value)} required />
      <div className={styles.actions}><button className="ds-button ds-button--primary" disabled={pending || !question.trim()} type="submit">{c.send}</button><button className="ds-button ds-button--secondary" type="button" onClick={() => { gate.current.cancel(); setTurns([]); setPending(false); setQuestion(""); }}>{c.reset}</button></div>
    </form>
    <p className={styles.muted}>{c.refresh}</p>
  </section>;
}

/** Answer first: headline, cited key facts, gaps, one next action, follow-ups, then collapsed evidence and provenance. */
function Answer({ answer, context, index, pending, onFollowup }: { answer: CopilotAnswer; context: CopilotContext; index: number; pending: boolean; onFollowup: (question: string) => void }) {
  const { locale, formatDate } = useExperienceLocale(); const c = copilotCopy(locale); const a = answerCopy(locale);
  const view = useMemo(() => composeAnswer(answer, context), [answer, context]);
  const limitation = (value: string) => value === "user_record" ? c.decisionNote : ["known_subtotal", "scenario_assumptions"].includes(value) ? c.scenarioNote : value || c.boundary;
  const source = (row: CopilotEvidence) => row.source === "scenarios" || row.source === "decision-room" ? copilotTopicLabel(row.topic, locale) : row.source;
  const anchor = (row: CopilotEvidence) => `copilot-${index}-${encodeURIComponent(row.id)}`;
  // Only references the composed presentation authorized are rendered as citations or evidence.
  const used = answer.used.filter(row => view.fullEvidenceRefs.includes(row.ref));
  const missing = view.fullEvidenceRefs.length || view.missingTotal ? answer.missing : [];
  const rowFor = (ref: string) => used.find(row => row.ref === ref);
  const cite = (refs: string[]) => refs.map(ref => {
    const row = rowFor(ref); if (!row) return null;
    const n = used.indexOf(row) + 1;
    return <a key={ref} className={styles.cite} href={`#${anchor(row)}`} data-citation-ref={row.ref} aria-label={answerText(a.citation, { n })}>[{n}]</a>;
  });
  const headline = headlineText(view.headline, locale);
  const action = nextActionLabel(view.nextAction.kind, locale);
  const notes = ([["market", c.marketNote], ["finance", c.financeNote], ["commute", c.commuteNote], ["scenario", c.scenarioNote], ["decision", c.decisionNote]] as const).filter(([topic]) => answer.topics.includes(topic)).map(([, note]) => note);
  /** A citation opens the collapsed provenance it points to; fragment navigation then scrolls and focus follows. */
  function reveal(event: MouseEvent<HTMLDivElement>) {
    const link = (event.target as HTMLElement).closest<HTMLAnchorElement>("a[data-citation-ref]");
    // Anchor ids are built from encoded evidence ids, so the raw hash is the id.
    const target = link ? document.getElementById(link.getAttribute("href")!.slice(1)) : null;
    if (!target) return;
    for (let node = target.parentElement; node; node = node.parentElement) if (node instanceof HTMLDetailsElement) node.open = true;
    requestAnimationFrame(() => target.focus());
  }
  function factLabel(fact: KeyFact) {
    if (fact.kind === "asking_unit") return a.askingUnit;
    if (fact.kind === "market_band") return a.savedBand;
    if (fact.kind === "commute") return a.savedRoute;
    const row = rowFor(fact.refs[0]);
    return row ? copilotEvidenceLabel(row.id, row.label, locale) : c.unknown;
  }
  function factValue(fact: KeyFact) {
    if (fact.band) return formatRange(fact.band.low, fact.band.high, fact.band.unit, locale);
    if (fact.kind === "commute" && typeof fact.value === "number") return [formatQuantity(fact.value, fact.unit, locale), fact.context[0], travelMode(fact.context[1], locale)].join(" · ");
    if (fact.kind === "risk") return copilotStatusLabel(fact.states[0], locale);
    if (typeof fact.value === "number") return formatQuantity(fact.value, fact.unit, locale);
    return fact.value ?? c.unknown;
  }
  return <div data-testid="copilot-answer" data-answer-status={view.status} data-headline-kind={view.headline.kind} className={styles.answer} onClick={reveal}>
    <p className={styles.headline} data-testid="copilot-headline"><strong className={styles.status}>{copilotStatusLabel(view.status, locale)}</strong> <span>{headline.text}</span> {cite(view.headline.refs)}</p>
    {headline.note && <p className={styles.note}>{headline.note}</p>}
    {view.headline.qualified && <p className={styles.muted}>{a.qualified}</p>}
    {view.keyFacts.length > 0 && <section aria-label={a.keyFacts} data-testid="copilot-key-facts"><h3>{a.keyFacts}</h3><ul className={styles.facts}>{view.keyFacts.map(fact => <li key={fact.refs.join("|")} data-fact-kind={fact.kind} data-fact-origin={fact.origin}>
      <span className={styles.factLabel}>{factLabel(fact)}</span>
      <span className={styles.value}>{factValue(fact)}</span>
      <span className={styles.factMeta}><span className={styles.chip}>{originLabel(fact.origin, locale)}</span>{fact.origin === "derived" && <span className={styles.muted}>{a.derivedFrom}</span>}{cite(fact.refs)}</span>
    </li>)}</ul></section>}
    {notes.length <= 2 ? notes.map(note => <p key={note} className={styles.muted}>{note}</p>)
      : view.keyFacts.some(fact => fact.kind === "monthly_housing") && <p className={styles.muted}>{c.financeNote}</p>}
    <section aria-label={a.missing} data-testid="copilot-missing-preview"><h3>{a.missing}</h3>
      {view.missingItems.length ? <ul className={styles.missing}>{view.missingItems.map(item => { const row = missing.find(entry => entry.ref === item.ref); return row && <li key={item.ref}><a href={item.href}>{copilotEvidenceLabel(row.id, row.label, locale)}</a> · <span>{copilotStatusLabel(item.status, locale)}</span></li>; })}</ul> : !view.missingTotal && <p className={styles.muted}>{a.noMissing}</p>}
      {view.missingTotal > view.missingItems.length && <p className={styles.muted}>{answerText(a.moreMissing, { count: view.missingTotal - view.missingItems.length })}</p>}
    </section>
    {action && view.nextAction.href && <section aria-label={a.nextAction} data-testid="copilot-next-action" className={styles.next}><h3>{a.nextAction}</h3><a className="ds-button ds-button--secondary ds-button--compact" href={view.nextAction.href} data-next-action={view.nextAction.kind}>{action}</a><p className={styles.muted}>{a.nextActionNote}</p></section>}
    <nav className={styles.actions} aria-label={c.followup}><button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} onClick={() => onFollowup(c.nextMissing)}>{c.nextMissing}</button>{view.followups.map(topic => <button className="ds-button ds-button--secondary ds-button--compact" disabled={pending} key={topic} onClick={() => onFollowup(copilotTopicLabel(topic, locale))}>{copilotTopicLabel(topic, locale)}</button>)}</nav>
    <details open={view.openMissing} data-testid="copilot-missing-all"><summary>{answerText(a.viewAllMissing, { count: missing.length })}</summary>{!used.length && <p>{c.empty}</p>}<ul className={styles.evidence}>{missing.map(row => <li key={row.ref}><a href={row.href}>{copilotEvidenceLabel(row.id, row.label, locale)}</a> · {copilotStatusLabel(row.status, locale)}<p>{c.unknown}</p><p>{row.limitation}</p></li>)}</ul></details>
    <details data-testid="copilot-evidence-ledger"><summary>{answerText(a.fullEvidence, { count: used.length })}</summary>
      {answer.conflicts.length > 0 && <p>{c.conflict}</p>}
      {notes.length > 2 && notes.map(note => <p key={note} className={styles.muted}>{note}</p>)}
      <p className={styles.muted}>{c.numeric}</p>
      {!used.length && <p>{c.empty}</p>}
      <ul className={styles.used}>{used.map((row, position) => <li key={row.ref}><a href={`#${anchor(row)}`} data-citation-ref={row.ref}>[{position + 1}] {copilotEvidenceLabel(row.id, row.label, locale)}</a>: <EvidenceValue row={row} /><span className={styles.chip}>{c.saved}</span><span className={styles.chip}>{source(row)}</span></li>)}</ul>
    </details>
    <details data-testid="copilot-provenance"><summary>{answerText(a.provenance, { count: used.length })}</summary><p className={styles.muted}>{c.provenance}</p><ul className={styles.evidence}>{used.map(row => <li id={anchor(row)} key={row.ref} data-evidence-ref={row.ref} tabIndex={-1}>
      <strong>{copilotEvidenceLabel(row.id, row.label, locale)}</strong> · <EvidenceValue row={row} />
      <p className={styles.chips}><span>{source(row)}</span><span>{c.saved}</span><span>{copilotStatusLabel(row.status, locale)}</span></p>
      <p>{formatEvidenceDate(row.checkedAt, formatDate, c.unknown)} / {formatEvidenceDate(row.updatedAt, formatDate, c.unknown, "source")}</p><p>{c.limitation}: {limitation(row.limitation)}</p><a href={row.href}>{c.inspect}</a>
    </li>)}</ul></details>
  </div>;
}
function EvidenceValue({ row }: { row: CopilotEvidence }) {
  const { locale } = useExperienceLocale();
  return <span className={styles.value}>{typeof row.value === "number" ? formatQuantity(row.value, row.unit, locale) : row.value}</span>;
}
