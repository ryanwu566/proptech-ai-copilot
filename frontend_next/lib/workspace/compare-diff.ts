import type { EvidenceField } from "./case-evidence";
import type { EvidenceSectionModel } from "./compare-report-model";

/**
 * Pure, deterministic field-by-field diff of saved comparison sections.
 * No storage, network, clock or locale access: equality is exact on the saved
 * projection, and unresolved values are never treated as equal values.
 * The model never orders, scores or prefers a case.
 */
export type CompareCell = EvidenceField<string | number>;
export type CellResolution = "resolved" | "stale" | "unresolved";
/**
 * differs: value, state, unit or source differs between cases.
 * identical: every case has a resolved, exactly equal value with equal state and source.
 * same_unresolved: every case lacks a usable value for the same recorded reason (not equal values).
 * same_stale: every case holds the same stale evidence; stale evidence is never collapsed.
 */
export type RowRelation = "differs" | "identical" | "same_unresolved" | "same_stale";
export type DiffReason = "value" | "state" | "unit" | "source";
export type CompareDiffRow = { id: string; label: string; relation: RowRelation; reasons: DiffReason[]; cells: CompareCell[]; resolutions: CellResolution[] };
export type CompareDiffSection = Omit<EvidenceSectionModel, "rows"> & { rows: CompareDiffRow[] };
export type CompareDiffCounts = { total: number; visible: number; identical: number; sameUnresolved: number };
export type CompareDiffModel = { sections: CompareDiffSection[]; counts: CompareDiffCounts };
export type CompareFieldsView = "differences" | "all";

export function cellResolution(cell: CompareCell): CellResolution {
  if (cell.status === "stale" || cell.freshness.inputRelation === "stale" || cell.freshness.timeRelation === "stale") return "stale";
  return cell.value === null ? "unresolved" : "resolved";
}
// Type-tagged keys keep 1 and "1" distinct without locale-dependent formatting.
function scalarKey(value: string | number | null): string { return value === null ? "null" : `${typeof value}:${String(value)}`; }
function valueKey(cell: CompareCell): string { return `${scalarKey(cell.value)}|${scalarKey(cell.historicalValue)}`; }
function stateKey(cell: CompareCell): string { return [cell.status, cell.missingReason ?? "", cell.freshness.inputRelation, cell.freshness.timeRelation].join("|"); }
function sourceKey(cell: CompareCell): string { return `${cell.source}|${cell.sourceReason ?? ""}`; }
function differs(cells: CompareCell[], key: (cell: CompareCell) => string): boolean { return new Set(cells.map(key)).size > 1; }

export function classifyCells(cells: CompareCell[]): Pick<CompareDiffRow, "relation" | "reasons" | "resolutions"> {
  const resolutions = cells.map(cellResolution);
  const reasons: DiffReason[] = [];
  if (differs(cells, valueKey)) reasons.push("value");
  if (differs(cells, stateKey) || new Set(resolutions).size > 1) reasons.push("state");
  if (differs(cells, (cell) => cell.unit)) reasons.push("unit");
  if (differs(cells, sourceKey)) reasons.push("source");
  // Fewer than two cells cannot establish sameness; keep the row visible.
  if (reasons.length || cells.length < 2) return { relation: "differs", reasons, resolutions };
  if (resolutions.includes("stale")) return { relation: "same_stale", reasons, resolutions };
  if (resolutions.every((resolution) => resolution === "resolved")) return { relation: "identical", reasons, resolutions };
  return { relation: "same_unresolved", reasons, resolutions };
}

export function isVisibleInDifferences(row: Pick<CompareDiffRow, "relation">): boolean { return row.relation === "differs" || row.relation === "same_stale"; }

/** `caseIndexes` selects which cells participate (e.g. a mobile pair); defaults to all cells. */
export function buildCompareDiff(sections: EvidenceSectionModel[], caseIndexes?: number[]): CompareDiffModel {
  const counts: CompareDiffCounts = { total: 0, visible: 0, identical: 0, sameUnresolved: 0 };
  const diffSections = sections.map(({ rows, ...section }) => ({ ...section, rows: rows.map((row): CompareDiffRow => {
    const cells = caseIndexes ? caseIndexes.map((index) => row.cells[index]).filter((cell) => cell !== undefined) : [...row.cells];
    const classified = classifyCells(cells);
    counts.total += 1;
    if (isVisibleInDifferences(classified)) counts.visible += 1;
    else if (classified.relation === "identical") counts.identical += 1;
    else counts.sameUnresolved += 1;
    return { id: row.id, label: row.label, cells, ...classified };
  }) }));
  return { sections: diffSections, counts };
}

export function visibleRows(section: CompareDiffSection, view: CompareFieldsView): CompareDiffRow[] {
  return view === "all" ? section.rows : section.rows.filter(isVisibleInDifferences);
}

export type KeyDifferenceGroup = "price" | "market" | "finance" | "commute" | "risk";
export type KeyDifference = { group: KeyDifferenceGroup; rows: CompareDiffRow[] };
export type KeyDifferencesModel = { items: KeyDifference[]; gapCounts: number[] | null };
const KEY_GROUPS: Array<{ group: KeyDifferenceGroup; order: (id: string) => number }> = [
  { group: "price", order: (id) => ["price-asking", "price-basis"].indexOf(id) },
  { group: "market", order: (id) => ["market-total", "market-period", "market-scope"].indexOf(id) },
  { group: "finance", order: (id) => ["finance-housing", "finance-payment", "finance-price", "finance-rate"].indexOf(id) },
  { group: "commute", order: (id) => ["commute-destination", "commute-duration", "commute-mode"].indexOf(id) },
  { group: "risk", order: (id) => (id.startsWith("risk-") ? 0 : -1) },
];
export const KEY_DIFFERENCE_ROW_LIMIT = 3;

/**
 * A bounded, fixed-order selection of differing saved rows. Groups appear only when
 * a saved row actually differs; no claim is synthesized beyond the row itself.
 * `gapCounts` is reported only when the number of listed evidence gaps differs.
 */
export function buildKeyDifferences(diff: CompareDiffModel, gapCounts: number[]): KeyDifferencesModel {
  const rows = diff.sections.flatMap((section) => section.rows).filter((row) => row.relation === "differs");
  const items = KEY_GROUPS.flatMap(({ group, order }) => {
    const matched = rows.map((row, index) => ({ row, index, position: order(row.id) })).filter((item) => item.position >= 0)
      .sort((a, b) => a.position - b.position || a.index - b.index).slice(0, KEY_DIFFERENCE_ROW_LIMIT).map((item) => item.row);
    return matched.length ? [{ group, rows: matched }] : [];
  });
  return { items, gapCounts: new Set(gapCounts).size > 1 ? [...gapCounts] : null };
}

export function parseFieldsView(value: string | null): CompareFieldsView { return value === "all" ? "all" : "differences"; }
/** Keeps the existing `cases` query and adds `fields=all` only for the expanded view. */
export function compareFieldsHref(baseHref: string, view: CompareFieldsView): string {
  if (view !== "all") return baseHref;
  return `${baseHref}${baseHref.includes("?") ? "&" : "?"}fields=all`;
}
