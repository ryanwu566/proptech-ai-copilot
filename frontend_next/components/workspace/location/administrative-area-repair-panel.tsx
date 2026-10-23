"use client";

import { useEffect, useRef, useState } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { api } from "@/lib/api";
import { readSavedCases, repairSavedCaseAdministrativeArea } from "@/lib/case-storage";
import { planAdministrativeAreaRepair } from "@/lib/workspace/administrative-area-repair";
import { acquireLocationResolution, type LocationCandidate } from "@/lib/workspace/location-confirmation";
import { locationConfirmationCopy, type LocationConfirmationCopyKey } from "@/lib/workspace/location-confirmation-copy";

type Step = { kind: "idle" | "finding" | "failed" }
  | { kind: "candidate"; candidate: LocationCandidate; version: string; saving: boolean };

/** Mounted only for a confirmed, incomplete anchor. Effects never acquire or save. */
export function AdministrativeAreaRepairPanel() {
  const workspace = useWorkspace();
  const { copyFrom } = useExperienceLocale();
  const copy = (key: LocationConfirmationCopyKey) => copyFrom(locationConfirmationCopy, key);
  const [step, setStep] = useState<Step>({ kind: "idle" });
  const busy = useRef(false);
  const active = useRef(true);
  const controller = useRef<AbortController | null>(null);
  const result = useRef<HTMLDivElement>(null);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; controller.current?.abort(); };
  }, []);
  useEffect(() => { if (step.kind === "candidate") result.current?.focus(); }, [step.kind]);

  async function recheck() {
    if (busy.current) return;
    const anchor = workspace.identity.anchor;
    const current = readSavedCases().find(row => row.id === workspace.caseId);
    const version = workspace.storageVersion;
    if (!anchor || !current || !version || JSON.stringify(current) !== version) { setStep({ kind: "failed" }); return; }
    busy.current = true;
    setStep({ kind: "finding" });
    const request = new AbortController();
    controller.current = request;
    try {
      const resolution = await acquireLocationResolution(anchor.address_input, signal => api.locationResolve(anchor.address_input, signal), request.signal);
      if (request.signal.aborted) return;
      const plan = resolution.kind === "candidate"
        ? planAdministrativeAreaRepair(current, resolution.candidate, version, new Date().toISOString()) : null;
      setStep(resolution.kind === "candidate" && plan?.kind === "write"
        ? { kind: "candidate", candidate: resolution.candidate, version, saving: false } : { kind: "failed" });
    } finally { busy.current = false; }
  }

  async function confirm() {
    if (busy.current || step.kind !== "candidate") return;
    busy.current = true;
    setStep({ ...step, saving: true });
    try {
      const outcome = await repairSavedCaseAdministrativeArea(workspace.caseId, step.candidate, step.version, () => active.current);
      if (active.current && outcome.status !== "confirmed") setStep({ kind: "failed" });
    } finally { busy.current = false; }
  }

  return <div className="mt-3 space-y-3" data-testid="administrative-area-repair">
    <p className="text-helper">{copy("adminRepairNote")}</p>
    {step.kind === "candidate" ? <div ref={result} tabIndex={-1} className="space-y-3" data-testid="administrative-area-candidate">
      <h3 className="text-subsection">{copy("adminRepairCandidate")}</h3>
      <p className="break-words text-body">{step.candidate.interpretedAddress}</p>
      <p className="text-body">{copy("county")}: {step.candidate.county} · {copy("district")}: {step.candidate.district}</p>
      <div className="flex flex-wrap gap-3">
        <CommercialButton size="touch" loading={step.saving} loadingLabel={copy("confirming")} onClick={() => void confirm()} data-testid="administrative-area-confirm">{copy("adminRepairConfirm")}</CommercialButton>
        <CommercialButton size="touch" variant="secondary" disabled={step.saving} onClick={() => setStep({ kind: "idle" })}>{copy("adminRepairCancel")}</CommercialButton>
      </div>
    </div> : <>
      {step.kind === "failed" && <div role="status" data-testid="administrative-area-repair-failure"><Message variant="warning">{copy("adminRepairFailed")}</Message></div>}
      <CommercialButton size="touch" loading={step.kind === "finding"} loadingLabel={copy("finding")} onClick={() => void recheck()} data-testid="administrative-area-recheck">{copy("adminRecheck")}</CommercialButton>
    </>}
  </div>;
}
