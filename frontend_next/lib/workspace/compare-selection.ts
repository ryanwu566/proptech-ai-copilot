/** Lightweight opaque-ID navigation; no evidence or persistence dependencies. */
export function isOpaqueCaseId(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}
export function parseCompareSelection(value: string | null): string[] { return value === null || value === "" ? [] : value.split(","); }
export function compareHref(ids: string[]): string { return `/compare${ids.length ? `?cases=${ids.map(encodeURIComponent).join(",")}` : ""}`; }
