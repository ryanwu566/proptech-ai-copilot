"use client";

import { useEffect } from "react";
import L from "leaflet";
import { Circle, LayersControl, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { NearbyCategory, NearbyPlace } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { classifyNearbyPlace, NEARBY_POI_STYLES, NEARBY_PROPERTY_STYLE, nearbyPoiIconSvg, type NearbyPoiKind, type NearbyQueryCategory } from "@/lib/workspace/nearby-poi-category";

/** A saved nearby facility already classified into a product kind, with localized text. */
export type GeoMapPoi = { id: string; name: string; lat: number; lng: number; kind: NearbyPoiKind; label: string };

const QUERY_CATEGORIES = new Set<string>(["transport", "school", "park", "medical", "shopping", "food"]);

function poiIcon(kind: NearbyPoiKind, selected = false) {
  const size = selected ? 36 : 26;
  return L.divIcon({
    className: "",
    html: `<span data-testid="nearby-marker" data-kind="${kind}" data-selected="${selected}" style="display:block;width:${size}px;height:${size}px;border-radius:999px;${selected ? "box-shadow:0 0 0 3px #fff,0 0 0 6px #0f172a,0 4px 14px rgba(15,23,42,.45)" : "box-shadow:0 2px 8px rgba(15,23,42,.35)"}">${nearbyPoiIconSvg(NEARBY_POI_STYLES[kind], size)}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// The property is a larger rounded-square pin with a house glyph and amber outline, unlike any circular POI.
const propertyIcon = () => L.divIcon({
  className: "",
  html: `<span data-testid="property-marker" style="display:block;width:38px;height:38px;filter:drop-shadow(0 3px 8px rgba(15,23,42,.45))">${nearbyPoiIconSvg(NEARBY_PROPERTY_STYLE, 38, "pin")}</span>`,
  iconSize: [38, 38],
  iconAnchor: [19, 19],
});

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

function FocusPoi({ poi }: { poi?: GeoMapPoi }) {
  const map = useMap();
  useEffect(() => { if (poi) map.panTo([poi.lat, poi.lng]); }, [map, poi]);
  return null;
}

export default function GeoMap({ center, zoom, categories, selectedPlace, onSelectPlace, centerLabel, radiusMeters = 800, scrollWheelZoomEnabled = true, pois = [], selectedPoiId, onSelectPoi }: { center: { lat: number; lng: number }; zoom: number; categories: NearbyCategory[]; selectedPlace?: NearbyPlace; onSelectPlace?: (place: NearbyPlace) => void; centerLabel?: string; radiusMeters?: number; scrollWheelZoomEnabled?: boolean; pois?: GeoMapPoi[]; selectedPoiId?: string; onSelectPoi?: (id: string) => void }) {
  const { copy } = useExperienceLocale();
  const baseLayers = {
    standard: copy("map.baseStandard"),
    light: copy("map.baseLight"),
    satellite: copy("map.baseSatellite"),
  };
  return <MapContainer center={[center.lat, center.lng]} zoom={zoom} scrollWheelZoom={scrollWheelZoomEnabled} className="h-full min-h-[360px] w-full sm:min-h-[500px] xl:min-h-[650px]">
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
    <Circle center={[center.lat, center.lng]} radius={radiusMeters} pathOptions={{ color: "#0891b2", fillColor: "#22d3ee", fillOpacity: 0.05, weight: 2 }} />
    <Marker position={[center.lat, center.lng]} icon={propertyIcon()} zIndexOffset={2000} title={centerLabel ?? copy("map.selected")} alt={centerLabel ?? copy("map.selected")}><Popup>{centerLabel ?? copy("map.selected")}</Popup></Marker>
    <FocusPoi poi={pois.find((poi) => poi.id === selectedPoiId)} />
    {pois.map((poi) => <Marker key={poi.id} position={[poi.lat, poi.lng]} icon={poiIcon(poi.kind, poi.id === selectedPoiId)} zIndexOffset={poi.id === selectedPoiId ? 1000 : 0} title={`${poi.name} · ${poi.label}`} alt={`${poi.name} · ${poi.label}`} eventHandlers={{ click: () => onSelectPoi?.(poi.id) }} />)}
    {categories.flatMap((group) => group.places.map((place) => <Marker key={place.place_id} position={[place.lat, place.lng]} icon={poiIcon(QUERY_CATEGORIES.has(group.category) ? classifyNearbyPlace(place.types, group.category as NearbyQueryCategory) : "other", selectedPlace?.place_id === place.place_id)} eventHandlers={{ click: () => onSelectPlace?.(place) }}><Popup><strong>{place.name}</strong><br />{group.label} · {Math.round(place.distance_m)} m{place.rating === null ? "" : ` · ${copy("map.rating")} ${place.rating}`}<br />{place.opening_status_label}<br />{place.address}</Popup></Marker>))}
  </MapContainer>;
}
