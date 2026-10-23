/** Complete calendar dates/ISO timestamps only. Date.parse also accepts bare years
 * and normalizes impossible days, neither of which is a source update date. */
function isDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(value) || !Number.isFinite(Date.parse(value))) return false;
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const calendar = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  return calendar.getUTCFullYear() === year && calendar.getUTCMonth() + 1 === month && calendar.getUTCDate() === day
    && (value.length === 10 || Number(value.slice(11, 13)) < 24);
}

/** Presentation only: never normalizes saved evidence or infers a vintage's date.
 * Timestamp fields reject labels; mixed source freshness fields preserve bounded
 * meaningful labels. The caller supplies its existing formatter and localized gap. */
export function formatEvidenceDate(
  value: string | null | undefined,
  formatDate: (value: string) => string,
  unavailable: string,
  kind: "date" | "source" = "date",
): string {
  if (typeof value !== "string") return unavailable;
  const text = value.trim();
  if (!text || /[\u0000-\u001f\u007f]/.test(text)) return unavailable;
  if (isDate(text)) return formatDate(text);
  if (kind === "date" || /^(?:未提供|未知|未保存|unknown|unavailable|not provided|n\/?a|null|undefined)$/i.test(text) || !/[\p{L}\p{N}]/u.test(text)) return unavailable;
  return text.slice(0, 200);
}
