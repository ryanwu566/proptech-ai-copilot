"use client";

import { useEffect, useRef, useState } from "react";
import type { HoldingCostResult, LoanCalculationResult } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { ActionSection, Section } from "@/components/design-system/section";
import { MetricItem, MetricRow, SummaryStrip } from "@/components/design-system/summary-strip";
import { updateSavedCaseFinanceEvidence, type SavedCaseIdentityExpectation } from "@/lib/case-storage";
import { buildFinanceModel, createFinanceInputFingerprint, mergeFinanceEvidence, type FinancePriceBasis } from "@/lib/workspace/finance-model";
import { createStoredFinanceEvidence } from "@/lib/workspace/finance-persistence";
import { moneyPriceContext } from "@/lib/workspace/money-workflow";
import { HoldingAssumptionForm, LoanAssumptionForm } from "./finance-assumption-forms";
import { MoneyFreshness, MoneyHoldingSummary, MoneyLoanSummary, MoneyTaxCheck, SavedMoneyAssumptions } from "./money-evidence";
import { MoneyOfferScenarios } from "./money-offer-scenarios";
import { useMoneyCopy } from "./use-money-copy";
import styles from "./money-workspace.module.css";

function identityExpectation(workspace: ReturnType<typeof useWorkspace>): SavedCaseIdentityExpectation | null {
  const anchor = workspace.identity.anchor;
  if (!anchor?.coordinates) return null;
  return { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address,
    coordinates: { latitude: anchor.coordinates.latitude, longitude: anchor.coordinates.longitude }, snapshotVersion: workspace.storageVersion };
}

export function FinanceWorkspace() {
  const workspace = useWorkspace();
  const { c, wan, monthly, percent } = useMoneyCopy();
  const latestWorkspace = useRef(workspace); latestWorkspace.current = workspace;
  const saveRevision = useRef(0);
  useEffect(() => () => { saveRevision.current++; }, []);
  const context = { caseId: workspace.caseId, revision: workspace.revision, identityAnchorId: workspace.identity.anchor?.journey_anchor_id ?? null,
    activePriceBasis: workspace.assumptions.activePriceBasis, activePriceWan: workspace.assumptions.activePriceWan, areaPing: workspace.assumptions.areaPing };
  const caseFingerprint = createFinanceInputFingerprint(context);
  const savedPrice = moneyPriceContext(context.activePriceWan, context.activePriceBasis, workspace.finance);
  const [selection, setSelection] = useState<{ context: string; amountWan: number; basis: FinancePriceBasis } | null>(null);
  const selected = selection?.context === caseFingerprint ? selection : null;
  const activePriceWan = selected?.amountWan ?? savedPrice.amountWan;
  const activePriceBasis = selected?.basis ?? savedPrice.basis;
  const [offerInput, setOfferInput] = useState(() => savedPrice.basis === "manual" && savedPrice.amountWan !== null ? String(savedPrice.amountWan) : "");
  const [loanResult, setLoanResult] = useState<LoanCalculationResult | null>(null);
  const [loanPaymentRevision, setLoanPaymentRevision] = useState(0);
  const [holdingResult, setHoldingResult] = useState<HoldingCostResult | null>(null);
  const savedAreaPing = workspace.finance?.savedAssumptions ? workspace.finance.savedAssumptions.areaPing : workspace.assumptions.areaPing ?? null;
  const [holdingAreaPing, setHoldingAreaPing] = useState<number | null>(savedAreaPing);
  const [calculatedAt, setCalculatedAt] = useState<string | null>(null);
  const [loanDirty, setLoanDirty] = useState(false);
  const [holdingDirty, setHoldingDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "failed">("idle");

  // External case edits invalidate in-flight work. Saved assumptions remain the form seeds.
  useEffect(() => {
    saveRevision.current++;
    setLoanResult(null); setHoldingResult(null); setCalculatedAt(null);
    setHoldingAreaPing(savedAreaPing); setLoanDirty(false); setHoldingDirty(false);
  }, [caseFingerprint, savedAreaPing]);

  const saved = workspace.finance;
  const matchesSaved = saved && (selected === null || (saved.freshness.status === "current"
    && (saved.savedAssumptions?.amountWan ?? saved.loan.propertyPriceWan) === activePriceWan
    && saved.priceSource === (activePriceBasis === "asking" ? "ASKING_PRICE" : activePriceBasis === "manual" ? "MANUAL_SCENARIO" : "COMPARABLE_ESTIMATE")));
  const baseFinance = matchesSaved ? { ...saved, priceBasis: { ...saved.priceBasis, amountWan: activePriceWan, basis: activePriceBasis } } : buildFinanceModel({
    ...context, identityState: workspace.identity.state, activePriceBasis, activePriceWan, areaPing: holdingAreaPing,
  });
  let finance = baseFinance;
  if (loanResult || holdingResult) {
    const computed = buildFinanceModel({ ...context, identityState: workspace.identity.state, activePriceBasis, activePriceWan,
      areaPing: holdingAreaPing, loanResult, holdingResult, calculatedAt });
    finance = mergeFinanceEvidence(baseFinance, computed, loanResult !== null, holdingResult !== null);
  }
  // Tax evidence is a bounded saved checklist, independent of an offer preview.
  if (saved) finance = { ...finance, tax: saved.tax };
  const dirty = loanDirty || holdingDirty;
  const expectation = identityExpectation(workspace);
  const savedLoanNeedsRefresh = saved?.loan.monthlyPaymentTwd != null && finance.loan.status !== "available";
  const saveDisabled = dirty || savedLoanNeedsRefresh || finance.freshness.status !== "current" || finance.freshness.calculatedAt === null || finance.calculation.query !== "succeeded" || !expectation;
  const basisLabel = activePriceBasis === "asking" ? "asking" : activePriceBasis === "estimate" ? "estimate" : "manual";
  const currentLoan = !loanDirty && finance.loan.status === "available";
  const currentHolding = !dirty && finance.holding.status === "available";
  const currentDownPaymentWan = currentLoan ? finance.loan.downPaymentWan : null;

  function selectPrice(amountWan: number, basis: FinancePriceBasis) {
    saveRevision.current++;
    setSelection({ context: caseFingerprint, amountWan, basis });
    setLoanResult(null); setHoldingResult(null); setCalculatedAt(null);
    setLoanDirty(false); setHoldingDirty(holdingDirty || holdingResult !== null || finance.holding.status !== "not_started"); setSaveStatus("idle");
  }
  function onLoanCalculated(result: LoanCalculationResult) {
    saveRevision.current++; setLoanResult(result); setHoldingResult(null);
    setLoanPaymentRevision(previous => previous + 1);
    setCalculatedAt(new Date().toISOString()); setLoanDirty(false);
    setHoldingDirty(previous => previous || holdingResult !== null || baseFinance.holding.status !== "not_started"); setSaveStatus("idle");
  }
  function onHoldingCalculated(result: HoldingCostResult, areaPing: number | null) {
    saveRevision.current++; setHoldingResult(result); setHoldingAreaPing(areaPing);
    setCalculatedAt(new Date().toISOString()); setHoldingDirty(false); setSaveStatus("idle");
  }
  async function saveFinance() {
    if (saveDisabled || !expectation) return;
    const responseRevision = saveRevision.current;
    try {
      const evidence = createStoredFinanceEvidence(finance, { caseId: workspace.caseId, revision: workspace.revision, areaPing: holdingAreaPing, caseInputFingerprint: caseFingerprint });
      const persisted = await updateSavedCaseFinanceEvidence(workspace.caseId, evidence, expectation,
        () => saveRevision.current === responseRevision && latestWorkspace.current.caseId === workspace.caseId && latestWorkspace.current.updatedAt === workspace.updatedAt);
      if (saveRevision.current === responseRevision) setSaveStatus(persisted ? "saved" : "failed");
    } catch { if (saveRevision.current === responseRevision) setSaveStatus("failed"); }
  }

  return <div data-testid="finance-workspace" className={`workspace-view ${styles.root}`}>
    <header className="space-y-2"><h1 className="text-page">{c("title")}</h1><p className="text-body">{c("intro")}</p></header>
    <div data-testid="money-summary" className={styles.summary}>
      <SummaryStrip label={c("summary")}>
        <MetricItem label={c("cashSubtotal")} value={wan(currentDownPaymentWan)} primary note={c("closingUnknown")} />
        <MetricItem label={c((finance.loan.gracePeriodYears ?? 0) > 0 ? "afterGrace" : "payment")} value={monthly(currentLoan ? finance.loan.monthlyPaymentTwd : null)} primary note={c("userAssumption")} />
        <MetricItem label={c("holdingSubtotal")} value={monthly(currentHolding ? finance.holding.knownMonthlySubtotalTwd : null)} primary note={c("monthlyNote")} />
      </SummaryStrip>
      <MoneyFreshness model={finance} dirty={dirty} />
      {saved?.freshness.source === "saved_snapshot" && <SavedMoneyAssumptions model={saved} />}
    </div>

    <Section title={c("cash")} description={c("closingUnknown")}>
      <div data-testid="finance-price-basis"><SummaryStrip label={c("cash")}>
        <MetricItem label={c(basisLabel)} value={wan(activePriceWan)} primary note={selected || activePriceBasis === "manual" ? c("userAssumption") : c("caseSource")} />
        <MetricItem label={c("down")} value={wan(currentDownPaymentWan)} note={`${c("downRatio")}: ${percent(finance.loan.downPaymentRatio)}`} />
        <MetricItem label={c("loan")} value={wan(currentLoan ? finance.loan.principalWan : null)} />
      </SummaryStrip></div>
      <dl className="mt-4 space-y-3" data-testid="money-cash-needed">
        <MetricRow label={c("cashSubtotal")} value={wan(currentDownPaymentWan)} />
        <MetricRow label={c("cashTotal")} value={c("unknown")} />
      </dl>
      {activePriceWan === null && <div className="mt-4"><Message variant="warning">{c("newPrice")}</Message></div>}
    </Section>

    <Section title={c("monthly")} description={c("loanBoundary")}>
      <p className="mb-5 text-helper">{c("defaults")}</p>
      <div className="grid min-w-0 gap-6 lg:grid-cols-2">
        {activePriceWan !== null && <LoanAssumptionForm key={`loan-${caseFingerprint}`} propertyPriceWan={activePriceWan} initial={saved?.loan}
          onDirty={() => { saveRevision.current++; setLoanDirty(true); setHoldingDirty(holdingDirty || holdingResult !== null || baseFinance.holding.status !== "not_started"); setSaveStatus("idle"); }} onCalculated={onLoanCalculated} />}
        <MoneyLoanSummary model={finance} dirty={loanDirty} />
      </div>
      <div className="mt-8 border-t border-[color:var(--border-subtle)] pt-6">
        <h3 className="mb-3 text-subsection">{c("holdingAssumptions")}</h3>
        <p className="mb-5 text-helper">{c("taxProxy")}</p>
        <div className="grid min-w-0 gap-6 lg:grid-cols-2">
          {activePriceWan !== null && <HoldingAssumptionForm key={`holding-${caseFingerprint}`} propertyPriceWan={activePriceWan}
            initialLoanPaymentTwd={loanResult?.monthly_payment ?? (finance.loan.status === "available" ? finance.loan.monthlyPaymentTwd : null)} loanPaymentRevision={loanPaymentRevision} initialAreaPing={savedAreaPing} initial={saved?.holding.assumptions}
            onDirty={() => { saveRevision.current++; setHoldingDirty(true); setSaveStatus("idle"); }} onCalculated={onHoldingCalculated} />}
          <MoneyHoldingSummary model={finance} dirty={holdingDirty} />
        </div>
      </div>
      <div data-testid="affordability-status" className="mt-5 text-body">
        <p>{finance.affordability.status === "assessed" ? `${c("burden")}: ${percent(finance.affordability.ratio)}` : c("unassessed")}</p>
        <p className="mt-2 text-helper">{c("burdenNote")}</p>
      </div>
    </Section>

    <Section title={c("transaction")}>
      <h3 className="text-subsection">{c("checklist")}</h3>
      <ul className="mb-6 mt-3 list-disc space-y-3 pl-5 text-body">{(["verifyFees", "verifyLoan", "verifyBills"] as const).map(key => <li key={key}>{c(key)}</li>)}</ul>
      <MoneyTaxCheck model={finance} />
    </Section>

    <Section title={c("offers")} description={c("offerNote")}>
      <MoneyOfferScenarios askingPriceWan={workspace.assumptions.askingPriceWan ?? null} offerInput={offerInput} setOfferInput={setOfferInput}
        loan={finance.loan} calculatedAt={finance.freshness.calculatedAt} disabled={dirty} onSelect={selectPrice} />
    </Section>

    <ActionSection id="finance-save-section">
      <CommercialButton onClick={saveFinance} disabled={saveDisabled} data-testid="finance-save">{c("save")}</CommercialButton>
      {saveDisabled && <p className="text-helper">{c("saveReady")}</p>}
      <div data-testid="finance-save-status" aria-live="polite">
        {saveStatus === "saved" && <Message variant="success">{c("saveSuccess")}</Message>}
        {saveStatus === "failed" && <Message variant="error">{c("saveFailure")}</Message>}
      </div>
    </ActionSection>
  </div>;
}
