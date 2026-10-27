"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { StatusLabel } from "@/components/design-system/status-label";
import type { VisualRole } from "@/components/design-system/types";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { formatMonthlyTwd } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { getMarketDisplayState } from "@/lib/market-result-state";
import { isActiveRun, isTerminalStep, type AutoBriefRun, type AutoBriefStep, type AutoBriefStepId } from "@/lib/workspace/auto-brief";
import type { autoBriefCopy } from "@/lib/workspace/auto-brief-copy";
import { nextScene, presentRail, RAIL_SCENE, sceneHold, plotNearby, railItems, sceneStep, targetScene, type AutoBriefScene, type RailStatus } from "@/lib/workspace/auto-brief-presentation";
import { NEARBY_POI_STYLES, NEARBY_PROPERTY_STYLE, nearbyPoiIconSvg } from "@/lib/workspace/nearby-poi-category";
import { buildWorkspaceOverview, type OverviewItem } from "@/lib/workspace/overview-model";
import { hazardName, presentMonthlyTwd, presentOverviewItem } from "@/lib/workspace/overview-presentation";
import { formatDemographicsCount, formatDemographicsMonth, formatDemographicsRatio } from "@/lib/workspace/village-demographics";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import styles from "./auto-brief-stage.module.css";

export type Translate = (key: keyof typeof autoBriefCopy.en, values?: Record<string, string | number>) => string;

const ROLE: Record<RailStatus, VisualRole> = {
  pending: "neutral", running: "information", available: "success", partial: "warning", no_data: "warning", unavailable: "error", needs_input: "warning", skipped: "disabled", needs_location: "warning",
};
/** A text glyph per status so state never depends on colour alone. */
const GLYPH: Record<RailStatus, string> = { pending: "○", running: "◐", available: "●", partial: "◑", no_data: "◌", unavailable: "✕", needs_input: "!", skipped: "–", needs_location: "!" };

function Status({ c, status }: { c: Translate; status: RailStatus }) {
  return <StatusLabel semanticRole={ROLE[status]} icon={<span aria-hidden="true">{GLYPH[status]}</span>}>{c(`status_${status}`)}</StatusLabel>;
}

/** Walks the displayed scene toward the real one, one short beat per scene; never ahead of the run. */
function useDisplayedScene(target: AutoBriefScene, motion: boolean, paused: boolean, showcase: boolean, fromStart: boolean): AutoBriefScene {
  // A run this viewer just started plays from the lock-in even if it already finished (a fixture run ends at once);
  // a reopened run shows where it is.
  const [shown, setShown] = useState<AutoBriefScene>(fromStart && motion && target !== "halted" ? "lockin" : target);
  useEffect(() => {
    const next = nextScene(shown, target, motion);
    if (next.scene === shown) return;
    if (!next.wait) { setShown(next.scene); return; }
    if (paused) return;
    const timer = window.setTimeout(() => setShown(next.scene), sceneHold(shown, showcase));
    return () => window.clearTimeout(timer);
  }, [shown, target, motion, paused, showcase]);
  return shown;
}

export type AutoBriefStageActions = {
  cancel(): void;
  start(): void;
  continueRun(): void;
  retry(id: AutoBriefStepId): void;
  canRestart: boolean;
};

/** Showcase-only end of story: the demo hands off to Compare, Report or the visitor's own property. */
export type ShowcaseLinks = { compareHref: string; reportHref: string; homeHref: string };

export function AutoBriefStage({ c, run, workspace, motion, paused, onPause, onSkip, actions, manualHref, briefHref, moneyHref, showcase, fromStart = false }: {
  c: Translate; run: AutoBriefRun; workspace: PropertyCaseWorkspace; motion: boolean; paused: boolean; showcase?: ShowcaseLinks; fromStart?: boolean;
  onPause(): void; onSkip(): void; actions: AutoBriefStageActions; manualHref: string; briefHref: string; moneyHref: string;
}) {
  const target = targetScene(run);
  const shown = useDisplayedScene(target, motion, paused, Boolean(showcase), fromStart);
  const active = isActiveRun(run.status);
  // The presentation may trail the run (always in a showcase, where a fixture run ends at once).
  const presenting = shown !== target;
  // After a run ends, each finished chapter can be reopened; a new run always returns to the live scene.
  const [review, setReview] = useState<AutoBriefScene | null>(null);
  useEffect(() => { if (active) setReview(null); }, [active]);
  const visible = !active && !presenting && review ? review : shown;
  const rail = showcase && presenting ? presentRail(railItems(run), shown) : railItems(run);
  const root = useRef<HTMLDivElement>(null);
  const wasPresenting = useRef(presenting);
  // When the presentation catches up its controls go away; keep keyboard focus on the result instead of the page body.
  useEffect(() => {
    if (wasPresenting.current && !presenting && (document.activeElement === document.body || document.activeElement === null)) {
      root.current?.querySelector<HTMLElement>("[data-auto-brief-primary]")?.focus({ preventScroll: true });
    }
    wasPresenting.current = presenting;
  }, [presenting]);
  const current = rail.find((item) => item.current);
  const stepOf = (id: AutoBriefStepId) => run.steps.find((step) => step.id === id)!;

  return <div ref={root} className={styles.stage} data-testid="auto-brief-stage" data-scene={visible} data-motion={motion ? "on" : "off"} data-showcase={showcase ? "on" : undefined}>
    <div className={styles.live} role="status" aria-live="polite" data-testid="auto-brief-status">
      <strong>{c(showcase && presenting ? "run_running" : `run_${run.status}`)}</strong>
      {current && <span> · {c("currentStage", { stage: c(`rail_${current.id}`) })}</span>}
      {run.reason && run.reason !== "cancelled" && !active && <p className="text-helper">{c(`reason_${run.reason}`)}</p>}
    </div>

    <ol className={styles.rail} aria-label={c("progress")}>
      {rail.map((item) => <li key={item.id} className={styles.railItem} data-testid={item.id === "lockin" ? "auto-brief-rail-lockin" : `auto-brief-step-${item.id}`}
        data-status={item.status} aria-current={item.current ? "step" : undefined}>
        {!active && !presenting && item.status !== "pending" && item.status !== "skipped" && item.status !== "needs_location" && shown !== "halted"
          ? <button type="button" className={styles.railButton} aria-pressed={visible === RAIL_SCENE[item.id]} onClick={() => setReview(RAIL_SCENE[item.id])} data-testid={`auto-brief-review-${item.id}`}>{c(`rail_${item.id}`)}</button>
          : <span className={styles.railLabel}>{c(`rail_${item.id}`)}</span>}
        <Status c={c} status={item.status} />
        {item.id === "location" && stepOf("location").parts && <span className="text-helper">{c("part_nearby")}: {c(`status_${stepOf("location").parts!.nearby}`)} · {c("part_demographics")}: {c(`status_${stepOf("location").parts!.demographics}`)}{stepOf("location").reused ? ` · ${c("reused")}` : ""}</span>}
      </li>)}
    </ol>

    <div className={styles.screen} data-testid="auto-brief-screen">
      <div key={visible} className={styles.scene} data-testid={`auto-brief-scene-${visible}`}>
        {review && !active && review !== shown && <CommercialButton variant="tertiary" size="compact" className={styles.back} onClick={() => setReview(null)} data-testid="auto-brief-back">{c("backToResult")}</CommercialButton>}
        {showcase && visible !== "halted" && <p className={styles.narration} data-testid="auto-brief-narration">{c(`narr_${visible}`)}</p>}
        <SceneBody c={c} scene={visible} run={run} workspace={workspace} actions={actions} briefHref={briefHref} moneyHref={moneyHref} manualHref={manualHref} lockinStatus={rail[0].status} showcase={showcase} />
      </div>
    </div>

    <div className={styles.context}>
      <h3 className="text-subsection">{c("sourceContext")}</h3>
      <SourceContext c={c} run={run} workspace={workspace} />
      {(active || presenting) && <div className={styles.controls} role="group" aria-label={c("controls")}>
        {active && <CommercialButton data-auto-brief-cancel variant="secondary" size="touch" onClick={actions.cancel} data-testid="auto-brief-cancel">{c("cancel")}</CommercialButton>}
        <CommercialButton data-auto-brief-control variant="tertiary" size="touch" disabled={!motion} aria-pressed={paused} onClick={onPause} data-testid="auto-brief-pause">{c(paused ? "resume" : "pause")}</CommercialButton>
        <CommercialButton data-auto-brief-control variant="tertiary" size="touch" aria-pressed={!motion} disabled={!motion} onClick={onSkip} data-testid="auto-brief-skip">{c("skip")}</CommercialButton>
      </div>}
    </div>
  </div>;

}

function SceneBody({ c, scene, run, workspace, actions, briefHref, moneyHref, manualHref, lockinStatus, showcase }: {
  c: Translate; scene: AutoBriefScene; run: AutoBriefRun; workspace: PropertyCaseWorkspace; actions: AutoBriefStageActions;
  briefHref: string; moneyHref: string; manualHref: string; lockinStatus: RailStatus; showcase?: ShowcaseLinks;
}) {
  const id = sceneStep(scene);
  const step = id ? run.steps.find((row) => row.id === id)! : null;
  // Evidence appears only once the scene's own step is terminal; until then the scene waits.
  const ready = !step || isTerminalStep(step.status);
  const header = (title: string, status: RailStatus | null = step?.status ?? null) => <header className={styles.sceneHeader}>
    <h3 className="text-section">{title}</h3>
    {status && <Status c={c} status={status} />}
  </header>;
  const waiting = <p className={styles.waiting} aria-busy="true">{c("waiting")}</p>;
  if (scene === "lockin") return <>{header(c("scene_lockin"), lockinStatus)}<LockIn c={c} workspace={workspace} /></>;
  if (scene === "halted") return <Halted c={c} run={run} actions={actions} manualHref={manualHref} />;
  if (scene === "complete") return <Completion c={c} run={run} workspace={workspace} actions={actions} briefHref={briefHref} moneyHref={moneyHref} manualHref={manualHref} showcase={showcase} />;
  if (scene === "market") return <>{header(c("scene_market"))}{ready ? <MarketEvidence c={c} step={step!} workspace={workspace} /> : waiting}</>;
  if (scene === "location") return <>{header(c("scene_location"))}{ready ? <LocationEvidence c={c} step={step!} workspace={workspace} /> : <><PropertyStage points={[]} />{waiting}</>}</>;
  if (scene === "risk") return <>{header(c("scene_risk"))}{ready ? <RiskEvidence c={c} step={step!} workspace={workspace} /> : waiting}</>;
  if (scene === "money") return <>{header(c("scene_money"))}{ready ? <MoneyEvidence c={c} step={step!} workspace={workspace} /> : waiting}</>;
  return <>{header(c("scene_converge"))}<Convergence c={c} run={run} /></>;
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return <div className={styles.fact}><dt>{label}</dt><dd>{value}</dd></div>;
}

function LockIn({ c, workspace }: { c: Translate; workspace: PropertyCaseWorkspace }) {
  const anchor = workspace.identity.anchor;
  const area = anchor?.administrative_location;
  return <div className={styles.lockin}>
    <PropertyStage points={[]} settle />
    <div className={styles.lockinCard}>
      <p className={styles.address}>{anchor?.normalized_address ?? workspace.displayAddress}</p>
      <dl className={styles.facts}>
        <Fact label={c("district")} value={[area?.city, area?.district].filter(Boolean).join(" ") || c("unknownValue")} />
        <Fact label={c("village")} value={area?.village || c("unknownValue")} />
        <Fact label={c("coordinates")} value={anchor?.coordinates ? <span data-numeric>{anchor.coordinates.latitude.toFixed(5)}, {anchor.coordinates.longitude.toFixed(5)}</span> : c("unknownValue")} />
      </dl>
      <p className="text-helper">{c("lockinNote")}</p>
    </div>
  </div>;
}

function Reason({ c, step }: { c: Translate; step: AutoBriefStep }) {
  return step.reason && step.status !== "available" && step.reason !== "cancelled" ? <p className="text-helper">{c(`reason_${step.reason}`)}</p> : null;
}

function MarketEvidence({ c, step, workspace }: { c: Translate; step: AutoBriefStep; workspace: PropertyCaseWorkspace }) {
  const result = workspace.marketPrice.market.result;
  const shows = result && (step.status === "available" || step.status === "partial");
  return <div className={styles.evidence}>
    {shows ? <>
      <p className={styles.badge} data-testid="auto-brief-market-state">{c(`market_${getMarketDisplayState(result)}`)}</p>
      <dl className={styles.facts}>
        <Fact label={c("marketPeriod")} value={result.period || c("unknownValue")} />
        <Fact label={c("marketSample")} value={typeof result.transaction_count === "number" ? <span data-numeric>{result.transaction_count}</span> : c("unknownValue")} />
        <Fact label={c("marketSource")} value={result.source_name || c("unknownValue")} />
      </dl>
      <p className="text-helper">{c("marketNote")}</p>
    </> : <p className={styles.badge} data-testid="auto-brief-market-state">{c(step.status === "no_data" ? "market_no_data" : "market_unavailable")}</p>}
    <Reason c={c} step={step} />
  </div>;
}

function PropertyStage({ points, settle = false }: { points: ReturnType<typeof plotNearby>["points"]; settle?: boolean }) {
  // Static, trusted SVG from the palette module; no provider text is interpolated.
  return <div className={styles.plot} data-settle={settle || undefined} aria-hidden="true">
    <span className={styles.ring} style={{ "--r": "100%" } as CSSProperties} />
    <span className={styles.ring} style={{ "--r": "62%" } as CSSProperties} />
    <span className={styles.ring} style={{ "--r": "28%" } as CSSProperties} />
    {points.map((point) => <span key={point.id} className={styles.poi} style={{ left: `${point.x}%`, top: `${point.y}%`, "--wave": point.wave } as CSSProperties}
      dangerouslySetInnerHTML={{ __html: nearbyPoiIconSvg(NEARBY_POI_STYLES[point.kind], 18) }} />)}
    <span className={styles.property} dangerouslySetInnerHTML={{ __html: nearbyPoiIconSvg(NEARBY_PROPERTY_STYLE, 30, "pin") }} />
  </div>;
}

function LocationEvidence({ c, step, workspace }: { c: Translate; step: AutoBriefStep; workspace: PropertyCaseWorkspace }) {
  const { locale } = useExperienceLocale();
  const nearby = workspace.location.nearbyFacilities;
  const plot = plotNearby(nearby);
  const demographics = workspace.location.villageDemographics?.demographics;
  const available = demographics?.status === "available" ? demographics : null;
  const ages = available ? [["ageChild", available.child_ratio], ["ageWorking", available.working_age_ratio], ["ageElderly", available.elderly_ratio]] as const : [];
  return <div className={styles.locationGrid}>
    <div>
      <PropertyStage points={plot.points} />
      <p className="text-helper">{c("nearbyRadius", { radius: nearby?.radiusM ?? 800 })}</p>
    </div>
    <div className={styles.evidence}>
      <h4 className="text-subsection">{c("nearbyTitle")}</h4>
      {plot.groups.length ? <ul className={styles.legend} data-testid="auto-brief-poi-legend">
        {plot.groups.map((row) => {
          const kind = nearby!.places.find((place) => plot.points.some((point) => point.id === place.id && point.group === row.group))?.kind ?? "other";
          return <li key={row.group} data-group={row.group} style={{ "--wave": row.wave } as CSSProperties}>
            <span aria-hidden="true" dangerouslySetInnerHTML={{ __html: nearbyPoiIconSvg(NEARBY_POI_STYLES[kind], 16) }} />
            <span>{c(`group_${row.group}`)}</span><span data-numeric>{row.count}</span>
          </li>;
        })}
      </ul> : <p className="text-helper">{c("noNearby")}</p>}
      <h4 className="text-subsection">{c("populationTitle")}</h4>
      {available ? <div data-testid="auto-brief-demographics">
        <dl className={styles.facts}>
          <Fact label={c("population")} value={<span data-numeric>{formatDemographicsCount(available.total_population, locale) ?? c("unknownValue")}</span>} />
          <Fact label={c("households")} value={<span data-numeric>{formatDemographicsCount(available.household_count, locale) ?? c("unknownValue")}</span>} />
        </dl>
        <ul className={styles.ages}>{ages.map(([key, ratio]) => <li key={key}>
          <span>{c(key)}</span><span className={styles.bar} style={{ "--share": `${Math.round((ratio ?? 0) * 100)}%` } as CSSProperties} aria-hidden="true" /><span data-numeric>{formatDemographicsRatio(ratio) ?? c("unknownValue")}</span>
        </li>)}</ul>
        <p className="text-helper">{c("statMonth", { month: formatDemographicsMonth(available.statistic_yyymm, locale) ?? c("unknownValue") })}</p>
      </div> : <p className="text-helper" data-testid="auto-brief-demographics-none">{c("noDemographics")}</p>}
      <Reason c={c} step={step} />
    </div>
  </div>;
}

function RiskEvidence({ c, step, workspace }: { c: Translate; step: AutoBriefStep; workspace: PropertyCaseWorkspace }) {
  const { locale } = useExperienceLocale();
  const rows = step.status === "available" || step.status === "partial" ? workspace.risk?.rows ?? [] : [];
  return <div className={styles.evidence}>
    {rows.length ? <ul className={styles.layers} data-testid="auto-brief-risk-layers">
      {rows.map((row, index) => {
        const evidence = resolveCommercialState("evidence", row.usability);
        const reading = resolveCommercialState("risk", row.interpretation);
        // Never a green "all clear": a match needs attention, everything else stays neutral or a caution.
        const role: VisualRole = row.matched ? "warning" : row.usability === "no_match" || row.usability === "usable" ? "neutral" : "warning";
        return <li key={row.key} data-layer={row.key} data-usability={row.usability} style={{ "--i": index } as CSSProperties}>
          <span className={styles.layerName}>{hazardName(row.key, locale, row.label)}</span>
          <StatusLabel semanticRole={role}>{evidence.label[locale]}</StatusLabel>
          <span className="text-helper">{reading.label[locale]}</span>
        </li>;
      })}
    </ul> : <p className={styles.badge}>{c(step.status === "no_data" ? "status_no_data" : rows.length === 0 && (step.status === "available" || step.status === "partial") ? "riskNone" : "status_unavailable")}</p>}
    <p className="text-helper">{c("riskNote")}</p>
    <Reason c={c} step={step} />
  </div>;
}

function MoneyEvidence({ c, step, workspace }: { c: Translate; step: AutoBriefStep; workspace: PropertyCaseWorkspace }) {
  const { locale } = useExperienceLocale();
  const finance = workspace.finance;
  if (step.status === "needs_input" || !finance) return <div className={styles.pauseCard} data-testid="auto-brief-money-missing">
    <p className={styles.badge}>{c("moneyMissingTitle")}</p>
    <p className="text-dense">{c("moneyMissing")}</p>
    <Reason c={c} step={step} />
  </div>;
  const monthly = (value: number | null) => locale === "zh-TW" ? formatMonthlyTwd(value) : presentMonthlyTwd(value, locale);
  return <div className={styles.evidence}>
    <dl className={styles.facts}>
      <Fact label={c("moneyPayment")} value={<span data-numeric>{monthly(finance.loan.monthlyPaymentTwd)}</span>} />
      <Fact label={c("moneyHolding")} value={<span data-numeric>{monthly(finance.holding.knownMonthlySubtotalTwd)}</span>} />
    </dl>
    <p className="text-helper">{c(finance.affordability.status === "assessed" ? "moneyAssessed" : "moneyUnassessed")}</p>
    <Reason c={c} step={step} />
  </div>;
}

const DOMAINS: AutoBriefStepId[] = ["market", "location", "risk", "money"];

function Convergence({ c, run }: { c: Translate; run: AutoBriefRun }) {
  return <div className={styles.converge}>
    <ul className={styles.tiles}>
      {DOMAINS.map((id, index) => <li key={id} style={{ "--i": index } as CSSProperties} data-status={run.steps.find((step) => step.id === id)!.status}>
        <span>{c(`rail_${id}`)}</span><Status c={c} status={run.steps.find((step) => step.id === id)!.status} />
      </li>)}
    </ul>
    <div className={styles.briefCard}><strong>{c("briefTarget")}</strong><p className="text-helper">{c("convergeText")}</p></div>
  </div>;
}

function Completion({ c, run, workspace, actions, briefHref, moneyHref, manualHref, showcase }: { c: Translate; run: AutoBriefRun; workspace: PropertyCaseWorkspace; actions: AutoBriefStageActions; briefHref: string; moneyHref: string; manualHref: string; showcase?: ShowcaseLinks }) {
  const gaps = run.steps.filter((step) => step.status !== "available");
  const retryable = run.steps.filter((step) => step.retryable);
  const money = run.steps.find((step) => step.id === "money");
  return <div className={styles.completion} data-testid="auto-brief-completion" data-ending={run.status}>
    <header className={styles.sceneHeader}><h3 className="text-section">{c(`run_${run.status}`)}</h3></header>
    <p className="text-body">{c(run.status === "completed" ? "leadCompleted" : "leadGaps")}</p>
    {run.gapCount !== null && <p className="text-helper" data-testid="auto-brief-gaps">{run.gapCount ? c("gaps", { count: run.gapCount }) : c("noGaps")}</p>}
    {gaps.length > 0 && <div><h4 className="text-subsection">{c("remaining")}</h4>
      <ul className={styles.gapList}>{gaps.map((step) => <li key={step.id}><span>{c(`rail_${step.id}`)}</span><Status c={c} status={step.status} /></li>)}</ul></div>}
    <BriefDigest c={c} workspace={workspace} />
    <div className={styles.actions}>
      <Link data-auto-brief-primary prefetch={false} className="ds-button ds-button--primary ds-button--touch" href={briefHref} data-testid="auto-brief-view-brief">{c("viewBrief")}</Link>
      {showcase ? <>
        <Link prefetch={false} className="ds-button ds-button--secondary ds-button--touch" href={showcase.compareHref} data-testid="auto-brief-compare">{c("compareDemo")}</Link>
        <Link prefetch={false} className="ds-button ds-button--secondary ds-button--touch" href={showcase.reportHref} data-testid="auto-brief-report">{c("openReport")}</Link>
        {actions.canRestart && <CommercialButton variant="tertiary" size="touch" onClick={actions.start} data-testid="auto-brief-replay">{c("replay")}</CommercialButton>}
        <Link prefetch={false} className="ds-button ds-button--tertiary ds-button--touch" href={showcase.homeHref} data-testid="auto-brief-analyze-own">{c("analyzeOwn")}</Link>
      </> : <>
        <Link prefetch={false} className="ds-button ds-button--secondary ds-button--touch" href={manualHref} data-testid="auto-brief-manual">{c("manual")}</Link>
        {money?.status === "needs_input" && <Link prefetch={false} className="ds-button ds-button--secondary ds-button--touch" href={moneyHref} data-testid="auto-brief-go-money">{c("goMoney")}</Link>}
        {actions.canRestart && <CommercialButton variant="tertiary" size="touch" onClick={actions.start} data-testid="auto-brief-restart">{c("restart")}</CommercialButton>}
      </>}
    </div>
    {!showcase && retryable.length > 0 && actions.canRestart && <div role="group" aria-label={c("retryIncomplete")} className={styles.actions}>
      {retryable.map((step) => <CommercialButton key={step.id} variant="tertiary" size="compact" onClick={() => actions.retry(step.id)} aria-label={c("retryStep", { step: c(`rail_${step.id}`) })} data-testid={`auto-brief-retry-${step.id}`}>{c("retry")} · {c(`rail_${step.id}`)}</CommercialButton>)}
    </div>}
  </div>;
}

function Halted({ c, run, actions, manualHref }: { c: Translate; run: AutoBriefRun; actions: AutoBriefStageActions; manualHref: string }) {
  const resumable = run.status === "interrupted" || run.status === "cancelled";
  return <div className={styles.completion} data-testid="auto-brief-halted">
    <header className={styles.sceneHeader}><h3 className="text-section">{c(`run_${run.status}`)}</h3></header>
    <div className={styles.actions}>
      {resumable && actions.canRestart && <CommercialButton data-auto-brief-primary size="touch" onClick={actions.continueRun} data-testid="auto-brief-continue">{c("continue")}</CommercialButton>}
      {actions.canRestart && <CommercialButton variant="secondary" size="touch" onClick={actions.start} data-testid="auto-brief-restart">{c("restart")}</CommercialButton>}
      <Link prefetch={false} className="ds-button ds-button--tertiary ds-button--touch" href={manualHref} data-testid="auto-brief-manual">{c("manual")}</Link>
    </div>
  </div>;
}

function SourceContext({ c, run, workspace }: { c: Translate; run: AutoBriefRun; workspace: PropertyCaseWorkspace }) {
  const status = (id: AutoBriefStepId) => run.steps.find((step) => step.id === id)!.status;
  const market = workspace.marketPrice.market.result?.source_name;
  const demographics = workspace.location.villageDemographics?.demographics;
  const rows: Array<[string, string | null]> = [
    [c("rail_market"), status("market") === "pending" ? null : market ?? null],
    [c("part_nearby"), status("location") === "pending" || !workspace.location.nearbyFacilities ? null : "Google Places"],
    [c("part_demographics"), status("location") === "pending" || demographics?.status !== "available" ? null : demographics.source_provider],
  ];
  return <dl className={styles.facts}>{rows.map(([label, value]) => <Fact key={label} label={label} value={value ?? "—"} />)}</dl>;
}

/** The final brief at a glance, from the same Overview model the full Brief uses. Nothing is ranked or added. */
function BriefDigest({ c, workspace }: { c: Translate; workspace: PropertyCaseWorkspace }) {
  const { locale } = useExperienceLocale();
  const overview = buildWorkspaceOverview(workspace);
  const groups: Array<[keyof typeof autoBriefCopy.en, OverviewItem[], string]> = [
    ["digestKnown", overview.known, "known"],
    ["digestAttention", [...overview.blockers, ...overview.attention], "attention"],
    ["digestUnknown", overview.unknown, "unknown"],
    ["digestQuestions", overview.actions, "questions"],
  ];
  return <section className={styles.digest} aria-label={c("digestTitle")} data-testid="auto-brief-digest">
    <h4 className="text-subsection">{c("digestTitle")}</h4>
    <div className={styles.digestGrid}>{groups.map(([title, items, key]) => <div key={key} className={styles.digestGroup} data-group={key}>
      <h5 className={styles.digestHeading}>{c(title)} <span data-numeric>{items.length}</span></h5>
      {items.length ? <ul>{items.slice(0, 3).map((item) => <li key={item.id}>{presentOverviewItem(item, locale).label}</li>)}</ul> : <p className="text-helper">{c("digestNone")}</p>}
      {items.length > 3 && <p className="text-helper">{c("digestMore", { count: items.length - 3 })}</p>}
    </div>)}</div>
  </section>;
}
