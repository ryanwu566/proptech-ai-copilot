"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { CadastralEvidence } from "@/lib/api";
import type { TerrainSurfaceCopy } from "@/lib/surface-copy";

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

function initialOverlayState(evidence: CadastralEvidence): OverlayState {
  return evidence.tile_url_template && evidence.mode !== "point_reference_only" ? "loading" : "not_configured";
}

export function TerrainCadastralEvidence({
  evidence,
  radiusM,
  coordinateSource,
  copy,
}: {
  evidence: CadastralEvidence;
  radiusM: number;
  coordinateSource: string;
  copy: TerrainSurfaceCopy;
}) {
  const [overlayState, setOverlayState] = useState<OverlayState>(() => initialOverlayState(evidence));
  useEffect(() => { setOverlayState(initialOverlayState(evidence)); }, [evidence]);
  const updateOverlayState = useCallback((state: OverlayState) => setOverlayState(state), []);
  const statusLabel = useMemo(() => ({
    loading: copy.cadastralLoading,
    visible: copy.cadastralReferenceOnly,
    unavailable: copy.cadastralUnavailable,
    not_configured: copy.cadastralNotConfigured,
  })[overlayState], [copy, overlayState]);
  const sourceLabel = copy.coordinateSources[coordinateSource] ?? copy.coordinateSources.unknown;

  return <section data-testid="terrain-cadastral-evidence" className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 bg-slate-950 px-4 py-4 text-white">
      <div className="min-w-0">
        <p className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-300">{copy.cadastralPointOnly}</p>
        <h3 className="mt-1 text-lg font-extrabold">{copy.cadastralTitle}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-300">{copy.cadastralSubtitle}</p>
      </div>
      <span data-testid="cadastral-availability-status" className="rounded-full border border-amber-300/50 bg-amber-300/10 px-3 py-1 text-[10px] font-black text-amber-200">{statusLabel}</span>
    </div>
    <div data-testid="cadastral-map-shell" role="region" aria-label={copy.cadastralMapAria} className="relative min-w-0 overflow-hidden bg-slate-100">
      <TerrainEvidenceLeafletMap evidence={evidence} radiusM={radiusM} markerLabel={copy.cadastralMarkerLegend} onOverlayState={updateOverlayState} />
      <div className="pointer-events-none absolute bottom-7 left-3 z-[500] max-w-[calc(100%-1.5rem)] rounded-lg border border-white/80 bg-white/90 px-2.5 py-1.5 text-[10px] font-bold text-slate-800 shadow">
        {copy.cadastralPointOnly}
      </div>
    </div>
    <div className="grid gap-3 p-4 text-xs sm:grid-cols-3">
      <EvidenceFact title={copy.cadastralWhere} body={`${evidence.center.lat.toFixed(6)}, ${evidence.center.lng.toFixed(6)}`} detail={`${copy.coordinateSource}: ${sourceLabel}`} />
      <EvidenceFact title={copy.cadastralChecked} body={`${evidence.provider} · ${statusLabel}`} detail={`${copy.cadastralLastChecked}: ${evidence.checked_at}`} />
      <EvidenceFact title={copy.cadastralStillNeeded} body={copy.cadastralManualVerification} detail={copy.cadastralMarkerLegend} />
    </div>
    <div data-testid="cadastral-point-reference-limitation" className="border-t border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-950">
      <strong>{copy.cadastralPointOnly}</strong><code className="mx-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-black">POINT_REFERENCE_ONLY</code>{copy.cadastralLimitation}
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-4 py-3 text-[10px] text-slate-600">
      <span>{copy.cadastralLegend}: ● {copy.cadastralMarkerLegend} · ◌ {copy.cadastralRadiusLegend}</span>
      {evidence.source_url && <a className="font-bold text-cyan-800 underline" href={evidence.source_url} target="_blank" rel="noreferrer">{copy.cadastralSource}: {evidence.provider_name ?? evidence.provider}</a>}
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
