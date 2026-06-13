"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { api, PropertySearchResult, PropertySearchSuggestion, PropertySearchTransaction } from "@/lib/api";
import { Button, EmptyState, Notice } from "@/components/ui";
import { ErrorState, LoadingState, MetricTile, SectionCard } from "@/components/product-ui";

export type PropertyFinderSelection = {
  city: string;
  district: string;
  road: string;
  building_type: string;
  area_ping: number;
};

export function PropertyFinder({ onUse, onLoanPrice, onResult }: { onUse: (selection: PropertyFinderSelection) => void; onLoanPrice: (priceWan: number) => void; onResult?: (result: PropertySearchResult) => void }) {
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
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "w-full min-w-0 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100";
  return <SectionCard title="找房雷達" description="依預算與條件，從官方實價登錄成交資料找出較符合的區域與路段，作為看屋方向參考。">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <label className="text-xs text-slate-500">縣市（可留空）<input className={`${inputClass} mt-1`} value={city} onChange={(event) => setCity(event.target.value)} placeholder="例如：台北市" /></label>
      <label className="text-xs text-slate-500">行政區（可用逗號分隔）<input className={`${inputClass} mt-1`} value={districtText} onChange={(event) => setDistrictText(event.target.value)} placeholder="例如：大安區、信義區" /></label>
      <NumberInput label="預算下限（萬元）" value={budgetMin} onChange={setBudgetMin} />
      <NumberInput label="預算上限（萬元）" value={budgetMax} onChange={setBudgetMax} />
      <NumberInput label="坪數下限" value={areaMin} onChange={setAreaMin} />
      <NumberInput label="坪數上限" value={areaMax} onChange={setAreaMax} />
      <label className="text-xs text-slate-500">建物型態<select className={`${inputClass} mt-1`} value={buildingType} onChange={(event) => setBuildingType(event.target.value)}><option value="">不限</option><option>住宅大樓</option><option>華廈</option><option>公寓</option><option>套房</option></select></label>
      <NumberInput label="屋齡上限" value={ageMax} onChange={setAgeMax} />
    </div>
    <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
      <Button className="w-full sm:w-auto" disabled={loading || !budgetMax} onClick={search}>{loading ? "搜尋中..." : "搜尋看屋方向"}</Button>
      <p className="text-[10px] leading-5 text-slate-500">僅使用 rolling 3 年官方 PLVR 歷史成交，不代表目前有待售物件。</p>
    </div>
    {error && <div className="mt-4"><ErrorState message={error} /></div>}
    {loading && <div className="mt-4"><LoadingState label="整理符合條件的區域與路段..." /></div>}
    {result && !loading && <PropertyFinderResults result={result} onUse={onUse} onLoanPrice={onLoanPrice} />}
  </SectionCard>;
}

function PropertyFinderResults({ result, onUse, onLoanPrice }: { result: PropertySearchResult; onUse: (selection: PropertyFinderSelection) => void; onLoanPrice: (priceWan: number) => void }) {
  if (!result.summary.matched_count) return <div className="mt-5"><EmptyState title="尚未找到符合條件的歷史成交" detail={result.summary.message} /></div>;
  return <div className="mt-6 space-y-5 border-t border-stone-200 pt-5">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricTile label="符合成交" value={`${result.summary.matched_count.toLocaleString()} 筆`} note={result.summary.data_source_label} />
      <MetricTile label="涵蓋行政區" value={`${result.summary.district_count} 區`} note={`${result.summary.city_count} 縣市`} />
      <MetricTile label="可參考路段" value={`${result.summary.road_count} 路段`} />
      <MetricTile label="成交期間" value={result.summary.period_min && result.summary.period_max ? `${result.summary.period_min} ~ ${result.summary.period_max}` : "資料不足"} />
    </div>
    <div>
      <h3 className="text-sm font-bold text-slate-900">推薦行政區</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{result.district_suggestions.map((item) => <article key={`${item.city}-${item.district}`} className="rounded-xl border border-stone-200 bg-stone-50/70 p-3"><div className="flex items-start justify-between gap-3"><div><p className="font-bold text-slate-900">{item.city} {item.district}</p><p className="mt-1 text-[10px] text-slate-500">{item.sample_count} 筆成交 · 中位總價 {item.median_total_price.toLocaleString()} 萬</p></div><span className="rounded-full bg-cyan-100 px-2 py-1 text-[10px] font-bold text-cyan-800">{item.score}</span></div><p className="mt-3 text-xs leading-5 text-slate-600">{item.reason}</p></article>)}</div>
    </div>
    <FinderTable title="推薦路段" minWidth="min-w-[820px]" headers={["區域", "路段", "成交筆數", "中位總價", "中位坪數", "常見型態", "操作"]}>
      {result.road_suggestions.map((item) => <tr key={`${item.city}-${item.district}-${item.road}`} className="border-t border-stone-100"><td className="p-2">{item.city} {item.district}</td><td>{item.road}</td><td>{item.sample_count}</td><td>{item.median_total_price.toLocaleString()} 萬</td><td>{item.median_area_ping} 坪</td><td>{item.common_building_type}</td><td><FinderActions onValuation={() => onUse(suggestionSelection(item))} onLoan={() => onLoanPrice(item.median_total_price)} /></td></tr>)}
    </FinderTable>
    <FinderTable title="符合條件的成交樣本" minWidth="min-w-[980px]" headers={["期間", "區域", "路段", "型態", "坪數", "總價", "每坪單價", "來源", "操作"]}>
      {result.matched_transactions.map((item, index) => <tr key={`${item.transaction_period}-${item.road}-${index}`} className="border-t border-stone-100"><td className="whitespace-nowrap p-2">{item.transaction_period}</td><td>{item.city} {item.district}</td><td>{item.road}</td><td>{item.building_type}</td><td>{item.area_ping}</td><td>{item.total_price.toLocaleString()} 萬</td><td>{item.unit_price_per_ping} 萬</td><td><span className="whitespace-nowrap rounded-full bg-cyan-50 px-2 py-1 font-bold text-cyan-800">{item.source_label}</span></td><td><FinderActions onValuation={() => onUse(transactionSelection(item))} onLoan={() => onLoanPrice(item.total_price)} /></td></tr>)}
    </FinderTable>
    <Notice tone="warning">{result.disclaimer}</Notice>
  </div>;
}

function FinderTable({ title, headers, minWidth, children }: { title: string; headers: string[]; minWidth: string; children: ReactNode }) {
  return <div><h3 className="text-sm font-bold text-slate-900">{title}</h3><p className="mb-2 mt-1 text-[10px] font-medium text-slate-400 sm:hidden">表格可左右滑動</p><div className="max-w-full touch-pan-x overflow-x-auto"><table className={`w-full ${minWidth} text-left text-[10px]`}><thead><tr className="bg-stone-50">{headers.map((header, index) => <th key={header} className={index === 0 ? "p-2" : ""}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div></div>;
}

function FinderActions({ onValuation, onLoan }: { onValuation: () => void; onLoan: () => void }) {
  return <div className="flex gap-1"><button type="button" onClick={onValuation} className="whitespace-nowrap rounded-lg border border-cyan-200 px-2 py-1 font-bold text-cyan-800 transition hover:bg-cyan-50">帶入估價</button><button type="button" onClick={onLoan} className="whitespace-nowrap rounded-lg border border-violet-200 px-2 py-1 font-bold text-violet-800 transition hover:bg-violet-50">帶入貸款</button></div>;
}

function NumberInput({ label, value, onChange }: { label: string; value: number | ""; onChange: (value: number | "") => void }) {
  return <label className="text-xs text-slate-500">{label}<input type="number" min="0" className="mt-1 w-full min-w-0 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100" value={value} onChange={(event) => onChange(event.target.value === "" ? "" : Number(event.target.value))} /></label>;
}

function suggestionSelection(item: PropertySearchSuggestion): PropertyFinderSelection {
  return { city: item.city, district: item.district, road: item.road ?? "", building_type: item.common_building_type, area_ping: item.median_area_ping };
}

function transactionSelection(item: PropertySearchTransaction): PropertyFinderSelection {
  return { city: item.city, district: item.district, road: item.road, building_type: item.building_type, area_ping: item.area_ping };
}
