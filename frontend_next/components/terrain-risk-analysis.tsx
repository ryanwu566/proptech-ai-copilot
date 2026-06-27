"use client";

import { useEffect, useState } from "react";
import { api, type LocationInsightResult, type TerrainHazardLayer, type TerrainRiskResult } from "@/lib/api";
import { HelpTooltip } from "@/components/help-tooltip";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";
import { HELP_CONTENT } from "@/lib/help-content";

export const TERRAIN_RISK_SESSION_KEY = "proptech:terrain-risk-result";
export const TERRAIN_RISK_RESULT_EVENT = "proptech:terrain-risk-result-ready";
export const TERRAIN_RISK_PREFILL_EVENT = "proptech:terrain-risk-prefill";

export type TerrainRiskPrefill = {
  address?: string;
  city?: string;
  district?: string;
  road?: string;
  latitude?: number;
  longitude?: number;
  radius_m?: number;
};

const DEFAULT_LAYERS = ["terrain", "landslide", "debris_flow", "flood", "geological_sensitivity", "liquefaction", "active_fault"];

export function prefillTerrainRisk(prefill: TerrainRiskPrefill) {
  window.dispatchEvent(new CustomEvent<TerrainRiskPrefill>(TERRAIN_RISK_PREFILL_EVENT, { detail: prefill }));
}

export function TerrainRiskAnalysis({ location }: { location?: LocationInsightResult }) {
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("台北市");
  const [district, setDistrict] = useState("大安區");
  const [road, setRoad] = useState("和平東路二段");
  const [latitude, setLatitude] = useState<number | "">("");
  const [longitude, setLongitude] = useState<number | "">("");
  const [radius, setRadius] = useState(500);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [result, setResult] = useState<TerrainRiskResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    function applyPrefill(event: Event) {
      const detail = (event as CustomEvent<TerrainRiskPrefill>).detail;
      setAddress(detail.address ?? "");
      setCity(detail.city ?? "");
      setDistrict(detail.district ?? "");
      setRoad(detail.road ?? "");
      setLatitude(detail.latitude ?? "");
      setLongitude(detail.longitude ?? "");
      setRadius(detail.radius_m ?? 500);
      setResult(undefined);
      window.sessionStorage.removeItem(TERRAIN_RISK_SESSION_KEY);
    }
    window.addEventListener(TERRAIN_RISK_PREFILL_EVENT, applyPrefill);
    return () => window.removeEventListener(TERRAIN_RISK_PREFILL_EVENT, applyPrefill);
  }, []);

  useEffect(() => {
    function applyResult(event: Event) {
      setResult((event as CustomEvent<TerrainRiskResult>).detail);
    }
    window.addEventListener(TERRAIN_RISK_RESULT_EVENT, applyResult);
    return () => window.removeEventListener(TERRAIN_RISK_RESULT_EVENT, applyResult);
  }, []);

  function useLocationPosition() {
    if (!location?.resolved_location) return;
    setAddress(location.resolved_location.address_label ?? "");
    setLatitude(location.resolved_location.latitude);
    setLongitude(location.resolved_location.longitude);
  }

  async function analyze() {
    setLoading(true);
    setError("");
    try {
      const next = await api.terrainRiskAnalyze({
        address, city, district, road, radius_m: radius,
        latitude: latitude === "" ? undefined : latitude,
        longitude: longitude === "" ? undefined : longitude,
        include_layers: layers,
      });
      setResult(next);
      window.sessionStorage.setItem(TERRAIN_RISK_SESSION_KEY, JSON.stringify(next));
      window.dispatchEvent(new CustomEvent<TerrainRiskResult>(TERRAIN_RISK_RESULT_EVENT, { detail: next }));
      window.dispatchEvent(new Event("proptech:workflow-status-updated"));
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const canAnalyze = Boolean(address.trim() || road.trim() || (latitude !== "" && longitude !== ""));
  const inputClass = "mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm";
  return <section id="terrain-risk-analysis" className="scroll-mt-20">
    <SectionCard title="地勢與災害風險分析" description="用官方公開圖資，初步檢查坡度、淹水、坡地災害與地質敏感風險。">
      <div className="mb-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-6 text-amber-900">
        <span>這是買房前的初步公開資料檢查，不代表正式防災結論或建築結構鑑定。</span>
        <HelpTooltip title={HELP_CONTENT.terrainRisk.title}>{HELP_CONTENT.terrainRisk.body}</HelpTooltip>
      </div>
      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="grid min-w-0 gap-3">
          <label className="text-xs text-slate-500">地址<input className={inputClass} value={address} onChange={(event) => setAddress(event.target.value)} placeholder="例：台北市大安區和平東路二段" /></label>
          <div className="grid gap-2 sm:grid-cols-3">
            <label className="text-xs text-slate-500">縣市<input className={inputClass} value={city} onChange={(event) => setCity(event.target.value)} /></label>
            <label className="text-xs text-slate-500">行政區<input className={inputClass} value={district} onChange={(event) => setDistrict(event.target.value)} /></label>
            <label className="text-xs text-slate-500">路段<input className={inputClass} value={road} onChange={(event) => setRoad(event.target.value)} /></label>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <label className="text-xs text-slate-500">緯度（選填）<input type="number" step="0.000001" className={inputClass} value={latitude} onChange={(event) => setLatitude(event.target.value === "" ? "" : Number(event.target.value))} /></label>
            <label className="text-xs text-slate-500">經度（選填）<input type="number" step="0.000001" className={inputClass} value={longitude} onChange={(event) => setLongitude(event.target.value === "" ? "" : Number(event.target.value))} /></label>
            <label className="text-xs text-slate-500">半徑（100–2000m）<input type="number" min="100" max="2000" className={inputClass} value={radius} onChange={(event) => setRadius(Number(event.target.value))} /></label>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600">
            {DEFAULT_LAYERS.map((layer) => <label key={layer} className="flex items-center gap-2 rounded-lg border border-stone-200 px-2 py-1"><input type="checkbox" checked={layers.includes(layer)} onChange={() => setLayers((rows) => rows.includes(layer) ? rows.filter((item) => item !== layer) : [...rows, layer])} />{layerLabel(layer)}</label>)}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <Button secondary disabled={!location?.resolved_location} onClick={useLocationPosition}>使用目前區位分析位置</Button>
            <Button className="w-full" disabled={loading || !canAnalyze} onClick={analyze}>{loading ? "分析中..." : "開始分析地勢風險"}</Button>
          </div>
          {!canAnalyze && <p className="text-[10px] leading-5 text-amber-700">請先輸入地址、路段或座標，再開始分析地勢風險。</p>}
          {error && <ErrorState message={error} />}
        </div>
        <div className="min-w-0">
          {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm leading-7 text-slate-500">尚未分析。完成區位分析後可帶入座標，或直接輸入地址後按「開始分析地勢風險」。</div> : <TerrainRiskResults result={result} />}
        </div>
      </div>
    </SectionCard>
  </section>;
}

function TerrainRiskResults({ result }: { result: TerrainRiskResult }) {
  const hazards = Object.values(result.hazards);
  return <div className="min-w-0 space-y-4">
    <div className={`rounded-xl border p-4 ${toneClass(result.overall.level)}`}>
      <p className="text-[10px] font-bold tracking-wider">地勢與災害風險</p>
      <h3 className="mt-1 text-xl font-extrabold">{result.overall.label}</h3>
      <p className="mt-2 text-sm leading-6">{result.overall.summary}</p>
      <p className="mt-2 text-[10px]">信心：{result.overall.confidence} · 資料品質：{result.data_quality.status}</p>
    </div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <MetricTile label="坡度／高程" value={result.terrain.slope_class ?? result.terrain.status} note={result.terrain.explanation} />
      {hazards.map((hazard) => <HazardCard key={hazard.key} hazard={hazard} />)}
    </div>
    {result.risk_factors.length > 0 ? <ListCard title="命中或需注意項目" items={result.risk_factors.map((item) => `${item.title}：${item.message}`)} /> : <Notice>目前沒有可用來源命中明確風險；若資料來源不足，不能解讀為低風險。</Notice>}
    <ListCard title="建議補查" items={result.recommended_checks} />
    <details className="min-w-0 rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-3 py-2.5 text-xs font-bold text-slate-700">查看官方來源與地圖圖層摘要</summary>
      <div className="max-w-full touch-pan-x overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-xs">
          <thead><tr className="bg-stone-50"><th className="p-2">圖層</th><th>狀態</th><th>資料年度</th><th>限制</th><th>外部查看</th></tr></thead>
          <tbody>{result.map_layers.map((layer) => <tr key={layer.key} className="border-t border-stone-100"><td className="p-2">{layer.label}</td><td>{layer.status}</td><td>{layer.data_vintage || "需至來源確認"}</td><td>{layer.limitation || layer.source_url || "未提供"}</td><td>{layer.external_view_url ? <a className="font-bold text-cyan-700 underline" href={layer.external_view_url} target="_blank" rel="noreferrer">前往官方圖台查看</a> : "需手動查詢"}</td></tr>)}</tbody>
        </table>
      </div>
    </details>
    {result.missing_sources.length > 0 && <Notice tone="warning">資料不足／需至官方圖台確認：{result.missing_sources.join("、")}</Notice>}
    <p className="text-[10px] leading-5 text-amber-700">{result.disclaimer}</p>
  </div>;
}

function HazardCard({ hazard }: { hazard: TerrainHazardLayer }) {
  return <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
    <p className="text-xs font-bold text-slate-800">{hazard.label}</p>
    <p className="mt-1 text-lg font-extrabold text-slate-950">{hazard.matched ? riskLabel(hazard.level) : statusLabel(hazard.status)}</p>
    <p className="mt-2 text-[11px] leading-5 text-slate-600">{hazard.explanation}</p>
    <p className="mt-2 text-[10px] text-slate-400">{hazard.source?.agency ?? "官方來源"} · {hazard.source?.status ?? hazard.status}</p>
  </div>;
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-xl border border-stone-200 bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}

function layerLabel(layer: string) {
  return ({ terrain: "地形", landslide: "坡地災害", debris_flow: "土石流", flood: "淹水", geological_sensitivity: "地質敏感", liquefaction: "土壤液化", active_fault: "活動斷層" } as Record<string, string>)[layer] ?? layer;
}

function statusLabel(status: string) {
  return ({ available: "已比對", limited: "有限資料", unavailable: "資料不足", error: "查詢失敗", skipped: "本次略過" } as Record<string, string>)[status] ?? status;
}

function riskLabel(level: string) {
  return ({ high: "需要優先確認", medium: "有項目需注意", low: "未比對到明確風險", unknown: "資料不足" } as Record<string, string>)[level] ?? level;
}

function toneClass(level: string) {
  if (level === "high") return "border-rose-200 bg-rose-50 text-rose-950";
  if (level === "medium") return "border-amber-200 bg-amber-50 text-amber-950";
  if (level === "low") return "border-emerald-200 bg-emerald-50 text-emerald-950";
  return "border-slate-200 bg-slate-50 text-slate-900";
}
