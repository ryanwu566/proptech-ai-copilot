"use client";

import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
import { MetricRow, MetricItem, SummaryStrip } from "@/components/design-system/summary-strip";
import type { FinanceModel } from "@/lib/workspace/finance-model";
import type { MoneyCopyKey } from "@/lib/workspace/money-copy";
import { useMoneyCopy } from "./use-money-copy";

export function MoneyFreshness({ model, dirty }: { model: FinanceModel; dirty: boolean }) {
  const { c, date } = useMoneyCopy();
  const stale = dirty || model.freshness.status === "stale";
  return <div data-testid="freshness-status" className="mt-4">
    <Message variant={stale ? "warning" : "information"} title={c(stale ? "stale" : model.freshness.source === "saved_snapshot" ? "saved" : model.freshness.source === "live_calculation" ? "unsaved" : "notCalculated")}>
      {stale ? c("staleNote") : model.freshness.source === "saved_snapshot" ? c("savedNote") : c("userAssumption")}
      {model.freshness.calculatedAt && <p className="mt-2">{c("calculatedAt")}: <time dateTime={model.freshness.calculatedAt}>{date(model.freshness.calculatedAt)}</time></p>}
    </Message>
  </div>;
}

export function SavedMoneyAssumptions({ model }: { model: FinanceModel }) {
  const { c, wan, money, percent, number, date } = useMoneyCopy();
  const assumed = (value: number | null, suffix = "") => value === null ? c("unknown") : `${number(value)}${suffix}`;
  const basis = model.priceSource === "ASKING_PRICE" ? "asking" : model.priceSource === "MANUAL_SCENARIO" ? "manual" : model.priceSource === "COMPARABLE_ESTIMATE" ? "estimate" : "unknown";
  const rows: [MoneyCopyKey, string][] = [
    ["source", c(basis)],
    ["originalPrice", wan(model.savedAssumptions?.amountWan ?? model.loan.propertyPriceWan)],
    ["downRatio", percent(model.loan.downPaymentRatio)],
    ["rate", assumed(model.loan.annualInterestRate, "%")],
    ["years", assumed(model.loan.loanYears, ` ${c("yearUnit")}`)],
    ["grace", assumed(model.loan.gracePeriodYears, ` ${c("yearUnit")}`)],
    ["income", wan(model.loan.monthlyIncomeWan)],
    ["area", assumed(model.savedAssumptions?.areaPing ?? null, ` ${c("ping")}`)],
    ["payment", money(model.holding.assumptions.loanMonthlyPaymentTwd)],
    ["managementRate", money(model.holding.assumptions.managementFeePerPingTwd)],
    ["repairRate", money(model.holding.assumptions.repairReservePerPingTwd)],
    ["homeTax", assumed(model.holding.assumptions.annualHomeTaxRatePercent, "%")],
    ["landTax", assumed(model.holding.assumptions.annualLandTaxRatePercent, "%")],
    ["insuranceYear", money(model.holding.assumptions.annualInsuranceTwd)],
    ["calculatedAt", date(model.freshness.calculatedAt)],
  ];
  return <div data-testid="saved-finance-assumptions" className="mt-4 min-w-0">
    <DetailsDisclosure summary={c("savedAssumptions")}>
      <dl className="space-y-2 text-body">
        {rows.map(([key, value]) => <MetricRow key={key} label={c(key)} value={value} />)}
      </dl>
    </DetailsDisclosure>
  </div>;
}

export function MoneyLoanSummary({ model, dirty }: { model: FinanceModel; dirty: boolean }) {
  const { c, wan, money, monthly } = useMoneyCopy();
  return <div data-testid="loan-summary" className="min-w-0 space-y-3">
    <h3 className="text-subsection">{c("loanAssumptions")}</h3>
    {(dirty || model.loan.status === "stale") && <p className="text-helper">{c("stale")}</p>}
    {model.loan.monthlyPaymentTwd === null ? <p className="text-body">{c("noLoan")}</p> : <dl className="space-y-2">
      <MetricRow label={c("down")} value={wan(model.loan.downPaymentWan)} />
      <MetricRow label={c("loan")} value={wan(model.loan.principalWan)} />
      <MetricRow label={c((model.loan.gracePeriodYears ?? 0) > 0 ? "afterGrace" : "payment")} value={monthly(model.loan.monthlyPaymentTwd)} />
      {(model.loan.gracePeriodYears ?? 0) > 0 && <MetricRow label={c("gracePayment")} value={monthly(model.loan.gracePeriodMonthlyPaymentTwd)} />}
      <MetricRow label={c("totalInterest")} value={money(model.loan.totalInterestTwd)} />
    </dl>}
  </div>;
}

export function MoneyHoldingSummary({ model, dirty }: { model: FinanceModel; dirty: boolean }) {
  const { c, monthly, annual } = useMoneyCopy();
  const labels: Record<string, MoneyCopyKey> = { loan: "payment", management: "management", repair_reserve: "repair_reserve", tax_estimate: "tax_estimate", insurance: "insurance" };
  return <div data-testid="holding-summary" className="min-w-0 space-y-3">
    <h3 className="text-subsection">{c("holdingResult")}</h3>
    {(dirty || model.holding.status === "stale") && <p className="text-helper">{c("stale")}</p>}
    {model.holding.knownMonthlySubtotalTwd === null ? <p className="text-body">{c("noHolding")}</p> : <>
      <SummaryStrip label={c("holdingResult")}><MetricItem label={c("holdingSubtotal")} value={monthly(model.holding.knownMonthlySubtotalTwd)} primary /><MetricItem label={c("annualTotal")} value={annual(model.holding.knownAnnualSubtotalTwd)} note={c("annualNote")} /></SummaryStrip>
      <dl data-testid="holding-breakdown" className="space-y-3">{model.holding.breakdown.map(row => <MetricRow key={row.key} label={c(labels[row.key] ?? "holdingResult")} value={row.status === "unestimated" ? c("missingArea") : monthly(row.monthlyAmountTwd)} />)}</dl>
    </>}
    <p className="text-helper">{c("monthlyNote")}</p>
  </div>;
}

export function MoneyTaxCheck({ model }: { model: FinanceModel }) {
  const { c, number } = useMoneyCopy();
  const summary = model.tax.summary;
  return <div data-testid="tax-summary" className="min-w-0 space-y-3">
    <h3 className="text-subsection">{c("taxSummary")}</h3>
    {model.tax.query === "failed" && <Message variant="warning">{c("taxFailed")}</Message>}
    {summary ? <>
      <p className="text-body">{c(summary.outcome === "eligible" ? "eligible" : summary.outcome === "not_eligible" ? "notEligible" : "review")}</p>
      <dl className="space-y-2">
        <MetricRow label={c("failedConditions")} value={number(summary.failedConditionCount)} />
        <MetricRow label={c("reviewItems")} value={number(summary.reviewItemCount)} />
        <MetricRow label={c("missingInfo")} value={number(summary.missingInformationCount)} />
        <MetricRow label={c("source")} value={summary.sourceName ?? c("unknown")} />
        <MetricRow label={c("effectiveDate")} value={summary.effectiveDate ?? c("unknown")} />
      </dl>
    </> : <p className="text-body">{c("noTax")}</p>}
    <p className="text-helper">{c("taxBoundary")}</p>
  </div>;
}
