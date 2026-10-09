import type { CommuteAddressLookupResult, CommuteRouteEvidence, LocationInsightResult } from "../api";
import type { SavedCase } from "../case-storage";
import type { TaskReadinessState } from "../commercial/state";
import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type { PropertyCaseWorkspace } from "./workspace-model";
// @ts-expect-error Native TS runner extension.
import { normalizeLocationInsightEvidence } from "../location-insight-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { areJourneyPropertyAddressesEquivalent } from "../journey-property-identity.ts";

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
  const insight = saved.data.locationInsight ? normalizeLocationInsightEvidence(saved.data.locationInsight) : undefined;
  const insightAddress = insight?.input?.address;
  const wrongAddress = typeof insightAddress === "string" && Boolean(insightAddress.trim()) && Boolean(anchor?.normalized_address)
    && !areJourneyPropertyAddressesEquivalent(insightAddress, anchor!.normalized_address);
  if (insight && wrongAddress) {
    insight.risk_facility_evidence = { status: "unavailable", count: null, source: insight.risk_facility_evidence?.source ?? null, checked_at: insight.risk_facility_evidence?.checked_at ?? null, reason: "property_identity_mismatch", limitation: "先前設施證據不屬於目前物件。" };
    insight.poi_summary = Object.fromEntries(Object.keys(insight.poi_summary).map((key) => [key, null])) as LocationInsightResult["poi_summary"];
  }

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
    ...(insight ? {
      insight,
      poiSummary: insight.poi_summary,
    } : {}),
    ...(routeCurrent ? { routeEvidence: storedRoute } : {}),
    routeInvalidated: Boolean(storedRoute && !routeCurrent),
    ...(saved.data.commuteTransit ? { transitContext: saved.data.commuteTransit } : {}),
  };
}

export function buildLocationOverviewHandoff(workspace: PropertyCaseWorkspace): LocationOverviewHandoff {
  const snapshot = workspace.location;
  const identityConfirmed = workspace.identity.state === "confirmed";
  const candidateRoute = identityConfirmed && snapshot.routeEvidence?.status === "resolved" ? snapshot.routeEvidence : undefined;
  const route = candidateRoute?.source === "google_routes" && !candidateRoute.fallback && !candidateRoute.partial
    ? candidateRoute
    : undefined;
  const transitAvailable = snapshot.transitContext?.status === "resolved";
  const unresolved: string[] = [];

  if (!identityConfirmed) unresolved.push("物件位置已變更，需重新確認");
  if (identityConfirmed && !route) {
    unresolved.push(snapshot.routeInvalidated ? "先前目的地路線不屬於目前物件" : snapshot.routeEvidence ? "目的地路線目前無法取得" : "尚未設定通勤目的地");
  }
  if (candidateRoute && !route) unresolved.push("路線僅為模擬、備援或部分結果，不能建立正式通勤就緒狀態。");
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
