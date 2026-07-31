"use client";

import { useEffect } from "react";
import L from "leaflet";
import { Circle, LayersControl, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { NearbyCategory, NearbyPlace } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";

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

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character] ?? character);
}

function Recenter({ center, zoom, selected, selectedLabel, distanceLabel, ratingLabel }: { center: { lat: number; lng: number }; zoom: number; selected?: NearbyPlace; selectedLabel: string; distanceLabel: string; ratingLabel: string }) {
  const map = useMap();
  useEffect(() => {
    map.setView(selected ? [selected.lat, selected.lng] : [center.lat, center.lng], selected ? Math.max(zoom, 17) : zoom);
    if (selected) {
      const distance = `${distanceLabel}: ${Math.round(selected.distance_m)} m`;
      const rating = selected.rating === null ? "" : `<br>${escapeHtml(ratingLabel)}: ${selected.rating}`;
      L.popup()
        .setLatLng([selected.lat, selected.lng])
        .setContent(`<strong>${escapeHtml(selectedLabel)}: ${escapeHtml(selected.name)}</strong><br>${escapeHtml(distance)}${rating}<br>${escapeHtml(selected.address)}`)
        .openOn(map);
    }
  }, [center, distanceLabel, map, ratingLabel, selected, selectedLabel, zoom]);
  return null;
}

export default function GeoMap({ center, zoom, categories, selectedPlace, onSelectPlace }: { center: { lat: number; lng: number }; zoom: number; categories: NearbyCategory[]; selectedPlace?: NearbyPlace; onSelectPlace?: (place: NearbyPlace) => void }) {
  const { copy } = useExperienceLocale();
  const baseLayers = {
    standard: copy("map.baseStandard"),
    light: copy("map.baseLight"),
    satellite: copy("map.baseSatellite"),
  };
  return <MapContainer center={[center.lat, center.lng]} zoom={zoom} scrollWheelZoom className="h-full min-h-[360px] w-full sm:min-h-[500px] xl:min-h-[650px]">
    <Recenter center={center} zoom={zoom} selected={selectedPlace} selectedLabel={copy("map.selected")} distanceLabel={copy("map.distance")} ratingLabel={copy("map.rating")} />
    <LayersControl position="topright">
      <LayersControl.BaseLayer checked name={baseLayers.standard}>
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      </LayersControl.BaseLayer>
      <LayersControl.BaseLayer name={baseLayers.light}>
        <TileLayer attribution="&copy; OpenStreetMap contributors &copy; CARTO" url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" />
      </LayersControl.BaseLayer>
      <LayersControl.BaseLayer name={baseLayers.satellite}>
        <TileLayer attribution="Tiles &copy; Esri" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
      </LayersControl.BaseLayer>
    </LayersControl>
    <Circle center={[center.lat, center.lng]} radius={800} pathOptions={{ color: "#0891b2", fillColor: "#22d3ee", fillOpacity: 0.05, weight: 2 }} />
    <Marker position={[center.lat, center.lng]} icon={markerIcon("#0f172a", true)}><Popup>{copy("map.selected")}</Popup></Marker>
    {categories.flatMap((group) => group.places.map((place) => <Marker key={place.place_id} position={[place.lat, place.lng]} icon={markerIcon(categoryColors[group.category] ?? "#64748b", false, selectedPlace?.place_id === place.place_id)} eventHandlers={{ click: () => onSelectPlace?.(place) }}><Popup><strong>{place.name}</strong><br />{group.label} · {Math.round(place.distance_m)} m{place.rating === null ? "" : ` · ${copy("map.rating")} ${place.rating}`}<br />{place.opening_status_label}<br />{place.address}</Popup></Marker>))}
  </MapContainer>;
}
