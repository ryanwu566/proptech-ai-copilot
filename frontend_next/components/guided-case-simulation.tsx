"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { OnboardingTour } from "@/components/onboarding-tour";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { CommercialButton } from "@/components/design-system/button";
import { DEMO_CASE } from "@/lib/guided-case-simulation";
import { DEMO_COPY, type DemoCopyKey } from "@/lib/guided-case-simulation-copy";
import { TOUR_STEPS, type TourStepId } from "@/lib/guided-tour";
import "./guided-case-simulation.css";

type DemoDraft = { typed: number; down: number; reviewed: boolean };
const initialDraft = (): DemoDraft => ({ typed: 0, down: DEMO_CASE.downPaymentPercent, reviewed: false });
const topics = { propertyCase: "property", marketEvidence: "market", locationCommute: "location", terrainRisk: "risk", finance: "finance", verificationChecklist: "verify", saveCompareReport: "report" } as const;

export function GuidedCaseSimulation({ onClose, opener }: { onClose: () => void; opener?: HTMLElement | null }) {
  const { copyFrom, copy } = useExperienceLocale();
  const [draft, setDraft] = useState(initialDraft);
  const text = (key: DemoCopyKey) => copyFrom(DEMO_COPY, key);
  return <OnboardingTour onClose={onClose} opener={opener} presentation={{
    title: text("title"), disclosure: text("disclosure"), exit: text("exit"),
    restart: text("restart"), completed: text("completed"),
    heading: (id) => id === "saveCompareReport" ? text("reportTitle") : copy(TOUR_STEPS.find(step => step.id === id)!.heading),
    description: (id) => id === "saveCompareReport" ? text("reportWhy") : copy(TOUR_STEPS.find(step => step.id === id)!.description),
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
    if (id !== "propertyCase" || typingDone) return;
    if (reduced) { finishTyping(); return; }
    const timer = window.setInterval(tick, 35);
    return () => window.clearInterval(timer);
    // The clock is semantic progress, independent of translated address length.
  }, [id, reduced, typingDone]);

  const stage = topics[id];
  const money = (amount: number) => text("currency", { amount: formatNumber(amount) });
  const next = `${stage}Next` as DemoCopyKey;
  return <div className="simulation-stage" data-testid="demo-stage" data-demo-id={DEMO_CASE.demoId}>
    <p className="simulation-badge">{text("badge")}</p>
    {id === "propertyCase" && <>
      <label className="simulation-field" htmlFor="demo-address">{text("address")}
        <input id="demo-address" data-testid="demo-address" className="ds-control" readOnly autoComplete="off" value={text("addressValue").slice(0, Math.ceil(text("addressValue").length * (reduced ? 1 : draft.typed / 32)))} />
      </label>
      {draft.typed < 32 && !reduced && <CommercialButton variant="tertiary" data-testid="demo-skip-typing" onClick={() => update({ typed: 32 })}>{text("skipTyping")}</CommercialButton>}
      {(draft.typed === 32 || reduced) && <div className="simulation-case" data-testid="demo-created" role="status">
        <p className="simulation-case-status">{text("created")}</p><h3>{text("caseName")}</h3>
        <dl><div><dt>{text("price")}</dt><dd>{money(DEMO_CASE.priceTwd)}</dd></div><div><dt>{text("area")}</dt><dd>{text("areaValue")}</dd></div></dl>
      </div>}
    </>}
    {id === "marketEvidence" && <>
      <div className="simulation-evidence">{DEMO_CASE.comparablesWan.map((value, index) => <article key={index} style={{ "--order": index } as React.CSSProperties}>
        <h3>{text("comparable", { amount: index + 1 })}</h3><strong>{money(value * 10_000)}</strong>
        <div className="simulation-bar" aria-hidden="true"><span style={{ width: `${value / 20}%` }} /></div>
      </article>)}</div><p className="simulation-note">{text("marketLimit")}</p>
    </>}
    {id === "locationCommute" && <>
      <div className="simulation-route" aria-hidden="true"><i /><span /><i /><span /><i /></div>
      <dl className="simulation-metrics"><div><dt>{text("walk")}</dt><dd>{text("minutes", { amount: DEMO_CASE.walkMinutes })}</dd></div><div><dt>{text("commute")}</dt><dd>{text("minutes", { amount: DEMO_CASE.commuteMinutes })}</dd></div></dl>
      <p className="simulation-note">{text("locationLimit")}</p>
    </>}
    {id === "terrainRisk" && <div className="simulation-evidence">{(["flood", "slope"] as const).map((key) => <article key={key}><h3>{text(key)}</h3><p className="simulation-unknown">{text("unknown")}</p></article>)}</div>}
    {id === "finance" && <>
      <label className="simulation-field" htmlFor="demo-down">{text("down")} · {formatNumber(draft.down)}%
        <input id="demo-down" data-testid="demo-down" type="range" min={20} max={50} step={5} value={draft.down} aria-valuetext={`${formatNumber(draft.down)}%`} onChange={(event) => update({ down: Number(event.target.value) })} />
      </label>
      <dl className="simulation-metrics"><div><dt>{text("cash")}</dt><dd>{money(DEMO_CASE.priceTwd * draft.down / 100)}</dd></div><div><dt>{text("loan")}</dt><dd>{money(DEMO_CASE.priceTwd * (100 - draft.down) / 100)}</dd></div></dl>
      <p className="simulation-note">{text("financeLimit")}</p>
    </>}
    {id === "verificationChecklist" && <>
      <label className={`simulation-review${draft.reviewed ? " is-reviewed" : ""}`}><input data-testid="demo-review" type="checkbox" checked={draft.reviewed} onChange={(event) => update({ reviewed: event.target.checked })} />{text("review")}</label>
      {draft.reviewed && <p role="status" className="simulation-case-status">{text("reviewed")}</p>}
      <p className="simulation-unknown">{text("flood")} · {text("unknown")}</p><p className="simulation-note">{text("reviewBoundary")}</p>
    </>}
    {id === "saveCompareReport" && <article className="simulation-report">
      <p className="simulation-case-status">{text("done")}</p><h3>{text("reportTitle")}</h3>
      <p>{text("caseName")} · {text("price")} · {money(DEMO_CASE.priceTwd)}</p>
      <p>{text("cash")} · {money(DEMO_CASE.priceTwd * draft.down / 100)}</p>
      <p className="simulation-unknown">{text("flood")} · {text("unknown")}</p>
      <p className="simulation-conclusion">{text("conclusion")}</p><p className="simulation-note">{text("reportBoundary")}</p>
    </article>}
    {id !== "saveCompareReport" && <p className="simulation-next"><span aria-hidden="true">→ </span>{text(next)}</p>}
  </div>;
}
