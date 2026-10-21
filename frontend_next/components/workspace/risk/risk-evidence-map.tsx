"use client";

import dynamic from "next/dynamic";
import type { ParcelGeoJsonGeometry } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { riskBuyerCopy } from "@/lib/workspace/risk-buyer-copy";

function MapLoading() {
  const { locale } = useExperienceLocale();
  return <div className="grid min-h-[360px] place-items-center bg-slate-100 text-sm text-slate-600 lg:min-h-[520px]">{riskBuyerCopy(locale).mapLoading}</div>;
}

const RiskEvidenceLeafletMap = dynamic(() => import("./risk-evidence-leaflet-map"), {
  ssr: false,
  loading: MapLoading,
});

export function RiskEvidenceMap({
  center,
  radiusM,
  hazardGeometries,
  selectedKey,
}: {
  center: { latitude: number; longitude: number };
  radiusM: number;
  hazardGeometries?: Record<string, ParcelGeoJsonGeometry | null>;
  selectedKey?: string;
}) {
  return <RiskEvidenceLeafletMap center={center} radiusM={radiusM} hazardGeometries={hazardGeometries} selectedKey={selectedKey} />;
}
