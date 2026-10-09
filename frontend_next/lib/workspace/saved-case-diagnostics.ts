import type { SavedCase } from "../case-storage";
// @ts-expect-error Native TS runner extension.
import { normalizeJourneyPropertyIdentityAnchor } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeStoredFinanceEvidence } from "./finance-persistence.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeStoredTerrainReferenceEvidence } from "../terrain-reference-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeChecklistReview } from "./checklist-persistence.ts";

export type SavedCaseReadIssue = { caseId: string | null; reason: "invalid_record" | "duplicate_id" | "limit_exceeded" };
export type SavedCaseReadDiagnostic = {
  status: "ready" | "empty" | "partial" | "parse_error" | "invalid_storage" | "storage_unavailable";
  cases: SavedCase[];
  issues: SavedCaseReadIssue[];
};

// @ts-expect-error Native TS runner extension.
import { isOpaqueCaseId } from "./compare-selection.ts";
// @ts-expect-error Native TS runner extension.
export { isOpaqueCaseId } from "./compare-selection.ts";
function object(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
function date(value: unknown): boolean {
  return typeof value === "string" && value.length <= 40 && Number.isFinite(Date.parse(value));
}
function strings(value: unknown): boolean { return Array.isArray(value) && value.length <= 100 && value.every((item) => typeof item === "string" && item.length <= 4000); }
function optionalEvidence(data: Record<string, unknown>, caseId: string): boolean {
  if (data.checklistReview !== undefined) { const review = normalizeChecklistReview(data.checklistReview); if (!review || review.caseId !== caseId) return false; }
  if (data.propertyIdentityAnchor !== undefined && !normalizeJourneyPropertyIdentityAnchor(data.propertyIdentityAnchor)) return false;
  if (data.financeEvidence !== undefined) { const normalized = normalizeStoredFinanceEvidence(data.financeEvidence); if (!normalized || normalized.case_id !== caseId) return false; }
  if (data.terrainReference !== undefined && !normalizeStoredTerrainReferenceEvidence(data.terrainReference)) return false;
  if (data.locationInsight !== undefined) {
    const location = data.locationInsight;
    if (!object(location) || !object(location.data_quality) || !["good", "limited", "unavailable"].includes(String(location.data_quality.status)) || !strings(location.data_quality.missing_sources) || !strings(location.data_quality.warnings)) return false;
    if (location.poi_summary !== undefined && (!object(location.poi_summary) || !["transit_count", "convenience_count", "school_count", "park_count", "medical_count", "risk_facility_count"].every((key) => ((location.poi_summary as Record<string, unknown>)[key] === null || typeof (location.poi_summary as Record<string, unknown>)[key] === "number" && Number.isFinite((location.poi_summary as Record<string, unknown>)[key]))))) return false;
    if (location.radius_m !== undefined && (typeof location.radius_m !== "number" || !Number.isFinite(location.radius_m) || location.radius_m < 0)) return false;
    if (location.demographics !== undefined && (!object(location.demographics) || !["available", "no_data"].includes(String(location.demographics.status)))) return false;
    if (object(location.demographics) && location.demographics.status === "available" && (typeof location.demographics.total_population !== "number" || !Number.isFinite(location.demographics.total_population) || typeof location.demographics.source_provider !== "string" || typeof location.demographics.source_dataset !== "string")) return false;
  }
  if (data.commuteRoute !== undefined) {
    const route = data.commuteRoute;
    if (!object(route) || !object(route.origin) || !object(route.destination) || typeof route.destination.address !== "string" || route.destination.address.length > 500 || !["resolved", "unresolved", "unavailable"].includes(String(route.status)) || !["transit", "driving", "walking"].includes(String(route.mode)) || !["google_routes", "mock", "none"].includes(String(route.source)) || !date(route.checked_at)) return false;
    if (![route.origin.latitude, route.origin.longitude].every((value) => typeof value === "number" && Number.isFinite(value)) || typeof route.partial !== "boolean" || typeof route.fallback !== "boolean") return false;
    if (![route.duration_min, route.duration_seconds, route.distance_m].every((value) => value === null || (typeof value === "number" && Number.isFinite(value) && value >= 0))) return false;
  }
  if (data.commuteTransit !== undefined && (!object(data.commuteTransit) || !["resolved", "unresolved", "unavailable"].includes(String(data.commuteTransit.status)) || !strings(data.commuteTransit.line_ids))) return false;
  if (data.marketInsight !== undefined && (!object(data.marketInsight) || !["available", "no_data", "unavailable", "incomplete", "invalid"].includes(String(data.marketInsight.data_status)))) return false;
  if (data.journeyContext !== undefined && (!object(data.journeyContext) || data.journeyContext.version !== 1 || !object(data.journeyContext.propertyContext) || !["asking", "valuation", "manual"].includes(String(data.journeyContext.priceBasis)))) return false;
  return true;
}
function core(value: unknown): value is SavedCase {
  if (!object(value) || !isOpaqueCaseId(value.id) || value.version !== 1 || value.workflowMode !== "buying_wizard") return false;
  if (typeof value.title !== "string" || value.title.length > 500 || !date(value.createdAt) || !date(value.updatedAt)) return false;
  if (!["property_search", "valuation", "affordability", "location", "risk", "report", "tax"].includes(String(value.activeWizardStep)) || typeof value.progress !== "number" || !Number.isFinite(value.progress) || value.progress < 0 || value.progress > 100) return false;
  if (!object(value.inputSummary) || !object(value.data) || !object(value.data.inputs)) return false;
  if (!optionalEvidence(value.data, value.id)) return false;
  const inputs = value.data.inputs;
  if (!["city", "district", "road", "building_type"].every((key) => typeof inputs[key] === "string" && String(inputs[key]).length <= 500)) return false;
  return ["area_ping", "building_age_years", "floor"].every((key) => typeof inputs[key] === "number" && Number.isFinite(inputs[key]));
}

/** Validate without writing migrations, exposing raw records, or replacing conflicts. */
export function parseSavedCasesDiagnostic(raw: string | null, normalize: (row: SavedCase) => SavedCase | null): SavedCaseReadDiagnostic {
  if (raw === null) return { status: "empty", cases: [], issues: [] };
  let values: unknown;
  try { values = JSON.parse(raw); } catch { return { status: "parse_error", cases: [], issues: [] }; }
  if (!Array.isArray(values)) return { status: "invalid_storage", cases: [], issues: [] };
  const ids = new Map<string, number>();
  for (const value of values) if (object(value) && isOpaqueCaseId(value.id)) ids.set(value.id, (ids.get(value.id) ?? 0) + 1);
  const cases: SavedCase[] = [];
  const issues: SavedCaseReadIssue[] = [];
  const duplicates = new Set<string>();
  for (const value of values) {
    const caseId = object(value) && isOpaqueCaseId(value.id) ? value.id : null;
    if (caseId && (ids.get(caseId) ?? 0) > 1) {
      if (!duplicates.has(caseId)) issues.push({ caseId, reason: "duplicate_id" });
      duplicates.add(caseId); continue;
    }
    try {
      const normalized = core(value) ? normalize(value) : null;
      if (!normalized) { issues.push({ caseId, reason: "invalid_record" }); continue; }
      if (cases.length >= 10) { issues.push({ caseId, reason: "limit_exceeded" }); continue; }
      cases.push(normalized);
    } catch { issues.push({ caseId, reason: "invalid_record" }); }
  }
  return { status: issues.length ? "partial" : cases.length ? "ready" : "empty", cases, issues };
}
