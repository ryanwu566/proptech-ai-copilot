// @ts-expect-error Node's native tests use source extensions.
import { CASE_DESTINATIONS } from "./model.ts";
// @ts-expect-error Node's native tests use source extensions.
import { compareHref, isOpaqueCaseId, parseCompareSelection } from "../workspace/compare-selection.ts";

// Evidence is a secondary case route, outside the primary workflow step list.
const RETURN_CASE_SECTIONS: readonly string[] = [...CASE_DESTINATIONS, "evidence"];

/** Only canonical workflow paths can become auth return intent. No path decoding
 * or URL normalization: either can turn hostile input into a different route.
 * Only Compare's supported selection/display query is retained. */
export function safeAuthReturn(value: string | null | undefined): string | null {
  if (!value || value.length > 2048 || /[\s\\#]/.test(value)) return null;
  if (["/", "/cases", "/compare", "/account", "/places", "/preferences"].includes(value)) return value;
  if (value.startsWith("/compare?")) {
    const query = new URLSearchParams(value.slice("/compare?".length));
    if ([...query.keys()].some(key => !["cases", "fields"].includes(key)) || query.getAll("cases").length > 1 || query.getAll("fields").length > 1) return null;
    const ids = parseCompareSelection(query.get("cases"));
    const fields = query.get("fields");
    if (ids.length > 4 || new Set(ids).size !== ids.length || !ids.every(isOpaqueCaseId) || fields !== null && !["all", "differences"].includes(fields)) return null;
    const path = compareHref(ids);
    return fields ? `${path}${ids.length ? "&" : "?"}fields=${fields}` : path;
  }
  const match = /^\/cases\/([A-Za-z0-9_-]+)\/([a-z-]+)$/.exec(value);
  return match && match[0] === value && isOpaqueCaseId(match[1]) && RETURN_CASE_SECTIONS.includes(match[2]) ? value : null;
}

export function authEntryHref(mode: "login" | "signup", destination: string | null | undefined): string {
  const safe = safeAuthReturn(destination);
  return `/${mode}${safe ? `?next=${encodeURIComponent(safe)}` : ""}`;
}
