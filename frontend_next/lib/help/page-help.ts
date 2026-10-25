// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { caseDestination, caseIdFromPath, nextCaseStep } from "../navigation/model.ts";

/** Pages with a contextual guide. Each id maps to one entry in the lazily loaded help catalogue. */
export const HELP_TOPICS = ["home", "market", "location", "risk", "money", "overview", "compare", "report"] as const;
export type HelpTopic = typeof HELP_TOPICS[number];

/** One destination the guide may point to next. The label key is resolved against the help catalogue. */
export type HelpNext =
  | { kind: "route"; href: string; label: "market" | "location" | "risk" | "money" | "overview" | "compare" | "report" }
  | { kind: "focus"; selector: string; label: "address" };

const CASE_SECTION_TOPICS: Record<string, HelpTopic> = {
  overview: "overview",
  market: "market",
  location: "location",
  "commute-planner": "location",
  risk: "risk",
  finance: "money",
  report: "report",
};

/** The guide for a pathname, or null where the page has none. Pure: reads nothing but the path. */
export function helpTopicForPath(pathname: string): HelpTopic | null {
  if (pathname === "/") return "home";
  if (pathname === "/compare") return "compare";
  const caseId = caseIdFromPath(pathname);
  if (caseId === undefined) return null;
  const section = pathname.split("/")[3] ?? "";
  return CASE_SECTION_TOPICS[section] ?? null;
}

const TOPIC_LABEL: Record<string, Extract<HelpNext, { kind: "route" }>["label"]> = {
  market: "market", location: "location", risk: "risk", finance: "money", overview: "overview", compare: "compare", report: "report",
};

/**
 * Suggested next destinations. The first one follows the same order as the workflow handoff (nextCaseStep);
 * none of them run a query or mark evidence complete. Compare picks cases itself, so it links nowhere new.
 */
export function helpNextSteps(topic: HelpTopic, pathname: string): HelpNext[] {
  if (topic === "home") return [{ kind: "focus", selector: "#commercial-address", label: "address" }];
  if (topic === "compare") return [];
  const caseId = caseIdFromPath(pathname);
  if (caseId === undefined) return [];
  const route = (section: "market" | "location" | "risk" | "finance" | "overview" | "report"): HelpNext => ({ kind: "route", href: caseDestination(caseId, section), label: TOPIC_LABEL[section] });
  const compare: HelpNext = { kind: "route", href: "/compare", label: "compare" };
  if (topic === "report") return [route("overview"), compare];
  if (topic === "overview") return [compare, route("report")];
  const section = topic === "money" ? "finance" : topic;
  const next = nextCaseStep(section);
  const primary = next === "compare" ? compare : route(next as "market" | "location" | "risk" | "finance" | "overview");
  // Location is also where a new case lands: market is the usual first query once the place is confirmed.
  if (topic === "location") return [route("market"), primary];
  return [primary];
}
