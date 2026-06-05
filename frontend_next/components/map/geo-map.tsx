"use client";

import { useEffect } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { MapPoiLayer } from "@/lib/api";

const categoryColors: Record<string, string> = {
  transport: "#2563eb",
  school: "#7c3aed",
  park: "#16a34a",
  medical: "#e11d48",
  commerce: "#ea580c",
};

function markerIcon(color: string, center = false) {
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:${center ? 20 : 14}px;height:${center ? 20 : 14}px;border-radius:999px;background:${color};border:3px solid white;box-shadow:0 2px 8px rgba(15,23,42,.3)"></span>`,
    iconAnchor: [center ? 10 : 7, center ? 10 : 7],
  });
}

function Recenter({ center, zoom }: { center: { lat: number; lng: number }; zoom: number }) {
  const map = useMap();
  useEffect(() => { map.setView([center.lat, center.lng], zoom); }, [center, map, zoom]);
  return null;
}

export default function GeoMap({ center, zoom, layers }: { center: { lat: number; lng: number }; zoom: number; layers: MapPoiLayer[] }) {
  return <MapContainer center={[center.lat, center.lng]} zoom={zoom} scrollWheelZoom className="h-full min-h-[360px] w-full sm:min-h-[500px] xl:min-h-[650px]">
    <Recenter center={center} zoom={zoom} />
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Circle center={[center.lat, center.lng]} radius={800} pathOptions={{ color: "#2563eb", fillColor: "#3b82f6", fillOpacity: 0.06, weight: 2 }} />
    <Marker position={[center.lat, center.lng]} icon={markerIcon("#0f172a", true)}><Popup>查詢中心點</Popup></Marker>
    {layers.flatMap((layer) => layer.points.map((point) => <Marker key={`${layer.category}-${point.name}`} position={[point.lat, point.lng]} icon={markerIcon(categoryColors[layer.category] ?? "#64748b")}><Popup><strong>{point.name}</strong><br />{layer.label} · 權重 {point.score_weight}</Popup></Marker>))}
  </MapContainer>;
}
