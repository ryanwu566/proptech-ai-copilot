"use client";

import { useEffect, useState } from "react";
import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { HOLDING_COST_RESULT_EVENT, HOLDING_COST_SESSION_KEY } from "@/components/holding-cost-calculator";
import { LOCATION_INSIGHT_RESULT_EVENT, LOCATION_INSIGHT_SESSION_KEY, prefillLocationInsight } from "@/components/location-insight";
import { DecisionReport } from "@/components/decision-report";
import { PropertyGuideMascot } from "@/components/property-guide-mascot";
import { RiskSummaryPanel } from "@/components/risk-summary-panel";
import { Button } from "@/components/ui";
import { buildValuationSummaryHtml, valuationSummaryFilename, type ValuationInputs } from "@/lib/valuation-share";
import { buildRiskSummary } from "@/lib/risk-summary";
import { WorkflowCommandCenter } from "@/components/workflow-command-center";
import type { WizardStepSummary } from "@/components/buying-wizard";
import { getActiveWizardStep } from "@/lib/buying-wizard-status";
import { buildWorkflowStatus, markWorkflowReportCompleted, readWorkflowSession, WORKFLOW_STATUS_EVENT } from "@/lib/workflow-status";
import { CaseManager } from "@/components/case-manager";
import { CASE_CLEARED_EVENT, CASE_LOADED_EVENT, saveCase, type SavedCase } from "@/lib/case-storage";
import { GuidedDemoRunner } from "@/components/guided-demo-runner";
import { HelpTooltip } from "@/components/help-tooltip";
import { HELP_CONTENT } from "@/lib/help-content";

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
  const [workflowSession, setWorkflowSession] = useState<{ reportCompleted: boolean; taxOracleResult?: TaxResult }>(() => ({ reportCompleted: false }));
  const [caseMessage, setCaseMessage] = useState("保存兩個以上案件後，就可以比較哪個更值得看。");
  useEffect(() => {
    const stored = readSession<WorkspaceContext>(WORKSPACE_CONTEXT_SESSION_KEY);
    if (stored) setContext({ ...stored, propertySearch: propertySearch ?? stored.propertySearch });
    setHoldingResult(stored?.holding ?? readSession<HoldingCostResult>(HOLDING_COST_SESSION_KEY));
    setLocation(readSession<LocationInsightResult>(LOCATION_INSIGHT_SESSION_KEY));
    const contextListener = (event: Event) => setContext((event as CustomEvent<WorkspaceContext>).detail);
    const holdingListener = (event: Event) => setHoldingResult((event as CustomEvent<HoldingCostResult>).detail);
    const locationListener = (event: Event) => setLocation((event as CustomEvent<LocationInsightResult>).detail);
    const workflowListener = () => setWorkflowSession(readWorkflowSession());
    const loadedListener = () => setCaseMessage("已回到上次進度。");
    const clearedListener = () => { setContext({ inputs: { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 } }); setHoldingResult(undefined); setLocation(undefined); setWorkflowSession({ reportCompleted: false }); setCaseMessage("保存兩個以上案件後，就可以比較哪個更值得看。"); };
    window.addEventListener(WORKSPACE_CONTEXT_EVENT, contextListener);
    window.addEventListener(HOLDING_COST_RESULT_EVENT, holdingListener);
    window.addEventListener(LOCATION_INSIGHT_RESULT_EVENT, locationListener);
    window.addEventListener(WORKFLOW_STATUS_EVENT, workflowListener);
    window.addEventListener(CASE_LOADED_EVENT, loadedListener);
    window.addEventListener(CASE_CLEARED_EVENT, clearedListener);
    workflowListener();
    return () => { window.removeEventListener(WORKSPACE_CONTEXT_EVENT, contextListener); window.removeEventListener(HOLDING_COST_RESULT_EVENT, holdingListener); window.removeEventListener(LOCATION_INSIGHT_RESULT_EVENT, locationListener); window.removeEventListener(WORKFLOW_STATUS_EVENT, workflowListener); window.removeEventListener(CASE_LOADED_EVENT, loadedListener); window.removeEventListener(CASE_CLEARED_EVENT, clearedListener); };
  }, [propertySearch]);
  const search = propertySearch ?? context.propertySearch;
  const { inputs, valuation, trend, loan } = context;
  const riskSummary = buildRiskSummary({ propertySearch: search, valuation, trend, loan, holding: holdingResult, location });
  const workflowStatus = buildWorkflowStatus({ propertySearch: search, valuation, loan, holding: holdingResult, location, riskSummary, reportCompleted: workflowSession.reportCompleted, taxOracleResult: workflowSession.taxOracleResult });
  const activeWizardStep = getActiveWizardStep(workflowStatus);
  const wizardSummaries: WizardStepSummary = {
    property_search: search ? [`符合預算成交 ${search.summary.matched_count} 筆`, `推薦路段 ${search.road_suggestions.length} 條`] : undefined,
    valuation: valuation ? [`中位估價 ${valuation.price_range.mid.toLocaleString()} 萬`, `估價區間 ${valuation.price_range.low.toLocaleString()}–${valuation.price_range.high.toLocaleString()} 萬`, `信心分數 ${valuation.confidence_score}`] : undefined,
    affordability: loan && holdingResult ? [`房貸月付 ${loan.monthly_payment.toLocaleString()} 元`, `每月持有成本 ${holdingResult.monthly_total_holding_cost.toLocaleString()} 元`] : undefined,
    location: location ? [`區位總分 ${location.location_score ?? "資料不足"}`, `資料品質 ${location.data_quality.status}`] : undefined,
    risk: riskSummary.overallSignal !== "unknown" ? [`${riskSummary.overallLabel}`, `總分 ${riskSummary.overallScore ?? "資料不足"}`] : undefined,
    report: workflowSession.reportCompleted ? ["看屋決策報告已產生"] : undefined,
    tax: workflowSession.taxOracleResult ? ["TaxOracle 稅務快篩已完成"] : undefined,
  };
  const stage = location && holdingResult && loan && valuation ? "complete" : location || holdingResult ? "location" : loan ? "loan" : valuation ? "valuation" : search ? "finder" : "start";
  function exportReport() {
    if (!valuation) return;
    const html = buildValuationSummaryHtml(inputs, valuation, trend, search, loan, holdingResult, location);
    const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = valuationSummaryFilename(); link.click(); URL.revokeObjectURL(url);
    markWorkflowReportCompleted();
  }
  function exportSavedCase(saved: SavedCase) {
    if (!saved.data.valuation) return;
    const html = buildValuationSummaryHtml(saved.data.inputs, saved.data.valuation, saved.data.trend, saved.data.propertySearch, saved.data.loan, saved.data.holdingCost, saved.data.locationInsight);
    const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = valuationSummaryFilename(); link.click(); URL.revokeObjectURL(url);
  }
  const currentCase = {
    activeWizardStep: activeWizardStep.id,
    progress: workflowStatus.overallProgress,
    inputSummary: { city: inputs.city, district: inputs.district, road: inputs.road, budgetMin: search?.summary.budget_min, budgetMax: search?.summary.budget_max, propertyPrice: valuation?.price_range.mid ?? loan?.property_price_wan, areaPing: inputs.area_ping },
    data: { inputs, propertySearch: search, valuation, trend, loan, holdingCost: holdingResult, locationInsight: location, riskSummary, taxOracle: workflowSession.taxOracleResult, reportCompleted: workflowSession.reportCompleted },
  };
  function saveCurrentCase() {
    saveCase(currentCase);
    setCaseMessage("案件已保存，下一步可匯出報告或繼續分析。");
  }
  return <section id="immersive-workspace" className="min-w-0 scroll-mt-20 overflow-hidden rounded-2xl border border-stone-200 bg-gradient-to-br from-[#f8f6f0] to-[#eef7f7] shadow-sm">
    <div className="border-b border-stone-200 bg-white px-4 py-4 sm:px-5"><div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(260px,360px)] sm:items-center"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">IMMERSIVE VIEWING WORKSPACE</p><h2 className="mt-1 text-xl font-bold text-slate-950">沉浸式看房工作台</h2><p className="mt-1 text-xs text-slate-500">導覽式看房流程：每次專注完成一個主要步驟，已完成內容收進摘要卡。</p></div><PropertyGuideMascot stage={stage} riskSignal={riskSummary.overallSignal} workflowStatus={workflowStatus} activeWizardStep={activeWizardStep.id} caseMessage={caseMessage} /></div></div>
    <div className="space-y-3 p-4 pb-0 lg:p-5 lg:pb-0"><GuidedDemoRunner onMessage={setCaseMessage} onSave={saveCurrentCase} onExport={exportReport} canExport={Boolean(valuation)} /><div className="flex flex-wrap items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-[10px] font-bold text-slate-600"><span>常用操作說明</span><HelpTooltip title={HELP_CONTENT.caseSave.title}>{HELP_CONTENT.caseSave.body}</HelpTooltip><HelpTooltip title={HELP_CONTENT.caseComparison.title}>{HELP_CONTENT.caseComparison.body}</HelpTooltip><HelpTooltip title={HELP_CONTENT.htmlExport.title}>{HELP_CONTENT.htmlExport.body}</HelpTooltip><HelpTooltip title={HELP_CONTENT.shareLink.title}>{HELP_CONTENT.shareLink.body}</HelpTooltip></div></div>
    <div className="grid min-w-0 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:p-5">
      <div className="min-w-0 space-y-4"><CaseManager current={currentCase} onSaved={() => setCaseMessage("案件已保存，下一步可繼續完成缺少的分析。")} onLoaded={() => setCaseMessage("已回到上次進度。")} onCleared={() => setCaseMessage("保存兩個以上案件後，就可以比較哪個更值得看。")} onExport={exportSavedCase} /><WorkflowCommandCenter status={workflowStatus} summaries={wizardSummaries} /><details className="rounded-xl border border-stone-200 bg-white" open={activeWizardStep.id === "risk"}><summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">Step 5 風險總評</summary><div className="border-t border-stone-100 p-4"><RiskSummaryPanel summary={riskSummary} /></div></details><details className="rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">查看各模組完成摘要</summary><div className="border-t border-stone-100 p-4"><FlowCards propertySearch={search} valuation={valuation} trend={trend} loan={loan} holding={holdingResult} location={location} /></div></details><details className="rounded-xl border border-stone-200 bg-white" open={activeWizardStep.id === "report"}><summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">Step 6 看屋決策報告</summary><div className="border-t border-stone-100 p-4"><DecisionReport propertySearch={search} valuation={valuation} loan={loan} holding={holdingResult} location={location} riskSummary={riskSummary} taxOracleResult={workflowSession.taxOracleResult} /></div></details></div>
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
