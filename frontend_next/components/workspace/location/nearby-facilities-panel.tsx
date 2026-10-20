"use client";

import { useEffect, useRef, useState } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { Panel, Section } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { api } from "@/lib/api";
import { updateSavedCaseLocationEvidence } from "@/lib/case-storage";
import { captureNearbyFacilities, groupNearbyFacilities, NEARBY_CATEGORIES, NEARBY_RADIUS_M, shareNearbyAcquisition, type NearbyFacilitiesEvidence } from "@/lib/workspace/nearby-facilities";
import { nearbyFacilitiesCopy, type NearbyCopyKey } from "@/lib/workspace/nearby-facilities-copy";

export function NearbyFacilitiesPanel() {
  const workspace = useWorkspace();
  const { copyFrom, formatDate, formatNumber } = useExperienceLocale();
  const copy = (key: NearbyCopyKey, values?: Record<string, string | number>) => copyFrom(nearbyFacilitiesCopy, key, values);
  const [status, setStatus] = useState<"idle" | "loading" | "failed" | "unsaved" | "saving">("idle");
  const [acquired, setAcquired] = useState<NearbyFacilitiesEvidence>();
  const busy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const anchor = workspace.identity.state === "confirmed" ? workspace.identity.anchor : undefined;
  const coordinates = anchor?.coordinates;
  const evidence = coordinates ? acquired ?? workspace.location.nearbyFacilities : undefined;
  const groups = evidence ? groupNearbyFacilities(evidence) : [];
  const expected = anchor && coordinates ? { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates, snapshotVersion: workspace.storageVersion } : undefined;

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
      if (mounted.current) { setAcquired(result.evidence); setStatus(result.saved ? "idle" : "unsaved"); }
    } catch { if (mounted.current) setStatus("failed"); }
    finally { busy.current = false; }
  }

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
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        {groups.map((group) => <Panel key={group.category} variant="plain" className="min-w-0" data-testid={`nearby-group-${group.category}`}>
          <h3 className="text-subsection">{copy(group.category)}</h3>
          <ul className="mt-3 space-y-3">
            {group.places.map((place) => <li key={place.id} className="min-w-0 border-t border-stone-200 pt-3">
              <p className="text-body font-semibold">{place.name}</p>
              <p className="text-helper">{copy("distance", { distance: formatNumber(place.distanceM) })}</p>
            </li>)}
          </ul>
        </Panel>)}
      </div>
    </div>
  </Section>;
}
