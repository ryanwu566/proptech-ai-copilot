"use client";

import dynamic from "next/dynamic";
import type { ParcelGeoJsonGeometry } from "@/lib/api";

const RiskEvidenceLeafletMap = dynamic(() => import("./risk-evidence-leaflet-map"), {
  ssr: false,
  loading: () => <div className="grid min-h-[360px] place-items-center bg-slate-100 text-sm text-slate-600 lg:min-h-[520px]">載入地圖中</div>,
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
