"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

import { api, type SatelliteReference } from "@/lib/api";


export type AcceptedSatelliteCoordinate = {
  latitude: number;
  longitude: number;
  accepted: boolean;
};

const DISCLAIMER = "Satellite reference imagery — not cadastral or statutory evidence.";

const fallbackResponse: SatelliteReference = {
  status: "unavailable",
  reason_code: "provider_error",
  source: "Sentinel-2 / Copernicus",
  dataset: "COPERNICUS/S2_SR_HARMONIZED",
  window_start: "—",
  window_end: "—",
  retrieval_time: "—",
  aoi_radius_m: 500,
  composite_method: "Median satellite reference composite across a fixed 90-day window.",
  cloud_filter_percent: 35,
  image_reference: null,
  attribution: "Contains modified Copernicus Sentinel data processed by Google Earth Engine.",
  limitations: ["Satellite reference is temporarily unavailable."],
  disclaimer: DISCLAIMER,
};

export function SatelliteEvidence({ coordinate }: { coordinate: AcceptedSatelliteCoordinate | null }) {
  const [evidence, setEvidence] = useState<SatelliteReference | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!coordinate?.accepted) {
      setEvidence(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setEvidence(null);
    setLoading(true);
    void api.satelliteReference(
      { latitude: coordinate.latitude, longitude: coordinate.longitude },
      controller.signal,
    ).then((result) => {
      if (!controller.signal.aborted) setEvidence(result);
    }).catch(() => {
      if (!controller.signal.aborted) setEvidence(fallbackResponse);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [coordinate?.accepted, coordinate?.latitude, coordinate?.longitude]);

  const status = evidence?.status ?? "unavailable";
  const statusLabel = !coordinate?.accepted
    ? "Confirmation required"
    : loading
      ? "Loading reference"
      : status === "available"
        ? "Available"
        : status === "limited"
          ? "Limited"
          : "Unavailable";
  const badgeClass = status === "available"
    ? "bg-emerald-100 text-emerald-900"
    : status === "limited"
      ? "bg-amber-100 text-amber-900"
      : "bg-stone-100 text-slate-700";

  return <section data-testid="satellite-evidence-card" className="min-w-0 rounded-xl border border-sky-200 bg-white p-4 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.16em] text-sky-700">Visual context</p>
        <h3 className="mt-1 text-base font-black text-slate-950">Satellite Evidence</h3>
      </div>
      <span data-testid="satellite-evidence-status" data-status={status} className={`rounded-full px-2 py-1 text-[10px] font-black ${badgeClass}`}>{statusLabel}</span>
    </div>

    {!coordinate?.accepted && <p className="mt-3 text-xs leading-5 text-amber-800">Confirm a terrain or location coordinate before requesting satellite reference imagery.</p>}
    {loading && <p className="mt-3 text-xs leading-5 text-slate-600">Requesting one bounded satellite reference composite…</p>}

    {evidence && <>
      {evidence.image_reference && <Image unoptimized width={512} height={512} data-testid="satellite-reference-image" src={evidence.image_reference} alt="Bounded Sentinel-2 satellite reference composite" className="mt-3 aspect-square w-full rounded-lg border border-stone-200 object-cover" />}
      <dl className="mt-3 grid gap-2 text-[11px] leading-5 text-slate-700">
        <div><dt className="font-black text-slate-900">Source</dt><dd>{evidence.source}</dd></div>
        <div><dt className="font-black text-slate-900">Dataset</dt><dd className="break-all">{evidence.dataset}</dd></div>
        <div><dt className="font-black text-slate-900">90-day window</dt><dd>{evidence.window_start} — {evidence.window_end}</dd></div>
        <div><dt className="font-black text-slate-900">Composite</dt><dd>{evidence.composite_method}</dd></div>
        <div><dt className="font-black text-slate-900">{evidence.status === "unavailable" ? "Checked" : "Retrieved"}</dt><dd>{evidence.retrieval_time}</dd></div>
        <div><dt className="font-black text-slate-900">Cloud filter</dt><dd>Scene metadata threshold ≤ {evidence.cloud_filter_percent}% plus SCL masking.</dd></div>
      </dl>
      <ul className="mt-3 space-y-1 text-[10px] leading-5 text-slate-600">{evidence.limitations.map((limitation) => <li key={limitation}>• {limitation}</li>)}</ul>
      <p className="mt-3 text-[10px] leading-5 text-slate-500">{evidence.attribution}</p>
    </>}

    <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-bold leading-5 text-amber-950">{evidence?.disclaimer ?? DISCLAIMER}</p>
  </section>;
}
