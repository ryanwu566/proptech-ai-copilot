"use client";

import { useEffect, useRef, useState } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { Section } from "@/components/design-system/section";
import { DemographicsInsightCard } from "@/components/demographics-insight-card";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { api } from "@/lib/api";
import { updateSavedCaseLocationEvidence } from "@/lib/case-storage";
import { captureVillageDemographics, shareVillageDemographicsAcquisition, type VillageDemographicsEvidence } from "@/lib/workspace/village-demographics";
import { villageDemographicsCopy, type VillageDemographicsCopyKey } from "@/lib/workspace/village-demographics-copy";

/**
 * Village demographics for the confirmed coordinate only. Acquired on an explicit action — a fresh
 * location confirmation in this view (`autoAcquire`, consumed once via `onAutoAcquire`) or the refresh
 * button — and otherwise read from the saved case. Reopening, Compare, Report and locale switches never acquire.
 */
export function VillageDemographicsPanel({ autoAcquire = false, onAutoAcquire }: { autoAcquire?: boolean; onAutoAcquire?: () => void }) {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const copy = (key: VillageDemographicsCopyKey) => copyFrom(villageDemographicsCopy, key);
  const anchor = workspace.identity.state === "confirmed" ? workspace.identity.anchor : undefined;
  const coordinates = anchor?.coordinates;
  const expected = anchor && coordinates ? { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates, snapshotVersion: workspace.storageVersion } : undefined;
  const saved = coordinates ? workspace.location.villageDemographics : undefined;
  const legacy = coordinates ? workspace.location.insight : undefined;
  const [status, setStatus] = useState<"idle" | "loading" | "failed" | "unsaved" | "saving">(() => autoAcquire && expected && !saved ? "loading" : "idle");
  const [acquired, setAcquired] = useState<VillageDemographicsEvidence>();
  const generation = useRef(0);
  const autoStarted = useRef(false);
  const mounted = useRef(true);
  const latest = useRef({ caseId: workspace.caseId, anchorId: anchor?.journey_anchor_id, coordinates });
  latest.current = { caseId: workspace.caseId, anchorId: anchor?.journey_anchor_id, coordinates };
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; generation.current++; }; }, []);

  /** The result still belongs to what is on screen: same case, same anchor, same coordinate, latest request. */
  function current(run: number, caseId: string, anchorId: string, origin: { latitude: number; longitude: number }) {
    const now = latest.current;
    return mounted.current && run === generation.current && now.caseId === caseId && now.anchorId === anchorId
      && now.coordinates?.latitude === origin.latitude && now.coordinates?.longitude === origin.longitude;
  }

  async function acquire() {
    if (!expected || !coordinates || !anchor) return;
    const run = ++generation.current;
    const caseId = workspace.caseId;
    const anchorId = anchor.journey_anchor_id;
    const origin = { latitude: coordinates.latitude, longitude: coordinates.longitude };
    setStatus("loading");
    try {
      const result = await shareVillageDemographicsAcquisition(JSON.stringify([caseId, anchorId, origin]), async () => {
        const evidence = captureVillageDemographics(await api.locationDemographics(origin.latitude, origin.longitude), origin);
        const persisted = await updateSavedCaseLocationEvidence(caseId, { villageDemographics: evidence }, expected);
        return { evidence, persisted };
      });
      if (!current(run, caseId, anchorId, origin)) return;
      setAcquired(result.evidence);
      setStatus(result.persisted ? "idle" : "unsaved");
    } catch {
      if (current(run, caseId, anchorId, origin)) setStatus("failed");
    }
  }

  async function save() {
    if (!acquired || !expected || !anchor) return;
    const run = ++generation.current;
    const caseId = workspace.caseId;
    const anchorId = anchor.journey_anchor_id;
    const origin = expected.coordinates;
    setStatus("saving");
    const persisted = await updateSavedCaseLocationEvidence(caseId, { villageDemographics: acquired }, expected).catch(() => false);
    if (current(run, caseId, anchorId, origin)) setStatus(persisted ? "idle" : "unsaved");
  }

  // A fresh confirmation in this view is the explicit location action; it acquires once for that identity.
  // The confirmation can land before or after this panel remounts for the new anchor, so react to the
  // request rather than to mount. Strict Mode re-runs share one in-flight request for the same identity.
  const anchorId = anchor?.journey_anchor_id;
  useEffect(() => {
    if (!autoAcquire || !expected || saved || autoStarted.current) return;
    autoStarted.current = true;
    onAutoAcquire?.();
    void acquire();
    return () => { autoStarted.current = false; };
    // Deps are deliberate: acquire reads the current render; re-run only on a new request or anchor.
  }, [autoAcquire, anchorId]);

  const evidence = acquired ?? saved;
  const busy = status === "loading" || status === "saving";
  const action = expected ? <div className="space-y-3">
    <CommercialButton size="touch" variant="secondary" className="max-w-full whitespace-normal" data-testid="demographics-refresh"
      disabled={busy || status === "unsaved"} loading={status === "loading"} loadingLabel={copy("loading")} onClick={() => void acquire()}>
      {copy(evidence ? "refresh" : "explore")}
    </CommercialButton>
    <div role="status" aria-live="polite" className="space-y-2">
      {status === "failed" && evidence && <Message variant="warning">{copy("failedKept")}</Message>}
      {(status === "unsaved" || status === "saving") && <Message variant="warning" action={<CommercialButton size="touch" variant="secondary" loading={status === "saving"} loadingLabel={copy("saving")} onClick={() => void save()}>{copy("save")}</CommercialButton>}>{copy("unsaved")}</Message>}
      {status === "idle" && acquired && <p className="text-helper">{copy("saved")}</p>}
    </div>
  </div> : undefined;

  return <Section title={copy("sectionTitle")} description={copy("sectionIntro")}>
    <div data-testid="village-demographics" data-evidence-key="demographics" className="min-w-0">
      {!expected ? <DemographicsInsightCard pending="confirm_first" />
        : status === "loading" ? <DemographicsInsightCard pending="loading" action={action} />
        : evidence ? <DemographicsInsightCard village={evidence.village} demographics={evidence.demographics} checkedAt={evidence.checkedAt} action={action} />
        // A failed explicit request with nothing saved is a coherent "unavailable" state, not an absent section.
        : status === "failed" ? <DemographicsInsightCard village={undefined} demographics={undefined} action={action} />
        : legacy?.village_resolution || legacy?.demographics ? <DemographicsInsightCard village={legacy.village_resolution} demographics={legacy.demographics} action={action} />
        : <DemographicsInsightCard pending="not_run" action={action} />}
    </div>
  </Section>;
}
