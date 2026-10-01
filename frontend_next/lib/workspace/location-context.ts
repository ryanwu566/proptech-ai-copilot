import type { CommuteAddressLookupResult, CommuteRouteEvidence, LocationInsightResult } from "../api";
import type { SavedCase } from "../case-storage";
import type { TaskReadinessState } from "../commercial/state";
import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type { PropertyCaseWorkspace } from "./workspace-model";

export type LocationPropertyContext = {
  address: string;
  normalizedAddress: string;
  coordinates: { latitude: number; longitude: number } | null;
  checkedAt: string | null;
  village: { name: string | null; code: string | null };
  sourceIds: string[];
};

export type LocationWorkspaceSnapshot = {
  property: LocationPropertyContext;
  insight?: LocationInsightResult;
  poiSummary?: LocationInsightResult["poi_summary"];
  routeEvidence?: CommuteRouteEvidence;
  routeInvalidated: boolean;
  transitContext?: CommuteAddressLookupResult;
};

export type LocationOverviewHandoff = {
  identityState: PropertyCaseWorkspace["identity"]["state"];
  mapReady: boolean;
  commuteReadiness: TaskReadinessState;
  selectedRoute?: {
    destination: string;
    mode: CommuteRouteEvidence["mode"];
    distanceM: number;
    durationMinutes: number;
    checkedAt: string;
  };
  unresolved: string[];
};

function addressFrom(saved: SavedCase, anchor: JourneyPropertyIdentityAnchorV1 | undefined): string {
  return anchor?.address_input
    || saved.data.journeyContext?.propertyContext.addressSummary
    || [saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].filter(Boolean).join("")
    || saved.title;
}

function routeMatchesOrigin(route: CommuteRouteEvidence, coordinates: NonNullable<JourneyPropertyIdentityAnchorV1["coordinates"]>): boolean {
  return Math.abs(route.origin.latitude - coordinates.latitude) <= 0.000001
    && Math.abs(route.origin.longitude - coordinates.longitude) <= 0.000001;
}

export function buildLocationWorkspaceSnapshot(saved: SavedCase): LocationWorkspaceSnapshot {
  const anchor = saved.data.propertyIdentityAnchor;
  const coordinates = anchor?.coordinates ?? null;
  const storedRoute = saved.data.commuteRoute;
  const routeCurrent = Boolean(storedRoute && coordinates && routeMatchesOrigin(storedRoute, coordinates));

  return {
    property: {
      address: addressFrom(saved, anchor),
      normalizedAddress: anchor?.normalized_address || addressFrom(saved, anchor),
      coordinates,
      checkedAt: anchor?.evidence.checked_at ?? null,
      village: {
        name: anchor?.administrative_location.village ?? null,
        code: anchor?.administrative_location.village_code ?? null,
      },
      sourceIds: anchor?.evidence.sources.map((source) => source.source_id) ?? [],
    },
    ...(saved.data.locationInsight ? {
      insight: saved.data.locationInsight,
      poiSummary: saved.data.locationInsight.poi_summary,
    } : {}),
    ...(routeCurrent ? { routeEvidence: storedRoute } : {}),
    routeInvalidated: Boolean(storedRoute && !routeCurrent),
    ...(saved.data.commuteTransit ? { transitContext: saved.data.commuteTransit } : {}),
  };
}

export function buildLocationOverviewHandoff(workspace: PropertyCaseWorkspace): LocationOverviewHandoff {
  const snapshot = workspace.location;
  const identityConfirmed = workspace.identity.state === "confirmed";
  const route = identityConfirmed && snapshot.routeEvidence?.status === "resolved" ? snapshot.routeEvidence : undefined;
  const transitAvailable = snapshot.transitContext?.status === "resolved";
  const unresolved: string[] = [];

  if (!identityConfirmed) unresolved.push("物件位置已變更，需重新確認");
  if (identityConfirmed && !route) {
    unresolved.push(snapshot.routeInvalidated ? "先前目的地路線不屬於目前物件" : snapshot.routeEvidence ? "目的地路線目前無法取得" : "尚未設定通勤目的地");
  }
  if (snapshot.transitContext && !transitAvailable) unresolved.push("大眾運輸周邊資料目前無法取得");

  const commuteReadiness: TaskReadinessState = !identityConfirmed
    ? "blocked"
    : route
      ? transitAvailable ? "ready" : "ready_with_limits"
      : "not_ready";

  return {
    identityState: workspace.identity.state,
    mapReady: workspace.identity.state === "confirmed" && snapshot.property.coordinates !== null,
    commuteReadiness,
    ...(route && route.distance_m !== null && route.duration_min !== null ? {
      selectedRoute: {
        destination: route.destination.address,
        mode: route.mode,
        distanceM: route.distance_m,
        durationMinutes: route.duration_min,
        checkedAt: route.checked_at,
      },
    } : {}),
    unresolved,
  };
}
