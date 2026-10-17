import type { AppPage } from "@/components/sidebar";

export type ProductGroup = "start" | "analysis" | "decisions" | "personal" | "supporting";
export const CASE_DESTINATIONS = ["overview", "market", "location", "risk", "finance", "scenarios", "decision-room", "commute-planner", "report", "planning"] as const;
export type CaseDestination = typeof CASE_DESTINATIONS[number];
type ProductEntry = { id: string; group: ProductGroup; href?: string; tool?: AppPage; section?: CaseDestination };
// Entry metadata only. Future capabilities belong here only once they have a real destination.
export const PRODUCT_ENTRIES = [
  { id: "home", group: "start", href: "/" },
  { id: "property", group: "start", href: "/?workflow=property" },
  { id: "cases", group: "start", href: "/cases" },
  { id: "market", group: "analysis", tool: "Market Insight Lite" },
  { id: "valuation", group: "analysis", tool: "房價估算" },
  { id: "location", group: "analysis", tool: "Map Insight Lite" },
  { id: "risk", group: "analysis", tool: "Terrain Risk" },
  { id: "finance", group: "analysis", section: "finance" },
  { id: "scenarios", group: "decisions", section: "scenarios" },
  { id: "decision-room", group: "decisions", section: "decision-room" },
  { id: "compare", group: "decisions", href: "/compare" },
  { id: "report", group: "decisions", section: "report" },
  { id: "preferences", group: "personal", href: "/preferences" },
  { id: "places", group: "personal", href: "/places" },
  { id: "commute-planner", group: "personal", section: "commute-planner" },
  { id: "account", group: "personal", href: "/account" },
  { id: "tax", group: "supporting", tool: "TaxOracle" },
  { id: "credit", group: "supporting", tool: "Aegis-Credit Lite" },
  { id: "identity", group: "supporting", href: "/vnext/property-identity" },
  { id: "planning", group: "supporting", section: "planning" },
] as const satisfies readonly ProductEntry[];
export type ProductId = typeof PRODUCT_ENTRIES[number]["id"];
export const PRODUCT_GROUPS: ProductGroup[] = ["start", "analysis", "decisions", "personal", "supporting"];

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
export function productHref(entry: ProductEntry, caseId?: string): string {
  if (entry.section) return caseId ? caseDestination(caseId, entry.section) : `/cases?next=${entry.section}`;
  if (entry.tool) return `/?tool=${encodeURIComponent(entry.tool)}`;
  return entry.href!;
}
export function filterEntries<T extends ProductEntry>(entries: readonly T[], query: string, label: (id: ProductId) => string): T[] {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return entries.filter((entry) => words.every((word) => `${label(entry.id as ProductId)} ${entry.id}`.toLocaleLowerCase().includes(word)));
}
export function nextCaseStep(section: string): "scenarios" | "decision-room" | "compare" | "overview" {
  if (section === "scenarios") return "decision-room";
  if (section === "decision-room") return "compare";
  if (section === "report") return "overview";
  return "scenarios";
}
