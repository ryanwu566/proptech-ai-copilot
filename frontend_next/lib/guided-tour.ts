import type { GuidedTourCopyKey } from "@/lib/guided-tour-copy";

type TourStep = { id: string; label: GuidedTourCopyKey; heading: GuidedTourCopyKey; description: GuidedTourCopyKey };
export const TOUR_STEPS = [
  { id: "propertyCase", label: "guide.property.label", heading: "guide.property.heading", description: "guide.property.description" },
  { id: "marketEvidence", label: "guide.market.label", heading: "guide.market.heading", description: "guide.market.description" },
  { id: "locationCommute", label: "guide.location.label", heading: "guide.location.heading", description: "guide.location.description" },
  { id: "terrainRisk", label: "guide.risk.label", heading: "guide.risk.heading", description: "guide.risk.description" },
  { id: "finance", label: "guide.finance.label", heading: "guide.finance.heading", description: "guide.finance.description" },
  { id: "verificationChecklist", label: "guide.verify.label", heading: "guide.verify.heading", description: "guide.verify.description" },
  { id: "saveCompareReport", label: "guide.save.label", heading: "guide.save.heading", description: "guide.save.description" },
] as const satisfies readonly TourStep[];
export type TourStepId = typeof TOUR_STEPS[number]["id"];
export type TourStatus = "skipped" | "completed";
export const TOUR_VERSION = "3";
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
