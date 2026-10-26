import type { CommuteAddressLookupResult, CommuteRouteEvidence, LocationInsightResult } from "../api";
import type { SavedCase } from "../case-storage";
import type { TaskReadinessState } from "../commercial/state";
import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type { PropertyCaseWorkspace } from "./workspace-model";
// @ts-expect-error Native TS runner extension.
import { identityConfirmationCopy, identityConfirmationKind } from "./identity-confirmation-copy.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeLocationInsightEvidence } from "../location-insight-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { areJourneyPropertyAddressesEquivalent } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeNearbyFacilities, type NearbyFacilitiesEvidence } from "./nearby-facilities.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeVillageDemographics, villageDemographicsMatches, type VillageDemographicsEvidence } from "./village-demographics.ts";
// @ts-expect-error Native TS runner extension.
import { locationViewCopy, type LocationUnresolvedKey } from "./location-view-copy.ts";

export type LocationPropertyContext = {
  address: string;
  normalizedAddress: string;
  coordinates: { latitude: number; longitude: number } | null;
  checkedAt: string | null;
  village: { name: string | null; code: string | null };
  sourceIds: string[];
};

export type LocationWorkspaceSnapshot = {
  nearbyFacilities?: NearbyFacilitiesEvidence;
  /** Present only for the currently confirmed coordinate; never carried across a re-located identity. */
  villageDemographics?: VillageDemographicsEvidence;
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
  /** zh-TW text of the unresolved items, kept for existing consumers; render `unresolvedKeys` in the active locale. */
  unresolved: string[];
  unresolvedKeys: Array<LocationUnresolvedKey | "identityPending" | "identityReconfirmation">;
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

export function buildLocationWorkspaceSnapshot(saved: SavedCase, identityConfirmed = false): LocationWorkspaceSnapshot {
  const anchor = saved.data.propertyIdentityAnchor;
  const coordinates = anchor?.coordinates ?? null;
  const nearby = normalizeNearbyFacilities(saved.data.nearbyFacilities);
  const nearbyCurrent = identityConfirmed && nearby && coordinates && anchor?.revalidation.status === "current"
    && Math.abs(nearby.origin.lat - coordinates.latitude) <= 0.000001 && Math.abs(nearby.origin.lng - coordinates.longitude) <= 0.000001;
  const demographics = normalizeVillageDemographics(saved.data.villageDemographics);
  const demographicsCurrent = identityConfirmed && anchor?.revalidation.status === "current" && villageDemographicsMatches(demographics, coordinates);
  const storedRoute = saved.data.commuteRoute;
  const routeCurrent = Boolean(storedRoute && coordinates && routeMatchesOrigin(storedRoute, coordinates));
  let insight = saved.data.locationInsight ? normalizeLocationInsightEvidence(saved.data.locationInsight) : undefined;
  const insightAddress = insight?.input?.address;
  const wrongAddress = typeof insightAddress === "string" && Boolean(insightAddress.trim()) && Boolean(anchor?.normalized_address)
    && !areJourneyPropertyAddressesEquivalent(insightAddress, anchor!.normalized_address);
  if (insight && wrongAddress) {
    // Every fact in the observation belongs to its original property.
    insight = undefined;
  }

  return {
    ...(nearbyCurrent ? { nearbyFacilities: nearby } : {}),
    ...(demographicsCurrent ? { villageDemographics: demographics } : {}),
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
  const unresolvedKeys: LocationOverviewHandoff["unresolvedKeys"] = [];

  if (!identityConfirmed) unresolvedKeys.push(identityConfirmationKind(workspace.identity) === "reconfirmation" ? "identityReconfirmation" : "identityPending");
  if (identityConfirmed && !route) unresolvedKeys.push(snapshot.routeInvalidated ? "routeInvalidated" : snapshot.routeEvidence ? "routeUnavailable" : "routeNotSet");
  if (candidateRoute && !route) unresolvedKeys.push("routeCandidateOnly");
  if (snapshot.transitContext && !transitAvailable) unresolvedKeys.push("transitUnavailable");
  const unresolved = unresolvedKeys.map((key) => key === "identityPending" ? identityConfirmationCopy["zh-TW"].pendingTitle
    : key === "identityReconfirmation" ? identityConfirmationCopy["zh-TW"].reconfirmationTitle
      : locationViewCopy["zh-TW"][key]);

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
    unresolvedKeys,
  };
}
