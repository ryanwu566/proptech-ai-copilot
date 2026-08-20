"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, PropertySearchResult, PropertySearchSuggestion, PropertySearchTransaction } from "@/lib/api";
import { Button, EmptyState, Notice } from "@/components/ui";
import { ErrorState, LoadingState, MetricTile, SectionCard } from "@/components/product-ui";
import { ImmersiveViewingWorkspace } from "@/components/immersive-viewing-workspace";
import { GUIDED_DEMO_RESULT_EVENT, type DemoResults } from "@/lib/demo-runner";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { buildPropertySearchVisualModel } from "@/lib/property-search-visualization";
import { PropertySearchPriceRangeChart } from "@/components/data-visualization/property-search-price-range-chart";
import { PropertySearchSampleChart } from "@/components/data-visualization/property-search-sample-chart";
import { PropertySearchEvidenceSummary } from "@/components/data-visualization/property-search-evidence-summary";
import { VisualDataUnavailableState } from "@/components/data-visualization/visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { BUILDING_TYPE_OPTIONS, getLocalizedBuildingTypeLabel } from "@/lib/structured-options";



export type PropertyFinderSelection = {
  city: string;
  district: string;
  road: string;
  building_type: string;
  area_ping: number;
  building_age_years?: number;
  floor?: number;
  asking_price_wan: number;
};

export function PropertyFinder({ onUseForValuation, onUseForLoan, onUseForHoldingCost, onUseForLocationInsight, onResult, initialResult, embedded = false }: { onUseForValuation: (selection: PropertyFinderSelection) => void; onUseForLoan: (priceWan: number, selection: PropertyFinderSelection) => void; onUseForHoldingCost: (priceWan: number, areaPing: number, selection: PropertyFinderSelection) => void; onUseForLocationInsight: (selection: PropertyFinderSelection, priceWan: number) => void; onResult?: (result: PropertySearchResult) => void; initialResult?: PropertySearchResult; embedded?: boolean }) {
  const { copy, locale } = useExperienceLocale();
  const [city, setCity] = useState("");
  const [districtText, setDistrictText] = useState("");
  const [budgetMin, setBudgetMin] = useState<number | "">("");
  const [budgetMax, setBudgetMax] = useState<number | "">(2500);
  const [areaMin, setAreaMin] = useState<number | "">(20);
  const [areaMax, setAreaMax] = useState<number | "">(45);
  const [buildingType, setBuildingType] = useState("");
  const [ageMax, setAgeMax] = useState<number | "">("");
  const [result, setResult] = useState<PropertySearchResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (initialResult) setResult(initialResult);
  }, [initialResult]);

  useEffect(() => {
    function applyDemoResult(event: Event) {
      const next = (event as CustomEvent<DemoResults>).detail.propertySearch;
      if (next) setResult(next);
    }
    window.addEventListener(GUIDED_DEMO_RESULT_EVENT, applyDemoResult);
    return () => window.removeEventListener(GUIDED_DEMO_RESULT_EVENT, applyDemoResult);
  }, []);

  function loadDemoConditions() {
    setCity("台北市"); setDistrictText("大安區"); setBudgetMin(1500); setBudgetMax(2500);
    setAreaMin(25); setAreaMax(35); setBuildingType("住宅大樓"); setAgeMax(""); setResult(undefined);
    setFeedback(`${copy("finder.demo")} — ${copy("finder.search")}`);
  }

  async function search() {
    if (!budgetMax) return;
    setLoading(true);
    setError("");
    try {
      const next = await api.propertySearch({
        city,
        districts: districtText.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
        budget_min: budgetMin || undefined,
        budget_max: budgetMax,
        area_ping_min: areaMin || undefined,
        area_ping_max: areaMax || undefined,
        building_type: buildingType,
        building_age_max: ageMax || undefined,
        limit: 50,
      });
      setResult(next);
      onResult?.(next);
    } catch {
      setError(copy("finder.error"));
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "w-full min-w-0 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100";
  return <div className="min-w-0 space-y-8"><div id="property-finder" className="scroll-mt-20"><SectionCard title={copy("finder.title")} description={copy("finder.description")}>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <label className="text-xs text-slate-500">{copy("finder.county")}<input className={`${inputClass} mt-1`} value={city} onChange={(event) => setCity(event.target.value)} placeholder={copy("finder.county")} /></label>
      <label className="text-xs text-slate-500">{copy("finder.district")}<input className={`${inputClass} mt-1`} value={districtText} onChange={(event) => setDistrictText(event.target.value)} placeholder={copy("finder.district")} /></label>
      <NumberInput label={copy("finder.budgetMin")} value={budgetMin} onChange={setBudgetMin} />
      <NumberInput label={copy("finder.budgetMax")} value={budgetMax} onChange={setBudgetMax} />
      <NumberInput label={copy("finder.areaMin")} value={areaMin} onChange={setAreaMin} />
      <NumberInput label={copy("finder.areaMax")} value={areaMax} onChange={setAreaMax} />
      <label className="text-xs text-slate-500">{copy("finder.buildingType")}<select data-localize-structured-select data-option-kind="building" className={`${inputClass} mt-1`} value={buildingType} onChange={(event) => setBuildingType(event.target.value)}><option value="">{copy("finder.unlimited")}</option>{BUILDING_TYPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{getLocalizedBuildingTypeLabel(option.value, locale)}</option>)}</select></label>
      <NumberInput label={copy("finder.ageMax")} value={ageMax} onChange={setAgeMax} />
    </div>
    <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
      <Button className="w-full sm:w-auto" disabled={loading || !budgetMax} onClick={search}>{loading ? copy("finder.searching") : copy("finder.search")}</Button>
      <Button secondary className="w-full sm:w-auto" disabled={loading} onClick={loadDemoConditions}>{copy("finder.demo")}</Button>
      <p className="text-[10px] leading-5 text-slate-500">{copy("finder.sourceNote")}</p>
    </div>
    {!budgetMax && <p className="mt-2 text-[10px] text-amber-700">{copy("finder.budgetRequired")}</p>}
    {feedback && <div className="mt-3"><Notice>{feedback}</Notice></div>}
    {error && <div className="mt-4"><ErrorState message={error} /></div>}
    {loading && <div className="mt-4"><LoadingState label={copy("finder.searching")} /></div>}
    {!result && !loading && <div className="mt-4"><EmptyState title={copy("finder.empty")} detail={copy("finder.emptyDetail")} /></div>}
    {result && !loading && <PropertyFinderResults result={result} onUseForValuation={onUseForValuation} onUseForLoan={onUseForLoan} onUseForHoldingCost={onUseForHoldingCost} onUseForLocationInsight={onUseForLocationInsight} />}
  </SectionCard></div>{!embedded && <ImmersiveViewingWorkspace propertySearch={result}/>}</div>;
}

function PropertyFinderResults({ result, onUseForValuation, onUseForLoan, onUseForHoldingCost, onUseForLocationInsight }: { result: PropertySearchResult; onUseForValuation: (selection: PropertyFinderSelection) => void; onUseForLoan: (priceWan: number, selection: PropertyFinderSelection) => void; onUseForHoldingCost: (priceWan: number, areaPing: number, selection: PropertyFinderSelection) => void; onUseForLocationInsight: (selection: PropertyFinderSelection, priceWan: number) => void }) {
  const { copy } = useExperienceLocale();
  const visualModel = buildPropertySearchVisualModel(result);
  if (visualModel.state !== "available") return <div className="mt-5"><VisualDataUnavailableState message={visualModel.state === "no_data" ? copy("finder.noData") : copy("common.unavailable")} /><PropertySearchEvidenceSummary model={visualModel} /></div>;
  return <div className="mt-6 space-y-5 border-t border-stone-200 pt-5">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricTile label={copy("common.count")} value={`${result.summary.matched_count.toLocaleString()} ${copy("common.records")}`} note={result.summary.data_source_label} />
      <MetricTile label={copy("finder.districts")} value={`${result.summary.district_count}`} note={`${result.summary.city_count}`} />
      <MetricTile label={copy("finder.roads")} value={`${result.summary.road_count}`} />
      <MetricTile label={copy("common.period")} value={result.summary.period_min && result.summary.period_max ? `${result.summary.period_min} ~ ${result.summary.period_max}` : copy("common.noData")} />
    </div>
    <div>
      <h3 className="text-sm font-bold text-slate-900">{copy("finder.districts")}</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{result.district_suggestions.map((item) => <article key={`${item.city}-${item.district}`} className="rounded-xl border border-stone-200 bg-stone-50/70 p-3"><div className="flex items-start justify-between gap-3"><div><p className="font-bold text-slate-900">{item.city} {item.district}</p><p className="mt-1 text-[10px] text-slate-500">{item.sample_count} {copy("common.records")} · {copy("valuation.totalPrice")} {item.median_total_price.toLocaleString()}</p></div><span className="rounded-full bg-cyan-100 px-2 py-1 text-[10px] font-bold text-cyan-800">{item.score}</span></div><p className="mt-3 text-xs leading-5 text-slate-600">{item.reason}</p></article>)}</div>
    </div>
    {visualModel.state === "available" ? <div className="grid min-w-0 gap-4 lg:grid-cols-2"><PropertySearchPriceRangeChart title={copy("valuation.range")} data={visualModel.districtRanges} /><PropertySearchPriceRangeChart title={copy("valuation.range")} data={visualModel.roadRanges} /><PropertySearchSampleChart data={visualModel.districtRanges} /><PropertySearchEvidenceSummary model={visualModel} /></div> : <VisualDataUnavailableState message={copy("common.unavailable")} />}
    <FinderTable title={copy("finder.roads")} minWidth="min-w-[820px]" headers={[copy("finder.districts"), copy("common.selectRoad"), copy("common.count"), copy("valuation.mid"), copy("finder.areaMin"), copy("finder.buildingType"), copy("action.open")] }>
      {result.road_suggestions.map((item) => { const selection=suggestionSelection(item); return <tr key={`${item.city}-${item.district}-${item.road}`} className="border-t border-stone-100"><td className="p-2">{item.city} {item.district}</td><td>{item.road}</td><td>{item.sample_count}</td><td>{item.median_total_price.toLocaleString()} 萬</td><td>{item.median_area_ping} 坪</td><td>{item.common_building_type}</td><td><FinderActions onValuation={() => onUseForValuation(selection)} onLoan={() => onUseForLoan(item.median_total_price, selection)} onHoldingCost={() => onUseForHoldingCost(item.median_total_price, item.median_area_ping, selection)} onLocation={() => onUseForLocationInsight(selection,item.median_total_price)} /></td></tr>; })}
    </FinderTable>
    <FinderTable title={copy("finder.transactions")} minWidth="min-w-[980px]" headers={[copy("common.period"), copy("finder.districts"), copy("common.selectRoad"), copy("finder.buildingType"), copy("finder.areaMin"), copy("valuation.estimateTotal"), copy("valuation.unitPrice"), copy("common.source"), copy("action.open")] }>
      {result.matched_transactions.map((item, index) => { const selection=transactionSelection(item); return <tr key={`${item.transaction_period}-${item.road}-${index}`} className="border-t border-stone-100"><td className="whitespace-nowrap p-2">{item.transaction_period}</td><td>{item.city} {item.district}</td><td>{item.road}</td><td>{item.building_type}</td><td>{item.area_ping}</td><td>{item.total_price.toLocaleString()} 萬</td><td>{item.unit_price_per_ping} 萬</td><td><span className="whitespace-nowrap rounded-full bg-cyan-50 px-2 py-1 font-bold text-cyan-800">{item.source_label}</span></td><td><FinderActions onValuation={() => onUseForValuation(selection)} onLoan={() => onUseForLoan(item.total_price, selection)} onHoldingCost={() => onUseForHoldingCost(item.total_price, item.area_ping, selection)} onLocation={() => onUseForLocationInsight(selection,item.total_price)} /></td></tr>; })}
    </FinderTable>
    <Notice tone="warning">{result.disclaimer}</Notice>
  </div>;
}

function FinderTable({ title, headers, minWidth, children }: { title: string; headers: string[]; minWidth: string; children: ReactNode }) {
  const { copy } = useExperienceLocale();
  const table = <><p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">{copy("finder.tableSwipe")}</p><div className="max-w-full touch-pan-x overflow-x-auto"><table className={`w-full ${minWidth} text-left text-[10px]`}><thead><tr className="bg-stone-50">{headers.map((header, index) => <th key={header} className={index === 0 ? "p-2" : ""}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div></>;
  return <DetailDisclosure title={`${copy("action.open")} ${title}`}>{table}</DetailDisclosure>;
}

function FinderActions({ onValuation, onLoan, onHoldingCost, onLocation }: { onValuation: () => void; onLoan: () => void; onHoldingCost: () => void; onLocation?: () => void }) {
  const { copy } = useExperienceLocale();
  return <div className="grid min-w-[190px] grid-cols-2 gap-1.5 sm:flex sm:flex-wrap"><button type="button" aria-label={copy("finder.useValuation")} onClick={onValuation} className="whitespace-nowrap rounded-md border border-cyan-200 bg-white px-2.5 py-1.5 font-bold text-cyan-800 transition hover:bg-cyan-50">{copy("finder.useValuation")}</button><button type="button" aria-label={copy("finder.useLoan")} onClick={onLoan} className="whitespace-nowrap rounded-md border border-violet-200 bg-white px-2.5 py-1.5 font-bold text-violet-800 transition hover:bg-violet-50">{copy("finder.useLoan")}</button><button type="button" aria-label={copy("finder.useHolding")} onClick={onHoldingCost} className="whitespace-nowrap rounded-md border border-amber-200 bg-white px-2.5 py-1.5 font-bold text-amber-800 transition hover:bg-amber-50">{copy("finder.useHolding")}</button><button type="button" aria-label={copy("finder.useLocation")} onClick={onLocation} className="whitespace-nowrap rounded-md border border-emerald-200 bg-white px-2.5 py-1.5 font-bold text-emerald-800 transition hover:bg-emerald-50">{copy("finder.useLocation")}</button></div>;
}

function NumberInput({ label, value, onChange }: { label: string; value: number | ""; onChange: (value: number | "") => void }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" min="0" className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100" value={value} onChange={(event) => onChange(event.target.value === "" ? "" : Number(event.target.value))} /></label>;
}

function suggestionSelection(item: PropertySearchSuggestion): PropertyFinderSelection {
  return { city: item.city, district: item.district, road: item.road ?? "", building_type: item.common_building_type, area_ping: item.median_area_ping, asking_price_wan: item.median_total_price };
}

function transactionSelection(item: PropertySearchTransaction): PropertyFinderSelection {
  return { city: item.city, district: item.district, road: item.road, building_type: item.building_type, area_ping: item.area_ping, building_age_years: item.building_age_years, floor: item.floor, asking_price_wan: item.total_price };
}
