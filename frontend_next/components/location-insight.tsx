"use client";

import { useEffect, useRef, useState } from "react";
import { api, LocationInsightResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { ErrorState, MetricTile, SectionCard } from "@/components/product-ui";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { TerrainRiskAnalysis } from "@/components/terrain-risk-analysis";
import { CommuteLivabilityCard } from "@/components/commute-livability-card";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { RuntimeCopyKey } from "@/lib/runtime-copy";
import { GeocodingAcceptanceNotice } from "@/components/geocoding-acceptance-notice";




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

export function LocationInsight({ onMap, onContextChange, onResult, initialContext, initialResult, embeddedJourney = false }: { onMap?: () => void; onContextChange?: (context: LocationInsightPrefill) => void; onResult?: (result: LocationInsightResult | null) => void; initialContext?: LocationInsightPrefill; initialResult?: LocationInsightResult; embeddedJourney?: boolean }) {
  const { copy } = useExperienceLocale();
  const [city, setCity] = useState(initialContext?.city ?? "台北市");
  const [district, setDistrict] = useState(initialContext?.district ?? "大安區");
  const [road, setRoad] = useState(initialContext?.road ?? "和平東路二段");
  const [address, setAddress] = useState(initialContext?.address ?? "");
  const [radius, setRadius] = useState(800);
  const [propertyPrice, setPropertyPrice] = useState<number | "">(initialContext?.property_price ?? "");
  const [areaPing, setAreaPing] = useState<number | "">(initialContext?.area_ping ?? "");
  const [buildingType, setBuildingType] = useState(initialContext?.building_type ?? "");
  const [result, setResult] = useState<LocationInsightResult | undefined>(initialResult);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef(0);

  function invalidateLocationFlow() {
    requestRef.current += 1;
    setResult(undefined);
    setLoading(false);
    setError("");
    onResult?.(null);
    window.sessionStorage.removeItem(LOCATION_INSIGHT_SESSION_KEY);
  }

  useEffect(() => {
    if (!initialContext) return;
    setCity(initialContext.city ?? "");
    setDistrict(initialContext.district ?? "");
    setRoad(initialContext.road ?? "");
    setAddress(initialContext.address ?? [initialContext.city, initialContext.district, initialContext.road].filter(Boolean).join(""));
    setPropertyPrice(initialContext.property_price ?? "");
    setAreaPing(initialContext.area_ping ?? "");
    setBuildingType(initialContext.building_type ?? "");
  }, [initialContext]);

  useEffect(() => { setResult(initialResult); }, [initialResult]);

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
      onContextChange?.(detail);
      invalidateLocationFlow();
    }
    window.addEventListener(LOCATION_INSIGHT_PREFILL_EVENT, applyPrefill);
    return () => window.removeEventListener(LOCATION_INSIGHT_PREFILL_EVENT, applyPrefill);
  }, [onContextChange]);

  useEffect(() => {
    function applyResult(event: Event) {
      setResult((event as CustomEvent<LocationInsightResult>).detail);
    }
    window.addEventListener(LOCATION_INSIGHT_RESULT_EVENT, applyResult);
    return () => window.removeEventListener(LOCATION_INSIGHT_RESULT_EVENT, applyResult);
  }, []);

  async function analyze() {
    if (!address.trim()) {
      setError(copy("location.empty"));
      return;
    }
    const requestId = ++requestRef.current;
    setLoading(true);
    setError("");
    setResult(undefined);
    onResult?.(null);
    try {
      const next = await api.locationInsight({
        city, district, road, address, radius_m: radius,
        property_price: propertyPrice === "" ? undefined : propertyPrice,
        area_ping: areaPing === "" ? undefined : areaPing,
        building_type: buildingType,
        use_existing_poi_sources: true,
      });
      if (requestId !== requestRef.current) return;
      setResult(next);
      onResult?.(next);
      window.sessionStorage.setItem(LOCATION_INSIGHT_SESSION_KEY, JSON.stringify(next));
      window.dispatchEvent(new CustomEvent<LocationInsightResult>(LOCATION_INSIGHT_RESULT_EVENT, { detail: next }));
    } catch (caught) {
      if (requestId === requestRef.current) setError(copy("location.error"));
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }

  function emitContext(overrides: LocationInsightPrefill = {}) {
    onContextChange?.({ city, district, road, address, property_price: propertyPrice === "" ? undefined : propertyPrice, area_ping: areaPing === "" ? undefined : areaPing, building_type: buildingType, ...overrides });
  }

  const inputClass = "mt-1 w-full min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm";
  return <div id="location-insight-calculator" className="scroll-mt-20 space-y-5"><span id="location-insight" className="block scroll-mt-20" aria-hidden="true" /><SectionCard title={copy("location.title")} description={copy("location.description")}>
    <div className="mb-4 grid gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs text-slate-600 sm:grid-cols-4">
      <FlowBadge label={`1. ${copy("location.title")}`} active />
      <FlowBadge label={`2. Terrain Risk`} active={Boolean(result?.resolved_location)} />
      <FlowBadge label={`3. ${copy("commute.title")}`} active />
      <FlowBadge label={`4. ${copy("location.map")}`} active />
    </div>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="grid min-w-0 gap-3">
        <label className="text-xs text-slate-500">{copy("location.address")}<input className={inputClass} value={address} onChange={(event) => { const value = event.target.value; setAddress(value); emitContext({ address: value }); invalidateLocationFlow(); }} placeholder={copy("location.address")} /></label>
        <label className="text-xs text-slate-500">{copy("location.radius")}<input type="number" min="100" max="1500" className={inputClass} value={radius} onChange={(event) => setRadius(Number(event.target.value))} /></label>
        <label className="text-xs text-slate-500">{copy("location.propertyPrice")}<input type="number" min="0" className={inputClass} value={propertyPrice} onChange={(event) => { const value = event.target.value === "" ? "" : Number(event.target.value); setPropertyPrice(value); emitContext({ property_price: value === "" ? undefined : value }); }} /></label>
        <label className="text-xs text-slate-500">{copy("location.area")}<input type="number" min="0" className={inputClass} value={areaPing} onChange={(event) => { const value = event.target.value === "" ? "" : Number(event.target.value); setAreaPing(value); emitContext({ area_ping: value === "" ? undefined : value }); }} /></label>
        <Button className="w-full" disabled={loading || !address.trim()} onClick={analyze}>{loading ? copy("location.analyzing") : copy("location.start")}</Button>
        {!address.trim() && <p className="text-[10px] leading-5 text-amber-700">{copy("location.empty")}</p>}
        {address.trim() && !result && !loading && <p className="text-[10px] leading-5 text-slate-500">{copy("location.changeNotice")}</p>}
        {error && <ErrorState message={error} />}
      </div>
      <div className="min-w-0">
        {!result ? <div className="grid min-h-52 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-5 text-center text-sm text-slate-500">{copy("location.empty")}</div> : <LocationResults result={result} />}
      </div>
    </div>
  </SectionCard>
    {!embeddedJourney && <details className="rounded-xl border border-stone-200 bg-white" open={Boolean(result?.resolved_location)}>
      <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">Terrain Risk</summary>
      <div className="border-t border-stone-100 p-4"><TerrainRiskAnalysis location={result} compactFromLocation resetKey={address} /></div>
    </details>}
    {!embeddedJourney && <details className="rounded-xl border border-stone-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-700">{copy("commute.title")}</summary>
      <div className="border-t border-stone-100 p-4"><CommuteLivabilityCard address={address} /></div>
    </details>}
    {!embeddedJourney && <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-xs font-bold text-slate-900">{copy("location.map")}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">{copy("map.sourceNote")}</p></div>
        <Button secondary className="w-full sm:w-auto" onClick={onMap}>{copy("location.map")}</Button>
      </div>
    </div>}
  </div>;
}

function FlowBadge({ label, active }: { label: string; active?: boolean }) {
  return <span className={`rounded-lg px-2.5 py-2 font-bold ${active ? "bg-cyan-50 text-cyan-800" : "bg-white text-slate-400"}`}>{label}</span>;
}

function LocationResults({ result }: { result: LocationInsightResult }) {
  const { copy } = useExperienceLocale();
  if (result.geocoding_acceptance && !result.geocoding_acceptance.accepted_for_analysis) {
    return <div data-testid="location-result" className="space-y-3"><GeocodingAcceptanceNotice acceptance={result.geocoding_acceptance} /><Notice tone="warning">{copy("location.noResult")}</Notice><DataQuality result={result} /></div>;
  }
  if (result.data_quality.status === "unavailable") {
    return <div data-testid="location-result" className="space-y-3">{result.geocoding_acceptance && <GeocodingAcceptanceNotice acceptance={result.geocoding_acceptance} />}<Notice tone="warning">{copy("location.noResult")}</Notice><DataQuality result={result} /></div>;
  }
  const scoreLabels: [keyof LocationInsightResult["category_scores"], string][] = [["transit_score", copy("location.transit")], ["convenience_score", copy("location.convenience")], ["education_score", copy("location.education")], ["green_space_score", copy("location.green")], ["medical_score", copy("location.medical")], ["risk_score", copy("location.risk")]];
  return <div data-testid="location-result" className="min-w-0 space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><MetricTile label={copy("location.score")} value={result.location_score ?? copy("common.noData")} note={result.resolved_location?.address_label} />{scoreLabels.map(([key, label]) => <MetricTile key={key} label={`${label}`} value={result.category_scores[key]} />)}</div>
    <div className="grid gap-3 sm:grid-cols-2"><ListCard title={copy("location.strengths")} items={result.strengths} /><ListCard title={copy("location.weaknesses")} items={result.weaknesses} /></div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(result.poi_summary).map(([key, value]) => <MetricTile key={key} label={poiLabel(key, copy)} value={`${value}`} />)}</div>
    <DetailDisclosure title={copy("location.poiDetails")}><p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">{copy("common.tableSwipe")}</p><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">{copy("common.source")}</th><th>{copy("location.address")}</th><th>{copy("location.radius")}</th><th>{copy("common.source")}</th></tr></thead><tbody>{result.nearest_pois.map((item, index) => <tr key={`${item.name}-${index}`} className="border-t border-stone-100"><td className="p-2">{item.category}</td><td>{item.name}</td><td>{item.distance_m}m</td><td>{item.source}</td></tr>)}</tbody></table></div></DetailDisclosure>
    <ListCard title={copy("location.buyerFit")} items={Object.entries(result.buyer_fit).map(([key, value]) => `${buyerLabel(key, copy)}: ${value}`)} />
    <Notice>{result.valuation_context.explanation}</Notice>
    <DataQuality result={result} />
    <p className="text-[10px] leading-5 text-amber-700">{result.disclaimer}</p>
  </div>;
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-xl border border-stone-200 bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}

function DataQuality({ result }: { result: LocationInsightResult }) {
  const { copy } = useExperienceLocale();
  return <DetailDisclosure title={copy("location.dataQuality")}><div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"><strong>{copy("common.dataLimit")}: {result.data_quality.status}</strong><ul className="mt-1 space-y-1">{result.data_quality.warnings.map((item) => <li key={item}>• {item}</li>)}</ul></div></DetailDisclosure>;
}

function poiLabel(key: string, copy: (key: RuntimeCopyKey) => string) {
  return ({ transit_count: copy("location.transit"), convenience_count: copy("location.convenience"), school_count: copy("location.education"), park_count: copy("location.green"), medical_count: copy("location.medical"), risk_facility_count: copy("location.risk") } as Record<string, string>)[key] ?? key;
}

function buyerLabel(key: string, copy: (key: RuntimeCopyKey) => string) {
  return ({ self_use_family: copy("location.buyerFit"), commuter: copy("commute.title"), investor: copy("valuation.level"), elderly: copy("location.buyerFit") } as Record<string, string>)[key] ?? key;
}
