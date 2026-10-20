import type { GuidedTourCopyKey } from "@/lib/guided-tour-copy";

type TourStep = { id: string; label: GuidedTourCopyKey; heading: GuidedTourCopyKey; description: GuidedTourCopyKey };
// The tour follows the modern case workspace; it never targets DOM nodes or starts analysis.
export const TOUR_STEPS = [
  { id: "createCase", label: "guide.create.label", heading: "guide.create.heading", description: "guide.create.description" },
  { id: "confirmLocation", label: "guide.confirm.label", heading: "guide.confirm.heading", description: "guide.confirm.description" },
  { id: "knownUnknown", label: "guide.unknown.label", heading: "guide.unknown.heading", description: "guide.unknown.description" },
  { id: "marketRisk", label: "guide.evidence.label", heading: "guide.evidence.heading", description: "guide.evidence.description" },
  { id: "questionsReport", label: "guide.decide.label", heading: "guide.decide.heading", description: "guide.decide.description" },
] as const satisfies readonly TourStep[];
export type TourStepId = typeof TOUR_STEPS[number]["id"];
export type TourStatus = "skipped" | "completed";
export const TOUR_VERSION = "4";
export const TOUR_STORAGE_KEY = "proptech_onboarding_state";
type TourStorage = Pick<Storage, "getItem" | "setItem">;

export function readTourStatus(storage: TourStorage): TourStatus | null {
  try {
    const raw = storage.getItem(TOUR_STORAGE_KEY);
    if (!raw || raw.length > 100) return null;
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const record = value as Record<string, unknown>;
    return Object.keys(record).length === 2 && record.version === TOUR_VERSION &&
      (record.status === "completed" || record.status === "skipped") ? record.status : null;
  } catch { return null; }
}

export function writeTourStatus(storage: TourStorage, status: TourStatus): void {
  try { storage.setItem(TOUR_STORAGE_KEY, JSON.stringify({ version: TOUR_VERSION, status })); }
  catch { /* Guidance remains usable when browser storage is disabled. */ }
}
