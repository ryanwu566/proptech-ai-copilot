"use client";

import { useEffect, useState } from "react";
import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { HOLDING_COST_RESULT_EVENT, HOLDING_COST_SESSION_KEY } from "@/components/holding-cost-calculator";
import { LOCATION_INSIGHT_RESULT_EVENT, LOCATION_INSIGHT_SESSION_KEY, prefillLocationInsight } from "@/components/location-insight";
import { DecisionReport } from "@/components/decision-report";
import { PropertyGuideMascot } from "@/components/property-guide-mascot";
import { RiskSummaryPanel } from "@/components/risk-summary-panel";
import { Button } from "@/components/ui";
import { buildValuationSummaryHtml, valuationSummaryFilename, type ValuationInputs } from "@/lib/valuation-share";
import { buildRiskSummary } from "@/lib/risk-summary";

export type WorkspaceContext = {
  inputs: ValuationInputs;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holding?: HoldingCostResult;
};
export const WORKSPACE_CONTEXT_EVENT = "proptech:viewing-workspace-context";
export const WORKSPACE_CONTEXT_SESSION_KEY = "proptech:viewing-workspace-context";

export function publishWorkspaceContext(context: WorkspaceContext) {
  window.sessionStorage.setItem(WORKSPACE_CONTEXT_SESSION_KEY, JSON.stringify(context));
  window.dispatchEvent(new CustomEvent<WorkspaceContext>(WORKSPACE_CONTEXT_EVENT, { detail: context }));
}

export function ImmersiveViewingWorkspace({ propertySearch }: { propertySearch?: PropertySearchResult }) {
  const [context, setContext] = useState<WorkspaceContext>(() => ({ inputs: { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 }, propertySearch }));
  const [holdingResult, setHoldingResult] = useState<HoldingCostResult>();
  const [location, setLocation] = useState<LocationInsightResult>();
  useEffect(() => {
    const stored = readSession<WorkspaceContext>(WORKSPACE_CONTEXT_SESSION_KEY);
    if (stored) setContext({ ...stored, propertySearch: propertySearch ?? stored.propertySearch });
    setHoldingResult(stored?.holding ?? readSession<HoldingCostResult>(HOLDING_COST_SESSION_KEY));
    setLocation(readSession<LocationInsightResult>(LOCATION_INSIGHT_SESSION_KEY));
    const contextListener = (event: Event) => setContext((event as CustomEvent<WorkspaceContext>).detail);
    const holdingListener = (event: Event) => setHoldingResult((event as CustomEvent<HoldingCostResult>).detail);
    const locationListener = (event: Event) => setLocation((event as CustomEvent<LocationInsightResult>).detail);
    window.addEventListener(WORKSPACE_CONTEXT_EVENT, contextListener);
    window.addEventListener(HOLDING_COST_RESULT_EVENT, holdingListener);
    window.addEventListener(LOCATION_INSIGHT_RESULT_EVENT, locationListener);
    return () => { window.removeEventListener(WORKSPACE_CONTEXT_EVENT, contextListener); window.removeEventListener(HOLDING_COST_RESULT_EVENT, holdingListener); window.removeEventListener(LOCATION_INSIGHT_RESULT_EVENT, locationListener); };
  }, [propertySearch]);
  const search = propertySearch ?? context.propertySearch;
  const { inputs, valuation, trend, loan } = context;
  const riskSummary = buildRiskSummary({ propertySearch: search, valuation, trend, loan, holding: holdingResult, location });
  const stage = location && holdingResult && loan && valuation ? "complete" : location || holdingResult ? "location" : loan ? "loan" : valuation ? "valuation" : search ? "finder" : "start";
  function exportReport() {
    if (!valuation) return;
    const html = buildValuationSummaryHtml(inputs, valuation, trend, search, loan, holdingResult, location);
    const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = valuationSummaryFilename(); link.click(); URL.revokeObjectURL(url);
  }
  return <section className="min-w-0 overflow-hidden rounded-2xl border border-stone-200 bg-[#f5f2ea]">
    <div className="border-b border-stone-200 bg-white px-4 py-4 sm:px-5"><div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(260px,360px)] sm:items-center"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">IMMERSIVE VIEWING WORKSPACE</p><h2 className="mt-1 text-xl font-bold text-slate-950">沉浸式看房工作台</h2><p className="mt-1 text-xs text-slate-500">一邊整理找房、估價與成本結果，一邊查看地點與區位摘要。</p></div><PropertyGuideMascot stage={stage} riskSignal={riskSummary.overallSignal} /></div></div>
    <div className="grid min-w-0 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:p-5">
      <div className="min-w-0 space-y-4"><RiskSummaryPanel summary={riskSummary} /><FlowCards propertySearch={search} valuation={valuation} trend={trend} loan={loan} holding={holdingResult} location={location} /><DecisionReport propertySearch={search} valuation={valuation} loan={loan} holding={holdingResult} location={location} riskSummary={riskSummary} /></div>
      <aside className="min-w-0 lg:sticky lg:top-16 lg:self-start"><MapSummary city={inputs.city} district={inputs.district} road={inputs.road} areaPing={inputs.area_ping} buildingType={inputs.building_type} valuation={valuation} location={location} onExport={exportReport} /></aside>
    </div>
  </section>;
}

function FlowCards({ propertySearch, valuation, trend, loan, holding, location }: { propertySearch?: PropertySearchResult; valuation?: ValuationResult; trend?: ValuationTrendResult; loan?: LoanCalculationResult; holding?: HoldingCostResult; location?: LocationInsightResult }) {
  const rows = [
    ["找房雷達", propertySearch ? `${propertySearch.summary.matched_count} 筆符合成交` : "下一步：依預算搜尋可負擔路段"],
    ["估價", valuation ? `${valuation.price_range.mid.toLocaleString()} 萬中位估價` : "下一步：帶入路段並完成估價"],
    ["市場趨勢", trend ? `${(trend.trend_annualized_rate * 100).toFixed(1)}% 年化趨勢` : "下一步：完成估價後載入趨勢"],
    ["貸款月付", loan ? `${loan.monthly_payment.toLocaleString()} 元／月` : "下一步：試算收入負擔"],
    ["持有成本", holding ? `${holding.monthly_total_holding_cost.toLocaleString()} 元／月` : "下一步：補入管理費、稅費與修繕"],
    ["區位分析", location ? `區位總分 ${location.location_score ?? "資料不足"}` : "下一步：分析生活圈與資料限制"],
  ];
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{rows.map(([title, detail]) => <div key={title} className="rounded-xl border border-stone-200 bg-white p-3"><p className="text-xs font-bold text-slate-900">{title}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">{detail}</p></div>)}</div>;
}

function MapSummary({ city, district, road, areaPing, buildingType, valuation, location, onExport }: { city: string; district: string; road: string; areaPing: number; buildingType: string; valuation?: ValuationResult; location?: LocationInsightResult; onExport: () => void }) {
  return <div className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm"><div className="relative h-28 bg-[radial-gradient(circle_at_25%_30%,#67e8f9_0_4px,transparent_5px),radial-gradient(circle_at_70%_55%,#fbbf24_0_4px,transparent_5px),linear-gradient(135deg,#e2e8f0,#f8fafc)]"><div className="absolute inset-3 rounded-lg border border-white/80 bg-white/35" /><span className="absolute bottom-2 right-3 text-[9px] font-bold text-slate-500">區位地圖摘要卡</span></div><div className="p-4"><p className="text-[10px] font-bold text-cyan-700">目前地點</p><h3 className="mt-1 font-bold text-slate-950">{location?.resolved_location?.address_label || `${city}${district}${road}`}</h3><p className="mt-1 text-[10px] text-slate-500">{areaPing} 坪 · {buildingType} · {valuation ? `${valuation.price_range.mid.toLocaleString()} 萬` : "尚未估價"}</p>{location?.resolved_location && <p className="mt-2 text-[10px] text-slate-400">{location.resolved_location.latitude.toFixed(5)}, {location.resolved_location.longitude.toFixed(5)}</p>}<div className="mt-3 grid grid-cols-2 gap-2 text-center"><MiniMetric label="區位分數" value={location?.location_score ?? "—"} /><MiniMetric label="交通 POI" value={location?.poi_summary.transit_count ?? "—"} /><MiniMetric label="便利 POI" value={location?.poi_summary.convenience_count ?? "—"} /><MiniMetric label="資料品質" value={location?.data_quality.status ?? "未分析"} /></div><div className="mt-3 space-y-2"><Button secondary className="w-full" onClick={() => prefillLocationInsight({ city, district, road, area_ping: areaPing, building_type: buildingType, property_price: valuation?.price_range.mid })}>分析區位</Button><Button className="w-full" disabled={!valuation} onClick={onExport}>匯出看屋報告</Button></div>{location?.nearest_pois.length ? <ul className="mt-3 space-y-1 text-[10px] text-slate-500">{location.nearest_pois.slice(0, 3).map((item) => <li key={`${item.name}-${item.distance_m}`}>{item.name} · {item.distance_m}m</li>)}</ul> : <p className="mt-3 text-[10px] leading-5 text-amber-700">完成區位分析後，這裡會顯示最近 POI 與資料限制。</p>}</div></div>;
}

function MiniMetric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-lg bg-stone-50 p-2"><p className="text-[9px] text-slate-400">{label}</p><p className="mt-1 text-xs font-bold text-slate-800">{value}</p></div>;
}

function readSession<T>(key: string): T | undefined {
  try { const value = window.sessionStorage.getItem(key); return value ? JSON.parse(value) as T : undefined; } catch { return undefined; }
}
