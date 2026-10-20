"use client";

import { useEffect, useRef, useState } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { Panel } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { api, ApiRequestError } from "@/lib/api";
import { confirmSavedCaseIdentity, type ConfirmIdentityResult } from "@/lib/case-storage";
import { buildConfirmedLocationAnchor, interpretLocationResolution, locationRequestFailure, type LocationCandidate, type LocationCandidateBlock } from "@/lib/workspace/location-confirmation";
import { locationConfirmationCopy, type LocationConfirmationCopyKey } from "@/lib/workspace/location-confirmation-copy";

type Failure = LocationCandidateBlock | Extract<ConfirmIdentityResult, { status: "blocked" }>["reason"];
type Step =
  | { kind: "idle" }
  | { kind: "finding" }
  | { kind: "candidate"; candidate: LocationCandidate; confirming: boolean }
  | { kind: "failed"; reason: Failure; candidate?: LocationCandidate };

/**
 * Two explicit steps for a never-located case: Find runs one geocode-only resolve
 * and saves nothing; Confirm persists only the identity anchor. Neither step runs
 * nearby, commute, market, valuation or risk providers.
 */
export function LocationConfirmationPanel({ onConfirmed }: { onConfirmed: () => void }) {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const copy = (key: LocationConfirmationCopyKey) => copyFrom(locationConfirmationCopy, key);
  const [step, setStep] = useState<Step>({ kind: "idle" });
  const busy = useRef(false);
  const request = useRef<AbortController | null>(null);
  const result = useRef<HTMLDivElement>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if (step.kind === "candidate" && !step.confirming) result.current?.focus(); }, [step]);

  async function find() {
    if (busy.current) return;
    busy.current = true;
    setStep({ kind: "finding" });
    const controller = new AbortController();
    request.current = controller;
    try {
      const resolution = interpretLocationResolution(await api.locationResolve(workspace.displayAddress, controller.signal), workspace.displayAddress);
      if (!controller.signal.aborted) setStep(resolution.kind === "candidate" ? { kind: "candidate", candidate: resolution.candidate, confirming: false } : { kind: "failed", reason: resolution.reason });
    } catch (error) {
      if (!controller.signal.aborted) setStep({ kind: "failed", reason: locationRequestFailure(error instanceof ApiRequestError ? error.status : undefined) });
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
    if (outcome.status === "confirmed") onConfirmed();
    else setStep({ kind: "failed", reason: outcome.reason, candidate });
  }

  const sourceLabel = (source: LocationCandidate["source"]) => copy(source === "tgos" ? "sourceTgos" : "sourceGoogle");
  return <Panel className="space-y-3" data-testid="location-confirmation">
    <Message variant="information" title={copy("failedTitle")}>{workspace.displayAddress}</Message>
    {(step.kind === "idle" || step.kind === "finding") && <div className="space-y-2">
      <CommercialButton size="touch" loading={step.kind === "finding"} loadingLabel={copy("finding")} onClick={() => void find()} data-testid="location-find">{copy("find")}</CommercialButton>
      <p className="text-helper">{copy("findNote")}</p>
    </div>}
    {step.kind === "candidate" && <div ref={result} tabIndex={-1} className="space-y-3" data-testid="location-candidate" aria-labelledby="location-candidate-title">
      <h2 id="location-candidate-title" className="text-subsection">{copy("candidateTitle")}</h2>
      <dl className="grid gap-2 text-dense sm:grid-cols-2">
        <div><dt className="font-bold">{copy("interpreted")}</dt><dd className="break-words">{step.candidate.interpretedAddress}</dd></div>
        <div><dt className="font-bold">{copy("county")} · {copy("district")}</dt><dd>{step.candidate.county ?? copy("adminUnknown")} · {step.candidate.district ?? copy("adminUnknown")}</dd></div>
        <div><dt className="font-bold">{copy("coordinates")}</dt><dd className="font-mono">{step.candidate.latitude.toFixed(6)}, {step.candidate.longitude.toFixed(6)}</dd></div>
        <div><dt className="font-bold">{copy("source")}</dt><dd>{sourceLabel(step.candidate.source)}</dd></div>
      </dl>
      <p className="text-helper">{copy("confirmNote")}</p>
      <div className="flex flex-wrap gap-3">
        <CommercialButton size="touch" loading={step.confirming} loadingLabel={copy("confirming")} onClick={() => void confirm(step.candidate)} data-testid="location-confirm">{copy("confirm")}</CommercialButton>
        <CommercialButton size="touch" variant="secondary" disabled={step.confirming} onClick={() => setStep({ kind: "idle" })}>{copy("reject")}</CommercialButton>
      </div>
    </div>}
    {step.kind === "failed" && <Message variant="error" title={copy("failedTitle")} action={<CommercialButton size="touch" variant="secondary" onClick={() => setStep(step.candidate && ["write_failed", "lock_unavailable", "storage_unavailable"].includes(step.reason) ? { kind: "candidate", candidate: step.candidate, confirming: false } : { kind: "idle" })}>{copy("retry")}</CommercialButton>}>
      <span data-testid="location-confirmation-failure" data-reason={step.reason}>{copy(step.reason)}</span>
    </Message>}
  </Panel>;
}
