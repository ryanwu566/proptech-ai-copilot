import type { AppPage } from "@/components/sidebar";

export const CASE_DESTINATIONS = ["overview", "market", "location", "risk", "finance", "scenarios", "decision-room", "commute-planner", "report", "planning"] as const;
export type CaseDestination = typeof CASE_DESTINATIONS[number];
// Copy ids for product areas. They label case destinations and supporting pages; the
// public header deliberately no longer lists them as an "Explore features" catalogue.
export type ProductId = "home" | "property" | "cases" | "market" | "valuation" | "location" | "risk" | "finance" | "scenarios" | "decision-room" | "compare" | "report" | "preferences" | "places" | "commute-planner" | "account" | "tax" | "credit" | "identity" | "planning";
// Legacy single-tool pages stay reachable only through existing /?tool= links; nothing links to them.
export const LEGACY_TOOL_PAGES = ["Market Insight Lite", "房價估算", "Map Insight Lite", "Terrain Risk", "TaxOracle", "Aegis-Credit Lite"] as const satisfies readonly AppPage[];
export function isLegacyToolPage(value: string | null): value is typeof LEGACY_TOOL_PAGES[number] {
  return LEGACY_TOOL_PAGES.includes(value as typeof LEGACY_TOOL_PAGES[number]);
}

export function parseCaseDestination(value: string | null): CaseDestination {
  return CASE_DESTINATIONS.includes(value as CaseDestination) ? value as CaseDestination : "overview";
}
export function caseDestination(caseId: string, section: CaseDestination): string {
  return `/cases/${encodeURIComponent(caseId)}/${section}`;
}
export function caseIdFromPath(pathname: string): string | undefined {
  const match = /^\/cases\/([^/]+)(?:\/|$)/.exec(pathname);
  try { return match ? decodeURIComponent(match[1]) : undefined; } catch { return undefined; }
}
export function nextCaseStep(section: string): "scenarios" | "decision-room" | "compare" | "overview" {
  if (section === "scenarios") return "decision-room";
  if (section === "decision-room") return "compare";
  if (section === "report") return "overview";
  return "scenarios";
}
