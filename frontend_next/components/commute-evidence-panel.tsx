"use client";

import { CommuteLivabilityCard } from "@/components/commute-livability-card";
import { CommuteRouteCard } from "@/components/commute-route-card";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { commuteRouteCopy } from "@/lib/commute-route-copy";
import type { CommuteAddressLookupResult, CommuteRouteEvidence, LocationInsightResult } from "@/lib/api";
import type { LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import type { CommuteLivabilityStatus } from "@/lib/commute-livability-ui";

type Props = {
  address: string;
  locationResult: LocationInsightResult | null;
  origin?: { latitude: number; longitude: number };
  routeEvidence?: CommuteRouteEvidence;
  transitResult?: CommuteAddressLookupResult;
  onRouteStatusChange: (status: LocationMarketDisplayStatus) => void;
  onRouteEvidence: (evidence: CommuteRouteEvidence | null) => void;
  onTransitStatusChange: (status: LocationMarketDisplayStatus) => void;
  onTransitResult: (result: CommuteAddressLookupResult | null) => void;
};

function transitStatus(status: CommuteLivabilityStatus): LocationMarketDisplayStatus {
  if (status === "idle") return "not_started";
  if (status === "error") return "unavailable";
  if (status === "resolved") return "available";
  if (status === "unresolved") return "no_data";
  return status;
}

export function CommuteEvidencePanel({ address, locationResult, origin: explicitOrigin, routeEvidence, transitResult, onRouteStatusChange, onRouteEvidence, onTransitStatusChange, onTransitResult }: Props) {
  const { copyFrom } = useExperienceLocale();
  const origin = explicitOrigin ?? locationResult?.resolved_location;
  return <div className="space-y-3">
    {origin ? (
      <CommuteRouteCard originLatitude={origin.latitude} originLongitude={origin.longitude} initialEvidence={routeEvidence} onStatusChange={onRouteStatusChange} onEvidence={onRouteEvidence} />
    ) : (
      <div className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs leading-5 text-slate-600">{copyFrom(commuteRouteCopy, "needsLocation")}</div>
    )}
    <CommuteLivabilityCard address={address} initialResult={transitResult} onStatusChange={(status) => onTransitStatusChange(transitStatus(status))} onResult={onTransitResult} />
  </div>;
}
