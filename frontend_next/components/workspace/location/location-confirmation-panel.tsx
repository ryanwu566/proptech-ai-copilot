"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { CommercialButton } from "@/components/design-system/button";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
import { Panel } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { api } from "@/lib/api";
import { confirmSavedCaseIdentity, type ConfirmIdentityResult } from "@/lib/case-storage";
import { acquireLocationResolution, buildConfirmedLocationAnchor, type LocationCandidateResult, type LocationCandidate, type LocationCandidateBlock } from "@/lib/workspace/location-confirmation";
import { locationStartHandoff } from "@/lib/workspace/location-start-handoff";
import { locationConfirmationCopy, type LocationConfirmationCopyKey } from "@/lib/workspace/location-confirmation-copy";

type Failure = LocationCandidateBlock | Extract<ConfirmIdentityResult, { status: "blocked" }>["reason"];
type Step =
  | { kind: "idle" }
  | { kind: "finding" }
  | { kind: "candidate"; candidate: LocationCandidate; confirming: boolean }
  | { kind: "failed"; reason: Failure; candidate?: LocationCandidate };

const CandidateMap = dynamic(() => import("@/components/map/geo-map"), { ssr: false });

function candidateStep(resolution: LocationCandidateResult): Step {
  return resolution.kind === "candidate" ? { kind: "candidate", candidate: resolution.candidate, confirming: false } : { kind: "failed", reason: resolution.reason };
}

/** Adopt the explicit Home lookup, or look up on an explicit in-case retry. Only Confirm saves identity. */
export function LocationConfirmationPanel({ onConfirmed }: { onConfirmed: () => void }) {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const copy = (key: LocationConfirmationCopyKey) => copyFrom(locationConfirmationCopy, key);
  const [step, setStep] = useState<Step>(() => locationStartHandoff.read(workspace.caseId, workspace.displayAddress) ? { kind: "finding" } : { kind: "idle" });
  const busy = useRef(step.kind === "finding");
  const request = useRef<AbortController | null>(null);
  const result = useRef<HTMLDivElement>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if (step.kind === "candidate" && !step.confirming) result.current?.focus(); }, [step]);
  useEffect(() => {
    const pending = locationStartHandoff.read(workspace.caseId, workspace.displayAddress);
    if (!pending) return;
    let active = true;
    pending.then((resolution) => {
      if (active) { busy.current = false; setStep(candidateStep(resolution)); }
    });
    return () => { active = false; };
  }, [workspace.caseId, workspace.displayAddress]);

  async function find() {
    if (busy.current) return;
    busy.current = true;
    locationStartHandoff.discard(workspace.caseId);
    setStep({ kind: "finding" });
    const controller = new AbortController();
    request.current = controller;
    try {
      const resolution = await acquireLocationResolution(workspace.displayAddress, (signal) => api.locationResolve(workspace.displayAddress, signal), controller.signal);
      if (!controller.signal.aborted) setStep(candidateStep(resolution));
    } finally {
      busy.current = false;
    }
  }

  async function confirm(candidate: LocationCandidate) {
    if (busy.current || !workspace.storageVersion) return;
    busy.current = true;
    setStep({ kind: "candidate", candidate, confirming: true });
    const anchor = buildConfirmedLocationAnchor(candidate, { now: () => new Date().toISOString(), idFactory: () => crypto.randomUUID() });
    const outcome: ConfirmIdentityResult = anchor
      ? await confirmSavedCaseIdentity(workspace.caseId, anchor, workspace.storageVersion).catch(() => ({ status: "blocked", reason: "write_failed" }) as const)
      : { status: "blocked", reason: "invalid_anchor" };
    busy.current = false;
    if (outcome.status === "confirmed") { locationStartHandoff.discard(workspace.caseId); onConfirmed(); }
    else setStep({ kind: "failed", reason: outcome.reason, candidate });
  }

  const sourceLabel = (source: LocationCandidate["source"]) => copy(source === "tgos" ? "sourceTgos" : "sourceGoogle");
  return <Panel className="space-y-3" data-testid="location-confirmation">
    {(step.kind === "idle" || step.kind === "finding") && <div className="space-y-2">
      <h2 className="text-subsection">{copy(step.kind === "finding" ? "finding" : "find")}</h2>
      <p className="break-words text-body">{workspace.displayAddress}</p>
      <CommercialButton size="touch" loading={step.kind === "finding"} loadingLabel={copy("finding")} onClick={() => void find()} data-testid="location-find">{copy("find")}</CommercialButton>
      <p className="text-helper">{copy("findNote")}</p>
    </div>}
    {step.kind === "candidate" && <div ref={result} tabIndex={-1} className="space-y-3" data-testid="location-candidate" aria-labelledby="location-candidate-title">
      <h2 id="location-candidate-title" className="text-subsection">{copy("candidateTitle")}</h2>
      <p className="break-words text-body font-semibold">{step.candidate.interpretedAddress}</p>
      <div role="region" aria-label={copy("mapContext")} data-testid="location-candidate-map" className="h-56 overflow-hidden rounded-xl [&_.leaflet-container]:!min-h-0">
        <CandidateMap center={{ lat: step.candidate.latitude, lng: step.candidate.longitude }} zoom={16} categories={[]} centerLabel={step.candidate.interpretedAddress} radiusMeters={0} scrollWheelZoomEnabled={false} />
      </div>
      <p className="text-helper">{copy("confirmNote")}</p>
      <div className="flex flex-wrap gap-3">
        <CommercialButton size="touch" loading={step.confirming} loadingLabel={copy("confirming")} onClick={() => void confirm(step.candidate)} data-testid="location-confirm">{copy("confirm")}</CommercialButton>
        <CommercialButton size="touch" variant="secondary" disabled={step.confirming} onClick={() => void find()}>{copy("reject")}</CommercialButton>
      </div>
      <DetailsDisclosure summary={copy("details")} data-testid="location-candidate-details" variant="compact">
        <dl className="grid gap-2 text-dense sm:grid-cols-2">
          <div><dt className="font-bold">{copy("interpreted")}</dt><dd className="break-words">{step.candidate.interpretedAddress}</dd></div>
          <div><dt className="font-bold">{copy("county")} · {copy("district")}</dt><dd>{step.candidate.county ?? copy("adminUnknown")} · {step.candidate.district ?? copy("adminUnknown")}</dd></div>
          <div><dt className="font-bold">{copy("coordinates")}</dt><dd className="font-mono">{step.candidate.latitude.toFixed(6)}, {step.candidate.longitude.toFixed(6)}</dd></div>
          <div><dt className="font-bold">{copy("source")}</dt><dd>{sourceLabel(step.candidate.source)}</dd></div>
        </dl>
      </DetailsDisclosure>
    </div>}
    {step.kind === "failed" && <Message variant="error" title={copy("failedTitle")} action={<CommercialButton size="touch" variant="secondary" onClick={() => { if (step.candidate && ["write_failed", "lock_unavailable", "storage_unavailable"].includes(step.reason)) setStep({ kind: "candidate", candidate: step.candidate, confirming: false }); else void find(); }}>{copy("retry")}</CommercialButton>}>
      <span data-testid="location-confirmation-failure" data-reason={step.reason}>{copy(step.reason)}</span>
    </Message>}
  </Panel>;
}
