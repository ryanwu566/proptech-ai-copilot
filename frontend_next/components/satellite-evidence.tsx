"use client";

import { useEffect, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import Image from "next/image";

import { api, type SatelliteReference } from "@/lib/api";


export type AcceptedSatelliteCoordinate = {
  latitude: number;
  longitude: number;
  accepted: boolean;
  propertyKey?: string;
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
  const { t, locale } = useExperienceLocale();
  const requestKey = coordinate?.accepted
    ? JSON.stringify([coordinate.propertyKey ?? "", coordinate.latitude, coordinate.longitude])
    : null;
  const latestKey = useRef(requestKey);
  latestKey.current = requestKey;
  const pending = useRef<{ key: string; controller: AbortController } | null>(null);
  const [stored, setStored] = useState<{ key: string; value: SatelliteReference } | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const evidence = stored?.key === requestKey ? stored.value : null;
  const loading = requestKey !== null && loadingKey === requestKey;

  useEffect(() => {
    setStored(null);
    setLoadingKey(null);
    return () => {
      if (pending.current?.key === requestKey) {
        pending.current.controller.abort();
        pending.current = null;
      }
    };
  }, [requestKey]);

  async function requestReference() {
    if (!coordinate?.accepted || !requestKey || pending.current?.key === requestKey) return;
    const controller = new AbortController();
    pending.current = { key: requestKey, controller };
    setStored(null);
    setLoadingKey(requestKey);
    const isCurrent = () => !controller.signal.aborted
      && latestKey.current === requestKey && pending.current?.controller === controller;
    try {
      const result = await api.satelliteReference(
        { latitude: coordinate.latitude, longitude: coordinate.longitude }, controller.signal,
      );
      if (isCurrent()) setStored({ key: requestKey, value: result });
    } catch {
      if (isCurrent()) setStored({ key: requestKey, value: fallbackResponse });
    } finally {
      if (isCurrent()) {
        pending.current = null;
        setLoadingKey(null);
      }
    }
  }

  const status = evidence?.status ?? "not_run";
  const statusLabel = !coordinate?.accepted
    ? t("commercial.confirmationRequired")
    : loading
      ? t("commercial.referenceLoading")
      : !evidence
        ? t("commercial.satelliteNotRun")
      : status === "available"
        ? t("commercial.referenceAvailable")
        : status === "limited"
          ? t("commercial.referenceLimited")
          : t("commercial.referenceUnavailable");
  const badgeClass = status === "available"
    ? "bg-sky-50 text-sky-900"
    : status === "limited"
      ? "bg-amber-100 text-amber-900"
      : "bg-stone-100 text-slate-700";

  return <section data-testid="satellite-evidence-card" className="min-w-0 rounded-lg border border-stone-200 bg-white p-4">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.16em] text-sky-700">{t("commercial.reference")}</p>
        <h3 className="mt-1 text-base font-black text-slate-950">{t("commercial.satelliteTitle")}</h3>
      </div>
      <span data-testid="satellite-evidence-status" data-status={status} className={`rounded-full px-2 py-1 text-[10px] font-black ${badgeClass}`}>{statusLabel}</span>
    </div>

    {!coordinate?.accepted && <p className="mt-3 text-xs leading-5 text-amber-800">{t("commercial.satelliteConfirm")}</p>}
    {coordinate?.accepted && !evidence && !loading && <p className="mt-3 text-xs leading-5 text-slate-600">{t("commercial.satelliteManual")}</p>}
    <button type="button" data-testid="satellite-request-action" disabled={!coordinate?.accepted || loading} onClick={() => void requestReference()} className="mt-3 rounded-lg border border-sky-700 bg-white px-3 py-2 text-xs font-bold text-sky-900 focus:outline-none focus:ring-2 focus:ring-sky-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">{t("commercial.satelliteRequest")}</button>
    {loading && <p className="mt-3 text-xs leading-5 text-slate-600">{t("commercial.satelliteLoading")}</p>}

    {evidence && <>
      {evidence.image_reference && <Image unoptimized width={512} height={512} data-testid="satellite-reference-image" src={evidence.image_reference} alt="Bounded Sentinel-2 satellite reference composite" className="mt-3 aspect-square w-full rounded-lg border border-stone-200 object-cover" />}
      <dl className="mt-3 grid gap-2 text-[11px] leading-5 text-slate-700">
        <div><dt className="font-black text-slate-900">{t("commercial.sourceLabel")}</dt><dd>{evidence.source}</dd></div>
        <div><dt className="font-black text-slate-900">{t("commercial.datasetLabel")}</dt><dd className="break-all">{evidence.dataset}</dd></div>
        <div><dt className="font-black text-slate-900">{t("commercial.windowLabel")}</dt><dd>{evidence.window_start} — {evidence.window_end}</dd></div>
        <div><dt className="font-black text-slate-900">{t("commercial.compositeLabel")}</dt><dd>{evidence.composite_method}</dd></div>
        <div><dt className="font-black text-slate-900">{t(evidence.status === "unavailable" ? "commercial.checkedLabel" : "commercial.retrievedLabel")}</dt><dd>{evidence.retrieval_time}</dd></div>
        <div><dt className="font-black text-slate-900">{t("commercial.cloudLabel")}</dt><dd>{locale === "zh-TW" ? "場景雲量門檻" : "Scene threshold"} ≤ {evidence.cloud_filter_percent}% · SCL</dd></div>
      </dl>
      <ul className="mt-3 space-y-1 text-[10px] leading-5 text-slate-600">{evidence.limitations.map((limitation) => <li key={limitation}>• {limitation}</li>)}</ul>
      <p className="mt-3 text-[10px] leading-5 text-slate-500">{evidence.attribution}</p>
    </>}

    <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-bold leading-5 text-amber-950">{t("commercial.satelliteDisclaimer")}</p>
  </section>;
}
