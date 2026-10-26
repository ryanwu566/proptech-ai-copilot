"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { Panel, Section } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { ExplicitMap } from "@/components/map/explicit-map";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { api } from "@/lib/api";
import { updateSavedCaseLocationEvidence } from "@/lib/case-storage";
import { captureNearbyFacilities, groupNearbyFacilities, NEARBY_CATEGORIES, NEARBY_RADIUS_M, shareNearbyAcquisition, type NearbyFacilitiesEvidence } from "@/lib/workspace/nearby-facilities";
import { nearbyFacilitiesCopy, type NearbyCopyKey } from "@/lib/workspace/nearby-facilities-copy";
import { NEARBY_POI_KINDS, NEARBY_POI_STYLES, NEARBY_PROPERTY_STYLE, nearbyPoiGroup, nearbyPoiIconSvg, type NearbyPoiGroup, type NearbyPoiKind, type NearbyPoiStyle } from "@/lib/workspace/nearby-poi-category";

const GeoMap = dynamic(() => import("@/components/map/geo-map"), { ssr: false });

const KIND_COPY: Record<NearbyPoiKind, NearbyCopyKey> = { rail: "kindRail", bus: "kindBus", transit: "kindTransit", education: "education", medical: "healthcare", park: "parks", shopping: "shopping", food: "food", other: "other" };

function Swatch({ style, shape }: { style: NearbyPoiStyle; shape?: "pin" }) {
  // Static, trusted SVG from the palette module; no provider text is interpolated.
  return <span className="inline-flex shrink-0" aria-hidden="true" dangerouslySetInnerHTML={{ __html: nearbyPoiIconSvg(style, shape ? 22 : 20, shape === "pin" ? "pin" : "circle") }} />;
}

/**
 * Nearby is acquired only on explicit intent: the Explore/Refresh button, or `autoAcquire` right after
 * the buyer confirms a location. Reopening, filtering, selecting and locale changes read saved evidence only.
 */
export function NearbyFacilitiesPanel({ autoAcquire = false, onAutoAcquire }: { autoAcquire?: boolean; onAutoAcquire?: () => void } = {}) {
  const workspace = useWorkspace();
  const { copyFrom, formatDate, formatNumber } = useExperienceLocale();
  const copy = (key: NearbyCopyKey, values?: Record<string, string | number>) => copyFrom(nearbyFacilitiesCopy, key, values);
  const [status, setStatus] = useState<"idle" | "loading" | "failed" | "unsaved" | "saving">("idle");
  const [acquired, setAcquired] = useState<NearbyFacilitiesEvidence>();
  const [filter, setFilter] = useState<NearbyPoiGroup | "all">("all");
  const [selectedId, setSelectedId] = useState<string>();
  const busy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const anchor = workspace.identity.state === "confirmed" ? workspace.identity.anchor : undefined;
  const coordinates = anchor?.coordinates;
  const latitude = coordinates?.latitude;
  const longitude = coordinates?.longitude;
  // A stable center keeps the map from recentring on every filter or selection change.
  const center = useMemo(() => latitude !== undefined && longitude !== undefined ? { lat: latitude, lng: longitude } : undefined, [latitude, longitude]);
  const evidence = coordinates ? acquired ?? workspace.location.nearbyFacilities : undefined;
  const groups = evidence ? groupNearbyFacilities(evidence) : [];
  const visibleGroups = filter === "all" ? groups : groups.filter((group) => group.category === filter);
  const visiblePlaces = visibleGroups.flatMap((group) => group.places);
  const presentKinds = NEARBY_POI_KINDS.filter((kind) => evidence?.places.some((place) => place.kind === kind));
  const expected = anchor && coordinates ? { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates, snapshotVersion: workspace.storageVersion } : undefined;
  const kindLabel = (kind: NearbyPoiKind) => copy(KIND_COPY[kind]);

  async function explore() {
    if (busy.current || !expected || !coordinates) return;
    busy.current = true;
    setStatus("loading");
    try {
      const key = JSON.stringify([workspace.caseId, expected.journeyAnchorId, coordinates]);
      const result = await shareNearbyAcquisition(key, async () => {
        const origin = { lat: coordinates.latitude, lng: coordinates.longitude };
        const response = await api.mapNearby(origin, [...NEARBY_CATEGORIES], NEARBY_RADIUS_M);
        const next = captureNearbyFacilities(response, origin);
        const saved = await updateSavedCaseLocationEvidence(workspace.caseId, { nearbyFacilities: next }, expected);
        return { evidence: next, saved };
      });
      if (mounted.current) { setAcquired(result.evidence); setSelectedId(undefined); setStatus(result.saved ? "idle" : "unsaved"); }
    } catch { if (mounted.current) setStatus("failed"); }
    finally { busy.current = false; }
  }

  // The panel remounts per confirmed anchor, so this runs once for the coordinates just accepted.
  const exploreRef = useRef(explore);
  exploreRef.current = explore;
  const ready = Boolean(expected);
  useEffect(() => {
    if (!autoAcquire || !ready) return;
    onAutoAcquire?.();
    void exploreRef.current();
  }, [autoAcquire, ready, onAutoAcquire]);

  async function save() {
    if (busy.current || !acquired || !expected) return;
    busy.current = true;
    setStatus("saving");
    try {
      const saved = await updateSavedCaseLocationEvidence(workspace.caseId, { nearbyFacilities: acquired }, expected);
      if (mounted.current) setStatus(saved ? "idle" : "unsaved");
    } catch { if (mounted.current) setStatus("unsaved"); }
    finally { busy.current = false; }
  }

  function choose(next: NearbyPoiGroup | "all") {
    setFilter(next);
    const selected = evidence?.places.find((place) => place.id === selectedId);
    if (selected && next !== "all" && nearbyPoiGroup(selected.kind) !== next) setSelectedId(undefined);
  }

  return <Section title={copy("title")} description={copy("intro")}>
    <div data-testid="nearby-facilities" className="min-w-0 space-y-4 [overflow-wrap:anywhere]">
      <p className="text-helper">{copy("limits")}</p>
      {!expected && <Message variant="information">{copy("confirmFirst")}</Message>}
      <CommercialButton size="touch" className="max-w-full whitespace-normal" disabled={!expected || status === "unsaved" || status === "saving"} loading={status === "loading"} loadingLabel={copy("loading")} onClick={explore}>
        {copy(evidence ? "refresh" : "explore")}
      </CommercialButton>
      <div role="status" aria-live="polite" className="space-y-3">
        {status === "failed" && <Message variant="warning">{copy("failed")}</Message>}
        {(status === "unsaved" || status === "saving") && <Message variant="warning" action={<CommercialButton size="touch" variant="secondary" loading={status === "saving"} loadingLabel={copy("saving")} onClick={save}>{copy("save")}</CommercialButton>}>{copy("unsaved")}</Message>}
        {evidence && <>
          <p className="text-helper">{copy("scope", { radius: formatNumber(evidence.radiusM) })}</p>
          <p className="text-helper">{copy("checked", { date: formatDate(evidence.checkedAt) })}</p>
          {status !== "unsaved" && status !== "saving" && <p className="text-helper">{copy("saved")}</p>}
          {evidence.partial && <Message variant="information">{copy("partial")}</Message>}
          {!groups.length && <Message variant="information">{copy("empty")}</Message>}
        </>}
      </div>
      {evidence && center && groups.length > 0 && <>
        <div role="group" aria-label={copy("filter")} data-testid="nearby-filter" className="flex min-w-0 flex-wrap gap-2">
          {(["all", ...groups.map((group) => group.category)] as const).map((key) => <button key={key} type="button" aria-pressed={filter === key} data-filter={key}
            className={`min-h-11 max-w-full rounded-full border px-4 text-dense font-semibold transition-colors ${filter === key ? "border-slate-900 bg-slate-900 text-white" : "border-stone-300 bg-white text-slate-700 hover:border-slate-500"}`}
            onClick={() => choose(key)}>
            {key === "all" ? copy("filterAll") : `${copy(key)} · ${formatNumber(groups.find((group) => group.category === key)!.places.length)}`}
          </button>)}
        </div>
        <p className="text-helper" data-testid="nearby-filter-count">{copy("filterCount", { shown: formatNumber(visiblePlaces.length), total: formatNumber(evidence.places.length) })}</p>
        <div className="min-w-0 space-y-4">
          <div className="min-w-0 space-y-3">
            <ul aria-label={copy("legend")} data-testid="nearby-legend" className="flex min-w-0 flex-wrap gap-x-4 gap-y-2 text-dense">
              <li className="flex min-w-0 items-center gap-2" data-kind="property"><Swatch style={NEARBY_PROPERTY_STYLE} shape="pin" />{copy("property")}</li>
              {presentKinds.map((kind) => <li key={kind} className="flex min-w-0 items-center gap-2" data-kind={kind}><Swatch style={NEARBY_POI_STYLES[kind]} />{kindLabel(kind)}</li>)}
            </ul>
            <div role="region" aria-label={copy("mapTitle")} data-testid="nearby-map" className="min-w-0 overflow-hidden rounded-xl border border-stone-200 [&_.leaflet-container]:!min-h-0">
              <ExplicitMap kind="nearby" open={selectedId !== undefined}>
                <div className="h-72 sm:h-96">
                  <GeoMap center={center} zoom={15} categories={[]} centerLabel={copy("property")} radiusMeters={evidence.radiusM} scrollWheelZoomEnabled={false}
                    pois={visiblePlaces.map((place) => ({ id: place.id, name: place.name, lat: place.lat, lng: place.lng, kind: place.kind, label: kindLabel(place.kind) }))}
                    selectedPoiId={selectedId} onSelectPoi={setSelectedId} />
                </div>
              </ExplicitMap>
            </div>
          </div>
          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            {visibleGroups.map((group) => <Panel key={group.category} variant="plain" className="min-w-0" data-testid={`nearby-group-${group.category}`}>
              <h3 className="text-subsection">{copy(group.category)}</h3>
              <ul className="mt-3 space-y-3">
                {group.places.map((place) => {
                  const selected = place.id === selectedId;
                  return <li key={place.id} data-kind={place.kind} data-selected={selected} className={`min-w-0 border-t pt-3 ${selected ? "border-slate-900" : "border-stone-200"}`}>
                    <div className="flex min-w-0 items-start gap-2">
                      <Swatch style={NEARBY_POI_STYLES[place.kind]} />
                      <div className="min-w-0 flex-1">
                        <p className="text-body font-semibold">{place.name}</p>
                        <p className="text-helper">{kindLabel(place.kind)} · {copy("distance", { distance: formatNumber(place.distanceM) })}</p>
                      </div>
                    </div>
                    <button type="button" aria-pressed={selected} className="mt-1 min-h-11 max-w-full text-left text-dense font-semibold text-slate-700 underline underline-offset-4 hover:text-slate-950"
                      onClick={() => setSelectedId(selected ? undefined : place.id)}>
                      {copy(selected ? "selected" : "locate")}
                    </button>
                  </li>;
                })}
              </ul>
            </Panel>)}
            {!visibleGroups.length && <Message variant="information">{copy("filteredEmpty")}</Message>}
          </div>
        </div>
      </>}
    </div>
  </Section>;
}
