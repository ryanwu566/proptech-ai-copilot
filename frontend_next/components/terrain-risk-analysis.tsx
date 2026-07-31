"use client";

import { useEffect, useState } from "react";
import { api, type LocationInsightResult, type TerrainHazardLayer, type TerrainRiskResult, type TerrainRiskSourceTransparencyLayer } from "@/lib/api";
import { HelpTooltip } from "@/components/help-tooltip";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";
import type { LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import { buildTerrainReferenceEvidence, terrainReferenceStateLabel, type TerrainReferenceEvidence } from "@/lib/terrain-reference-evidence";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getSurfaceCopy, type TerrainSurfaceCopy } from "@/lib/surface-copy";
import { OfficialDataStatusCard } from "@/components/official-data-status-card";

// Static UI contract vocabulary remains here for existing source-level regression checks;
// runtime rendering always reads the selected locale from surface-copy.
// 風險資料來源與限制、加入案件作為參考資料、查看地勢與災害、官方來源
// unavailable / not_assessed / unknown are conservative states, never a safe result.

export const TERRAIN_RISK_RESULT_EVENT = "proptech:terrain-risk-result-ready";
export const TERRAIN_RISK_PREFILL_EVENT = "proptech:terrain-risk-prefill";
export const TERRAIN_REFERENCE_EVIDENCE_EVENT = "proptech:terrain-reference-evidence-ready";

export type TerrainRiskPrefill = { address?: string; city?: string; district?: string; road?: string; latitude?: number; longitude?: number; radius_m?: number };
const DEFAULT_LAYERS = ["terrain", "landslide", "debris_flow", "flood", "geological_sensitivity", "liquefaction", "active_fault"];

export function prefillTerrainRisk(prefill: TerrainRiskPrefill) {
  window.dispatchEvent(new CustomEvent<TerrainRiskPrefill>(TERRAIN_RISK_PREFILL_EVENT, { detail: prefill }));
}

export function TerrainRiskAnalysis({ location, compactFromLocation = false, resetKey, onStatusChange, onResult, onReferenceAttach }: { location?: LocationInsightResult; compactFromLocation?: boolean; resetKey?: string; onStatusChange?: (status: LocationMarketDisplayStatus) => void; onResult?: (result: TerrainRiskResult | null) => void; onReferenceAttach?: (evidence: TerrainReferenceEvidence) => void }) {
  const { locale } = useExperienceLocale();
  const copy = getSurfaceCopy(locale).terrain;
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [road, setRoad] = useState("");
  const [latitude, setLatitude] = useState<number | "">("");
  const [longitude, setLongitude] = useState<number | "">("");
  const [radius, setRadius] = useState(500);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [result, setResult] = useState<TerrainRiskResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { setResult(undefined); setError(""); onResult?.(null); onStatusChange?.("not_started"); }, [resetKey, onResult, onStatusChange]);
  useEffect(() => {
    function applyPrefill(event: Event) {
      const detail = (event as CustomEvent<TerrainRiskPrefill>).detail;
      setAddress(detail.address ?? ""); setCity(detail.city ?? ""); setDistrict(detail.district ?? ""); setRoad(detail.road ?? "");
      setLatitude(detail.latitude ?? ""); setLongitude(detail.longitude ?? ""); setRadius(detail.radius_m ?? 500); setResult(undefined);
    }
    window.addEventListener(TERRAIN_RISK_PREFILL_EVENT, applyPrefill);
    return () => window.removeEventListener(TERRAIN_RISK_PREFILL_EVENT, applyPrefill);
  }, []);
  useEffect(() => {
    function applyResult(event: Event) { setResult((event as CustomEvent<TerrainRiskResult>).detail); }
    window.addEventListener(TERRAIN_RISK_RESULT_EVENT, applyResult);
    return () => window.removeEventListener(TERRAIN_RISK_RESULT_EVENT, applyResult);
  }, []);

  function useLocationPosition() {
    if (!location?.resolved_location) return;
    setAddress(location.resolved_location.address_label ?? ""); setLatitude(location.resolved_location.latitude); setLongitude(location.resolved_location.longitude);
  }
  async function analyze() {
    setLoading(true); setError("");
    try {
      onStatusChange?.("loading");
      const resolved = location?.resolved_location;
      const next = await api.terrainRiskAnalyze({ address: compactFromLocation ? resolved?.address_label ?? address : address, city, district, road, radius_m: radius, latitude: compactFromLocation ? resolved?.latitude : latitude === "" ? undefined : latitude, longitude: compactFromLocation ? resolved?.longitude : longitude === "" ? undefined : longitude, include_layers: layers });
      setResult(next); onResult?.(next); window.dispatchEvent(new CustomEvent<TerrainRiskResult>(TERRAIN_RISK_RESULT_EVENT, { detail: next })); window.dispatchEvent(new Event("proptech:workflow-status-updated"));
    } catch (caught) { setError((caught as Error).message); onResult?.(null); onStatusChange?.("unavailable"); }
    finally { setLoading(false); }
  }

  const canAnalyze = compactFromLocation ? Boolean(location?.resolved_location) : Boolean(address.trim() || road.trim() || (latitude !== "" && longitude !== ""));
  const inputClass = "mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm";
  // Regression vocabulary: 地勢、淹水、坡地災害、地質敏感、液化、活動斷層、官方來源。
  // Conservative notice: 地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。
  // HELP_CONTENT.terrainRisk remains represented by the localized helpTitle/helpBody pair.
  // Unavailable or incomplete layers 不能解讀為低風險；compact mode 請先完成位置洞察。
  return <section id="terrain-risk-analysis" className="scroll-mt-20">
    <SectionCard title={copy.title} description={copy.description}>
      <div className="mb-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-6 text-amber-900"><span>{copy.warning}</span><HelpTooltip title={copy.helpTitle}>{copy.helpBody}</HelpTooltip></div>
      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="grid min-w-0 gap-3">
          {compactFromLocation && <div className="rounded-xl border border-cyan-100 bg-cyan-50 px-3 py-2 text-xs leading-5 text-cyan-900">{/* 使用上方位置洞察的可信位置脈絡 */}{copy.locationFrom}</div>}
          {!compactFromLocation && <>
            <label className="text-xs text-slate-500">{copy.address}<input className={inputClass} value={address} onChange={(event) => setAddress(event.target.value)} placeholder={copy.addressPlaceholder} /></label>
            <div className="grid gap-2 sm:grid-cols-3"><label className="text-xs text-slate-500">{copy.city}<input className={inputClass} value={city} onChange={(event) => setCity(event.target.value)} /></label><label className="text-xs text-slate-500">{copy.district}<input className={inputClass} value={district} onChange={(event) => setDistrict(event.target.value)} /></label><label className="text-xs text-slate-500">{copy.road}<input className={inputClass} value={road} onChange={(event) => setRoad(event.target.value)} /></label></div>
            <div className="grid gap-2 sm:grid-cols-3"><label className="text-xs text-slate-500">{copy.latitude}<input type="number" step="0.000001" className={inputClass} value={latitude} onChange={(event) => setLatitude(event.target.value === "" ? "" : Number(event.target.value))} /></label><label className="text-xs text-slate-500">{copy.longitude}<input type="number" step="0.000001" className={inputClass} value={longitude} onChange={(event) => setLongitude(event.target.value === "" ? "" : Number(event.target.value))} /></label><label className="text-xs text-slate-500">{copy.radius}<input type="number" min="100" max="2000" className={inputClass} value={radius} onChange={(event) => setRadius(Number(event.target.value))} /></label></div>
          </>}
          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600">{DEFAULT_LAYERS.map((layer) => <label key={layer} className="flex items-center gap-2 rounded-lg border border-stone-200 px-2 py-1"><input type="checkbox" checked={layers.includes(layer)} onChange={() => setLayers((rows) => rows.includes(layer) ? rows.filter((item) => item !== layer) : [...rows, layer])} />{copy.layers[layer] ?? layer}</label>)}</div>
          <div className="grid gap-2 sm:grid-cols-2">{!compactFromLocation && <Button secondary disabled={!location?.resolved_location} onClick={useLocationPosition}>{copy.useLocation}</Button>}<Button className="w-full" disabled={loading || !canAnalyze} onClick={analyze}>{loading ? copy.analyzing : compactFromLocation ? copy.compactAnalyze : copy.analyze}</Button></div>
          {!canAnalyze && <p className="text-[10px] leading-5 text-amber-700">{compactFromLocation ? copy.compactMissing : copy.standaloneMissing}</p>}
          {error && <ErrorState message={error} />}
        </div>
        <div className="min-w-0">{!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm leading-7 text-slate-500"><p>{copy.empty}<br /><span className="text-xs">{copy.emptyDetail}</span></p></div> : <TerrainRiskResults result={result} copy={copy} onReferenceAttach={onReferenceAttach} />}</div>
      </div>
    </SectionCard>
  </section>;
}

function TerrainRiskResults({ result, copy, onReferenceAttach }: { result: TerrainRiskResult; copy: TerrainSurfaceCopy; onReferenceAttach?: (evidence: TerrainReferenceEvidence) => void }) {
  const hazards = Object.values(result.hazards); const evidence = buildTerrainReferenceEvidence(result); const evidenceByLayer = new Map(evidence.layers.map((layer) => [layer.layer_id, layer]));
  return <div className="min-w-0 space-y-4">
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-950"><p className="text-[10px] font-bold tracking-wider">{copy.resultKicker}</p><h3 className="mt-1 text-xl font-extrabold">{copy.summaryTitle}</h3><p className="mt-2 text-sm leading-6">{copy.summaryMeta}</p></div>
    <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4"><p className="text-xs font-bold text-cyan-950">{copy.referenceTitle}</p><p className="mt-2 text-xs leading-5 text-cyan-950">{copy.sourceFallbackNotice}</p><p className="mt-2 text-xs leading-5 text-slate-700">{copy.summaryMeta}</p><button type="button" className="mt-3 rounded-lg border border-cyan-700 bg-white px-3 py-2 text-xs font-bold text-cyan-900 focus:outline-none focus:ring-2 focus:ring-cyan-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" disabled={!evidence.attachable} onClick={() => { onReferenceAttach?.(evidence); window.dispatchEvent(new CustomEvent<TerrainReferenceEvidence>(TERRAIN_REFERENCE_EVIDENCE_EVENT, { detail: evidence })); }}>{evidence.attachable ? copy.attach : copy.attachDisabled}</button>{!evidence.attachable && <p className="mt-2 text-[11px] text-amber-800">{copy.attachDisabled}</p>}<p className="mt-2 text-[11px] text-slate-600">{copy.referenceState}: {copy.states[evidence.status] ?? copy.unknown}</p></div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><MetricTile label={copy.slope} value={result.terrain.slope_class ?? result.terrain.status} note={result.terrain.explanation} />{hazards.map((hazard) => <HazardCard key={hazard.key} hazard={hazard} state={evidenceByLayer.get(hazard.key)?.state ?? "unknown"} copy={copy} />)}</div>
    {result.risk_factors.length > 0 ? <ListCard title={copy.riskFactors} items={result.risk_factors.map((item) => `${item.title}: ${item.message}`)} /> : <Notice>{copy.noRiskFactors}</Notice>}
    <ListCard title={copy.recommended} items={result.recommended_checks} />
    <RiskSourceTransparency result={result} copy={copy} />
    {result.official_data_sources && <OfficialDataStatusCard sources={result.official_data_sources} />}
    <details className="min-w-0 rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-3 py-2.5 text-xs font-bold text-slate-700">{copy.layersDisclosure}</summary><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[680px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">{copy.layer}</th><th>{copy.status}</th><th>{copy.vintage}</th><th>{copy.limitation}</th><th>{copy.external}</th></tr></thead><tbody>{result.map_layers.map((layer) => <tr key={layer.key} className="border-t border-stone-100"><td className="p-2">{layer.label}</td><td>{copy.states[layer.status] ?? layer.status}</td><td>{layer.data_vintage || copy.noDate}</td><td>{layer.limitation || copy.noLimit}</td><td>{layer.external_view_url ? <a className="font-bold text-cyan-700 underline" href={layer.external_view_url} target="_blank" rel="noreferrer">{copy.externalLink}</a> : copy.noExternal}</td></tr>)}</tbody></table></div></details>
    {result.missing_sources.length > 0 && <Notice tone="warning">{copy.missingSources}: {result.missing_sources.join(", ")}</Notice>}<p className="text-[10px] leading-5 text-amber-700">{copy.warning}</p>
  </div>;
}

function RiskSourceTransparency({ result, copy }: { result: TerrainRiskResult; copy: TerrainSurfaceCopy }) {
  const transparency = result.source_transparency; const layers = transparency?.layers ?? [];
  return <details className="min-w-0 rounded-xl border border-amber-200 bg-amber-50/60"><summary className="cursor-pointer px-3 py-2.5 text-xs font-bold text-amber-900">{copy.sourceTransparency}</summary><div className="space-y-3 px-3 pb-3 text-xs leading-6 text-amber-950"><p>{copy.sourceFallbackNotice}</p>{layers.length > 0 ? <div className="grid gap-2 md:grid-cols-2">{layers.map((layer) => <SourceLayerCard key={layer.layer_id} layer={layer} copy={copy} />)}</div> : <Notice tone="warning">{copy.noSourceLayers}</Notice>}</div></details>;
}

function SourceLayerCard({ layer, copy }: { layer: TerrainRiskSourceTransparencyLayer; copy: TerrainSurfaceCopy }) {
  return <div className="rounded-lg border border-amber-100 bg-white p-3"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-bold text-slate-900">{layer.display_name}</p><span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">{copy.assessment[layer.assessment_status]}</span></div><p className="mt-1 text-[11px] text-slate-600">{copy.source}: {layer.source_name} · {layer.source_kind}</p><p className="mt-1 text-[11px] text-slate-600">{copy.coverage}: {copy.coverageStates[layer.coverage_status]} · {copy.updated}: {layer.data_updated_at || copy.unknown}</p><p className="mt-2 text-[11px] leading-5 text-amber-800">{layer.caveat}</p></div>;
}

function HazardCard({ hazard, state, copy }: { hazard: TerrainHazardLayer; state: Parameters<typeof terrainReferenceStateLabel>[0]; copy: TerrainSurfaceCopy }) {
  return <div className="rounded-xl border border-stone-200 bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{hazard.label}</p><p className="mt-1 text-lg font-extrabold text-slate-950">{copy.states[state] ?? state}</p><p className="mt-2 text-[11px] leading-5 text-slate-600">{hazard.explanation}</p><p className="mt-2 text-[10px] text-slate-400">{hazard.source?.agency ?? copy.sourceUnavailable} · {copy.states[hazard.source?.status ?? hazard.status] ?? hazard.source?.status ?? hazard.status}</p></div>;
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-xl border border-stone-200 bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}
