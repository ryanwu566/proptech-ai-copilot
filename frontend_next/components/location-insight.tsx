"use client";

import { useEffect, useState } from "react";
import { api, LocationInsightResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";


export type LocationInsightPrefill = {
  city?: string;
  district?: string;
  road?: string;
  address?: string;
  property_price?: number;
  area_ping?: number;
  building_type?: string;
};

export const LOCATION_INSIGHT_PREFILL_EVENT = "proptech:location-insight-prefill";
export const LOCATION_INSIGHT_SESSION_KEY = "proptech:location-insight-result";

export function prefillLocationInsight(prefill: LocationInsightPrefill) {
  window.dispatchEvent(new CustomEvent<LocationInsightPrefill>(LOCATION_INSIGHT_PREFILL_EVENT, { detail: prefill }));
}

export function LocationInsight() {
  const [city, setCity] = useState("台北市");
  const [district, setDistrict] = useState("大安區");
  const [road, setRoad] = useState("和平東路二段");
  const [address, setAddress] = useState("");
  const [radius, setRadius] = useState(800);
  const [propertyPrice, setPropertyPrice] = useState<number | "">("");
  const [areaPing, setAreaPing] = useState<number | "">("");
  const [buildingType, setBuildingType] = useState("");
  const [result, setResult] = useState<LocationInsightResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    function applyPrefill(event: Event) {
      const detail = (event as CustomEvent<LocationInsightPrefill>).detail;
      setCity(detail.city ?? "");
      setDistrict(detail.district ?? "");
      setRoad(detail.road ?? "");
      setAddress(detail.address ?? "");
      setPropertyPrice(detail.property_price ?? "");
      setAreaPing(detail.area_ping ?? "");
      setBuildingType(detail.building_type ?? "");
      setResult(undefined);
      window.sessionStorage.removeItem(LOCATION_INSIGHT_SESSION_KEY);
    }
    window.addEventListener(LOCATION_INSIGHT_PREFILL_EVENT, applyPrefill);
    return () => window.removeEventListener(LOCATION_INSIGHT_PREFILL_EVENT, applyPrefill);
  }, []);

  async function analyze() {
    setLoading(true);
    setError("");
    try {
      const next = await api.locationInsight({
        city, district, road, address, radius_m: radius,
        property_price: propertyPrice === "" ? undefined : propertyPrice,
        area_ping: areaPing === "" ? undefined : areaPing,
        building_type: buildingType,
        use_existing_poi_sources: true,
      });
      setResult(next);
      window.sessionStorage.setItem(LOCATION_INSIGHT_SESSION_KEY, JSON.stringify(next));
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm";
  return <SectionCard title="區位分析" description="沿用既有定位與 800m POI 生活圈資料，用可解釋規則整理買房前的區位優缺點。">
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="grid min-w-0 gap-3">
        <label className="text-xs text-slate-500">縣市<input className={inputClass} value={city} onChange={(event) => setCity(event.target.value)} /></label>
        <label className="text-xs text-slate-500">行政區<input className={inputClass} value={district} onChange={(event) => setDistrict(event.target.value)} /></label>
        <label className="text-xs text-slate-500">路段<input className={inputClass} value={road} onChange={(event) => setRoad(event.target.value)} /></label>
        <label className="text-xs text-slate-500">完整地址（可選）<input className={inputClass} value={address} onChange={(event) => setAddress(event.target.value)} /></label>
        <label className="text-xs text-slate-500">分析半徑（公尺）<input type="number" min="100" max="1500" className={inputClass} value={radius} onChange={(event) => setRadius(Number(event.target.value))} /></label>
        <label className="text-xs text-slate-500">房屋總價（萬元，可選）<input type="number" min="0" className={inputClass} value={propertyPrice} onChange={(event) => setPropertyPrice(event.target.value === "" ? "" : Number(event.target.value))} /></label>
        <label className="text-xs text-slate-500">坪數（可選）<input type="number" min="0" className={inputClass} value={areaPing} onChange={(event) => setAreaPing(event.target.value === "" ? "" : Number(event.target.value))} /></label>
        <Button className="w-full" disabled={loading || (!address.trim() && !road.trim())} onClick={analyze}>{loading ? "分析中..." : "分析區位"}</Button>
        {error && <ErrorState message={error} />}
      </div>
      <div className="min-w-0">
        {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500">輸入地點，或從找房雷達／估價條件帶入後分析區位。</div> : <LocationResults result={result} />}
      </div>
    </div>
  </SectionCard>;
}

function LocationResults({ result }: { result: LocationInsightResult }) {
  if (result.data_quality.status === "unavailable") {
    return <div className="space-y-3"><Notice tone="warning">目前資料不足，建議改用完整地址或手動查詢。</Notice><DataQuality result={result} /></div>;
  }
  const scoreLabels: [keyof LocationInsightResult["category_scores"], string][] = [["transit_score", "交通"], ["convenience_score", "生活機能"], ["education_score", "教育"], ["green_space_score", "公園"], ["medical_score", "醫療"], ["risk_score", "風險資料"]];
  return <div className="min-w-0 space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><MetricTile label="區位總分" value={result.location_score ?? "資料不足"} note={result.resolved_location?.address_label} />{scoreLabels.map(([key, label]) => <MetricTile key={key} label={`${label}分數`} value={result.category_scores[key]} />)}</div>
    <div className="grid gap-3 sm:grid-cols-2"><ListCard title="區位優點" items={result.strengths} /><ListCard title="區位缺點" items={result.weaknesses} /></div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(result.poi_summary).map(([key, value]) => <MetricTile key={key} label={poiLabel(key)} value={`${value} 處`} />)}</div>
    <div><p className="mb-2 text-xs font-bold text-slate-800">最近 POI</p><p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">表格可左右滑動</p><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">類別</th><th>名稱</th><th>距離</th><th>來源</th></tr></thead><tbody>{result.nearest_pois.map((item, index) => <tr key={`${item.name}-${index}`} className="border-t border-stone-100"><td className="p-2">{item.category}</td><td>{item.name}</td><td>{item.distance_m}m</td><td>{item.source}</td></tr>)}</tbody></table></div></div>
    <ListCard title="適合族群" items={Object.entries(result.buyer_fit).map(([key, value]) => `${buyerLabel(key)}：${value}`)} />
    <Notice>{result.valuation_context.explanation}</Notice>
    <DataQuality result={result} />
    <p className="text-[10px] leading-5 text-amber-700">{result.disclaimer}</p>
  </div>;
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-xl border border-stone-200 bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}

function DataQuality({ result }: { result: LocationInsightResult }) {
  return <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"><strong>資料品質：{result.data_quality.status}</strong><ul className="mt-1 space-y-1">{result.data_quality.warnings.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}

function poiLabel(key: string) {
  return ({ transit_count: "交通 POI", convenience_count: "採買／餐飲 POI", school_count: "學校", park_count: "公園", medical_count: "醫療", risk_facility_count: "嫌惡設施資料" } as Record<string, string>)[key] ?? key;
}

function buyerLabel(key: string) {
  return ({ self_use_family: "自住家庭", commuter: "通勤族", investor: "投資評估", elderly: "高齡族群" } as Record<string, string>)[key] ?? key;
}
