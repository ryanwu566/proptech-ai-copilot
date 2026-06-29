"use client";

import { useEffect, useState } from "react";
import { api, LocationInsightResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { TerrainRiskAnalysis, TERRAIN_RISK_SESSION_KEY } from "@/components/terrain-risk-analysis";
import { CommuteLivabilityCard } from "@/components/commute-livability-card";


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
export const LOCATION_INSIGHT_RESULT_EVENT = "proptech:location-insight-result-ready";

export function prefillLocationInsight(prefill: LocationInsightPrefill) {
  window.dispatchEvent(new CustomEvent<LocationInsightPrefill>(LOCATION_INSIGHT_PREFILL_EVENT, { detail: prefill }));
}

export function LocationInsight({ onMap }: { onMap?: () => void }) {
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

  function invalidateLocationFlow() {
    setResult(undefined);
    setError("");
    window.sessionStorage.removeItem(LOCATION_INSIGHT_SESSION_KEY);
    window.sessionStorage.removeItem(TERRAIN_RISK_SESSION_KEY);
  }

  useEffect(() => {
    function applyPrefill(event: Event) {
      const detail = (event as CustomEvent<LocationInsightPrefill>).detail;
      setCity(detail.city ?? "");
      setDistrict(detail.district ?? "");
      setRoad(detail.road ?? "");
      setAddress(detail.address ?? `${detail.city ?? ""}${detail.district ?? ""}${detail.road ?? ""}`);
      setPropertyPrice(detail.property_price ?? "");
      setAreaPing(detail.area_ping ?? "");
      setBuildingType(detail.building_type ?? "");
      invalidateLocationFlow();
    }
    window.addEventListener(LOCATION_INSIGHT_PREFILL_EVENT, applyPrefill);
    return () => window.removeEventListener(LOCATION_INSIGHT_PREFILL_EVENT, applyPrefill);
  }, []);

  useEffect(() => {
    function applyResult(event: Event) {
      setResult((event as CustomEvent<LocationInsightResult>).detail);
    }
    window.addEventListener(LOCATION_INSIGHT_RESULT_EVENT, applyResult);
    return () => window.removeEventListener(LOCATION_INSIGHT_RESULT_EVENT, applyResult);
  }, []);

  async function analyze() {
    if (!address.trim()) {
      setError("請先輸入完整物件地址。");
      return;
    }
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
      window.dispatchEvent(new CustomEvent<LocationInsightResult>(LOCATION_INSIGHT_RESULT_EVENT, { detail: next }));
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm";
  return <div id="location-insight-calculator" className="scroll-mt-20 space-y-5"><span id="location-insight" className="block scroll-mt-20" aria-hidden="true" /><SectionCard title="看位置" description="用同一個物件地址，依序完成位置洞察、地勢／災害風險、通勤與生活機能，再前往地圖查看。">
    <div className="mb-4 grid gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs text-slate-600 sm:grid-cols-4">
      <FlowBadge label="1. 位置洞察" active />
      <FlowBadge label="2. 地勢／災害風險" active={Boolean(result?.resolved_location)} />
      <FlowBadge label="3. 通勤與生活機能" active />
      <FlowBadge label="4. 在地圖查看" active />
    </div>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="grid min-w-0 gap-3">
        <label className="text-xs text-slate-500">物件地址<input className={inputClass} value={address} onChange={(event) => { setAddress(event.target.value); invalidateLocationFlow(); }} placeholder="請輸入完整物件地址" /></label>
        <label className="text-xs text-slate-500">分析半徑（公尺）<input type="number" min="100" max="1500" className={inputClass} value={radius} onChange={(event) => setRadius(Number(event.target.value))} /></label>
        <label className="text-xs text-slate-500">房屋總價（萬元，可選）<input type="number" min="0" className={inputClass} value={propertyPrice} onChange={(event) => setPropertyPrice(event.target.value === "" ? "" : Number(event.target.value))} /></label>
        <label className="text-xs text-slate-500">坪數（可選）<input type="number" min="0" className={inputClass} value={areaPing} onChange={(event) => setAreaPing(event.target.value === "" ? "" : Number(event.target.value))} /></label>
        <Button className="w-full" disabled={loading || !address.trim()} onClick={analyze}>{loading ? "分析中..." : "開始位置分析"}</Button>
        {!address.trim() && <p className="text-[10px] leading-5 text-amber-700">請先輸入完整物件地址。</p>}
        {address.trim() && !result && !loading && <p className="text-[10px] leading-5 text-slate-500">地址變更後，舊的位置洞察、地勢與通勤結果會失效；請重新按下開始位置分析。</p>}
        {error && <ErrorState message={error} />}
      </div>
      <div className="min-w-0">
        {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500">請先輸入完整物件地址，按下「開始位置分析」後才會呼叫位置洞察 API。</div> : <LocationResults result={result} />}
      </div>
    </div>
  </SectionCard>
    <details className="rounded-xl border border-stone-200 bg-white" open={Boolean(result?.resolved_location)}>
      <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">地勢／災害風險</summary>
      <div className="border-t border-stone-100 p-4"><TerrainRiskAnalysis location={result} compactFromLocation resetKey={address} /></div>
    </details>
    <details className="rounded-xl border border-stone-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">通勤與生活機能</summary>
      <div className="border-t border-stone-100 p-4"><CommuteLivabilityCard address={address} /></div>
    </details>
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-xs font-bold text-slate-900">在地圖查看</p><p className="mt-1 text-[11px] leading-5 text-slate-500">前往既有地圖洞察頁；目前不在工作台預先載入大型地圖，也不偽造地址同步。</p></div>
        <Button secondary className="w-full sm:w-auto" onClick={onMap}>在地圖查看</Button>
      </div>
    </div>
  </div>;
}

function FlowBadge({ label, active }: { label: string; active?: boolean }) {
  return <span className={`rounded-lg px-2.5 py-2 font-bold ${active ? "bg-cyan-50 text-cyan-800" : "bg-white text-slate-400"}`}>{label}</span>;
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
    <DetailDisclosure title="查看最近 POI 詳細表"><p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">表格可左右滑動</p><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">類別</th><th>名稱</th><th>距離</th><th>來源</th></tr></thead><tbody>{result.nearest_pois.map((item, index) => <tr key={`${item.name}-${index}`} className="border-t border-stone-100"><td className="p-2">{item.category}</td><td>{item.name}</td><td>{item.distance_m}m</td><td>{item.source}</td></tr>)}</tbody></table></div></DetailDisclosure>
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
  return <DetailDisclosure title="查看資料品質與限制"><div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"><strong>資料品質：{result.data_quality.status}</strong><ul className="mt-1 space-y-1">{result.data_quality.warnings.map((item) => <li key={item}>• {item}</li>)}</ul></div></DetailDisclosure>;
}

function poiLabel(key: string) {
  return ({ transit_count: "交通 POI", convenience_count: "採買／餐飲 POI", school_count: "學校", park_count: "公園", medical_count: "醫療", risk_facility_count: "嫌惡設施資料" } as Record<string, string>)[key] ?? key;
}

function buyerLabel(key: string) {
  return ({ self_use_family: "自住家庭", commuter: "通勤族", investor: "投資評估", elderly: "高齡族群" } as Record<string, string>)[key] ?? key;
}
