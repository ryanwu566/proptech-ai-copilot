"use client";

import { useEffect } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { NearbyCategory, NearbyPlace } from "@/lib/api";

const categoryColors: Record<string, string> = {
  transport: "#2563eb",
  school: "#7c3aed",
  park: "#16a34a",
  medical: "#e11d48",
  shopping: "#ea580c",
  food: "#d97706",
};

function markerIcon(color: string, center = false, selected = false) {
  const size = center ? 20 : selected ? 18 : 14;
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:999px;background:${color};border:${selected ? 4 : 3}px solid white;box-shadow:0 2px ${selected ? 14 : 8}px rgba(15,23,42,.35)"></span>`,
    iconAnchor: [size / 2, size / 2],
  });
}

function Recenter({ center, zoom, selected }: { center: { lat: number; lng: number }; zoom: number; selected?: NearbyPlace }) {
  const map = useMap();
  useEffect(() => { map.setView(selected ? [selected.lat, selected.lng] : [center.lat, center.lng], selected ? Math.max(zoom, 17) : zoom); }, [center, map, selected, zoom]);
  return null;
}

export default function GeoMap({ center, zoom, categories, selectedPlace, onSelectPlace }: { center: { lat: number; lng: number }; zoom: number; categories: NearbyCategory[]; selectedPlace?: NearbyPlace; onSelectPlace?: (place: NearbyPlace) => void }) {
  return <MapContainer center={[center.lat, center.lng]} zoom={zoom} scrollWheelZoom className="h-full min-h-[360px] w-full sm:min-h-[500px] xl:min-h-[650px]">
    <Recenter center={center} zoom={zoom} selected={selectedPlace} />
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Circle center={[center.lat, center.lng]} radius={800} pathOptions={{ color: "#0891b2", fillColor: "#22d3ee", fillOpacity: 0.05, weight: 2 }} />
    <Marker position={[center.lat, center.lng]} icon={markerIcon("#0f172a", true)}><Popup>查詢中心點</Popup></Marker>
    {categories.flatMap((group) => group.places.map((place) => <Marker key={place.place_id} position={[place.lat, place.lng]} icon={markerIcon(categoryColors[group.category] ?? "#64748b", false, selectedPlace?.place_id === place.place_id)} eventHandlers={{ click: () => onSelectPlace?.(place) }}><Popup><strong>{place.name}</strong><br />{group.label} · {place.distance_m} 公尺<br />{place.rating ? `評分 ${place.rating} · ` : ""}{place.business_status === "OPERATIONAL" ? "營業中" : place.business_status}<br />{place.address}</Popup></Marker>))}
  </MapContainer>;
}
