import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";
import type { BuyingWizardStep } from "@/lib/buying-wizard-status";
import type { ValuationInputs } from "@/lib/valuation-share";

export const SAVED_CASES_STORAGE_KEY = "proptech.savedCases.v1";
export const CASE_LOADED_EVENT = "proptech:saved-case-loaded";
export const CASE_CLEARED_EVENT = "proptech:current-case-cleared";
export const MAX_SAVED_CASES = 10;

export type SavedCaseData = {
  inputs: ValuationInputs;
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  trend?: ValuationTrendResult;
  loan?: LoanCalculationResult;
  holdingCost?: HoldingCostResult;
  locationInsight?: LocationInsightResult;
  terrainRisk?: TerrainRiskResult;
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
    return Array.isArray(rows) ? rows.filter((row) => row?.version === 1).slice(0, MAX_SAVED_CASES) : [];
  } catch {
    return [];
  }
}

export function saveCase(input: SaveCaseInput): SavedCase {
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
  setSession("proptech:viewing-workspace-context", context);
  setSession("proptech:holding-cost-result", saved.data.holdingCost);
  setSession("proptech:location-insight-result", saved.data.locationInsight);
  setSession("proptech:terrain-risk-result", saved.data.terrainRisk);
  setSession("proptech:taxoracle-result", saved.data.taxOracle);
  if (saved.data.reportCompleted) window.sessionStorage.setItem("proptech:workflow-report-completed", "true");
  else window.sessionStorage.removeItem("proptech:workflow-report-completed");
  window.sessionStorage.setItem("proptech:pending-section", targetForStep(saved.activeWizardStep));
  window.dispatchEvent(new CustomEvent<SavedCase>(CASE_LOADED_EVENT, { detail: saved }));
  window.dispatchEvent(new CustomEvent("proptech:viewing-workspace-context", { detail: context }));
  if (saved.data.holdingCost) window.dispatchEvent(new CustomEvent("proptech:holding-cost-result-ready", { detail: saved.data.holdingCost }));
  if (saved.data.locationInsight) window.dispatchEvent(new CustomEvent("proptech:location-insight-result-ready", { detail: saved.data.locationInsight }));
  if (saved.data.terrainRisk) window.dispatchEvent(new CustomEvent("proptech:terrain-risk-result-ready", { detail: saved.data.terrainRisk }));
  window.dispatchEvent(new Event("proptech:workflow-status-updated"));
}

export function clearCurrentCase() {
  for (const key of ["proptech:viewing-workspace-context", "proptech:holding-cost-result", "proptech:location-insight-result", "proptech:terrain-risk-result", "proptech:taxoracle-result", "proptech:workflow-report-completed", "proptech:pending-section"]) {
    window.sessionStorage.removeItem(key);
  }
  window.dispatchEvent(new Event(CASE_CLEARED_EVENT));
  window.dispatchEvent(new Event("proptech:workflow-status-updated"));
}

function compactCaseData(data: SavedCaseData): SavedCaseData {
  return {
    ...data,
    propertySearch: data.propertySearch ? { ...data.propertySearch, matched_transactions: data.propertySearch.matched_transactions.slice(0, 20) } : undefined,
    valuation: data.valuation ? { ...data.valuation, comparables: data.valuation.comparables.slice(0, 20) } : undefined,
    locationInsight: data.locationInsight ? { ...data.locationInsight, nearest_pois: data.locationInsight.nearest_pois.slice(0, 20) } : undefined,
    terrainRisk: data.terrainRisk ? { ...data.terrainRisk, risk_factors: data.terrainRisk.risk_factors.slice(0, 10), map_layers: data.terrainRisk.map_layers.slice(0, 10) } : undefined,
  };
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
