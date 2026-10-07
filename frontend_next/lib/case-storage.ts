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
import { normalizeStoredFinanceEvidence, type StoredFinanceEvidenceV1 } from "@/lib/workspace/finance-persistence";
import { buildSavedCaseSnapshotUpdate, type SaveSnapshotIdentityState, type SaveSnapshotResult } from "@/lib/workspace/case-snapshot-save";

export const SAVED_CASES_STORAGE_KEY = "proptech.savedCases.v1";
export const CASE_LOADED_EVENT = "proptech:saved-case-loaded";
export const CASE_UPDATED_EVENT = "proptech:saved-case-updated";
export const CASE_CLEARED_EVENT = "proptech:current-case-cleared";
export const MAX_SAVED_CASES = 10;

// Historical list bounds are intentionally replaced by empty safe arrays.

export type SavedCaseData = {
  inputs: ValuationInputs;
  propertyIdentityAnchor?: JourneyPropertyIdentityAnchorV1;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  valuationEvidence?: PropertyCaseEvidence;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holdingCost?: HoldingCostResult;
  locationInsight?: LocationInsightResult;
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
};

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
  if (typeof window === "undefined") return [];
  try {
    const value = window.localStorage.getItem(SAVED_CASES_STORAGE_KEY);
    const rows = value ? JSON.parse(value) as SavedCase[] : [];
    return Array.isArray(rows) ? rows.filter((row) => row?.version === 1).map(normalizeSavedCase).filter((row): row is SavedCase => row !== null).slice(0, MAX_SAVED_CASES) : [];
  } catch {
    return [];
  }
}

export function saveCase(input: SaveCaseInput): SavedCase | null {
  if (getDraftSaveMissingFields(input).length > 0) return null;
  const now = new Date().toISOString();
  const saved: SavedCase = {
    ...input,
    id: createId(),
    title: input.title?.trim() || buildCaseTitle(input.inputSummary),
    createdAt: now,
    updatedAt: now,
    version: 1,
    workflowMode: "buying_wizard",
    data: compactCaseData(input.data),
  };
  writeCases([saved, ...readSavedCases()].slice(0, MAX_SAVED_CASES));
  return saved;
}

export function resaveSavedCaseSnapshot(
  caseId: string,
  expected: SavedCaseIdentityExpectation | undefined,
  identityState: SaveSnapshotIdentityState,
  expectedUpdatedAt: string,
  now: () => string = () => new Date().toISOString(),
): SaveSnapshotResult {
  const update = buildSavedCaseSnapshotUpdate(readSavedCases(), caseId, expected, identityState, expectedUpdatedAt, now, compactCaseData);
  if (update.result.status === "saved") {
    writeCases(update.rows);
    window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: update.result.saved }));
  }
  return update.result;
}

export function deleteSavedCase(id: string) {
  writeCases(readSavedCases().filter((row) => row.id !== id));
}

export function updateSavedCaseLocationEvidence(caseId: string, patch: {
  commuteRoute?: CommuteRouteEvidence | null;
  commuteTransit?: CommuteAddressLookupResult | null;
}, expectedIdentity?: SavedCaseIdentityExpectation): boolean {
  const rows = readSavedCases();
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0) return false;
  const current = rows[index];
  if (!identityMatches(current, expectedIdentity)) return false;
  const data: SavedCaseData = { ...current.data };
  if (Object.prototype.hasOwnProperty.call(patch, "commuteRoute")) {
    data.commuteRoute = compactCommuteRouteEvidence(patch.commuteRoute ?? undefined);
  }
  if (Object.prototype.hasOwnProperty.call(patch, "commuteTransit")) {
    data.commuteTransit = compactCommuteTransitEvidence(patch.commuteTransit ?? undefined);
  }
  const updated: SavedCase = { ...current, updatedAt: new Date().toISOString(), data };
  rows[index] = updated;
  writeCases(rows);
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseRiskEvidence(
  caseId: string,
  terrainReference: StoredTerrainReferenceEvidenceV1 & { checked_at?: string | null },
  expectedIdentity: SavedCaseIdentityExpectation,
): boolean {
  const rows = readSavedCases();
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || !identityMatches(rows[index], expectedIdentity)) return false;
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
  writeCases(rows);
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseMarketEvidence(
  caseId: string,
  marketInsight: MarketResult,
  expectedIdentity: SavedCaseIdentityExpectation,
): boolean {
  const boundedMarket = compactMarketInsight(marketInsight);
  if (!boundedMarket) return false;
  const rows = readSavedCases();
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || !identityMatches(rows[index], expectedIdentity)) return false;
  const updated: SavedCase = {
    ...rows[index],
    updatedAt: new Date().toISOString(),
    data: { ...rows[index].data, marketInsight: boundedMarket },
  };
  rows[index] = updated;
  writeCases(rows);
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseValuationEvidence(
  caseId: string,
  valuation: ValuationResult,
  expectedIdentity: SavedCaseIdentityExpectation,
): boolean {
  if (!getActionableValuation(valuation)) return false;
  const rows = readSavedCases();
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || !identityMatches(rows[index], expectedIdentity)) return false;
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
  writeCases(rows);
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function updateSavedCaseFinanceEvidence(
  caseId: string,
  evidence: StoredFinanceEvidenceV1,
  expectedIdentity: SavedCaseIdentityExpectation,
): boolean {
  const normalized = normalizeStoredFinanceEvidence(evidence);
  if (!normalized || normalized.case_id !== caseId) return false;
  const rows = readSavedCases();
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0 || !identityMatches(rows[index], expectedIdentity)) return false;
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
  writeCases(rows);
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_UPDATED_EVENT, { detail: updated }));
  return true;
}

export function clearSavedCases() {
  window.localStorage.removeItem(SAVED_CASES_STORAGE_KEY);
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
    locationInsight: data.locationInsight ? { ...data.locationInsight, resolved_location: null, nearest_pois: [] } : undefined,
    marketInsight: compactMarketInsight(data.marketInsight),
    commuteRoute: compactCommuteRouteEvidence(data.commuteRoute),
    commuteTransit: compactCommuteTransitEvidence(data.commuteTransit),
    terrainReference: normalizeStoredTerrainReferenceEvidence(data.terrainReference) ?? migrateLegacyTerrainReference(data.terrainRisk),
    riskEvidenceCheckedAt: typeof data.riskEvidenceCheckedAt === "string" && Number.isFinite(Date.parse(data.riskEvidenceCheckedAt))
      ? data.riskEvidenceCheckedAt
      : undefined,
    terrainRisk: undefined,
    financeEvidence,
    ...(financeEvidence ? { loan: undefined, holdingCost: undefined, taxOracle: undefined } : {}),
  };
}

function normalizeSavedCase(row: SavedCase): SavedCase | null {
  try {
    const fallbackInputs = { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 };
    const data = row.data && typeof row.data === "object" ? row.data : { inputs: fallbackInputs };
    return { ...row, title: typeof row.title === "string" ? row.title : "", data: compactCaseData(data as SavedCaseData) };
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

function writeCases(rows: SavedCase[]) {
  window.localStorage.setItem(SAVED_CASES_STORAGE_KEY, JSON.stringify(rows));
}

function createId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `case-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}
