"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { CadastralEvidence, LandsectContext, ParcelGeometryEvidence } from "@/lib/api";
import type { TerrainSurfaceCopy } from "@/lib/surface-copy";
import type { ParcelGeometryCopy } from "@/lib/parcel-geometry-copy";

type OverlayState = "loading" | "visible" | "unavailable" | "not_configured";

function MapLoadingShell() {
  return <div className="grid h-[320px] place-items-center bg-slate-100 sm:h-[420px]" aria-hidden="true">
    <span className="h-9 w-9 animate-pulse rounded-full border-4 border-white bg-slate-800 shadow-lg" />
  </div>;
}

const TerrainEvidenceLeafletMap = dynamic(() => import("@/components/map/terrain-evidence-leaflet-map"), {
  ssr: false,
  loading: MapLoadingShell,
});

function initialOverlayState(landsect: LandsectContext | undefined, evidence: CadastralEvidence): OverlayState {
  return landsect?.tile_url_template || evidence.tile_url_template ? "loading" : "not_configured";
}

export function TerrainCadastralEvidence({
  evidence,
  parcelEvidence,
  landsect,
  radiusM,
  coordinateSource,
  copy,
  parcelCopy,
}: {
  evidence: CadastralEvidence;
  parcelEvidence?: ParcelGeometryEvidence;
  landsect?: LandsectContext;
  radiusM: number;
  coordinateSource: string;
  copy: TerrainSurfaceCopy;
  parcelCopy: ParcelGeometryCopy;
}) {
  const [overlayState, setOverlayState] = useState<OverlayState>(() => initialOverlayState(landsect, evidence));
  useEffect(() => { setOverlayState(initialOverlayState(landsect, evidence)); }, [landsect, evidence]);
  const updateOverlayState = useCallback((state: OverlayState) => setOverlayState(state), []);
  const statusLabel = useMemo(() => ({
    loading: copy.cadastralLoading,
    visible: copy.cadastralReferenceOnly,
    unavailable: copy.cadastralUnavailable,
    not_configured: copy.cadastralNotConfigured,
  })[overlayState], [copy, overlayState]);
  const sourceLabel = copy.coordinateSources[coordinateSource] ?? copy.coordinateSources.unknown;
  const parcelBadge = parcelEvidence?.status === "verified_official" ? parcelCopy.officialVector : parcelEvidence?.status === "user_provided" ? parcelCopy.userProvided : parcelCopy.pointReference;
  const consistency = parcelEvidence?.location_geometry_consistency;
  const consistencyLabel = consistency === "POSSIBLE_MISMATCH" ? parcelCopy.mismatch : consistency === "CONSISTENT" ? parcelCopy.consistent : parcelCopy.notChecked;

  return <section data-testid="terrain-cadastral-evidence" data-parcel-status={parcelEvidence?.status ?? "point_reference_only"} className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 bg-slate-950 px-4 py-4 text-white">
      <div className="min-w-0">
        <p data-testid="parcel-source-badge" className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-300">{parcelBadge}</p>
        <h3 className="mt-1 text-lg font-extrabold">{copy.cadastralTitle}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-300">{copy.cadastralSubtitle}</p>
      </div>
      <span data-testid="cadastral-availability-status" className="rounded-full border border-amber-300/50 bg-amber-300/10 px-3 py-1 text-[10px] font-black text-amber-200">{parcelCopy.sectionContext}: {statusLabel}</span>
    </div>
    <div data-testid="cadastral-map-shell" role="region" aria-label={copy.cadastralMapAria} className="relative min-w-0 overflow-hidden bg-slate-100">
      <TerrainEvidenceLeafletMap evidence={evidence} parcelEvidence={parcelEvidence} landsect={landsect} radiusM={radiusM} markerLabel={parcelCopy.markerLegend} onOverlayState={updateOverlayState} />
      <div className="pointer-events-none absolute bottom-7 left-3 z-[500] max-w-[calc(100%-1.5rem)] rounded-lg border border-white/80 bg-white/90 px-2.5 py-1.5 text-[10px] font-bold text-slate-800 shadow">
        {parcelBadge}
      </div>
    </div>
    <div className="grid gap-3 p-4 text-xs sm:grid-cols-3">
      <EvidenceFact title={copy.cadastralWhere} body={`${evidence.center.lat.toFixed(6)}, ${evidence.center.lng.toFixed(6)}`} detail={`${copy.coordinateSource}: ${sourceLabel}`} />
      <EvidenceFact title={copy.cadastralChecked} body={parcelBadge} detail={parcelEvidence?.area_m2 !== undefined ? `${parcelCopy.computedArea}: ${parcelEvidence.area_m2.toLocaleString()} m²` : `${copy.cadastralLastChecked}: ${evidence.checked_at}`} />
      <EvidenceFact title={copy.cadastralStillNeeded} body={consistencyLabel} detail={copy.cadastralManualVerification} />
    </div>
    <div data-testid="cadastral-point-reference-limitation" className={`border-t px-4 py-3 text-xs leading-6 ${(!parcelEvidence || parcelEvidence.status === "point_reference_only") ? "border-rose-200 bg-rose-50 text-rose-950 font-bold" : "border-amber-200 bg-amber-50 text-amber-950"}`}>
      <strong className="uppercase">{parcelBadge}</strong>{(!parcelEvidence || parcelEvidence.status === "point_reference_only") && <span className="ml-1">{copy.cadastralPointOnly}</span>}<code className="mx-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-black">{parcelEvidence?.source_label ?? "POINT_REFERENCE_ONLY"}</code>{parcelEvidence?.limitation ?? copy.cadastralLimitation}
    </div>
    <div data-testid="parcel-geometry-facts" className="grid gap-2 border-t border-cyan-100 bg-cyan-50 p-4 text-[11px] leading-5 text-cyan-950 sm:grid-cols-2">
      <p>{parcelEvidence?.area_m2 !== undefined ? `${parcelCopy.computedArea}: ${parcelEvidence.area_m2.toLocaleString()} m²` : parcelCopy.pointReference}</p>
      <p className={consistency === "POSSIBLE_MISMATCH" ? "font-bold text-rose-800" : ""}>{consistencyLabel}</p>
      {parcelEvidence?.geometry_validity === "REPAIRED" && <p className="font-bold text-amber-800">{parcelCopy.repaired}</p>}
      <p data-testid="landsect-semantics">{parcelCopy.landsectLimitation}</p>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-4 py-3 text-[10px] text-slate-600">
      <span>{copy.cadastralLegend}: ● {copy.cadastralMarkerLegend} · ◌ {copy.cadastralRadiusLegend}</span>
      {evidence.source_url && <a className="font-bold text-cyan-800 underline" href={evidence.source_url} target="_blank" rel="noreferrer">{copy.cadastralSource}: {evidence.provider_name ?? evidence.provider}</a>}
      <span className="break-words">● {parcelCopy.markerLegend} · ◇ {parcelCopy.uploadLegend} · ◆ {parcelCopy.officialLegend} · ◌ {parcelCopy.radiusLegend} · ▦ {parcelCopy.sectionLegend}</span>
      {landsect?.source_url && <a className="font-bold text-cyan-800 underline" href={landsect.source_url} target="_blank" rel="noreferrer">LANDSECT</a>}
    </div>
  </section>;
}

function EvidenceFact({ title, body, detail }: { title: string; body: string; detail: string }) {
  return <div className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-3">
    <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">{title}</p>
    <p className="mt-1 break-words font-extrabold text-slate-950">{body}</p>
    <p className="mt-1 break-words text-[10px] leading-4 text-slate-600">{detail}</p>
  </div>;
}
