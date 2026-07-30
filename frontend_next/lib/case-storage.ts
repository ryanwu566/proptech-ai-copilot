import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";
import type { BuyingWizardStep } from "@/lib/buying-wizard-status";
import type { ValuationInputs } from "@/lib/valuation-share";
import { getTrustedValuationEvidence, type PropertyCaseEvidence } from "@/lib/property-case-evidence";
import { migrateLegacyTerrainReference, normalizeStoredTerrainReferenceEvidence, type StoredTerrainReferenceEvidenceV1 } from "@/lib/terrain-reference-evidence";

export const SAVED_CASES_STORAGE_KEY = "proptech.savedCases.v1";
export const CASE_LOADED_EVENT = "proptech:saved-case-loaded";
export const CASE_CLEARED_EVENT = "proptech:current-case-cleared";
export const MAX_SAVED_CASES = 10;

// Historical list bounds are intentionally replaced by empty safe arrays.

export type SavedCaseData = {
  inputs: ValuationInputs;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  valuationEvidence?: PropertyCaseEvidence;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holdingCost?: HoldingCostResult;
  locationInsight?: LocationInsightResult;
  /** Legacy input only; new saved cases use terrainReference. */
  terrainRisk?: TerrainRiskResult;
  terrainReference?: StoredTerrainReferenceEvidenceV1;
  riskSummary?: RiskSummary;
  taxOracle?: TaxResult;
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

export function deleteSavedCase(id: string) {
  writeCases(readSavedCases().filter((row) => row.id !== id));
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

function compactCaseData(data: SavedCaseData): SavedCaseData {
  const valuationEvidence = getTrustedValuationEvidence(data.valuation);
  return {
    ...data,
    propertySearch: data.propertySearch ? { ...data.propertySearch, matched_transactions: [] } : undefined,
    valuationEvidence,
    valuation: data.valuation && valuationEvidence.transferable ? {
      ...data.valuation,
      comparables: [],
      source_details: {
        file: "",
        nature: "official summary",
        complete_real_price_registry: false,
        formal_appraisal: false,
        bank_appraisal: false,
        future_adapter: "",
      },
    } : undefined,
    locationInsight: data.locationInsight ? { ...data.locationInsight, resolved_location: null, nearest_pois: [] } : undefined,
    terrainReference: normalizeStoredTerrainReferenceEvidence(data.terrainReference) ?? migrateLegacyTerrainReference(data.terrainRisk),
    terrainRisk: undefined,
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
  if (!address) missing.push("address_or_property_identifier");
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
