"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import { Circle, GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { CadastralEvidence, LandsectContext, ParcelGeometryEvidence } from "@/lib/api";

type OverlayState = "loading" | "visible" | "unavailable" | "not_configured";

function analyzedPointIcon(center: CadastralEvidence["center"]) {
  return L.divIcon({
    className: "",
    html: `<span data-testid="terrain-analyzed-marker" data-lat="${center.lat}" data-lng="${center.lng}" style="display:block;width:22px;height:22px;border-radius:999px;background:#0f172a;border:4px solid white;box-shadow:0 3px 16px rgba(15,23,42,.45)"></span>`,
    iconAnchor: [11, 11],
  });
}

function Recenter({ center }: { center: CadastralEvidence["center"] }) {
  const map = useMap();
  useEffect(() => { map.setView([center.lat, center.lng], 17); }, [center.lat, center.lng, map]);
  return null;
}

function FitParcel({ evidence }: { evidence?: ParcelGeometryEvidence }) {
  const map = useMap();
  useEffect(() => {
    if (!evidence?.geometry || !evidence.can_spatial_intersect) return;
    const bounds = L.geoJSON(evidence.geometry as never).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 18 });
  }, [evidence, map]);
  return null;
}

function safeTileTemplate(value?: string): string | null {
  if (!value) return null;
  if (/(?:api[_-]?key|token|credential|secret)=/i.test(value)) return null;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try {
    const url = new URL(value);
    if (url.protocol === "https:" && url.hostname === "wmts.nlsc.gov.tw") return value;
  } catch {
    return null;
  }
  return null;
}

export default function TerrainEvidenceLeafletMap({
  evidence,
  parcelEvidence,
  landsect,
  radiusM,
  markerLabel,
  onOverlayState,
}: {
  evidence: CadastralEvidence;
  parcelEvidence?: ParcelGeometryEvidence;
  landsect?: LandsectContext;
  radiusM: number;
  markerLabel: string;
  onOverlayState: (state: OverlayState) => void;
}) {
  const configuredTileTemplate = landsect?.tile_url_template ?? evidence.tile_url_template;
  const tileTemplate = safeTileTemplate(configuredTileTemplate);
  const overlayFailed = useRef(false);

  useEffect(() => {
    overlayFailed.current = false;
    if (configuredTileTemplate && !tileTemplate) onOverlayState("unavailable");
  }, [configuredTileTemplate, onOverlayState, tileTemplate]);

  return <MapContainer
    center={[evidence.center.lat, evidence.center.lng]}
    zoom={17}
    scrollWheelZoom={false}
    className="h-[320px] w-full touch-pan-y sm:h-[420px]"
    data-testid="terrain-cadastral-map"
  >
    <Recenter center={evidence.center} />
    <FitParcel evidence={parcelEvidence} />
    <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {tileTemplate && <TileLayer
      attribution={landsect?.attribution ?? "NLSC LANDSECT"}
      opacity={0.72}
      url={tileTemplate}
      eventHandlers={{
        tileerror: () => {
          overlayFailed.current = true;
          onOverlayState("unavailable");
        },
        tileload: () => {
          if (!overlayFailed.current) onOverlayState("visible");
        },
      }}
    />}
    {parcelEvidence?.geometry && parcelEvidence.can_spatial_intersect && <GeoJSON
      key={`${parcelEvidence.checked_at}-${parcelEvidence.geometry_type}`}
      data={parcelEvidence.geometry as never}
      pathOptions={parcelEvidence.status === "verified_official"
        ? { color: "#065f46", fillColor: "#10b981", fillOpacity: 0.14, weight: 3, className: "official-parcel-vector" }
        : { color: "#0891b2", fillColor: "#22d3ee", fillOpacity: 0.12, weight: 3, dashArray: "8 6", className: "user-provided-parcel" }}
    />}
    <Circle
      center={[evidence.center.lat, evidence.center.lng]}
      radius={radiusM}
      pathOptions={{ color: "#d97706", fillColor: "#f59e0b", fillOpacity: 0.05, weight: 2, dashArray: "7 6" }}
    />
    <Marker position={[evidence.center.lat, evidence.center.lng]} icon={analyzedPointIcon(evidence.center)}>
      <Popup>{markerLabel}</Popup>
    </Marker>
  </MapContainer>;
}
