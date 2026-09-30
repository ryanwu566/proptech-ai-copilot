import type { EvidenceKey, InputFingerprint } from "./workspace-model";

export type WorkspaceInputChange = "address" | "coordinates" | "identity_conflict" | "area" | "asking_price" | "active_price" | "commute_destination";

const INVALIDATION: Record<WorkspaceInputChange, readonly EvidenceKey[]> = {
  address: ["market", "valuation", "location", "commute", "risk", "finance"],
  coordinates: ["market", "valuation", "location", "commute", "risk"],
  identity_conflict: ["market", "valuation", "location", "commute", "risk", "finance"],
  area: ["valuation", "finance"],
  asking_price: ["finance"],
  active_price: ["finance"],
  commute_destination: ["commute"],
};

export function computeInvalidation(change: WorkspaceInputChange): EvidenceKey[] {
  return [...INVALIDATION[change]];
}

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stable(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function buildInputFingerprint(value: unknown): InputFingerprint {
  return `workspace-v1:${stable(value)}`;
}

export function canCommitEvidence(input: {
  currentRevision: number;
  responseRevision: number;
  currentFingerprint: InputFingerprint;
  responseFingerprint: InputFingerprint;
}): boolean {
  return input.currentRevision === input.responseRevision && input.currentFingerprint === input.responseFingerprint;
}
