"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "../workspace-provider";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { CommercialButton } from "@/components/design-system/button";
import { Panel, Section } from "@/components/design-system/section";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { buildLocationOverviewHandoff } from "@/lib/workspace/location-context";
import { calculateScenario, emptyScenario, parseScenarioSave, SCENARIO_FIELDS, SCENARIO_STORAGE_KEY, type ScenarioInput, type ScenarioField } from "@/lib/workspace/scenario-model";
import type { ScenarioCopyKey } from "@/lib/workspace/scenario-copy";
import type { CopyCatalogue } from "@/lib/copy-catalogue";
import styles from "./scenario-lab.module.css";

const letters = ["A", "B", "C"];
const metrics = ["purchaseCashTwd", "principalTwd", "paymentTwd", "monthlyOwnershipTwd", "firstYearTwd", "acquisitionTotalTwd", "holdingCashTwd"] as const;
const costMetrics = new Set<string>(["purchaseCashTwd", "monthlyOwnershipTwd", "firstYearTwd", "acquisitionTotalTwd", "holdingCashTwd"]);

type ScenarioLabProps = { catalogue: CopyCatalogue<ScenarioCopyKey> };

export function ScenarioLab({ catalogue }: ScenarioLabProps) {
  const workspace = useWorkspace();
  // Drafts are bound to a property and frozen evidence context, never just price.
  const context = JSON.stringify([workspace.caseId, workspace.revision, workspace.updatedAt, workspace.identity, workspace.assumptions, workspace.finance, workspace.location.routeEvidence]);
  return <ScenarioEditor key={context} context={context} catalogue={catalogue} />;
}

function ScenarioEditor({ context, catalogue }: ScenarioLabProps & { context: string }) {
  const workspace = useWorkspace();
  const { locale, copyFrom, formatNumber, formatDate } = useExperienceLocale();
  const c = (key: ScenarioCopyKey) => copyFrom(catalogue, key);
  const finance = workspace.finance;
  const savedPrice = finance?.savedAssumptions?.amountWan ?? finance?.loan.propertyPriceWan ?? null;
  const askingTwd = workspace.assumptions.askingPriceWan == null ? null : workspace.assumptions.askingPriceWan * 10000;
  const seedPrice = askingTwd ?? (workspace.assumptions.activePriceWan == null ? null : workspace.assumptions.activePriceWan * 10000);
  const compatibleLoan = finance?.freshness.status === "current" && finance.loan.status === "available" && finance.loan.gracePeriodYears === 0;
  const initial: ScenarioInput = {
    ...emptyScenario(), offerTwd: seedPrice,
    downValue: compatibleLoan && finance.loan.downPaymentRatio !== null ? finance.loan.downPaymentRatio * 100 : null,
    ratePercent: compatibleLoan ? finance.loan.annualInterestRate : null,
    loanYears: compatibleLoan ? finance.loan.loanYears : null,
  };
  const [drafts, setDrafts] = useState<ScenarioInput[]>(() => letters.map(() => ({ ...initial })));
  const [baseline, setBaseline] = useState<ScenarioInput | null>(null);
  const [status, setStatus] = useState<"savedStatus" | "failed" | "damaged" | null>(null);
  const storageKey = `${SCENARIO_STORAGE_KEY}:${workspace.caseId}`;
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      const stored = parseScenarioSave(raw, context);
      if (stored) { setDrafts(stored.drafts); setBaseline(stored.baseline); }
      else if (raw) setStatus("damaged");
    } catch { setStatus("failed"); }
  }, [context, storageKey]);

  const results = drafts.map(calculateScenario);
  const baselineResult = baseline ? calculateScenario(baseline) : null;
  const route = buildLocationOverviewHandoff(workspace).selectedRoute;
  const acceptedMinutes = route && Number.isFinite(route.durationMinutes) && route.durationMinutes >= 0 ? route.durationMinutes : null;
  const money = (value: number | null) => value === null ? c("unknown") : `TWD ${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)}`;
  const delta = (value: number | null, reference: number | null) => value === null || reference === null ? c("unknown") : `${value - reference > 0 ? "+" : ""}${money(value - reference)}`;
  function update(index: number, field: ScenarioField, value: string) {
    setDrafts(previous => previous.map((draft, i) => i === index ? { ...draft, [field]: value === "" ? null : Number(value) } : draft));
    setStatus(null);
  }
  function switchDown(index: number, mode: ScenarioInput["downMode"]) {
    setDrafts(previous => previous.map((draft, i) => {
      if (i !== index || draft.downMode === mode) return draft;
      const value = draft.downValue === null || draft.offerTwd === null || draft.offerTwd <= 0 ? null
        : mode === "amount" ? draft.offerTwd * (draft.downValue / 100) : draft.downValue / draft.offerTwd * 100;
      return { ...draft, downMode: mode, downValue: value };
    }));
    setStatus(null);
  }
  function save() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, context, drafts, baseline }));
      setStatus("savedStatus");
    } catch { setStatus("failed"); }
  }
  const validDrafts = results.every(result => Object.keys(result.errors).length === 0);

  return <div className="workspace-view" data-testid="scenario-lab">
    <header className="space-y-2"><p className="text-meta">{c("readonly")}</p><h1 className="text-page">{c("title")}</h1><p className="text-body">{c("intro")}</p></header>
    <Panel variant="plain"><div className={styles.references}>
      <div><p className="text-meta">{c("asking")}</p><strong>{money(askingTwd)}</strong></div>
      <div><p className="text-meta">{c("saved")}</p><strong>{money(savedPrice === null ? null : savedPrice * 10000)}</strong></div>
    </div><p className="mt-3 text-helper">{c("boundary")}</p>
      {finance?.loan.propertyPriceWan != null && !compatibleLoan && <p className="mt-2 text-helper">{c("stale")}</p>}
    </Panel>
    <Section title={c("assumptions")} description={c("inputNote")}>
      <div className={styles.cards}>
        {drafts.map((draft, index) => <Panel key={letters[index]} className={styles.card} data-testid={`scenario-${letters[index]}`}>
          <h3 className="text-subsection">{c("scenario")} {letters[index]}</h3>
          <div className={styles.live} data-testid="live-results" aria-live="polite" aria-atomic="true">
            <dl>{(["paymentTwd", "purchaseCashTwd", "monthlyOwnershipTwd"] as const).map(metric => <div key={metric}><dt>{c(metric)}</dt><dd>{money(results[index][metric])}</dd></div>)}</dl>
            {results[index].purchaseCashTwd !== null && <p>{c(results[index].costsComplete ? "complete" : "subtotal")}</p>}
          </div>
          {SCENARIO_FIELDS.map(field => <div key={field} className={styles.field}>
            {field === "downValue" && <label className={styles.label}>{c("downMode")}<select data-testid="input-downMode" value={draft.downMode} onChange={event => switchDown(index, event.target.value as ScenarioInput["downMode"])}><option value="ratio">{c("ratio")}</option><option value="amount">{c("amount")}</option></select></label>}
            <label className={styles.label} htmlFor={`${letters[index]}-${field}`}>{c(field)}{field === "downValue" ? ` (${draft.downMode === "ratio" ? "%" : "TWD"})` : ""}</label>
            <input id={`${letters[index]}-${field}`} data-testid={`input-${field}`} type="number" inputMode="decimal" min={field === "offerTwd" ? "0.01" : field === "loanYears" || field === "holdingYears" ? "1" : "0"} max={field === "ratePercent" || (field === "downValue" && draft.downMode === "ratio") || field === "loanYears" || field === "holdingYears" ? 100 : field === "commuteMinutes" ? 1440 : 1e12} step={field === "loanYears" || field === "holdingYears" ? "1" : "any"} value={draft[field] ?? ""} onChange={event => update(index, field, event.target.value)} aria-invalid={Boolean(results[index].errors[field])} aria-describedby={results[index].errors[field] ? `${letters[index]}-${field}-error` : undefined} />
            {results[index].errors[field] && <p className={styles.error} id={`${letters[index]}-${field}-error`} data-testid={`error-${field}`}>{c(results[index].errors[field]!)}</p>}
          </div>)}
          <div data-testid="scenario-unknown" className={styles.unknown}><h4 className="text-meta">{c("unknownItems")}</h4>
            <ul>{results[index].unknown.filter(field => field !== "commuteMinutes" || acceptedMinutes === null).map(field => <li key={field}>{c(field)}</li>)}</ul>
            {results[index].unknown.filter(field => field !== "commuteMinutes" || acceptedMinutes === null).length === 0 && <p>{c("none")}</p>}
          </div>
          <CommercialButton variant="secondary" data-testid="freeze-baseline" disabled={Object.keys(results[index].errors).length > 0 || draft.offerTwd === null} onClick={() => { setBaseline({ ...draft }); setStatus(null); }}>{c("freeze")}</CommercialButton>
        </Panel>)}
      </div>
    </Section>
    <Section title={c("comparison")} description={c("scroll")}>
      <div className={styles.tableScroll} role="region" aria-label={c("comparison")} tabIndex={0}>
        <table className={styles.table} data-testid="scenario-comparison"><caption className="sr-only">{c("comparison")}</caption><thead><tr><th scope="col">{c("scenario")}</th>{letters.map(letter => <th key={letter} scope="col">{c("scenario")} {letter}</th>)}</tr></thead><tbody>
          {metrics.map(metric => <tr key={metric}><th scope="row">{c(metric)}</th>{results.map((result, i) => <td key={i} data-testid={`${letters[i]}-${metric}`}><strong>{money(result[metric])}</strong>{costMetrics.has(metric) && result[metric] !== null && <small>{c(result.costsComplete ? "complete" : "subtotal")}</small>}</td>)}</tr>)}
          {(["askingDelta", "savedDelta", "baselineDelta"] as const).map(key => <tr key={key}><th scope="row">{c(key)}</th>{drafts.map((draft, i) => <td key={i} data-testid={`${letters[i]}-${key}`}>{delta(results[i].errors.offerTwd ? null : draft.offerTwd, key === "askingDelta" ? askingTwd : key === "savedDelta" ? savedPrice === null ? null : savedPrice * 10000 : baseline?.offerTwd ?? null)}</td>)}</tr>)}
          {([["paymentDelta", "paymentTwd"], ["cashDelta", "purchaseCashTwd"], ["ownershipDelta", "monthlyOwnershipTwd"], ["yearDelta", "firstYearTwd"]] as const).map(([label, metric]) => <tr key={label}><th scope="row">{c(label)}</th>{results.map((result, i) => <td key={i}>{baselineResult && (metric === "paymentTwd" || (result.costsComplete && baselineResult.costsComplete)) ? delta(result[metric], baselineResult[metric]) : c("unknown")}</td>)}</tr>)}
          <tr><th scope="row">{c("commute")}</th>{drafts.map((draft, i) => <td key={i}>{results[i].errors.commuteMinutes ? c("unknown") : draft.commuteMinutes !== null ? `${formatNumber(draft.commuteMinutes)} ${c("minutes")}` : acceptedMinutes !== null ? `${formatNumber(acceptedMinutes)} ${c("minutes")}` : c("unknown")}<small>{draft.commuteMinutes !== null ? c("manual") : acceptedMinutes !== null ? c("accepted") : ""}</small></td>)}</tr>
        </tbody></table>
      </div>
    </Section>
    <Section title={c("baseline")}>
      <Panel variant="plain" data-testid="scenario-baseline">{baseline ? <><dl className={styles.baseline}>{SCENARIO_FIELDS.map(field => <div key={field}><dt>{c(field)}{field === "downValue" ? ` (${baseline.downMode === "ratio" ? "%" : "TWD"})` : ""}</dt><dd>{baseline[field] === null ? c("unknown") : field.endsWith("Twd") ? money(baseline[field]) : formatNumber(baseline[field])}</dd></div>)}</dl><CommercialButton variant="secondary" className="mt-3" onClick={() => { setBaseline(null); setStatus(null); }}>{c("clear")}</CommercialButton></> : <p>{c("noBaseline")}</p>}</Panel>
      <CommercialButton data-testid="scenario-save" className="mt-4" disabled={!validDrafts} onClick={save}>{c("save")}</CommercialButton>
      <p data-testid="scenario-status" role="status" className="mt-3 text-body">{status ? c(status) : ""}</p>
    </Section>
    <Section title={c("commute")}><Panel variant="plain">{route && acceptedMinutes !== null ? <><p>{c("accepted")}: {route.destination} · {formatNumber(acceptedMinutes)} {c("minutes")}</p><p className="mt-2 text-helper">{c("source")}: Google Routes · {c("checked")}: {formatDate(route.checkedAt)}</p></> : <p>{c("noCommute")}</p>}<p className="mt-2 text-helper">{c("commuteNote")}</p></Panel></Section>
    <DetailsDisclosure summary={c("method")}><p className="text-body">{c("methodNote")}</p></DetailsDisclosure>
  </div>;
}
