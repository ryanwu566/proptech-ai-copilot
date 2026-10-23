import type { CommuteAddressLookupResult, CommuteRouteEvidence, HoldingCostResult, LoanCalculationResult, LocationInsightResult, MarketResult, PropertySearchResult, TaxResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";
import type { BuyingWizardStep } from "@/lib/buying-wizard-status";
import type { ValuationInputs } from "@/lib/valuation-share";
import { getTrustedValuationEvidence, type PropertyCaseEvidence } from "@/lib/property-case-evidence";
import { migrateLegacyTerrainReference, normalizeStoredTerrainReferenceEvidence, type StoredTerrainReferenceEvidenceV1 } from "@/lib/terrain-reference-evidence";
import type { JourneyPriceBasis } from "@/lib/closed-loop-journey";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";
import type { PriceJourneyDisplayStatus } from "@/lib/price-affordability-journey";
import { compactCommuteRouteEvidence, compactCommuteTransitEvidence } from "@/lib/commute-route-evidence";
import { normalizeJourneyPropertyIdentityAnchor, type JourneyPropertyIdentityAnchorV1 } from "@/lib/journey-property-identity";
import { getActionableValuation, getStoredActionableValuation } from "@/lib/valuation-result-state";
import { compactActionableValuationSummary, compactActionableValuationTrendSummary, compactMarketInsight } from "@/lib/workspace/market-price-persistence";
import { captureJourneyFinanceEvidence, normalizeStoredFinanceEvidence, type StoredFinanceEvidenceV1 } from "@/lib/workspace/finance-persistence";
import { buildSavedCaseSnapshotUpdate, type SaveSnapshotIdentityState, type SaveSnapshotResult } from "@/lib/workspace/case-snapshot-save";
import { parseSavedCasesDiagnostic, type SavedCaseReadDiagnostic } from "@/lib/workspace/saved-case-diagnostics";
import { normalizeFinancePriceEvidence, type FinancePriceEvidence } from "@/lib/finance-price-provenance";
import { normalizeLocationInsightEvidence } from "@/lib/location-insight-evidence";
import { invalidateChangedChecklist, normalizeChecklistReview, type StoredChecklistReviewV1 } from "@/lib/workspace/checklist-persistence";
import { planAddressDraft, type AddressDraftResult } from "@/lib/workspace/case-draft";
import { planIdentityConfirmation } from "@/lib/workspace/location-confirmation";
import type { LocationCandidate } from "@/lib/workspace/location-confirmation";
import { capturePendingLocation, restorePendingLocation, type PendingLocationCandidate } from "@/lib/workspace/pending-location";
import { normalizeNearbyFacilities, type NearbyFacilitiesEvidence } from "@/lib/workspace/nearby-facilities";

export const SAVED_CASES_STORAGE_KEY = "proptech.savedCases.v1";
export const CASE_LOADED_EVENT = "proptech:saved-case-loaded";
export const CASE_UPDATED_EVENT = "proptech:saved-case-updated";
export const CASE_CLEARED_EVENT = "proptech:current-case-cleared";
export const MAX_SAVED_CASES = 10;

// Legacy provider detail arrays stay empty; nearby v1 keeps only its bounded contextual evidence.

export type SavedCaseData = {
  inputs: ValuationInputs;
  propertyIdentityAnchor?: JourneyPropertyIdentityAnchorV1;
  pendingLocationCandidate?: PendingLocationCandidate;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  valuationEvidence?: PropertyCaseEvidence;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  financePriceEvidence?: FinancePriceEvidence;
  holdingCost?: HoldingCostResult;
  locationInsight?: LocationInsightResult;
  nearbyFacilities?: NearbyFacilitiesEvidence;
  commuteRoute?: CommuteRouteEvidence;
  commuteTransit?: CommuteAddressLookupResult;
  marketInsight?: MarketResult;
  journeyContext?: {
    version: 1;
    propertyContext: JourneyPropertyContext;
    priceBasis: JourneyPriceBasis;
    activePriceWan?: number;
    manualPriceWan?: number;
    valuationStatus?: PriceJourneyDisplayStatus;
  };
  /** Legacy input only; new saved cases use terrainReference. */
  terrainRisk?: TerrainRiskResult;
  terrainReference?: StoredTerrainReferenceEvidenceV1;
  riskEvidenceCheckedAt?: string;
  riskSummary?: RiskSummary;
  taxOracle?: TaxResult;
  financeEvidence?: StoredFinanceEvidenceV1;
  reportCompleted?: boolean;
  checklistReview?: StoredChecklistReviewV1;
};

export type SavedCase = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  version: 1;
  workflowMode: "buying_wizard";
  activeWizardStep: BuyingWizardStep;
  progress: number;
  inputSummary: {
    city?: string;
    district?: string;
    road?: string;
    budgetMin?: number | null;
    budgetMax?: number;
    propertyPrice?: number;
    areaPing?: number;
  };
  data: SavedCaseData;
};

export type SaveCaseInput = Omit<SavedCase, "id" | "title" | "createdAt" | "updatedAt" | "version" | "workflowMode"> & { title?: string };

export type SavedCaseIdentityExpectation = {
  journeyAnchorId: string;
  normalizedAddress: string;
  coordinates: { latitude: number; longitude: number };
  /** Transient read version, never persisted or sent to a provider. */
  snapshotVersion?: string;
};

/** Evaluated after the storage lock is acquired, before any evidence mutation. */
export type SavedCaseCommitGuard = () => boolean;

function identityMatches(current: SavedCase, expected?: SavedCaseIdentityExpectation): boolean {
  if (!expected) return true;
  const anchor = current.data.propertyIdentityAnchor;
  return Boolean(
    anchor
    && anchor.revalidation.status === "current"
    && anchor.journey_anchor_id === expected.journeyAnchorId
    && anchor.normalized_address === expected.normalizedAddress
    && anchor.coordinates
    && Math.abs(anchor.coordinates.latitude - expected.coordinates.latitude) <= 0.000001
    && Math.abs(anchor.coordinates.longitude - expected.coordinates.longitude) <= 0.000001
  );
}

export function readSavedCases(): SavedCase[] {
  return readSavedCasesDiagnostic().cases;
}

export function readSavedCasesDiagnostic(): SavedCaseReadDiagnostic {
  return readStorageSnapshot().diagnostic;
}

function readStorageSnapshot(): { raw: string | null; diagnostic: SavedCaseReadDiagnostic } {
  const unavailable = { raw: null, diagnostic: { status: "storage_unavailable" as const, cases: [], issues: [] } };
  if (typeof window === "undefined") return unavailable;
  try {
    const raw = window.localStorage.getItem(SAVED_CASES_STORAGE_KEY);
    return { raw, diagnostic: parseSavedCasesDiagnostic(raw, normalizeSavedCase) };
  } catch {
    return unavailable;
  }
}

/** All writers share this origin-wide lock. No unsafe synchronous fallback. */
async function mutateSavedCases<T>(failure: T, mutation: () => T): Promise<T> {
  if (typeof window === "undefined" || !window.navigator?.locks?.request) return failure;
  try {
    return await window.navigator.locks.request(SAVED_CASES_STORAGE_KEY, { mode: "exclusive" }, () => mutation());
  } catch {
    return failure;
  }
}

function mutateSavedCaseEvidence(
  caseId: string,
  expected: SavedCaseIdentityExpectation | undefined,
  canCommit: SavedCaseCommitGuard | undefined,
  mutation: (snapshotVersion: string) => boolean,
): Promise<boolean> {
  const version = expected?.snapshotVersion ?? JSON.stringify(readSavedCases().find((row) => row.id === caseId));
  return mutateSavedCases(false, () => {
    if (canCommit && !canCommit()) return false;
    return mutation(version);
  });
}

export function saveCase(input: SaveCaseInput): Promise<SavedCase | null> {
  return mutateSavedCases<SavedCase | null>(null, () => saveCaseUnlocked(input));
}

function saveCaseUnlocked(input: SaveCaseInput): SavedCase | null {
  if (getDraftSaveMissingFields(input).length > 0) return null;
  try {
    const snapshot = readStorageSnapshot();
    const read = snapshot.diagnostic;
    if (["parse_error", "invalid_storage", "storage_unavailable"].includes(read.status) || read.cases.length >= MAX_SAVED_CASES) return null;
    const now = new Date().toISOString();
    const saved: SavedCase = {
      ...input,
      id: createId(),
      title: input.title?.trim() || buildCaseTitle(input.inputSummary),
      createdAt: now,
      updatedAt: now,
      version: 1,
      workflowMode: "buying_wizard",
      data: compactCaseData({ ...input.data, checklistReview: undefined }),
    };
    const financeEvidence = captureJourneyFinanceEvidence({ ...saved, data: input.data });
    if (financeEvidence) saved.data = compactCaseData({ ...input.data, checklistReview: undefined, financeEvidence });
    if (!writeCases([saved, ...read.cases].slice(0, MAX_SAVED_CASES), snapshot.raw)) return null;
    return saved;
  } catch {
    return null;
  }
}

/** Home address start: reopen an untouched draft or create one. Local only; never runs providers. */
export async function createAddressDraftCase(address: string): Promise<AddressDraftResult> {
  if (typeof window === "undefined" || !window.navigator?.locks?.request) return { status: "blocked", reason: "lock_unavailable" };
  return mutateSavedCases<AddressDraftResult>({ status: "blocked", reason: "lock_unavailable" }, () => {
    try {
      const snapshot = readStorageSnapshot();
      const plan = planAddressDraft(snapshot.diagnostic, address, { id: createId(), now: new Date().toISOString(), maxCases: MAX_SAVED_CASES });
      if (plan.kind === "blocked") return { status: "blocked", reason: plan.reason };
      if (plan.kind === "reopen") return { status: "reopened", caseId: plan.saved.id };
      const saved = { ...plan.saved, data: compactCaseData(plan.saved.data) };
      if (!writeCases([saved, ...snapshot.diagnostic.cases], snapshot.raw)) return { status: "blocked", reason: "write_failed" };
      return { status: "created", caseId: saved.id };
    } catch {
      return { status: "blocked", reason: "write_failed" };
    }
  });
}

export type ReservedCasesPlan = { kind: "blocked"; reason: string } | { kind: "unchanged" } | { kind: "write"; rows: SavedCase[]; installed: string[] };

/**
 * Demo installer only: plan against the locked read, then write through the validated writer.
 * Only rows named in `installed` are compacted here; every other row keeps its exact stored object.
 */
export async function writeReservedCases<P extends ReservedCasesPlan>(plan: (read: SavedCaseReadDiagnostic) => P): Promise<P | { kind: "blocked"; reason: "lock_unavailable" | "write_failed" }> {
  const locked = { kind: "blocked", reason: "lock_unavailable" } as const;
  const failed = { kind: "blocked", reason: "write_failed" } as const;
  if (typeof window === "undefined" || !window.navigator?.locks?.request) return locked;
  return mutateSavedCases<P | typeof locked | typeof failed>(locked, () => {
    try {
      const snapshot = readStorageSnapshot();
      const result = plan(snapshot.diagnostic);
      if (result.kind !== "write") return result;
      const installed = new Set(result.installed);
      const stored = new Map((snapshot.raw ? JSON.parse(snapshot.raw) as SavedCase[] : []).filter((row) => row && typeof row === "object").map((row) => [row.id, row]));
      const rows = result.rows.map((row) => installed.has(row.id) ? { ...row, data: compactCaseData(row.data) } : stored.get(row.id) ?? row);
      return writeCases(rows, snapshot.raw) ? result : failed;
    } catch {
      return failed;
    }
  });
}

export type ConfirmIdentityResult =
  | { status: "confirmed"; saved: SavedCase }
  | { status: "blocked"; reason: "lock_unavailable" | "storage_unavailable" | "case_changed" | "already_identified" | "invalid_anchor" | "write_failed" };

export type SavePendingLocationResult = { status: "saved"; saved: SavedCase } | Extract<ConfirmIdentityResult, { status: "blocked" }>;

/** Local compare-and-swap write under the same origin-wide lock as every case writer. */
export async function savePendingLocationCandidate(caseId: string, candidate: LocationCandidate, expectedVersion: string): Promise<SavePendingLocationResult> {
  if (typeof window === "undefined" || !window.navigator?.locks?.request) return { status: "blocked", reason: "lock_unavailable" };
  return mutateSavedCases<SavePendingLocationResult>({ status: "blocked", reason: "lock_unavailable" }, () => {
    try {
      const snapshot = readStorageSnapshot();
      if (["parse_error", "invalid_storage", "storage_unavailable"].includes(snapshot.diagnostic.status)) return { status: "blocked", reason: "storage_unavailable" };
      const rows = snapshot.diagnostic.cases;
      const index = rows.findIndex((row) => row.id === caseId);
      const current = rows[index];
      if (!current || JSON.stringify(current) !== expectedVersion) return { status: "blocked", reason: "case_changed" };
      if (current.data.propertyIdentityAnchor) return { status: "blocked", reason: "already_identified" };
      const pending = capturePendingLocation(current, candidate);
      if (!pending) return { status: "blocked", reason: "invalid_anchor" };
      const updated = { ...current, updatedAt: new Date().toISOString(), data: { ...current.data, pendingLocationCandidate: pending } };
      rows[index] = updated;
      if (!writeCases(rows, snapshot.raw)) return { status: "blocked", reason: "write_failed" };
      window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
      return { status: "saved", saved: updated };
    } catch { return { status: "blocked", reason: "write_failed" }; }
  });
}

/**
 * Persist an explicitly user-confirmed location anchor on a never-located case.
 * Compare-and-swap on the exact read version; never overwrites an existing anchor
 * and never touches evidence, so confirmation itself runs no provider.
 */
export async function confirmSavedCaseIdentity(caseId: string, anchor: JourneyPropertyIdentityAnchorV1, expectedVersion: string): Promise<ConfirmIdentityResult> {
  if (typeof window === "undefined" || !window.navigator?.locks?.request) return { status: "blocked", reason: "lock_unavailable" };
  return mutateSavedCases<ConfirmIdentityResult>({ status: "blocked", reason: "lock_unavailable" }, () => {
    try {
      const snapshot = readStorageSnapshot();
      if (["parse_error", "invalid_storage", "storage_unavailable"].includes(snapshot.diagnostic.status)) return { status: "blocked", reason: "storage_unavailable" };
      const rows = snapshot.diagnostic.cases;
      const index = rows.findIndex((row) => row.id === caseId);
      const plan = planIdentityConfirmation(rows[index], anchor, expectedVersion);
      if (plan.kind === "blocked") return { status: "blocked", reason: plan.reason };
      const updated: SavedCase = { ...rows[index], updatedAt: new Date().toISOString(), data: compactCaseData({ ...rows[index].data, pendingLocationCandidate: undefined, propertyIdentityAnchor: plan.anchor }) };
      rows[index] = updated;
      if (!writeCases(rows, snapshot.raw)) return { status: "blocked", reason: "write_failed" };
      window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
      return { status: "confirmed", saved: updated };
    } catch {
      return { status: "blocked", reason: "write_failed" };
    }
  });
}

export function resaveSavedCaseSnapshot(
  caseId: string,
  expected: SavedCaseIdentityExpectation | undefined,
  identityState: SaveSnapshotIdentityState,
  expectedUpdatedAt: string,
  now: () => string = () => new Date().toISOString(),
  checklistReview?: StoredChecklistReviewV1,
): Promise<SaveSnapshotResult> {
  const expectation = expected ? { ...expected, snapshotVersion: expected.snapshotVersion ?? JSON.stringify(readSavedCases().find((row) => row.id === caseId)) } : undefined;
  return mutateSavedCases<SaveSnapshotResult>({ status: "blocked", reason: "storage_unavailable", message: "案件未保存；此瀏覽器無法安全協調案件儲存，請使用支援安全儲存的瀏覽器後再試。" },
    () => resaveSavedCaseSnapshotUnlocked(caseId, expectation, identityState, expectedUpdatedAt, now, checklistReview));
}

function resaveSavedCaseSnapshotUnlocked(
  caseId: string,
  expected: SavedCaseIdentityExpectation | undefined,
  identityState: SaveSnapshotIdentityState,
  expectedUpdatedAt: string,
  now: () => string = () => new Date().toISOString(),
  checklistReview?: StoredChecklistReviewV1,
): SaveSnapshotResult {
  const snapshot = readStorageSnapshot();
  const read = snapshot.diagnostic;
  if (["parse_error", "invalid_storage", "storage_unavailable"].includes(read.status)) return { status: "blocked", reason: "storage_unavailable", message: "本機案件儲存無法安全讀取；請檢查儲存資料後再保存。" };
  const update = buildSavedCaseSnapshotUpdate(read.cases, caseId, expected, identityState, expectedUpdatedAt, now, compactCaseData, checklistReview);
  if (update.result.status === "saved") {
    if (!writeCases(update.rows, snapshot.raw)) return { status: "blocked", reason: "storage_unavailable", message: "案件未保存；儲存空間不足、無法使用或案件已在另一個畫面更新。原有案件仍保留，請重新開啟後再試。" };
    window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: update.result.saved }));
  }
  return update.result;
}

export function deleteSavedCase(id: string) {
  return mutateSavedCases(false, () => deleteSavedCaseUnlocked(id));
}

function deleteSavedCaseUnlocked(id: string) {
  const snapshot = readStorageSnapshot();
  return writeCases(snapshot.diagnostic.cases.filter((row) => row.id !== id), snapshot.raw);
}

export function updateSavedCaseLocationEvidence(caseId: string, patch: {
  nearbyFacilities?: NearbyFacilitiesEvidence;
  commuteRoute?: CommuteRouteEvidence | null;
  commuteTransit?: CommuteAddressLookupResult | null;
}, expectedIdentity?: SavedCaseIdentityExpectation, canCommit?: SavedCaseCommitGuard): Promise<boolean> {
  return mutateSavedCaseEvidence(caseId, expectedIdentity, canCommit, (version) => updateSavedCaseLocationEvidenceUnlocked(caseId, patch, expectedIdentity, version));
}

function updateSavedCaseLocationEvidenceUnlocked(caseId: string, patch: {
  nearbyFacilities?: NearbyFacilitiesEvidence;
  commuteRoute?: CommuteRouteEvidence | null;
  commuteTransit?: CommuteAddressLookupResult | null;
}, expectedIdentity: SavedCaseIdentityExpectation | undefined, snapshotVersion: string): boolean {
  const snapshot = readStorageSnapshot();
  const rows = snapshot.diagnostic.cases;
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0) return false;
  const current = rows[index];
  if (JSON.stringify(current) !== snapshotVersion || !identityMatches(current, expectedIdentity)) return false;
  const data: SavedCaseData = { ...current.data };
  if (Object.prototype.hasOwnProperty.call(patch, "nearbyFacilities")) {
    const nearby = normalizeNearbyFacilities(patch.nearbyFacilities);
    if (!nearby || !expectedIdentity || Math.abs(nearby.origin.lat - expectedIdentity.coordinates.latitude) > 0.000001
      || Math.abs(nearby.origin.lng - expectedIdentity.coordinates.longitude) > 0.000001) return false;
    data.nearbyFacilities = nearby;
  }
  if (Object.prototype.hasOwnProperty.call(patch, "commuteRoute")) {
    data.commuteRoute = compactCommuteRouteEvidence(patch.commuteRoute ?? undefined);
  }
  if (Object.prototype.hasOwnProperty.call(patch, "commuteTransit")) {
    data.commuteTransit = compactCommuteTransitEvidence(patch.commuteTransit ?? undefined);
  }
  const updated: SavedCase = { ...current, updatedAt: new Date().toISOString(), data };
  rows[index] = updated;
  if (!writeCases(rows, snapshot.raw)) return false;
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseRiskEvidence(
  caseId: string,
  terrainReference: StoredTerrainReferenceEvidenceV1 & { checked_at?: string | null },
  expectedIdentity: SavedCaseIdentityExpectation,
  canCommit?: SavedCaseCommitGuard,
): Promise<boolean> {
  return mutateSavedCaseEvidence(caseId, expectedIdentity, canCommit, (version) => updateSavedCaseRiskEvidenceUnlocked(caseId, terrainReference, expectedIdentity, version));
}

function updateSavedCaseRiskEvidenceUnlocked(
  caseId: string,
  terrainReference: StoredTerrainReferenceEvidenceV1 & { checked_at?: string | null },
  expectedIdentity: SavedCaseIdentityExpectation,
  snapshotVersion: string,
): boolean {
  const snapshot = readStorageSnapshot();
  const rows = snapshot.diagnostic.cases;
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || JSON.stringify(rows[index]) !== snapshotVersion || !identityMatches(rows[index], expectedIdentity)) return false;
  const { checked_at: checkedAt, ...boundedReference } = terrainReference;
  const normalized = normalizeStoredTerrainReferenceEvidence(boundedReference);
  if (!normalized) return false;
  const updated: SavedCase = {
    ...rows[index],
    updatedAt: new Date().toISOString(),
    data: {
      ...rows[index].data,
      terrainReference: normalized,
      riskEvidenceCheckedAt: checkedAt ?? new Date().toISOString(),
      terrainRisk: undefined,
    },
  };
  rows[index] = updated;
  if (!writeCases(rows, snapshot.raw)) return false;
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseMarketEvidence(
  caseId: string,
  marketInsight: MarketResult,
  expectedIdentity: SavedCaseIdentityExpectation,
  canCommit?: SavedCaseCommitGuard,
): Promise<boolean> {
  return mutateSavedCaseEvidence(caseId, expectedIdentity, canCommit, (version) => updateSavedCaseMarketEvidenceUnlocked(caseId, marketInsight, expectedIdentity, version));
}

function updateSavedCaseMarketEvidenceUnlocked(
  caseId: string,
  marketInsight: MarketResult,
  expectedIdentity: SavedCaseIdentityExpectation,
  snapshotVersion: string,
): boolean {
  const boundedMarket = compactMarketInsight(marketInsight);
  if (!boundedMarket) return false;
  const snapshot = readStorageSnapshot();
  const rows = snapshot.diagnostic.cases;
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || JSON.stringify(rows[index]) !== snapshotVersion || !identityMatches(rows[index], expectedIdentity)) return false;
  const updated: SavedCase = {
    ...rows[index],
    updatedAt: new Date().toISOString(),
    data: { ...rows[index].data, marketInsight: boundedMarket },
  };
  rows[index] = updated;
  if (!writeCases(rows, snapshot.raw)) return false;
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseValuationEvidence(
  caseId: string,
  valuation: ValuationResult,
  expectedIdentity: SavedCaseIdentityExpectation,
  canCommit?: SavedCaseCommitGuard,
): Promise<boolean> {
  return mutateSavedCaseEvidence(caseId, expectedIdentity, canCommit, (version) => updateSavedCaseValuationEvidenceUnlocked(caseId, valuation, expectedIdentity, version));
}

function updateSavedCaseValuationEvidenceUnlocked(
  caseId: string,
  valuation: ValuationResult,
  expectedIdentity: SavedCaseIdentityExpectation,
  snapshotVersion: string,
): boolean {
  if (!getActionableValuation(valuation)) return false;
  const snapshot = readStorageSnapshot();
  const rows = snapshot.diagnostic.cases;
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || JSON.stringify(rows[index]) !== snapshotVersion || !identityMatches(rows[index], expectedIdentity)) return false;
  const updated: SavedCase = {
    ...rows[index],
    updatedAt: new Date().toISOString(),
    data: compactCaseData({
      ...rows[index].data,
      valuation,
      // Trend detail is useful during the active session but is not part of
      // the bounded actionable valuation summary saved with the case.
      trend: undefined,
    }),
  };
  rows[index] = updated;
  if (!writeCases(rows, snapshot.raw)) return false;
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseFinanceEvidence(
  caseId: string,
  evidence: StoredFinanceEvidenceV1,
  expectedIdentity: SavedCaseIdentityExpectation,
  canCommit?: SavedCaseCommitGuard,
): Promise<boolean> {
  return mutateSavedCaseEvidence(caseId, expectedIdentity, canCommit, (version) => updateSavedCaseFinanceEvidenceUnlocked(caseId, evidence, expectedIdentity, version));
}

function updateSavedCaseFinanceEvidenceUnlocked(
  caseId: string,
  evidence: StoredFinanceEvidenceV1,
  expectedIdentity: SavedCaseIdentityExpectation,
  snapshotVersion: string,
): boolean {
  const normalized = normalizeStoredFinanceEvidence(evidence);
  if (!normalized || normalized.case_id !== caseId) return false;
  const snapshot = readStorageSnapshot();
  const rows = snapshot.diagnostic.cases;
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || JSON.stringify(rows[index]) !== snapshotVersion || !identityMatches(rows[index], expectedIdentity)) return false;
  const updated: SavedCase = {
    ...rows[index],
    updatedAt: new Date().toISOString(),
    data: {
      ...rows[index].data,
      financeEvidence: normalized,
      loan: undefined,
      holdingCost: undefined,
      taxOracle: undefined,
    },
  };
  rows[index] = updated;
  if (!writeCases(rows, snapshot.raw)) return false;
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function clearSavedCases() {
  return mutateSavedCases(false, () => {
    window.localStorage.removeItem(SAVED_CASES_STORAGE_KEY);
    if (window.localStorage.getItem(SAVED_CASES_STORAGE_KEY) !== null) return false;
    window.dispatchEvent(new Event(CASE_UPDATED_EVENT));
    return true;
  });
}

export function loadSavedCase(saved: SavedCase) {
  const context = {
    inputs: saved.data.inputs,
    propertySearch: saved.data.propertySearch,
    valuation: saved.data.valuation,
    trend: saved.data.trend,
    loan: saved.data.loan,
    holding: saved.data.holdingCost,
  };
  window.sessionStorage.setItem("proptech:pending-section", targetForStep(saved.activeWizardStep));
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_LOADED_EVENT, { detail: saved }));
  window.dispatchEvent(new CustomEvent("proptech:viewing-workspace-context", { detail: context }));
  window.dispatchEvent(new Event("proptech:workflow-status-updated"));
}

export function clearCurrentCase() {
  for (const key of ["proptech:viewing-workspace-context", "proptech:holding-cost-result", "proptech:location-insight-result", "proptech:taxoracle-result", "proptech:workflow-report-completed", "proptech:pending-section"]) {
    window.sessionStorage.removeItem(key);
  }
  window.dispatchEvent(new Event(CASE_CLEARED_EVENT));
  window.dispatchEvent(new Event("proptech:workflow-status-updated"));
}

export function compactCaseData(data: SavedCaseData): SavedCaseData {
  const freshEvidence = getTrustedValuationEvidence(data.valuation);
  const storedSummary = getStoredActionableValuation(data.valuation);
  const hasTrustedStoredEvidence = data.valuationEvidence?.status === "trusted"
    && data.valuationEvidence.source === "official_valuation"
    && data.valuationEvidence.transferable === true;
  const valuationEvidence = freshEvidence.transferable
    ? freshEvidence
    : storedSummary && hasTrustedStoredEvidence
      ? data.valuationEvidence
      : !data.valuation && ["unavailable", "partial"].includes(data.valuationEvidence?.status ?? "")
        ? { status: data.valuationEvidence!.status, source: "none", label: "成交資料推估", value: null, range: null, confidence: null, reason: "已儲存的查詢未取得可採用的價格推估", transferable: false } as PropertyCaseEvidence
      : freshEvidence;
  const transferableValuation = freshEvidence.transferable || (storedSummary !== null && hasTrustedStoredEvidence);
  const compactedValuation = data.valuation && transferableValuation
    ? compactActionableValuationSummary(data.valuation)
    : undefined;
  const financeEvidence = normalizeStoredFinanceEvidence(data.financeEvidence) ?? undefined;
  return {
    ...data,
    propertyIdentityAnchor: normalizeJourneyPropertyIdentityAnchor(data.propertyIdentityAnchor) ?? undefined,
    propertySearch: data.propertySearch ? { ...data.propertySearch, matched_transactions: [] } : undefined,
    valuationEvidence,
    valuation: compactedValuation ? { ...compactedValuation, comparables: [] } : undefined,
    trend: compactActionableValuationTrendSummary(data.trend),
    locationInsight: data.locationInsight ? { ...normalizeLocationInsightEvidence(data.locationInsight), resolved_location: null, nearest_pois: [] } : undefined,
    nearbyFacilities: normalizeNearbyFacilities(data.nearbyFacilities),
    financePriceEvidence: normalizeFinancePriceEvidence(data.financePriceEvidence) ?? undefined,
    marketInsight: compactMarketInsight(data.marketInsight),
    commuteRoute: compactCommuteRouteEvidence(data.commuteRoute),
    commuteTransit: compactCommuteTransitEvidence(data.commuteTransit),
    terrainReference: normalizeStoredTerrainReferenceEvidence(data.terrainReference) ?? migrateLegacyTerrainReference(data.terrainRisk),
    riskEvidenceCheckedAt: typeof data.riskEvidenceCheckedAt === "string" && Number.isFinite(Date.parse(data.riskEvidenceCheckedAt))
      ? data.riskEvidenceCheckedAt
      : undefined,
    terrainRisk: undefined,
    financeEvidence,
    checklistReview: normalizeChecklistReview(data.checklistReview) ?? undefined,
    ...(financeEvidence ? { loan: undefined, holdingCost: undefined, taxOracle: undefined } : {}),
  };
}

function normalizeSavedCase(row: SavedCase): SavedCase | null {
  try {
    const fallbackInputs = { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 };
    const data = row.data && typeof row.data === "object" ? row.data : { inputs: fallbackInputs };
    const normalized = { ...row, title: typeof row.title === "string" ? row.title : "", data: compactCaseData(data as SavedCaseData) };
    normalized.data.pendingLocationCandidate = restorePendingLocation(normalized);
    return normalized;
  } catch {
    return null;
  }
}

export function getDraftSaveMissingFields(input: SaveCaseInput): string[] {
  const missing: string[] = [];
  if (!input.title?.trim()) missing.push("case_name");
  const address = [input.inputSummary.city, input.inputSummary.district, input.inputSummary.road].filter((value) => typeof value === "string" && value.trim()).join("");
  if (!address) {
    const anchor = input.data.propertyIdentityAnchor;
    if (!anchor?.normalized_address.trim()) missing.push("address_or_property_identifier");
    else if (anchor.revalidation.status !== "current" || anchor.location_status === "stale") missing.push("property_identity_revalidation");
    else if (!anchor.coordinates) missing.push("accepted_property_coordinates");
  }
  return missing;
}

function buildCaseTitle(summary: SavedCase["inputSummary"]) {
  if (summary.road) return `${summary.city ?? ""}${summary.district ?? ""}${summary.road}`.trim();
  if (summary.city || summary.district) return `${summary.city ?? ""}${summary.district ?? ""}${summary.budgetMax ? `｜${summary.budgetMax}萬內` : ""}`;
  return "未命名看屋案件";
}

function targetForStep(step: BuyingWizardStep) {
  return { property_search: "property-finder", valuation: "valuation-calculator", affordability: "loan-calculator", location: "location-insight-calculator", risk: "risk-summary", report: "decision-report", tax: "taxoracle" }[step];
}

function setSession(key: string, value: unknown) {
  if (value === undefined) window.sessionStorage.removeItem(key);
  else window.sessionStorage.setItem(key, JSON.stringify(value));
}

/** Write only validated snapshots; retain quarantined originals for explicit recovery. */
function writeCases(rows: SavedCase[], expectedRaw: string | null): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = window.localStorage.getItem(SAVED_CASES_STORAGE_KEY);
    if (raw !== expectedRaw) return false;
    const read = parseSavedCasesDiagnostic(raw, normalizeSavedCase);
    if (["parse_error", "invalid_storage", "storage_unavailable"].includes(read.status)) return false;
    const previous = read.cases;
    const validIds = new Set(previous.map((row) => row.id));
    const original: unknown[] = raw === null ? [] : JSON.parse(raw);
    const retained = original.filter((value) => !value || typeof value !== "object" || !validIds.has((value as SavedCase).id));
    const retainedIds = new Set(retained.map((value) => value && typeof value === "object" ? (value as SavedCase).id : undefined));
    if (rows.some((row) => retainedIds.has(row.id))) return false;
    const bounded = rows.map((row) => row.data.checklistReview ? { ...row, data: { ...row.data, checklistReview: invalidateChangedChecklist(previous.find((item) => item.id === row.id), row) } } : row);
    // Check the exact serialized read contract before reporting success.
    const serialized = JSON.stringify(bounded);
    const candidate = parseSavedCasesDiagnostic(serialized, normalizeSavedCase);
    if (candidate.status !== (rows.length ? "ready" : "empty") || candidate.cases.length !== rows.length) return false;
    const next = JSON.stringify([...bounded, ...retained]);
    window.localStorage.setItem(SAVED_CASES_STORAGE_KEY, next);
    if (window.localStorage.getItem(SAVED_CASES_STORAGE_KEY) !== next) return false;
    window.dispatchEvent(new Event(CASE_UPDATED_EVENT));
    return true;
  } catch {
    return false;
  }
}

function createId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `case-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}
