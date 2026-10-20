"use client";

import { CommercialButton } from "@/components/design-system/button";
import { Field, UnitInput } from "@/components/design-system/field";
import { MetricRow } from "@/components/design-system/summary-strip";
import type { FinanceModel, FinancePriceBasis } from "@/lib/workspace/finance-model";
import { projectMoneyOffer } from "@/lib/workspace/money-workflow";
import { useMoneyCopy } from "./use-money-copy";

export function MoneyOfferScenarios({ askingPriceWan, offerInput, setOfferInput, loan, calculatedAt, disabled, onSelect }: {
  askingPriceWan: number | null; offerInput: string; setOfferInput: (value: string) => void;
  loan: FinanceModel["loan"]; calculatedAt: string | null; disabled: boolean; onSelect: (price: number, basis: FinancePriceBasis) => void;
}) {
  const { c, wan, money, monthly, percent, number, date } = useMoneyCopy();
  const offer = offerInput === "" ? null : Number(offerInput);
  const validOffer = offer !== null && Number.isFinite(offer) && offer > 0 && offer <= 1e8;
  return <div data-testid="money-offer-scenarios" className="min-w-0 space-y-5">
    <p className="text-helper">{c("offerSaveNote")}</p>
    <p className="text-body" data-testid="offer-shared-assumptions">{c("downRatio")}: {percent(loan.downPaymentRatio)} · {c("rate")}: {loan.annualInterestRate === null ? c("unknown") : `${number(loan.annualInterestRate)}%`} · {c("years")}: {loan.loanYears ?? c("unknown")} · {c("grace")}: {loan.gracePeriodYears ?? c("unknown")} {c("yearUnit")}</p>
    <p className="text-helper">{c("source")}: {c("userAssumption")} · {c("calculatedAt")}: {calculatedAt ? <time dateTime={calculatedAt}>{date(calculatedAt)}</time> : c("unknown")}</p>
    {loan.status === "stale" && <p className="text-helper">{c("stale")}</p>}
    {(disabled || loan.monthlyPaymentTwd === null) && <p className="text-helper">{c("offerUnknown")}</p>}
    <Field label={c("offerInput")} errorText={offerInput !== "" && !validOffer ? c("invalid") : undefined}>
      <UnitInput data-testid="money-offer-input" type="number" min="0.01" max="100000000" step="0.01" value={offerInput} onChange={event => setOfferInput(event.target.value)} suffix={c("wanUnit")} unitLabel={c("wanUnit")} />
    </Field>
    <div className="grid min-w-0 gap-5 md:grid-cols-2" aria-live="polite">
      {([{ id: "asking", price: askingPriceWan, label: "asking" }, { id: "offer", price: validOffer ? offer : null, label: "manual" }] as const).map(item => {
        const projection = projectMoneyOffer(item.price, loan);
        return <div key={item.id} data-testid={`money-${item.id}-projection`} className="min-w-0 space-y-3 border-t border-[color:var(--border-subtle)] pt-4">
          <h3 className="text-subsection">{c(item.label)}</h3>
          <dl className="space-y-2">
            <MetricRow label={c(item.label)} value={wan(item.price)} />
            <MetricRow label={c("cashSubtotal")} value={money(projection.cashKnownSubtotalTwd)} />
            <MetricRow label={c("loan")} value={money(projection.loanTwd)} />
            <MetricRow label={c((loan.gracePeriodYears ?? 0) > 0 ? "afterGrace" : "payment")} value={monthly(projection.monthlyPaymentTwd)} />
            {(loan.gracePeriodYears ?? 0) > 0 && <MetricRow label={c("gracePayment")} value={monthly(projection.graceMonthlyPaymentTwd)} />}
          </dl>
          <CommercialButton variant="secondary" data-testid={`money-use-${item.id}`} disabled={disabled || item.price === null} onClick={() => { if (item.price !== null) onSelect(item.price, item.id === "asking" ? "asking" : "manual"); }}>{c(item.id === "asking" ? "useAsking" : "useOffer")}</CommercialButton>
        </div>;
      })}
    </div>
    <p className="text-helper">{c("closingUnknown")}</p>
    <p className="text-helper">{c("localMethod")}</p>
  </div>;
}
