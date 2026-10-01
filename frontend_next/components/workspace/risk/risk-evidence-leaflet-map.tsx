"use client";

import { useEffect } from "react";
import L from "leaflet";
import { Circle, GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { ParcelGeoJsonGeometry } from "@/lib/api";
import styles from "./risk-environment.module.css";

function propertyIcon(center: { latitude: number; longitude: number }) {
  return L.divIcon({
    className: "",
    html: `<span data-testid="risk-property-marker" data-lat="${center.latitude}" data-lng="${center.longitude}" style="display:block;width:22px;height:22px;border-radius:999px;background:#172033;border:4px solid white;box-shadow:0 3px 14px rgba(15,23,42,.35)"></span>`,
    iconAnchor: [11, 11],
  });
}

function Recenter({ center }: { center: { latitude: number; longitude: number } }) {
  const map = useMap();
  useEffect(() => { map.setView([center.latitude, center.longitude], 15); }, [center.latitude, center.longitude, map]);
  return null;
}

export default function RiskEvidenceLeafletMap({
  center,
  radiusM,
  hazardGeometries = {},
  selectedKey,
}: {
  center: { latitude: number; longitude: number };
  radiusM: number;
  hazardGeometries?: Record<string, ParcelGeoJsonGeometry | null>;
  selectedKey?: string;
}) {
  const geometries = Object.entries(hazardGeometries).filter((entry): entry is [string, ParcelGeoJsonGeometry] => entry[1] !== null);
  return <MapContainer center={[center.latitude, center.longitude]} zoom={15} scrollWheelZoom={false} className={styles.mapCanvas}>
    <Recenter center={center} />
    <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {geometries.map(([key, geometry]) => <GeoJSON
      key={key}
      data={geometry as never}
      pathOptions={{
        color: key === selectedKey ? "#a61b16" : "#854d0e",
        fillColor: key === selectedKey ? "#e78d87" : "#e9bd55",
        fillOpacity: key === selectedKey ? 0.28 : 0.12,
        weight: key === selectedKey ? 4 : 2,
      }}
    />)}
    <Circle center={[center.latitude, center.longitude]} radius={radiusM} pathOptions={{ color: "#0f5c78", fillColor: "#7cc3df", fillOpacity: 0.06, weight: 2, dashArray: "7 6" }} />
    <Marker position={[center.latitude, center.longitude]} icon={propertyIcon(center)}><Popup>目前物件位置</Popup></Marker>
  </MapContainer>;
}
