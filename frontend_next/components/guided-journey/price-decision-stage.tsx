import type { ReactNode } from "react";
import { useState } from "react";
import type { ValuationResult } from "@/lib/api";
import { JourneyPropertyContextHeader } from "@/components/guided-journey/journey-property-context-header";
import { JourneyMissingDataPanel } from "@/components/guided-journey/journey-missing-data-panel";
import { PriceDecisionSnapshot } from "@/components/guided-journey/price-decision-snapshot";
import { PriceTrustStatusStrip } from "@/components/guided-journey/price-trust-status-strip";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";
import { buildPriceDecisionSnapshot, buildPriceTrustStatusItems, getSafePriceContext, type PriceJourneyDisplayStatus } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { PriceBasisSelector } from "@/components/guided-journey/price-basis-selector";
import type { JourneyPriceBasis } from "@/lib/closed-loop-journey";

type PriceHandlers = {
  onResult: (result: ValuationResult | undefined) => void;
  onStatusChange: (status: PriceJourneyDisplayStatus) => void;
};

export function PriceDecisionStage({ propertyContext, valuationResult: result, priceBasis, activePriceWan, manualPriceWan, renderValuation, onValuationResult, onPriceBasisChange, onBackToLocation, onContinueToAffordability, onTransferToLoan, onTransferToHolding }: { propertyContext: JourneyPropertyContext; valuationResult?: ValuationResult; priceBasis: JourneyPriceBasis; activePriceWan?: number; manualPriceWan?: number; renderValuation: (context: JourneyPropertyContext, handlers: PriceHandlers) => ReactNode; onValuationResult: (result: ValuationResult | undefined, status: PriceJourneyDisplayStatus) => void; onPriceBasisChange: (basis: JourneyPriceBasis, manualPriceWan?: number) => void; onBackToLocation: () => void; onContinueToAffordability: () => void; onTransferToLoan: (priceWan: number) => void; onTransferToHolding: (priceWan: number, areaPing?: number) => void }) {
  const [statusOverride, setStatusOverride] = useState<PriceJourneyDisplayStatus>();
  const { t } = useExperienceLocale();
  const context = getSafePriceContext({ propertyContext, result });
  const displayContext = statusOverride ? { ...context, officialValuationStatus: statusOverride } : context;
  const snapshot = buildPriceDecisionSnapshot(displayContext, result);
  const statusItems = buildPriceTrustStatusItems(displayContext, result);
  const missingItems = [
    propertyContext.selectionStatus === "not_selected" ? t("state.empty.next") : "",
    propertyContext.areaPing === undefined ? t("state.partial.next") : "",
    propertyContext.askingPriceWan === undefined ? t("state.partial.next") : "",
    !result ? t("state.not_assessed.next") : "",
    result && !snapshot.actionsAvailable ? t("state.no_official_data.next") : "",
  ].filter(Boolean);

  function handleResult(next: ValuationResult | undefined) {
    setStatusOverride(undefined);
    onValuationResult(next, next ? getSafePriceContext({ propertyContext, result: next }).officialValuationStatus : "not_started");
  }

  function handleStatusChange(status: PriceJourneyDisplayStatus) {
    setStatusOverride(status);
    if (status === "loading" || status === "not_started" || status === "unavailable" || status === "no_data") onValuationResult(undefined, status);
  }

  return <div className="min-w-0 space-y-4">
    <JourneyPropertyContextHeader context={propertyContext} onBackToProperty={onBackToLocation} />
    <PriceTrustStatusStrip items={statusItems} />
    <section data-testid="price-decision-workspace" data-property-area={propertyContext.areaPing} aria-labelledby="price-decision-workspace-heading" className="min-w-0 space-y-3"><div><h3 id="price-decision-workspace-heading" className="text-lg font-black text-slate-950">{t("journey.price.title")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("journey.price.description")}</p></div>{renderValuation(propertyContext, { onResult: handleResult, onStatusChange: handleStatusChange })}</section>
    <PriceDecisionSnapshot snapshot={snapshot} />
    <PriceBasisSelector basis={priceBasis} askingPriceWan={propertyContext.askingPriceWan} valuationPriceWan={snapshot.actionsAvailable ? result?.price_range.mid : undefined} activePriceWan={activePriceWan} manualPriceWan={manualPriceWan} onChange={onPriceBasisChange} />
    {snapshot.actionsAvailable && result && <section aria-labelledby="price-transfer-actions-heading" className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4"><h3 id="price-transfer-actions-heading" className="text-sm font-black text-emerald-950">{t("evidence.details")}</h3><p className="mt-1 text-xs leading-5 text-emerald-900">{t("trust.noPurchase")}</p><div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap"><button type="button" aria-label={t("journey.affordability.title")} onClick={() => onTransferToLoan(result.price_range.mid)} className="rounded-lg bg-emerald-700 px-3 py-2.5 text-sm font-bold text-white hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">{t("journey.affordability.title")}</button><button type="button" aria-label={t("trust.holdingEstimate")} onClick={() => onTransferToHolding(result.price_range.mid, propertyContext.areaPing)} className="rounded-lg border border-emerald-300 bg-white px-3 py-2.5 text-sm font-bold text-emerald-900 hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">{t("trust.holdingEstimate")}</button><span className="self-center text-xs text-emerald-900">{t("trust.noPurchase")}</span></div></section>}
    <JourneyMissingDataPanel title={t("state.partial.heading")} items={missingItems} />
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-4"><h3 className="text-sm font-black text-slate-950">{t("journey.affordability.next")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("journey.affordability.description")}</p><button type="button" onClick={onContinueToAffordability} className="mt-3 w-full rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-bold text-white hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">{t("journey.affordability.next")}</button></div>
  </div>;
}
