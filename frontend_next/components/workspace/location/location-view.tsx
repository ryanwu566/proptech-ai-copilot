"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { CommuteEvidencePanel } from "@/components/commute-evidence-panel";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { MapFrame } from "@/components/design-system/map-frame";
import { Message } from "@/components/design-system/message";
import { EvidenceSection, Panel, Section } from "@/components/design-system/section";
import { MetricItem, SummaryStrip } from "@/components/design-system/summary-strip";
import { StatusLabel } from "@/components/design-system/status-label";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import type { CommuteAddressLookupResult, CommuteRouteEvidence } from "@/lib/api";
import { updateSavedCaseLocationEvidence } from "@/lib/case-storage";
import { resolveCommercialState } from "@/lib/commercial/state";
import { buildLocationOverviewHandoff } from "@/lib/workspace/location-context";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { homeStartCopy } from "@/lib/home-start-copy";
import { locationConfirmationCopy } from "@/lib/workspace/location-confirmation-copy";
import { identityConfirmationCopy, identityConfirmationKind } from "@/lib/workspace/identity-confirmation-copy";
import { hasCompleteAdministrativeArea } from "@/lib/journey-property-identity";
import { nearbyFacilitiesCopy } from "@/lib/workspace/nearby-facilities-copy";
import { LocationConfirmationPanel } from "./location-confirmation-panel";
import { AdministrativeAreaRepairPanel } from "./administrative-area-repair-panel";
import { NearbyFacilitiesPanel } from "./nearby-facilities-panel";
import { VillageDemographicsPanel } from "./village-demographics-panel";
import { villageDemographicsCopy } from "@/lib/workspace/village-demographics-copy";
import { formatDemographicsMonth } from "@/lib/workspace/village-demographics";
import { formatLocationDistance, formatLocationDuration, locationViewCopy, type LocationViewCopyKey } from "@/lib/workspace/location-view-copy";
import { ExplicitMap } from "@/components/map/explicit-map";

function MapLoading() {
  const { copyFrom } = useExperienceLocale();
  return <div className="grid min-h-[360px] place-items-center bg-stone-100 text-sm text-slate-500">{copyFrom(locationViewCopy, "mapLoading")}</div>;
}

const GeoMap = dynamic(() => import("@/components/map/geo-map"), {
  ssr: false,
  loading: () => <MapLoading />,
});

const POI_LABELS = {
  transit_count: "poiTransit",
  convenience_count: "poiConvenience",
  school_count: "poiSchool",
  park_count: "poiPark",
  medical_count: "poiMedical",
  risk_facility_count: "poiRiskFacility",
} as const satisfies Record<string, LocationViewCopyKey>;

const MODE_LABELS = { transit: "modeTransit", driving: "modeDriving", walking: "modeWalking" } as const satisfies Record<string, LocationViewCopyKey>;

const RISK_STATUS: Record<string, LocationViewCopyKey> = { available: "riskAvailable", no_match: "riskNoMatch", no_coverage: "riskNoCoverage", unavailable: "riskUnavailable", unknown: "riskUnknown" };
const RISK_REASON: Record<string, LocationViewCopyKey> = {
  risk_facilities_source_unavailable: "riskReasonSourceUnavailable",
  risk_facilities_coverage_not_preserved: "riskReasonCoverageNotPreserved",
  successful_query: "riskReasonSuccess",
  property_identity_mismatch: "riskReasonIdentityMismatch",
};

export function LocationView() {
  const workspace = useWorkspace();
  const { copyFrom, locale } = useExperienceLocale();
  const copy = (key: LocationViewCopyKey, values?: Record<string, string | number>) => copyFrom(locationViewCopy, key, values);
  const unknown = copy("unknownNotRetrieved");
  const latestWorkspace = useRef(workspace);
  latestWorkspace.current = workspace;
  const persistence = useRef({ route: 0, transit: 0, mounted: true });
  const heading = useRef<HTMLHeadingElement>(null);
  const [locationConfirmed, setLocationConfirmed] = useState(false);
  // Case whose location was confirmed in this view; only that confirmation may acquire demographics.
  const [confirmedCaseId, setConfirmedCaseId] = useState<string | null>(null);
  // A successful explicit confirmation refreshes Nearby once for the accepted coordinates; reopening never does.
  const [refreshNearby, setRefreshNearby] = useState(false);
  const nearbyRefreshStarted = useCallback(() => setRefreshNearby(false), []);
  useEffect(() => {
    persistence.current.mounted = true;
    return () => { persistence.current.mounted = false; persistence.current.route++; persistence.current.transit++; };
  }, []);
  // Arriving from a removed control (e.g. Home start) leaves focus on <body>; land it on the task heading.
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => { if (document.activeElement === document.body) heading.current?.focus({ preventScroll: true }); });
    return () => window.cancelAnimationFrame(frame);
  }, []);
  const snapshot = workspace.location;
  const savedDemographics = snapshot.villageDemographics?.demographics ?? snapshot.insight?.demographics;
  const demographicsSource = savedDemographics?.status === "available" ? savedDemographics : undefined;
  const handoff = buildLocationOverviewHandoff(workspace);
  const coordinates = snapshot.property.coordinates;
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const locationState = workspace.evidence.location.usability
    ? resolveCommercialState("evidence", workspace.evidence.location.usability)
    : resolveCommercialState("query", workspace.evidence.location.query);
  const readiness = resolveCommercialState("readiness", handoff.commuteReadiness);
  const anchor = workspace.identity.state === "confirmed" ? workspace.identity.anchor : undefined;
  // An address-only case was never located; "changed / re-confirm" copy would be untrue for it.
  const neverLocated = workspace.identity.state === "unconfirmed" && !workspace.identity.anchor;
  const reconfirmation = identityConfirmationKind(workspace.identity) === "reconfirmation";
  const identityExpectation = anchor?.coordinates ? {
    journeyAnchorId: anchor.journey_anchor_id,
    normalizedAddress: anchor.normalized_address,
    coordinates: anchor.coordinates,
    snapshotVersion: workspace.storageVersion,
  } : undefined;

  async function persistRoute(evidence: CommuteRouteEvidence | null) {
    const revision = ++persistence.current.route;
    if (identityExpectation) await updateSavedCaseLocationEvidence(workspace.caseId, { commuteRoute: evidence }, identityExpectation,
      () => persistence.current.mounted && persistence.current.route === revision && latestWorkspace.current.caseId === workspace.caseId && latestWorkspace.current.identity.state === "confirmed");
  }

  async function persistTransit(result: CommuteAddressLookupResult | null) {
    const revision = ++persistence.current.transit;
    if (identityExpectation) await updateSavedCaseLocationEvidence(workspace.caseId, { commuteTransit: result }, identityExpectation,
      () => persistence.current.mounted && persistence.current.transit === revision && latestWorkspace.current.caseId === workspace.caseId && latestWorkspace.current.identity.state === "confirmed");
  }

  return <div className="workspace-view" data-testid="commercial-location-workspace">
    <header className="workspace-view__heading">
      <p className="text-meta">{copy("eyebrow")}</p>
      <h1 ref={heading} tabIndex={-1} className="text-page">{copy("title")}</h1>
      <p className="text-body">{copy("intro")}</p>
    </header>

    <div role="status" data-testid="location-confirmation-status">{locationConfirmed && !neverLocated && <Message variant="success">{copyFrom(locationConfirmationCopy, "confirmed")}</Message>}</div>
    {anchor && workspace.evidence.market.query === "not_started" && <div data-testid="build-preview-pack"><Message variant="information" action={<Link prefetch={false} className="ds-button ds-button--primary" href={`/cases/${encodeURIComponent(workspace.caseId)}/market`}>{copyFrom(homeStartCopy, "buildPack")}</Link>}>{copyFrom(homeStartCopy, "buildPackHint")}</Message></div>}
    {anchor && !hasCompleteAdministrativeArea(anchor) && <div data-testid="location-administrative-incomplete"><Message variant="information">{copyFrom(locationConfirmationCopy, "adminIncomplete")}</Message><AdministrativeAreaRepairPanel key={`${workspace.caseId}:${workspace.storageVersion}`} /></div>}

    <SummaryStrip label={copy("statusStrip")}>
      <MetricItem label={copy("metricProperty")} value={<StatusLabel semanticRole={identity.role}>{identity.label[locale]}</StatusLabel>} />
      <MetricItem label={copy("metricNearby")} value={<StatusLabel semanticRole={locationState.role}>{locationState.label[locale]}</StatusLabel>} note={copy("metricNearbyNote")} />
      <MetricItem label={copy("metricCommute")} value={<StatusLabel semanticRole={readiness.role}>{readiness.label[locale]}</StatusLabel>} />
    </SummaryStrip>

    <div className="commercial-location-grid">
      <div className="min-w-0">    {handoff.mapReady && coordinates ? <MapFrame
      title={copy("mapTitle")}
      description={snapshot.property.normalizedAddress}
      attribution={copy("mapAttribution")}
      detail={<span>{copy("mapChecked", { date: snapshot.property.checkedAt ?? copy("notProvided") })}</span>}
    >
      <ExplicitMap key={`${workspace.caseId}:${coordinates.latitude}:${coordinates.longitude}`} kind="location"><GeoMap center={{ lat: coordinates.latitude, lng: coordinates.longitude }} zoom={16} categories={[]} centerLabel={snapshot.property.normalizedAddress} radiusMeters={snapshot.insight?.radius_m ?? 800} scrollWheelZoomEnabled={false} /></ExplicitMap>
    </MapFrame> : neverLocated ? <div data-testid="location-not-yet-confirmed" className="space-y-3"><Message variant="information" title={copyFrom(homeStartCopy, "locationPendingTitle")}>
      {copyFrom(homeStartCopy, "locationPending")}
    </Message><LocationConfirmationPanel key={JSON.stringify([workspace.caseId, workspace.storageVersion, workspace.displayAddress])} onConfirmed={() => { setLocationConfirmed(true); setConfirmedCaseId(workspace.caseId); setRefreshNearby(true); }} /></div> : <Message variant="warning" title={copyFrom(identityConfirmationCopy, reconfirmation ? "reconfirmationTitle" : "pendingTitle")}>
      {copyFrom(identityConfirmationCopy, reconfirmation ? "reconfirmationLocation" : "pendingLocation")}
    </Message>}

</div>
      <div className="min-w-0">    <Section title={copy("commuteTitle")} description={copy("commuteDescription")}>
      <div data-evidence-key="commute" className="space-y-3">
      {handoff.selectedRoute && snapshot.transitContext?.status !== "resolved" && <Message variant="warning">{copy("routeOnlyTransitUnavailable")}</Message>}
      {handoff.mapReady && coordinates ? <CommuteEvidencePanel
        address={snapshot.property.normalizedAddress}
        locationResult={snapshot.insight ?? null}
        origin={{ latitude: coordinates.latitude, longitude: coordinates.longitude }}
        routeEvidence={snapshot.routeEvidence}
        transitResult={snapshot.transitContext}
        onRouteStatusChange={() => undefined}
        onRouteEvidence={persistRoute}
        onTransitStatusChange={() => undefined}
        onTransitResult={persistTransit}
      /> : <Message variant="warning">{copyFrom(identityConfirmationCopy, reconfirmation ? "reconfirmationRoute" : "pendingRoute")}</Message>}
      </div>
    </Section>

</div>
    </div>

    <NearbyFacilitiesPanel key={JSON.stringify([workspace.caseId, workspace.identity.state, anchor?.journey_anchor_id, coordinates])} autoAcquire={refreshNearby} onAutoAcquire={nearbyRefreshStarted} />

    {((!snapshot.nearbyFacilities && (snapshot.insight || snapshot.poiSummary)) || snapshot.insight?.risk_facility_evidence) && <Section title={copy("legacyTitle")} description={copy("legacyDescription")}>
      <div data-evidence-key="location" className="space-y-3">
      {!snapshot.nearbyFacilities && <>{snapshot.poiSummary ? <SummaryStrip label={copy("poiSummaryLabel")} className="location-poi-summary">
        {(Object.keys(POI_LABELS) as Array<keyof typeof POI_LABELS>).map((key) => <MetricItem key={key} label={copy(POI_LABELS[key])} value={snapshot.poiSummary?.[key] ?? unknown} />)}
      </SummaryStrip> : <Message variant="inline" title={copy("poiSummaryMissingTitle")}>{copy("poiSummaryMissing")}</Message>}
      <div data-testid="poi-summary" className="sr-only">{snapshot.poiSummary ? (Object.keys(POI_LABELS) as Array<keyof typeof POI_LABELS>).map((key) => copy("poiSummaryItem", { label: copy(POI_LABELS[key]), value: snapshot.poiSummary?.[key] ?? unknown })).join(copy("listSeparator")) : copy("poiSummaryMissingTitle")}</div>
      {snapshot.insight && (!Array.isArray(snapshot.insight.nearest_pois) || snapshot.insight.nearest_pois.length === 0) && <Message variant="information" title={copyFrom(nearbyFacilitiesCopy, "legacyTitle")}>{copyFrom(nearbyFacilitiesCopy, "legacySummary")}</Message>}
      </>}
      {snapshot.insight?.risk_facility_evidence && <Panel variant="plain" data-testid="risk-facility-source">
        <h3 className="text-subsection">{copy("riskTitle")}</h3>
        <p className="text-body">{copy(RISK_STATUS[snapshot.insight.risk_facility_evidence.status] ?? "riskUnknown")}</p>
        {/* A saved source is a provider identifier and is shown as stored. */}
        <p className="text-helper">{snapshot.insight.risk_facility_evidence.source ?? copy("riskSourceMissing")} · {snapshot.insight.risk_facility_evidence.checked_at?.match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? copy("notProvided")}</p>
        {/* The saved limitation is kept verbatim in zh-TW, the language it is recorded in; other locales get the localized equivalent. */}
        <p className="text-helper">{copy("riskReasonLimitation", { reason: copy(RISK_REASON[snapshot.insight.risk_facility_evidence.reason ?? ""] ?? "riskReasonOther"), limitation: locale === "zh-TW" && snapshot.insight.risk_facility_evidence.limitation ? snapshot.insight.risk_facility_evidence.limitation : copy("riskLimitation") })}</p>
      </Panel>}
      </div>
    </Section>}

    <VillageDemographicsPanel key={JSON.stringify(["demographics", workspace.caseId, workspace.identity.state, anchor?.journey_anchor_id, coordinates])} autoAcquire={confirmedCaseId === workspace.caseId} onAutoAcquire={() => setConfirmedCaseId(null)} />

    <Section title={copy("limitsTitle")}>
      <div className="grid gap-3 md:grid-cols-2">
        <Panel variant="plain">
          <h2 className="text-subsection">{copy("currentLimits")}</h2>
          <ul className="mt-2 space-y-1 text-dense">
            {handoff.unresolvedKeys.length ? handoff.unresolvedKeys.map((key) => <li key={key}>• {key === "identityPending" ? copyFrom(identityConfirmationCopy, "pendingTitle") : key === "identityReconfirmation" ? copyFrom(identityConfirmationCopy, "reconfirmationTitle") : copy(key)}</li>) : <li>• {copy("noLimits")}</li>}
            {/* Saved analysis warnings are backend text recorded in zh-TW only; other locales get a localized count, never mixed text. */}
            {locale === "zh-TW"
              ? snapshot.insight?.data_quality?.warnings?.map((item) => <li key={item}>• {item}</li>)
              : snapshot.insight?.data_quality?.warnings?.length ? <li>• {copy("savedWarnings", { count: snapshot.insight.data_quality.warnings.length })}</li> : null}
          </ul>
        </Panel>
        <Panel variant="plain">
          <h2 className="text-subsection">{copy("nextTitle")}</h2>
          <ul className="mt-2 space-y-1 text-dense">
            <li>• {copy("next1")}</li>
            <li>• {copy("next2")}</li>
            <li>• {copy("next3")}</li>
          </ul>
        </Panel>
      </div>
    </Section>

    <EvidenceSection>
      <DetailsDisclosure summary={copy("sourcesTitle")}>
        <dl className="grid gap-3 text-dense sm:grid-cols-2">
          <SourceDetail label={copy("metricProperty")} value={copy("sourcePropertyValue", { sources: friendlySources(snapshot.property.sourceIds, copy), date: snapshot.property.checkedAt ?? copy("notProvided") })} />
          {coordinates && <SourceDetail label={copyFrom(locationConfirmationCopy, "coordinates")} value={`${coordinates.latitude.toFixed(6)}, ${coordinates.longitude.toFixed(6)}`} />}
          <SourceDetail label={copy("adminLocation")} value={`${snapshot.property.village.name ?? copy("villageUnconfirmed")}${snapshot.insight?.village_resolution?.source_vintage ? copy("boundaryVintage", { vintage: snapshot.insight.village_resolution.source_vintage }) : ""}`} />
          <SourceDetail label={copy("routeSource")} value={handoff.identityState !== "confirmed" ? copy("routeNeedsReconfirm") : snapshot.routeEvidence ? copy("sourceDated", { source: snapshot.routeEvidence.source === "google_routes" ? "Google Routes" : copy("routeSimulated"), date: snapshot.routeEvidence.checked_at }) : copy("notRetrieved")} />
          <SourceDetail label={copy("transitSource")} value={snapshot.transitContext ? copy("sourceDated", { source: "TDX", date: snapshot.transitContext.source_updated_at ?? snapshot.transitContext.snapshot_generated_at ?? copy("dateNotProvided") }) : copy("notRetrieved")} />
          <SourceDetail label={copy("demographicsSource")} value={demographicsSource ? copyFrom(villageDemographicsCopy, "sourceSummary", { month: formatDemographicsMonth(demographicsSource.statistic_yyymm, locale) ?? copyFrom(villageDemographicsCopy, "insufficient") }) : copyFrom(villageDemographicsCopy, "sourceSummaryNone")} />
        </dl>
        {handoff.selectedRoute && <p className="mt-3 text-meta">{copy("selectedRoute", { destination: handoff.selectedRoute.destination, mode: copy(MODE_LABELS[handoff.selectedRoute.mode]), distance: formatLocationDistance(handoff.selectedRoute.distanceM, locale), duration: formatLocationDuration(handoff.selectedRoute.durationMinutes, locale) })}</p>}
      </DetailsDisclosure>
    </EvidenceSection>
  </div>;
}

function friendlySources(sourceIds: string[], copy: (key: LocationViewCopyKey) => string): string {
  if (!sourceIds.length) return copy("sourceNone");
  return sourceIds.map((source) => copy(source === "google_geocoding" ? "sourceGoogle" : source === "tgos_geocoding" ? "sourceTgos" : source === "nlsc_village_boundary" ? "sourceNlsc" : "sourceUser")).join(copy("sourceSeparator"));
}

function SourceDetail({ label, value }: { label: string; value: string }) {
  return <div><dt className="font-bold text-slate-800">{label}</dt><dd className="mt-1 break-words text-slate-600">{value}</dd></div>;
}
