import type { SavedCase } from "../case-storage";
import type { SavedCaseReadDiagnostic } from "./saved-case-diagnostics";

/**
 * Home address start → bounded local case draft.
 * Pure: no provider calls, geocoding or analysis. Identity stays unconfirmed and
 * every evidence domain stays not started; only the typed address is recorded.
 */
export const MAX_DRAFT_ADDRESS_LENGTH = 200;
export const ADDRESS_DRAFT_SOURCE_LABEL = "使用者輸入";

export type AddressDraftFailure = "invalid_address" | "lock_unavailable" | "storage_unavailable" | "storage_invalid" | "limit_reached" | "write_failed";
export type AddressDraftResult =
  | { status: "created" | "reopened"; caseId: string }
  | { status: "blocked"; reason: AddressDraftFailure };
export type AddressDraftPlan =
  | { kind: "reopen"; saved: SavedCase }
  | { kind: "create"; saved: SavedCase }
  | { kind: "blocked"; reason: AddressDraftFailure };

const PLACEHOLDER_INPUTS = { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 } as const;
const EVIDENCE_FIELDS = ["propertyIdentityAnchor", "propertySearch", "valuation", "trend", "loan", "financePriceEvidence", "holdingCost", "locationInsight", "commuteRoute", "commuteTransit", "marketInsight", "terrainRisk", "terrainReference", "riskEvidenceCheckedAt", "riskSummary", "taxOracle", "financeEvidence", "reportCompleted", "checklistReview"] as const;

/** Collapse whitespace and strip control characters; null when empty or over the bound. */
export function normalizeDraftAddress(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const address = value.replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim();
  return address && address.length <= MAX_DRAFT_ADDRESS_LENGTH ? address : null;
}

/** Address-only record: placeholder inputs, no anchor, no evidence, no price or area. */
export function buildAddressDraftCase(address: string, { id, now }: { id: string; now: string }): SavedCase | null {
  const normalized = normalizeDraftAddress(address);
  if (!normalized) return null;
  return {
    id, title: normalized, createdAt: now, updatedAt: now, version: 1, workflowMode: "buying_wizard",
    activeWizardStep: "location", progress: 0, inputSummary: {},
    data: {
      inputs: { ...PLACEHOLDER_INPUTS },
      journeyContext: { version: 1, propertyContext: { addressSummary: normalized, sourceLabel: ADDRESS_DRAFT_SOURCE_LABEL, selectionStatus: "partial" }, priceBasis: "asking" },
    },
  };
}

/** Placeholder inputs carry no building facts; they only satisfy the legacy record shape. */
export function hasPlaceholderInputs(saved: Pick<SavedCase, "data">): boolean {
  const inputs = saved.data.inputs;
  return !inputs.city.trim() && !inputs.district.trim() && !inputs.road.trim() && !inputs.building_type.trim();
}

/** An untouched Home draft for the same address can be reopened instead of duplicated. */
export function isPristineAddressDraft(saved: SavedCase, address: string): boolean {
  const journey = saved.data.journeyContext;
  const context = journey?.propertyContext;
  const summary = saved.inputSummary;
  return Boolean(context && journey)
    && saved.title === address && saved.updatedAt === saved.createdAt && saved.progress === 0
    && journey!.priceBasis === "asking"
    && context!.addressSummary === address
    && context!.buildingType === undefined && context!.buildingAgeYears === undefined && context!.floor === undefined
    && !context!.city && !context!.district && !context!.road && context!.askingPriceWan === undefined && context!.areaPing === undefined
    && journey!.activePriceWan === undefined && journey!.manualPriceWan === undefined
    && !summary.city && !summary.district && !summary.road && summary.propertyPrice === undefined && summary.areaPing === undefined
    && hasPlaceholderInputs(saved)
    && EVIDENCE_FIELDS.every((field) => !saved.data[field]);
}

/** Decide, inside the storage lock, whether to reopen, create or refuse. Never drops existing cases. */
export function planAddressDraft(read: SavedCaseReadDiagnostic, address: unknown, options: { id: string; now: string; maxCases: number }): AddressDraftPlan {
  const normalized = normalizeDraftAddress(address);
  if (!normalized) return { kind: "blocked", reason: "invalid_address" };
  if (read.status === "storage_unavailable") return { kind: "blocked", reason: "storage_unavailable" };
  if (read.status === "parse_error" || read.status === "invalid_storage") return { kind: "blocked", reason: "storage_invalid" };
  const existing = read.cases.find((saved) => isPristineAddressDraft(saved, normalized));
  if (existing) return { kind: "reopen", saved: existing };
  if (read.cases.length >= options.maxCases) return { kind: "blocked", reason: "limit_reached" };
  if (read.cases.some((saved) => saved.id === options.id)) return { kind: "blocked", reason: "write_failed" };
  const saved = buildAddressDraftCase(normalized, options);
  return saved ? { kind: "create", saved } : { kind: "blocked", reason: "invalid_address" };
}
