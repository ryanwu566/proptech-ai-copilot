"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { CommercialButton } from "@/components/design-system/button";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
import { Panel } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { confirmSavedCaseIdentity, type ConfirmIdentityResult } from "@/lib/case-storage";
import { buildConfirmedLocationAnchor, type LocationCandidateResult, type LocationCandidate, type LocationCandidateBlock, type RejectedLocationCandidate } from "@/lib/workspace/location-confirmation";
import { acquireCaseLocation } from "@/lib/workspace/location-acquisition";
import { locationStartHandoff } from "@/lib/workspace/location-start-handoff";
import { locationConfirmationCopy, type LocationConfirmationCopyKey } from "@/lib/workspace/location-confirmation-copy";

type Failure = LocationCandidateBlock | Extract<ConfirmIdentityResult, { status: "blocked" }>["reason"];
type Step =
  | { kind: "idle" }
  | { kind: "finding" }
  | { kind: "candidate"; candidate: LocationCandidate; confirming: boolean }
  | { kind: "choice"; candidates: LocationCandidate[] }
  | { kind: "failed"; reason: Failure; candidate?: LocationCandidate; rejected?: RejectedLocationCandidate[] };

const CandidateMap = dynamic(() => import("@/components/map/geo-map"), { ssr: false });

function candidateStep(resolution: LocationCandidateResult): Step {
  if (resolution.kind === "candidate") return { kind: "candidate", candidate: resolution.candidate, confirming: false };
  if (resolution.kind === "choice") return { kind: "choice", candidates: resolution.candidates };
  return { kind: "failed", reason: resolution.reason, rejected: resolution.rejected };
}

/** Adopt the explicit Home lookup, or look up on an explicit in-case retry. Only Confirm saves identity. */
export function LocationConfirmationPanel({ onConfirmed }: { onConfirmed: () => void }) {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const copy = (key: LocationConfirmationCopyKey) => copyFrom(locationConfirmationCopy, key);
  const [step, setStep] = useState<Step>(() => workspace.pendingLocationCandidate
    ? { kind: "candidate", candidate: workspace.pendingLocationCandidate, confirming: false }
    : locationStartHandoff.read(workspace.caseId, workspace.displayAddress) ? { kind: "finding" } : { kind: "idle" });
  const busy = useRef(step.kind === "finding");
  const request = useRef<AbortController | null>(null);
  const result = useRef<HTMLDivElement>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if ((step.kind === "candidate" && !step.confirming) || step.kind === "choice") result.current?.focus(); }, [step]);
  useEffect(() => {
    const pending = locationStartHandoff.read(workspace.caseId, workspace.displayAddress);
    if (!pending || workspace.pendingLocationCandidate) return;
    let active = true;
    pending.then((resolution) => {
      if (active) { busy.current = false; setStep(candidateStep(resolution)); }
    });
    return () => { active = false; };
  }, [workspace.caseId, workspace.displayAddress, workspace.pendingLocationCandidate]);
  useEffect(() => {
    if (!workspace.pendingLocationCandidate) return;
    busy.current = false;
    setStep({ kind: "candidate", candidate: workspace.pendingLocationCandidate, confirming: false });
  }, [workspace.pendingLocationCandidate]);

  async function find() {
    if (busy.current) return;
    busy.current = true;
    locationStartHandoff.discard(workspace.caseId);
    setStep({ kind: "finding" });
    const controller = new AbortController();
    request.current = controller;
    try {
      const resolution = await acquireCaseLocation(workspace.caseId, workspace.displayAddress, controller.signal);
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
  const admin = (item: { county: string | null; district: string | null }) => `${item.county ?? copy("adminUnknown")} · ${item.district ?? copy("adminUnknown")}`;
  return <Panel className="location-confirmation space-y-3" data-testid="location-confirmation" data-step={step.kind}>
    {(step.kind === "idle" || step.kind === "finding") && <div className="space-y-2">
      <h2 className="text-subsection">{copy(step.kind === "finding" ? "finding" : "find")}</h2>
      <p className="location-address break-words">{workspace.displayAddress}</p>
      {/* Stages mirror real states only: the saved draft, this lookup, then the buyer's explicit Confirm. */}
      {step.kind === "finding" && <ol className="location-stages" aria-label={copy("stages")}>
        <li data-stage="done">{copy("stageCase")}</li>
        <li data-stage="current" aria-current="step">{copy("stageLocate")}</li>
        <li data-stage="pending">{copy("stageConfirm")}</li>
      </ol>}
      <CommercialButton size="touch" loading={step.kind === "finding"} loadingLabel={copy("finding")} onClick={() => void find()} data-testid="location-find">{copy("find")}</CommercialButton>
      <p className="text-helper">{copy("findNote")}</p>
    </div>}
    {step.kind === "candidate" && <div ref={result} tabIndex={-1} className="ds-reveal space-y-3" data-testid="location-candidate" aria-labelledby="location-candidate-title">
      <h2 id="location-candidate-title" className="text-subsection">{copy("candidateTitle")}</h2>
      <p className="break-words text-body font-semibold">{step.candidate.interpretedAddress}</p>
      <div role="region" aria-label={copy("mapContext")} data-testid="location-candidate-map" className="h-56 overflow-hidden rounded-xl [&_.leaflet-container]:!min-h-0">
        <CandidateMap center={{ lat: step.candidate.latitude, lng: step.candidate.longitude }} zoom={16} categories={[]} centerLabel={step.candidate.interpretedAddress} radiusMeters={0} scrollWheelZoomEnabled={false} />
      </div>
      {step.candidate.countyUnverified && <Message variant="warning"><span data-testid="location-county-unverified">{copy("countyUnverified")}</span></Message>}
      <p className="text-helper">{copy("confirmNote")}</p>
      <p className="text-helper" data-testid="location-not-legal">{copy("notLegal")}</p>
      <div className="flex flex-wrap gap-3">
        <CommercialButton size="touch" loading={step.confirming} loadingLabel={copy("confirming")} onClick={() => void confirm(step.candidate)} data-testid="location-confirm">{copy("confirm")}</CommercialButton>
        <CommercialButton size="touch" variant="secondary" disabled={step.confirming} onClick={() => void find()}>{copy("reject")}</CommercialButton>
      </div>
      <DetailsDisclosure summary={copy("details")} data-testid="location-candidate-details" variant="compact">
        <dl className="grid gap-2 text-dense sm:grid-cols-2">
          <div><dt className="font-bold">{copy("interpreted")}</dt><dd className="break-words">{step.candidate.interpretedAddress}</dd></div>
          <div><dt className="font-bold">{copy("county")} · {copy("district")}</dt><dd>{admin(step.candidate)}</dd></div>
          {step.candidate.postalCode && <div><dt className="font-bold">{copy("postalCode")}</dt><dd>{step.candidate.postalCode}</dd></div>}
          <div><dt className="font-bold">{copy("coordinates")}</dt><dd className="font-mono">{step.candidate.latitude.toFixed(6)}, {step.candidate.longitude.toFixed(6)}</dd></div>
          <div><dt className="font-bold">{copy("source")}</dt><dd>{sourceLabel(step.candidate.source)}</dd></div>
        </dl>
      </DetailsDisclosure>
    </div>}
    {step.kind === "choice" && <div ref={result} tabIndex={-1} className="ds-reveal space-y-3" data-testid="location-choice" aria-labelledby="location-choice-title">
      <h2 id="location-choice-title" className="text-subsection">{copy("choiceTitle")}</h2>
      <p className="text-helper">{copy("choiceNote")}</p>
      <ul className="space-y-3">
        {step.candidates.map((candidate, index) => <li key={`${candidate.latitude}:${candidate.longitude}:${index}`} data-testid="location-choice-option" className="min-w-0 rounded-xl border border-stone-200 p-3 [overflow-wrap:anywhere]">
          <p className="text-body font-semibold">{candidate.interpretedAddress}</p>
          <p className="text-helper">{copy("county")} · {copy("district")}：{admin(candidate)}{candidate.postalCode ? ` · ${copy("postalCode")} ${candidate.postalCode}` : ""}</p>
          <p className="text-helper">{copy("coordinates")}：<span className="font-mono">{candidate.latitude.toFixed(6)}, {candidate.longitude.toFixed(6)}</span> · {copy("source")}：{sourceLabel(candidate.source)}</p>
          <CommercialButton size="touch" variant="secondary" className="mt-2" onClick={() => setStep({ kind: "candidate", candidate, confirming: false })}>{copy("choose")}</CommercialButton>
        </li>)}
      </ul>
      <CommercialButton size="touch" variant="secondary" onClick={() => void find()}>{copy("reject")}</CommercialButton>
    </div>}
    {step.kind === "failed" && <Message variant="error" title={copy("failedTitle")} action={<CommercialButton size="touch" variant="secondary" onClick={() => { if (step.candidate && ["write_failed", "lock_unavailable", "storage_unavailable"].includes(step.reason)) setStep({ kind: "candidate", candidate: step.candidate, confirming: false }); else void find(); }}>{copy(["administrative_mismatch", "address_mismatch", "low_precision"].includes(step.reason) ? "reject" : "retry")}</CommercialButton>}>
      <span data-testid="location-confirmation-failure" data-reason={step.reason}>{copy(step.reason)}</span>
    </Message>}
    {step.kind === "failed" && step.rejected?.length ? <div className="space-y-2" data-testid="location-rejected">
      <h3 className="text-subsection">{copy("rejectedTitle")}</h3>
      <p className="text-helper">{copy("rejectedNote")}</p>
      <ul className="space-y-2">
        {step.rejected.map((item, index) => <li key={`${item.latitude}:${item.longitude}:${index}`} data-testid="location-rejected-option" data-block-reason={item.blockReason} aria-disabled="true" className="min-w-0 rounded-xl border border-dashed border-rose-300 bg-rose-50 p-3 [overflow-wrap:anywhere]">
          <p className="text-meta font-bold text-rose-800">⊘ {copy(`badge_${item.blockReason}`)}</p>
          <p className="text-body">{item.interpretedAddress}</p>
          <p className="text-helper">{copy("county")} · {copy("district")}：{admin(item)} · {copy("source")}：{sourceLabel(item.source)}</p>
        </li>)}
      </ul>
    </div> : null}
  </Panel>;
}
