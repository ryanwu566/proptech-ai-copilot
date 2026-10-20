"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { OnboardingTour } from "@/components/onboarding-tour";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { CommercialButton } from "@/components/design-system/button";
import { DEMO_CASE } from "@/lib/guided-case-simulation";
import { DEMO_COPY, type DemoCopyKey } from "@/lib/guided-case-simulation-copy";
import { TOUR_STEPS, type TourStepId } from "@/lib/guided-tour";
import "./guided-case-simulation.css";

// Zero-provider by construction: this module imports no API client, storage or case repository.
type DemoDraft = { typed: number; confirmed: boolean };
const initialDraft = (): DemoDraft => ({ typed: 0, confirmed: false });

export function GuidedCaseSimulation({ onClose, opener }: { onClose: () => void; opener?: HTMLElement | null }) {
  const { copyFrom, copy } = useExperienceLocale();
  const [draft, setDraft] = useState(initialDraft);
  const text = (key: DemoCopyKey) => copyFrom(DEMO_COPY, key);
  return <OnboardingTour onClose={onClose} opener={opener} presentation={{
    title: text("title"), disclosure: text("disclosure"), exit: text("exit"),
    restart: text("restart"), completed: text("completed"),
    heading: (id) => id === "questionsReport" ? text("reportTitle") : copy(TOUR_STEPS.find(step => step.id === id)!.heading),
    description: (id) => id === "questionsReport" ? text("reportWhy") : copy(TOUR_STEPS.find(step => step.id === id)!.description),
    onRestart: () => setDraft(initialDraft()),
    renderStage: (id) => <SimulationStage id={id} draft={draft} update={(change) => setDraft((value) => ({ ...value, ...change }))} />,
  }} />;
}

function SimulationStage({ id, draft, update }: { id: TourStepId; draft: DemoDraft; update: (change: Partial<DemoDraft>) => void }) {
  const { copyFrom, formatNumber } = useExperienceLocale();
  const text = (key: DemoCopyKey, values?: Record<string, string | number>) => copyFrom(DEMO_COPY, key, values);
  const [reduced, setReduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const typingDone = draft.typed === 32;
  const finishTyping = useEffectEvent(() => update({ typed: 32 }));
  const tick = useEffectEvent(() => update({ typed: Math.min(32, draft.typed + 1) }));
  // Each stage mount owns its timer; changing locale never remounts the stage.
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (id !== "createCase" || typingDone) return;
    if (reduced) { finishTyping(); return; }
    const timer = window.setInterval(tick, 35);
    return () => window.clearInterval(timer);
    // The clock is semantic progress, independent of translated address length.
  }, [id, reduced, typingDone]);

  const money = (amount: number) => text("currency", { amount: formatNumber(amount) });
  const known = (key: typeof DEMO_CASE.known[number]) => key === "price" ? `${text("price")} · ${money(DEMO_CASE.priceTwd)}` : text(key);
  const unknowns = <div className="simulation-evidence">{DEMO_CASE.unknown.map((key) => <article key={key}><h3>{text(key)}</h3><p className="simulation-unknown">{text("unknown")}</p></article>)}</div>;
  return <div className="simulation-stage" data-testid="demo-stage" data-demo-id={DEMO_CASE.demoId}>
    <p className="simulation-badge">{text("badge")}</p>
    {id === "createCase" && <>
      <label className="simulation-field" htmlFor="demo-address">{text("address")}
        <input id="demo-address" data-testid="demo-address" className="ds-control" readOnly autoComplete="off" value={text("addressValue").slice(0, Math.ceil(text("addressValue").length * (reduced ? 1 : draft.typed / 32)))} />
      </label>
      {draft.typed < 32 && !reduced && <CommercialButton variant="tertiary" data-testid="demo-skip-typing" onClick={() => update({ typed: 32 })}>{text("skipTyping")}</CommercialButton>}
      {(draft.typed === 32 || reduced) && <div className="simulation-case" data-testid="demo-created" role="status">
        <p className="simulation-case-status">{text("created")}</p><h3>{text("caseName")}</h3>
        <dl><div><dt>{text("price")}</dt><dd>{money(DEMO_CASE.priceTwd)}</dd></div><div><dt>{text("area")}</dt><dd>{text("areaValue")}</dd></div></dl>
      </div>}
      <p className="simulation-note">{text("typingNote")}</p>
    </>}
    {id === "confirmLocation" && <>
      <dl className="simulation-metrics"><div><dt>{text("address")}</dt><dd>{text("addressValue")}</dd></div><div><dt>{text("interpreted")}</dt><dd>{text("interpretedValue")}</dd></div></dl>
      <label className={`simulation-review${draft.confirmed ? " is-reviewed" : ""}`}><input data-testid="demo-confirm" type="checkbox" checked={draft.confirmed} onChange={(event) => update({ confirmed: event.target.checked })} />{text("confirm")}</label>
      {draft.confirmed && <p role="status" className="simulation-case-status">{text("confirmed")}</p>}
      <p className="simulation-note">{text("confirmBoundary")}</p>
    </>}
    {id === "knownUnknown" && <div className="simulation-split">
      <section aria-labelledby="demo-known"><h3 id="demo-known">{text("knownTitle")}</h3><ul>{DEMO_CASE.known.map((key) => <li key={key}>{known(key)}</li>)}</ul></section>
      <section aria-labelledby="demo-unknown"><h3 id="demo-unknown">{text("unknownTitle")}</h3><ul>{DEMO_CASE.unknown.map((key) => <li key={key} className="simulation-unknown">{text(key)} · {text("unknown")}</li>)}</ul></section>
      <p className="simulation-safe" data-testid="demo-unknown-safe" role="note">{text("unknownSafe")}</p>
    </div>}
    {id === "marketRisk" && <>
      <div className="simulation-evidence">{DEMO_CASE.comparablesWan.map((value, index) => <article key={index} style={{ "--order": index } as React.CSSProperties}>
        <h3>{text("comparable", { amount: index + 1 })}</h3><strong>{money(value * 10_000)}</strong>
        <div className="simulation-bar" aria-hidden="true"><span style={{ width: `${value / 20}%` }} /></div>
      </article>)}</div><p className="simulation-note">{text("marketLimit")}</p>
      {unknowns}<p className="simulation-note">{text("riskLimit")}</p>
    </>}
    {id === "questionsReport" && <>
      <section className="simulation-questions" aria-labelledby="demo-questions"><h3 id="demo-questions">{text("questionsTitle")}</h3>
        <ol>{DEMO_CASE.questions.map((key) => <li key={key}>{text(key)}</li>)}</ol><p className="simulation-note">{text("compareNote")}</p>
      </section>
      <article className="simulation-report">
        <p className="simulation-case-status">{text("done")}</p><h3>{text("reportTitle")}</h3>
        <p>{text("caseName")} · {text("price")} · {money(DEMO_CASE.priceTwd)}</p>
        <p className="simulation-unknown">{text("flood")} · {text("unknown")}</p>
        <p className="simulation-conclusion">{text("conclusion")}</p><p className="simulation-note">{text("reportBoundary")}</p>
      </article>
    </>}
    {id !== "questionsReport" && <p className="simulation-next"><span aria-hidden="true">→ </span>{text(`${id}Next`)}</p>}
  </div>;
}
