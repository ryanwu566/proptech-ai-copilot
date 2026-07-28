import type { ReactNode } from "react";
import { useState } from "react";
import type { ValuationResult } from "@/lib/api";
import { JourneyPropertyContextHeader } from "@/components/guided-journey/journey-property-context-header";
import { JourneyMissingDataPanel } from "@/components/guided-journey/journey-missing-data-panel";
import { PriceDecisionSnapshot } from "@/components/guided-journey/price-decision-snapshot";
import { PriceTrustStatusStrip } from "@/components/guided-journey/price-trust-status-strip";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";
import { buildPriceDecisionSnapshot, buildPriceTrustStatusItems, getSafePriceContext, type PriceJourneyDisplayStatus } from "@/lib/price-affordability-journey";

type PriceHandlers = {
  onResult: (result: ValuationResult | undefined) => void;
  onStatusChange: (status: PriceJourneyDisplayStatus) => void;
};

export function PriceDecisionStage({ propertyContext, renderValuation, renderPropertySearch, onBackToLocation, onContinueToAffordability, onTransferToLoan, onTransferToHolding }: { propertyContext: JourneyPropertyContext; renderValuation: (context: JourneyPropertyContext, handlers: PriceHandlers) => ReactNode; renderPropertySearch: () => ReactNode; onBackToLocation: () => void; onContinueToAffordability: () => void; onTransferToLoan: (priceWan: number) => void; onTransferToHolding: (priceWan: number, areaPing?: number) => void }) {
  const [result, setResult] = useState<ValuationResult>();
  const [statusOverride, setStatusOverride] = useState<PriceJourneyDisplayStatus>();
  const context = getSafePriceContext({ propertyContext, result });
  const displayContext = statusOverride ? { ...context, officialValuationStatus: statusOverride } : context;
  const snapshot = buildPriceDecisionSnapshot(displayContext, result);
  const statusItems = buildPriceTrustStatusItems(displayContext, result);
  const missingItems = [
    propertyContext.selectionStatus === "not_selected" ? "尚未選擇物件" : "",
    propertyContext.areaPing === undefined ? "缺少坪數" : "",
    propertyContext.askingPriceWan === undefined ? "缺少開價" : "",
    !result ? "尚未執行估價" : "",
    result && !snapshot.actionsAvailable ? "尚未有可採取行動的官方估價" : "",
  ].filter(Boolean);

  function handleResult(next: ValuationResult | undefined) {
    setResult(next);
    setStatusOverride(undefined);
  }

  return <div className="min-w-0 space-y-4">
    <JourneyPropertyContextHeader context={propertyContext} onBackToProperty={onBackToLocation} />
    <PriceTrustStatusStrip items={statusItems} />
    <section aria-labelledby="price-decision-workspace-heading" className="min-w-0 space-y-3"><div><h3 id="price-decision-workspace-heading" className="text-lg font-black text-slate-950">估價主工作區</h3><p className="mt-1 text-xs leading-5 text-slate-600">先確認資料狀態、官方可比成交與估價區間。只有正式且可採取行動的估價，才能手動帶入後續工具。</p></div>{renderValuation(propertyContext, { onResult: handleResult, onStatusChange: setStatusOverride })}</section>
    <PriceDecisionSnapshot snapshot={snapshot} />
    {snapshot.actionsAvailable && result && <section aria-labelledby="price-transfer-actions-heading" className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4"><h3 id="price-transfer-actions-heading" className="text-sm font-black text-emerald-950">明確帶入後續工具</h3><p className="mt-1 text-xs leading-5 text-emerald-900">只有按下按鈕才會帶入估價；不會自動計算或儲存。</p><div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap"><button type="button" aria-label="用此估價試算貸款" onClick={() => onTransferToLoan(result.price_range.mid)} className="rounded-lg bg-emerald-700 px-3 py-2.5 text-sm font-bold text-white hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">用此估價試算貸款</button><button type="button" aria-label="用此估價試算持有成本" onClick={() => onTransferToHolding(result.price_range.mid, propertyContext.areaPing)} className="rounded-lg border border-emerald-300 bg-white px-3 py-2.5 text-sm font-bold text-emerald-900 hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">用此估價試算持有成本</button><span className="self-center text-xs text-emerald-900">案件儲存仍需沿用既有信任 guard 與明確確認流程。</span></div></section>}
    <details className="rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500">重新查看官方成交條件</summary><div className="border-t border-stone-100 p-4">{renderPropertySearch()}</div></details>
    <JourneyMissingDataPanel title="價格資料待補與限制" items={missingItems} />
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-4"><h3 className="text-sm font-black text-slate-950">下一步：計算資金與稅務</h3><p className="mt-1 text-xs leading-5 text-slate-600">仍可前往下一步；若尚未有可採取行動的官方估價，資金試算將使用你自行輸入的總價。</p><button type="button" onClick={onContinueToAffordability} className="mt-3 w-full rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-bold text-white hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">下一步：計算資金與稅務</button></div>
  </div>;
}
