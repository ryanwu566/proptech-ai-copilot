"use client";

import { useState, type ReactNode } from "react";
import { LocationInsight, type LocationInsightPrefill } from "@/components/location-insight";
import { CommuteLivabilityCard } from "@/components/commute-livability-card";
import { TerrainRiskAnalysis } from "@/components/terrain-risk-analysis";
import { AmenityCategoryChart } from "@/components/data-visualization/amenity-category-chart";
import { TerrainStatusMatrix } from "@/components/data-visualization/terrain-status-matrix";
import { JourneyPropertyContextHeader } from "@/components/guided-journey/journey-property-context-header";
import { LocationMarketSnapshot } from "@/components/guided-journey/location-market-snapshot";
import { LocationMarketStatusStrip } from "@/components/guided-journey/location-market-status-strip";
import { LocationMarketToolSelector } from "@/components/guided-journey/location-market-tool-selector";
import type { CommuteAddressLookupResult, LocationInsightResult, MarketResult, TerrainRiskResult } from "@/lib/api";
import type { TerrainReferenceEvidence } from "@/lib/terrain-reference-evidence";
import { addVisitedLocationMarketTool, buildAmenityCategoryModel, buildLocationMarketSnapshot, buildLocationMarketStatusItems, getSafeJourneyPropertyContext, type JourneyPropertyContext, type LocationMarketDisplayStatus, type LocationMarketToolId } from "@/lib/location-market-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type MarketHandlers = {
  onStatusChange: (status: LocationMarketDisplayStatus) => void;
  onResult: (result: MarketResult | null) => void;
};

export function LocationMarketStage({ renderMarket, onMap, onBackToProperty, onContinueToPrice, onPropertyContextChange, onTerrainReferenceReady }: { renderMarket: (context: JourneyPropertyContext, handlers: MarketHandlers) => ReactNode; onMap: () => void; onBackToProperty: () => void; onContinueToPrice: (context: JourneyPropertyContext) => void; onPropertyContextChange?: (context: JourneyPropertyContext) => void; onTerrainReferenceReady?: (evidence: TerrainReferenceEvidence) => void }) {
  const [propertyContext, setPropertyContext] = useState<JourneyPropertyContext>(() => getSafeJourneyPropertyContext(undefined));
  const [locationResult, setLocationResult] = useState<LocationInsightResult | null>(null);
  const [commuteResult, setCommuteResult] = useState<CommuteAddressLookupResult | null>(null);
  const [commuteDisplayStatus, setCommuteDisplayStatus] = useState<LocationMarketDisplayStatus>("not_started");
  const [terrainResult, setTerrainResult] = useState<TerrainRiskResult | null>(null);
  const [terrainDisplayStatus, setTerrainDisplayStatus] = useState<LocationMarketDisplayStatus>("not_started");
  const [marketResult, setMarketResult] = useState<MarketResult | null>(null);
  const [marketDisplayStatus, setMarketDisplayStatus] = useState<LocationMarketDisplayStatus>("not_started");
  const [activeTool, setActiveTool] = useState<LocationMarketToolId | null>(null);
  const [visitedTools, setVisitedTools] = useState<LocationMarketToolId[]>([]);
  const { t } = useExperienceLocale();

  function updatePropertyContext(next: LocationInsightPrefill) {
    const nextContext = getSafeJourneyPropertyContext({
      ...propertyContext,
      city: next.city ?? propertyContext.city,
      district: next.district ?? propertyContext.district,
      road: next.road ?? propertyContext.road,
      addressSummary: next.address ?? propertyContext.addressSummary,
      buildingType: next.building_type ?? propertyContext.buildingType,
      areaPing: next.area_ping ?? propertyContext.areaPing,
      askingPriceWan: next.property_price ?? propertyContext.askingPriceWan,
      sourceLabel: "使用者輸入或選擇",
      selectionStatus: "partial",
    });
    setPropertyContext(nextContext);
    onPropertyContextChange?.(nextContext);
  }

  function selectTool(tool: LocationMarketToolId) {
    setVisitedTools((current) => addVisitedLocationMarketTool(current, tool));
    setActiveTool(tool);
  }

  const statusItems = buildLocationMarketStatusItems({ locationResult, commuteResult, commuteDisplayStatus, terrainResult, terrainDisplayStatus, marketResult, marketDisplayStatus });
  const snapshot = buildLocationMarketSnapshot(statusItems);
  const amenityCategories = buildAmenityCategoryModel(locationResult);
  const contextAddress = propertyContext.addressSummary || [propertyContext.city, propertyContext.district, propertyContext.road].filter(Boolean).join("");

  function openStatus(id: LocationMarketStatusItemId) {
    if (id === "location") {
      document.getElementById("location-insight-calculator")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    selectTool(id);
  }

  return <div className="space-y-4">
    <JourneyPropertyContextHeader context={propertyContext} onBackToProperty={onBackToProperty} />
    <LocationMarketStatusStrip items={statusItems} onOpen={openStatus} />
    <section aria-labelledby="location-market-primary-heading" className="space-y-3">
      <div><h3 id="location-market-primary-heading" className="text-lg font-black text-slate-950">{t("journey.location.title")} · Location Insight</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("journey.location.description")}</p></div>
      <LocationInsight embeddedJourney onMap={onMap} onContextChange={updatePropertyContext} onResult={setLocationResult} />
      <AmenityCategoryChart categories={amenityCategories} />
      <div className="rounded-xl border border-stone-200 bg-white p-4"><p className="text-xs font-bold text-slate-900">{t("page.map")}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">{t("evidence.summaryDescription")}</p><button type="button" onClick={onMap} className="mt-3 w-full rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800 transition hover:bg-cyan-50 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">{t("page.map")}</button></div>
    </section>
    <LocationMarketToolSelector activeTool={activeTool} onSelect={selectTool} />
    {visitedTools.includes("commute") && <section hidden={activeTool !== "commute"} aria-hidden={activeTool !== "commute"} aria-labelledby="location-market-commute-heading" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><h3 id="location-market-commute-heading" className="text-base font-black text-slate-950">{t("journey.location.next")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.referenceOnly")}</p><div className="mt-3"><CommuteLivabilityCard address={contextAddress} onStatusChange={(status) => setCommuteDisplayStatus(status === "idle" ? "not_started" : status === "error" ? "unavailable" : status === "resolved" ? "available" : status === "unresolved" ? "no_data" : status)} onResult={setCommuteResult} /></div></section>}
    {visitedTools.includes("terrain") && <section hidden={activeTool !== "terrain"} aria-hidden={activeTool !== "terrain"} aria-labelledby="location-market-terrain-heading" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><h3 id="location-market-terrain-heading" className="text-base font-black text-slate-950">{t("page.terrain")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.referenceOnly")}</p><div className="mt-3"><TerrainRiskAnalysis compactFromLocation location={locationResult ?? undefined} resetKey={contextAddress} onStatusChange={setTerrainDisplayStatus} onResult={setTerrainResult} onReferenceAttach={onTerrainReferenceReady} /></div><div className="mt-4"><TerrainStatusMatrix result={terrainResult} /></div></section>}
    {visitedTools.includes("market") && <section hidden={activeTool !== "market"} aria-hidden={activeTool !== "market"} aria-labelledby="location-market-market-heading" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><h3 id="location-market-market-heading" className="text-base font-black text-slate-950">{t("page.market")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.noPurchase")}</p><div className="mt-3">{renderMarket(propertyContext, { onStatusChange: setMarketDisplayStatus, onResult: setMarketResult })}</div></section>}
    <LocationMarketSnapshot items={statusItems} evidenceAvailable={snapshot.evidenceAvailable} />
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-4"><p className="text-xs font-bold text-cyan-900">{t("journey.price.next")}</p><p className="mt-1 text-sm font-black text-slate-950">{t("journey.price.title")}</p><p className="mt-1 text-xs leading-5 text-slate-600">{t("trust.noPurchase")}</p><button type="button" onClick={() => onContinueToPrice(propertyContext)} className="mt-3 w-full rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">{t("journey.price.next")}</button></div>
  </div>;
}

type LocationMarketStatusItemId = "location" | LocationMarketToolId;

// Legacy trust contracts: 不代表沒有風險 · 市場資料僅供研究參考 · 通勤資訊只供生活安排參考 · 不會自動執行估價或保存案件 · 不代表法律或主管機關認定
// Legacy flow marker: 下一步：確認合理價格 · 只切換到價格分析 · 不會自動執行估價、建立估算、保存案件 · 研究參考，不會自動影響估價或案件決策 · 不會影響估價、風險或案件排名
