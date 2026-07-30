import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { HoldingCostPrefill } from "@/components/holding-cost-calculator";
import type { HoldingCostResult, LoanCalculationResult, TaxResult } from "@/lib/api";
import { JourneyMissingDataPanel } from "@/components/guided-journey/journey-missing-data-panel";
import { AffordabilityDecisionSnapshot } from "@/components/guided-journey/affordability-decision-snapshot";
import { AffordabilityStatusStrip } from "@/components/guided-journey/affordability-status-strip";
import { AffordabilityToolSelector } from "@/components/guided-journey/affordability-tool-selector";
import { JourneyPropertyContextHeader } from "@/components/guided-journey/journey-property-context-header";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";
import { addVisitedAffordabilityTool, buildAffordabilityStatusItems, buildJourneyAffordabilityContext, type AffordabilityToolId, type JourneyPriceContext } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type LoanHandlers = { onResult: (result: LoanCalculationResult) => void; onHoldingCost: (result: LoanCalculationResult) => void };
type HoldingHandlers = { onResult: (result: HoldingCostResult) => void };
type TaxHandlers = { onResult: (result: TaxResult) => void };

export function AffordabilityDecisionStage({ propertyContext, priceContext, explicitPriceWan, initialSecondaryTool, initialHoldingPrefill, renderLoan, renderHolding, renderTax, onContextChange, onBackToPrice, onContinueToDecision }: { propertyContext: JourneyPropertyContext; priceContext?: JourneyPriceContext; explicitPriceWan?: number; initialSecondaryTool?: AffordabilityToolId; initialHoldingPrefill?: HoldingCostPrefill; renderLoan: (priceWan: number | undefined, handlers: LoanHandlers) => ReactNode; renderHolding: (prefill: HoldingCostPrefill | undefined, handlers: HoldingHandlers) => ReactNode; renderTax: (handlers: TaxHandlers) => ReactNode; onContextChange?: (context: ReturnType<typeof buildJourneyAffordabilityContext>) => void; onBackToPrice: () => void; onContinueToDecision: () => void }) {
  const [loanResult, setLoanResult] = useState<LoanCalculationResult>();
  const [holdingResult, setHoldingResult] = useState<HoldingCostResult>();
  const [taxResult, setTaxResult] = useState<TaxResult>();
  const [holdingPrefill, setHoldingPrefill] = useState<HoldingCostPrefill>();
  const [activeSecondaryTool, setActiveSecondaryTool] = useState<AffordabilityToolId | null>(null);
  const [visitedTools, setVisitedTools] = useState<AffordabilityToolId[]>([]);
  const { t, formatNumber } = useExperienceLocale();
  useEffect(() => {
    if (!initialSecondaryTool) return;
    setVisitedTools((current) => addVisitedAffordabilityTool(current, initialSecondaryTool));
    setActiveSecondaryTool(initialSecondaryTool);
  }, [initialSecondaryTool]);
  useEffect(() => {
    if (initialHoldingPrefill) setHoldingPrefill(initialHoldingPrefill);
  }, [initialHoldingPrefill]);
  const context = useMemo(() => buildJourneyAffordabilityContext({ propertyPriceWan: explicitPriceWan, loanResult, holdingResult, taxResult }), [explicitPriceWan, holdingResult, loanResult, taxResult]);
  const statusItems = buildAffordabilityStatusItems(context);
  useEffect(() => { onContextChange?.(context); }, [context, onContextChange]);

  function selectTool(tool: AffordabilityToolId) {
    setVisitedTools((current) => addVisitedAffordabilityTool(current, tool));
    setActiveSecondaryTool(tool);
  }

  function transferToHolding(result: LoanCalculationResult) {
    setHoldingPrefill({ property_price: result.property_price_wan, loan_monthly_payment: result.monthly_payment, monthly_income: result.monthly_income_wan, area_ping: propertyContext.areaPing });
    selectTool("holding");
  }

  return <div className="min-w-0 space-y-4">
    <JourneyPropertyContextHeader context={propertyContext} onBackToProperty={onBackToPrice} />
    <section aria-labelledby="affordability-price-context-heading" className="rounded-xl border border-violet-100 bg-violet-50/50 p-4"><h3 id="affordability-price-context-heading" className="text-sm font-black text-slate-950">{t("journey.price.title")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.noPurchase")}</p><p className="mt-2 text-sm font-bold text-slate-900">{explicitPriceWan === undefined ? t("state.empty.next") : `${t("journey.price.title")}: ${formatNumber(explicitPriceWan)}`}</p></section>
    <AffordabilityStatusStrip items={statusItems} />
    <section aria-labelledby="affordability-loan-heading" className="min-w-0 space-y-3"><div><h3 id="affordability-loan-heading" className="text-lg font-black text-slate-950">{t("journey.affordability.title")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.loanEstimate")}</p></div>{renderLoan(explicitPriceWan, { onResult: setLoanResult, onHoldingCost: transferToHolding })}</section>
    <AffordabilityToolSelector activeTool={activeSecondaryTool} onSelect={selectTool} />
    {visitedTools.includes("holding") && <section hidden={activeSecondaryTool !== "holding"} aria-hidden={activeSecondaryTool !== "holding"} aria-labelledby="affordability-holding-heading" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><h3 id="affordability-holding-heading" className="text-base font-black text-slate-950">{t("trust.holdingEstimate")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.holdingEstimate")}</p><div className="mt-3">{renderHolding(holdingPrefill, { onResult: setHoldingResult })}</div></section>}
    {visitedTools.includes("tax") && <section hidden={activeSecondaryTool !== "tax"} aria-hidden={activeSecondaryTool !== "tax"} aria-labelledby="affordability-tax-heading" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><h3 id="affordability-tax-heading" className="text-base font-black text-slate-950">{t("page.tax")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.taxInfo")}</p><div className="mt-3">{renderTax({ onResult: setTaxResult })}</div></section>}
    <AffordabilityDecisionSnapshot context={context} />
    <JourneyMissingDataPanel title={t("state.partial.heading")} items={context.missingDataLabels} />
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-4"><h3 className="text-sm font-black text-slate-950">{t("journey.decision.next")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("journey.decision.description")}</p><button type="button" onClick={onContinueToDecision} className="mt-3 w-full rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-bold text-white hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">{t("journey.decision.next")}</button></div>
  </div>;
}
