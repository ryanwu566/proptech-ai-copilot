export const GOOGLE_MAPS_EMBED_ORIGIN = "https://www.google.com";
export const GOOGLE_MAP_ZOOM = 17;
export const GOOGLE_STREET_VIEW_RADIUS_METRES = 50;

export type GoogleMapsEmbedUrls = {
  mapUrl: string;
  streetViewUrl: string;
};

export function buildGoogleMapsEmbedUrls({
  browserKey,
  latitude,
  longitude,
}: {
  browserKey: string | undefined;
  latitude: number;
  longitude: number;
}): GoogleMapsEmbedUrls | null {
  const key = browserKey?.trim();
  if (!key || !hasValidGoogleMapsCoordinates(latitude, longitude)) return null;

  const coordinates = `${latitude},${longitude}`;
  const mapUrl = new URL("/maps/embed/v1/view", GOOGLE_MAPS_EMBED_ORIGIN);
  mapUrl.searchParams.set("key", key);
  mapUrl.searchParams.set("center", coordinates);
  mapUrl.searchParams.set("zoom", String(GOOGLE_MAP_ZOOM));
  mapUrl.searchParams.set("maptype", "roadmap");

  const streetViewUrl = new URL("/maps/embed/v1/streetview", GOOGLE_MAPS_EMBED_ORIGIN);
  streetViewUrl.searchParams.set("key", key);
  streetViewUrl.searchParams.set("location", coordinates);
  streetViewUrl.searchParams.set("radius", String(GOOGLE_STREET_VIEW_RADIUS_METRES));

  return { mapUrl: mapUrl.toString(), streetViewUrl: streetViewUrl.toString() };
}

export function hasValidGoogleMapsCoordinates(latitude: number, longitude: number) {
  return Number.isFinite(latitude)
    && Number.isFinite(longitude)
    && latitude >= -90
    && latitude <= 90
    && longitude >= -180
    && longitude <= 180;
}
