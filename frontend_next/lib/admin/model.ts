// @ts-expect-error Native TS test runner uses explicit extensions.
import { adminCopy, type AdminCopyKey } from "./copy.ts";
import type { ExperienceLocale } from "../experience-i18n";

export const sections = ["overview", "users", "usage", "providers", "limits", "operations", "audit"] as const;
export type AdminSection = typeof sections[number];
export type DataState = "known" | "unknown" | "unavailable" | "not_applicable";
type Scalar = string | number | boolean | null;
type Parser<T> = (value: unknown) => T;
type Shape = Record<string, Parser<unknown>>;

function fail(): never { throw new Error("admin_contract_invalid"); }
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return fail();
  return value as Record<string, unknown>;
}
function enumeration<const T extends readonly string[]>(values: T): Parser<T[number]> {
  return (value) => typeof value === "string" && values.includes(value) ? value as T[number] : fail();
}
function nullable<T>(parser: Parser<T>): Parser<T | null> { return (value) => value == null ? null : parser(value); }
const number: Parser<number> = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= Number.MAX_SAFE_INTEGER ? value : fail();
const count: Parser<number> = (value) => Number.isSafeInteger(number(value)) ? value as number : fail();
const boolean: Parser<boolean> = (value) => typeof value === "boolean" ? value : fail();
const code: Parser<string> = (value) => typeof value === "string" && /^[a-z][a-z0-9_.-]{0,63}$/.test(value) ? value : fail();
const uuid: Parser<string> = (value) => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value) ? value : fail();
const date: Parser<string> = (value) => typeof value === "string" && value.length <= 40 && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)) ? value : fail();
const source = enumeration(["wave_1a", "wave_1b", "wave_1c", "provider_observations", "provider_cost_metrics", "anti_abuse", "build_identity", "external"] as const);
const window = enumeration(["current_snapshot", "process_lifetime", "last_result", "last_24h", "last_7d"] as const);
const state = enumeration(["known", "unknown", "unavailable", "not_applicable"] as const);
function shape<S extends Shape>(schema: S): Parser<{ [K in keyof S]: ReturnType<S[K]> }> {
  return (value) => {
    const row = object(value);
    return Object.fromEntries(Object.entries(schema).map(([key, parser]) => [key, parser(row[key])])) as { [K in keyof S]: ReturnType<S[K]> };
  };
}
function list<T>(parser: Parser<T>, max = 50): Parser<T[]> {
  return (value) => Array.isArray(value) && value.length <= max ? value.map(parser) : fail();
}
const metricParser = shape({ key: enumeration(["accounts", "active_users", "requests", "provider_attempts", "admitted", "rejected", "http_429", "http_5xx", "latency_ms", "quota_consumed", "cache_hit", "warnings", "events", "health"] as const), state, value: nullable(number), source, window });
export type Metric = ReturnType<typeof metricParser>;
const costParser = shape({ state: enumeration(["known", "unknown", "not_applicable"] as const), amount: nullable(number), currency: nullable(enumeration(["USD", "TWD", "JPY", "KRW"] as const)) });
export type Cost = ReturnType<typeof costParser>;
export const userParser = shape({ user_id: uuid, status: enumeration(["active", "suspended", "unknown"] as const), platform_role: enumeration(["consumer", "platform_admin", "unknown"] as const), created_at: nullable(date), last_activity: nullable(date), usage_requests: nullable(count) });
const usageParser = shape({ capability: code, provider: nullable(code), requests: nullable(count), provider_attempts: nullable(count), admitted: nullable(count), rejected: nullable(count), http_429: nullable(count), http_5xx: nullable(count), latency_ms: nullable(number), quota_consumed: nullable(count), cache_hit: nullable(count), cost: costParser });
const providerParser = shape({ capability: code, configuration: enumeration(["configured", "not_configured", "invalid", "not_applicable"] as const), status: enumeration(["not_checked", "available", "partial", "limited", "no_data", "no_match", "unavailable", "error", "unaccepted", "resolved", "unresolved", "demo"] as const), freshness: enumeration(["current", "fresh", "stale", "unknown", "unavailable"] as const), checked_at: nullable(date), last_success: nullable(date), last_failure: nullable(date), disabled: boolean, quota_evidence: enumeration(["unavailable"] as const) });
const limitParser = shape({ capability: code, audience: enumeration(["all_peers"] as const), requests: count, window_seconds: count, operations: count, operation_window_seconds: count, concurrency: count, enabled: boolean });
const evidenceParser = shape({ key: enumeration(["release", "compatibility", "maintenance", "backup", "restore", "incident", "fleet_enforcement", "principal_quota"] as const), state, value: nullable(enumeration(["enabled", "disabled", "declared", "local_only"] as const)), commit_sha: nullable((value: unknown) => typeof value === "string" && /^[a-f0-9]{40}$/.test(value) ? value : fail()), source });
const boundedText = (max: number): Parser<string> => (value) => typeof value === 'string' && value.length <= max ? value : fail();
const stateFields: Parser<string> = (value) => {
  if (value == null) return '';
  const row = object(value);
  return ['status','platform_role','principal_class','request_hour','operation_hour','operation_day']
    .filter((key) => row[key] !== undefined).map((key) => `${key}: ${boundedText(64)(String(row[key]))}`).join(' · ');
};
const auditParser = shape({ target: nullable(boundedText(64)), reason: nullable(boundedText(500)), command_id: nullable(uuid), before_state: stateFields, after_state: stateFields, timestamp: date, actor: nullable(uuid), event_type: enumeration(["account_suspended", "account_restored", "role_changed", "policy_changed", "admin_read", "access_denied"] as const), target_type: enumeration(["account", "policy", "admin"] as const), outcome: enumeration(["success", "denied", "failure"] as const), reason_code: enumeration(["authorized", "permission_denied", "account_suspended", "policy_updated", "unknown"] as const) });
const snapshotParser = shape({ schema_version: enumeration(["admin-v1"] as const), section: enumeration(sections), state: enumeration(["available", "partial", "empty", "unavailable"] as const), source, window, as_of: date,
  reason: nullable(enumeration(["waiting_for_1a", "waiting_for_1b", "process_local", "external_evidence", "source_unavailable", "durable_aggregates"] as const)), next_cursor: nullable((value: unknown) => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value) ? value : fail()),
  metrics: list(metricParser, 20), users: list(userParser), usage: list(usageParser), providers: list(providerParser), limits: list(limitParser), operations: list(evidenceParser, 20), audit: list(auditParser) });
export type AdminSnapshot = ReturnType<typeof snapshotParser>;

export function parseSnapshot(value: unknown, expected: AdminSection): AdminSnapshot {
  const result = snapshotParser(value);
  if (result.section !== expected) fail();
  for (const metric of result.metrics) if ((metric.state === "known") !== (metric.value !== null)) fail();
  for (const row of result.usage) {
    const cost = row.cost;
    if (cost.state === "known" ? cost.amount === null || cost.currency === null : cost.amount !== null || cost.currency !== null) fail();
  }
  return result;
}
export function label(value: string, locale: ExperienceLocale): string {
  if (value === 'fleet_enforcement') value = 'capability_scope';
  return Object.hasOwn(adminCopy[locale], value) ? adminCopy[locale][value as AdminCopyKey] : value;
}
export function scalarValue(value: Scalar, locale: ExperienceLocale): string {
  if (value === null) return label("unknown", locale);
  if (typeof value === "number") return new Intl.NumberFormat(locale).format(value);
  if (typeof value === "boolean") return label(value ? "enabled" : "disabled", locale);
  return label(value, locale);
}
export function metricValue(metric: Metric, locale: ExperienceLocale): string {
  return metric.state === "known" && metric.value !== null ? scalarValue(metric.value, locale) : label(metric.state, locale);
}
export function costValue(cost: Cost, locale: ExperienceLocale): string {
  return cost.state === "known" && cost.amount !== null && cost.currency ? new Intl.NumberFormat(locale, { style: "currency", currency: cost.currency }).format(cost.amount) : label(cost.state, locale);
}

export function adminTimestamp(value: string, locale: ExperienceLocale): string {
  return `${new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23", timeZone: "UTC" }).format(new Date(value))} UTC`;
}

export function sessionTransition(previous: string | null, event: string, userId: string | null): { identity: string | null; revoke: boolean } {
  if (event === "SIGNED_OUT") return { identity: null, revoke: true };
  if (event === "SIGNED_IN" || event === "INITIAL_SESSION") return { identity: userId, revoke: userId === null || (previous !== null && previous !== userId) };
  return { identity: previous, revoke: false };
}
