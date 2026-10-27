import type { DemographicsAvailable, DemographicsInsight, VillageResolution } from "../api";
import type { ExperienceLocale } from "../experience-i18n";

/**
 * Village demographics bound to one confirmed coordinate.
 * Spatial point -> NLSC village polygon -> RIS village code join happens on the backend; the
 * geocoder's administrative labels never take part in it. Nothing here fills, derives or smooths metrics.
 */
export type VillageDemographicsEvidence = {
  version: 1;
  origin: { lat: number; lng: number };
  checkedAt: string;
  village: VillageResolution;
  demographics: DemographicsInsight;
};

export type DemographicsViewState = "available" | "unresolved" | "ambiguous" | "no_data" | "unavailable";
export type DemographicsFreshness = { kind: "current" | "stale" | "unknown"; months: number | null };

const COORDINATE_TOLERANCE = 0.000001;
const STALE_AFTER_MONTHS = 2;
const VILLAGE_STATUSES = ["resolved", "unresolved", "ambiguous", "unavailable"] as const;
const TRENDS = ["increasing", "decreasing", "stable"] as const;
// Backend reasons meaning the source could not be read, as opposed to the village having no rows.
const UNAVAILABLE_REASONS = new Set(["demographics_unavailable", "village_resolver_unavailable", "location_not_resolved"]);

const record = (value: unknown): Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const count = (value: unknown): value is number => finite(value) && value >= 0 && Number.isInteger(value);
const signedCount = (value: unknown): value is number => finite(value) && Number.isInteger(value);
const ratio = (value: unknown): value is number | null => value === null || (finite(value) && value >= 0 && value <= 1);
const text = (value: unknown, max = 120): string | null => typeof value === "string" && value.trim() ? value.trim().slice(0, max) : null;
const month = (value: unknown): string | null => typeof value === "string" && /^\d{5,6}$/.test(value) && Number(value.slice(-2)) >= 1 && Number(value.slice(-2)) <= 12 ? value : null;
const near = (a: number, b: number) => Math.abs(a - b) <= COORDINATE_TOLERANCE;
const isDate = (value: unknown): value is string => typeof value === "string" && value.length <= 40 && Number.isFinite(Date.parse(value));

function village(value: unknown): VillageResolution | undefined {
  const v = record(value);
  if (!VILLAGE_STATUSES.includes(v.status as VillageResolution["status"])) return undefined;
  const status = v.status as VillageResolution["status"];
  const resolved = status === "resolved";
  return {
    status,
    county: resolved ? text(v.county) : null,
    town: resolved ? text(v.town) : null,
    village: resolved ? text(v.village) : null,
    // Kept only as the persisted join identity; never rendered.
    village_code: resolved ? text(v.village_code, 32) : null,
    district_code: resolved ? text(v.district_code, 32) : null,
    source: "nlsc_village_boundary",
    source_vintage: text(v.source_vintage, 32),
    reason: text(v.reason, 80) ?? "",
    ...(status === "ambiguous" && count(v.candidate_count) ? { candidate_count: v.candidate_count } : {}),
  };
}

function demographics(value: unknown): DemographicsInsight | undefined {
  const d = record(value);
  if (d.status === "no_data") return { status: "no_data", reason: text(d.reason, 80) ?? "" };
  if (d.status !== "available") return undefined;
  if (!count(d.total_population) || !count(d.household_count) || !count(d.observed_month_count) || d.observed_month_count < 1
    || !ratio(d.child_ratio) || !ratio(d.working_age_ratio) || !ratio(d.elderly_ratio)
    || !(d.average_household_size === null || (finite(d.average_household_size) && d.average_household_size >= 0))
    || !signedCount(d.population_change) || !signedCount(d.household_change)
    || !(d.population_change_ratio === null || finite(d.population_change_ratio))
    || !TRENDS.includes(d.trend_status as DemographicsAvailable["trend_status"]) || !month(d.statistic_yyymm)) return undefined;
  const audit = Array.isArray(d.audit_reasons) ? d.audit_reasons.filter((item): item is string => typeof item === "string").slice(0, 20) : [];
  return {
    status: "available",
    reason: null,
    statistic_yyymm: month(d.statistic_yyymm),
    statistic_month: text(d.statistic_month, 20),
    total_population: d.total_population,
    household_count: d.household_count,
    average_household_size: d.average_household_size as number | null,
    child_ratio: d.child_ratio,
    working_age_ratio: d.working_age_ratio,
    elderly_ratio: d.elderly_ratio,
    first_month: month(d.first_month),
    last_month: month(d.last_month),
    observed_month_count: d.observed_month_count,
    population_change: d.population_change,
    population_change_ratio: d.population_change_ratio as number | null,
    household_change: d.household_change,
    has_month_gaps: d.has_month_gaps === true,
    trend_status: d.trend_status as DemographicsAvailable["trend_status"],
    source_provider: text(d.source_provider, 40) ?? "RIS",
    source_dataset: text(d.source_dataset, 40) ?? "ODRP014",
    ...(audit.length ? { audit_reasons: audit } : {}),
  };
}

/** Accept a /demographics/location response only for the coordinate that was asked about. */
export function captureVillageDemographics(value: unknown, expected: { latitude: number; longitude: number }, now = () => new Date().toISOString()): VillageDemographicsEvidence {
  const data = record(value);
  const v = village(data.village_resolution);
  const d = demographics(data.demographics);
  if (!finite(data.latitude) || !finite(data.longitude) || !near(data.latitude, expected.latitude) || !near(data.longitude, expected.longitude) || !v || !d) {
    throw new Error("unavailable_village_demographics");
  }
  // Available figures for a village that did not resolve uniquely cannot belong to this point.
  if (d.status === "available" && v.status !== "resolved") throw new Error("unavailable_village_demographics");
  return { version: 1, origin: { lat: expected.latitude, lng: expected.longitude }, checkedAt: isDate(data.checked_at) ? data.checked_at : now(), village: v, demographics: d };
}

/** Revalidate on every read and save so old or malformed storage stays bounded. */
export function normalizeVillageDemographics(value: unknown): VillageDemographicsEvidence | undefined {
  const stored = record(value);
  const origin = record(stored.origin);
  if (stored.version !== 1 || !finite(origin.lat) || !finite(origin.lng) || Math.abs(origin.lat) > 90 || Math.abs(origin.lng) > 180 || !isDate(stored.checkedAt)) return undefined;
  try {
    return captureVillageDemographics({ latitude: origin.lat, longitude: origin.lng, checked_at: stored.checkedAt, village_resolution: stored.village, demographics: stored.demographics }, { latitude: origin.lat, longitude: origin.lng });
  } catch { return undefined; }
}

export function villageDemographicsMatches(evidence: VillageDemographicsEvidence | undefined, coordinates: { latitude: number; longitude: number } | null | undefined): evidence is VillageDemographicsEvidence {
  return Boolean(evidence && coordinates && near(evidence.origin.lat, coordinates.latitude) && near(evidence.origin.lng, coordinates.longitude));
}

/** One coherent state for every outcome; a missing payload is unavailable, never hidden. */
export function demographicsViewState(villageResolution?: VillageResolution, insight?: DemographicsInsight): DemographicsViewState {
  if (villageResolution?.status === "unavailable") return "unavailable";
  if (villageResolution?.status === "unresolved") return "unresolved";
  if (villageResolution?.status === "ambiguous") return "ambiguous";
  if (!insight) return "unavailable";
  if (insight.status === "available") return "available";
  return UNAVAILABLE_REASONS.has(insight.reason) ? "unavailable" : "no_data";
}

/** A trend needs at least two observed months; gaps are flagged, never filled. */
export function hasSufficientTrend(insight: DemographicsAvailable): boolean {
  return insight.observed_month_count >= 2 && Boolean(insight.first_month && insight.last_month);
}

function rocMonth(value: string | null | undefined): { year: number; month: number } | null {
  const valid = month(value);
  return valid ? { year: Number(valid.slice(0, -2)) + 1911, month: Number(valid.slice(-2)) } : null;
}

/** Age of the statistic month against today; recomputed on read so a reopened case is not shown as fresh. */
export function demographicsFreshness(insight: DemographicsAvailable, today: Date = new Date()): DemographicsFreshness {
  const observed = rocMonth(insight.statistic_yyymm);
  if (!observed) return { kind: "unknown", months: null };
  const months = (today.getUTCFullYear() - observed.year) * 12 + today.getUTCMonth() + 1 - observed.month;
  if (months < 0) return { kind: "unknown", months: null };
  return { kind: months > (insight.stale_after_months ?? STALE_AFTER_MONTHS) ? "stale" : "current", months };
}

const INTL: Record<ExperienceLocale, string> = { "zh-TW": "zh-TW", en: "en-US", ja: "ja-JP", ko: "ko-KR" };

export function formatDemographicsMonth(value: string | null | undefined, locale: ExperienceLocale): string | null {
  const parsed = rocMonth(value);
  if (!parsed) return null;
  if (locale === "zh-TW") return `民國${parsed.year - 1911}年${String(parsed.month).padStart(2, "0")}月`;
  return new Intl.DateTimeFormat(INTL[locale], { year: "numeric", month: locale === "en" ? "short" : "long", timeZone: "UTC" }).format(Date.UTC(parsed.year, parsed.month - 1, 1));
}

/** NLSC vintages arrive as "ROC-YYYMMDD"; anything else is not shown rather than echoed raw. */
export function formatBoundaryVintage(value: string | null | undefined, locale: ExperienceLocale): string | null {
  const match = /^ROC-(\d{3})(\d{2})(\d{2})$/.exec(value ?? "");
  if (!match) return null;
  const [year, monthValue, day] = [Number(match[1]) + 1911, Number(match[2]), Number(match[3])];
  if (monthValue < 1 || monthValue > 12 || day < 1 || day > 31) return null;
  return new Intl.DateTimeFormat(INTL[locale], { dateStyle: "medium", timeZone: "UTC" }).format(Date.UTC(year, monthValue - 1, day));
}

export function formatDemographicsCount(value: number | null | undefined, locale: ExperienceLocale): string | null {
  return finite(value) ? new Intl.NumberFormat(INTL[locale]).format(value) : null;
}

export function formatDemographicsSignedCount(value: number | null | undefined, locale: ExperienceLocale): string | null {
  return finite(value) ? `${value > 0 ? "+" : ""}${new Intl.NumberFormat(INTL[locale]).format(value)}` : null;
}

/** null stays insufficient; 0 is a real observed share. */
export function formatDemographicsRatio(value: number | null | undefined): string | null {
  return finite(value) ? `${(value * 100).toFixed(1)}%` : null;
}

export function formatDemographicsSignedRatio(value: number | null | undefined): string | null {
  return finite(value) ? `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)}%` : null;
}

export function formatHouseholdSizeValue(value: number | null | undefined): string | null {
  return finite(value) ? value.toFixed(2) : null;
}

const inFlight = new Map<string, Promise<unknown>>();
/** Share one acquisition + save across rapid clicks, Strict Mode effects or remounts of the same identity. */
export function shareVillageDemographicsAcquisition<T>(key: string, acquire: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(key);
  if (existing) return existing as Promise<T>;
  const pending = acquire().finally(() => { if (inFlight.get(key) === pending) inFlight.delete(key); });
  inFlight.set(key, pending);
  return pending;
}
