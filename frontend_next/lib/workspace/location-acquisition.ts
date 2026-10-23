import { api } from "@/lib/api";
import { readSavedCases, savePendingLocationCandidate } from "@/lib/case-storage";
import { acquireLocationResolution, type LocationCandidateResult } from "./location-confirmation";
import { locationStartHandoff } from "./location-start-handoff";

/** Called only by explicit Home Start / Find / Retry. Finishes saving even if its view is left. */
export async function acquireCaseLocation(caseId: string, address: string, signal?: AbortSignal): Promise<LocationCandidateResult> {
  const current = readSavedCases().find((row) => row.id === caseId);
  if (!current) return { kind: "blocked", reason: "case_changed" };
  const version = JSON.stringify(current);
  const resolution = await acquireLocationResolution(address, (requestSignal) => api.locationResolve(address, requestSignal), signal);
  if (resolution.kind !== "candidate" || signal?.aborted) return resolution;
  const saved = await savePendingLocationCandidate(caseId, resolution.candidate, version);
  // A settled candidate must only be restored through the saved case/address binding.
  locationStartHandoff.discard(caseId);
  return saved.status === "saved" ? resolution : { kind: "blocked", reason: saved.reason };
}
