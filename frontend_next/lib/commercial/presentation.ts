// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { resolveCommercialState, type CommercialLocale } from "./state.ts";

export function evidenceStatusLabel(value: unknown, locale: CommercialLocale): string {
  if (value === "not_started" || value === "not_checked") return resolveCommercialState("query", "not_started").label[locale];
  if (value === "partial") return resolveCommercialState("completeness", "partial").label[locale];
  if (value === "available" || value === "good" || value === "usable") return resolveCommercialState("evidence", "usable").label[locale];
  if (["limited", "no_match", "no_coverage", "unavailable", "stale", "unverified", "unsupported"].includes(String(value))) {
    return resolveCommercialState("evidence", value).label[locale];
  }
  return resolveCommercialState("evidence", "unavailable").label[locale];
}

export function officialRuntimeStatusLabel(value: unknown, locale: CommercialLocale): string {
  return evidenceStatusLabel(value, locale);
}

export function pointReferencePresentation(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() && value !== "POINT_REFERENCE_ONLY" ? value : fallback;
}
