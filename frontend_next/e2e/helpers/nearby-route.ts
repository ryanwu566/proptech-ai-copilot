import type { Page } from "@playwright/test";

export type NearbyCall = { lat: number; lng: number; radius_m: number; categories: string[]; language_code: string };

/**
 * Confirming a location refreshes Nearby once for the accepted coordinates. Fulfil it with one
 * bounded Google Places fixture centred on the request, and record each payload for assertions.
 */
export async function routeNearby(page: Page, calls: NearbyCall[]) {
  await page.route("**/map/nearby", async (route) => {
    const payload = route.request().postDataJSON() as NearbyCall;
    calls.push(payload);
    await route.fulfill({ json: {
      center: { lat: payload.lat, lng: payload.lng }, radius_m: 800, source: "google_places", checked_at: "2026-10-20T03:00:00Z",
      categories: [{ category: "transport", source: "google_places", places: [{ place_id: "confirm-mrt", name: "Confirmed fixture station", lat: payload.lat + 0.001, lng: payload.lng, types: ["subway_station", "transit_station"], source: "google_places" }] }],
    } }).catch(() => {});
  });
}

export const isNearbyRequest = (url: URL) => url.pathname.endsWith("/map/nearby");
