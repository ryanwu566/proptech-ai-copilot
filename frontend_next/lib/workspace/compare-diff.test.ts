import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildComparisonModel } from "./compare-report-model.ts";
// @ts-expect-error Native TS runner extension.
import { buildCompareDiff, buildKeyDifferences, classifyCells, visibleRows, parseFieldsView, compareFieldsHref, KEY_DIFFERENCE_ROW_LIMIT, type CompareCell, type CompareDiffRow } from "./compare-diff.ts";

const evidence = (id = "case-a") => projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case(id)));
function cell(overrides: Partial<CompareCell> = {}): CompareCell {
  return { id: "x", label: "X", domain: "market", unit: "萬元", value: 100, historicalValue: null, status: "limited", missingReason: null, source: "S", limitation: "L", nextAction: "N",
    freshness: { origin: "saved_snapshot", inputRelation: "unknown", timeRelation: "unknown", checkedAt: null, sourceUpdatedAt: null }, ...overrides };
}
function standardPair() {
  const a = e9Case(); const b = e9Case("case-b");
  delete b.data.marketInsight; delete b.data.financeEvidence; delete b.data.commuteRoute;
  const cases = [a, b].map((row) => projectCaseEvidence(adaptSavedCaseToWorkspace(row)));
  return buildComparisonModel(cases, ["case-a", "case-b"]);
}
const allRows = (sections: Array<{ rows: CompareDiffRow[] }>) => sections.flatMap((section) => section.rows);

test("resolved equal values are identical; any value, state, unit or source change differs", () => {
  assert.equal(classifyCells([cell(), cell()]).relation, "identical");
  assert.deepEqual(classifyCells([cell(), cell({ value: 101 })]).reasons, ["value"]);
  assert.deepEqual(classifyCells([cell(), cell({ status: "available" })]).reasons, ["state"]);
  assert.deepEqual(classifyCells([cell(), cell({ unit: "元" })]).reasons, ["unit"]);
  assert.deepEqual(classifyCells([cell(), cell({ source: "T" })]).reasons, ["source"]);
  assert.equal(classifyCells([cell({ value: 1 }), cell({ value: "1" })]).relation, "differs");
});
test("unresolved values never become equal values; differing missing states stay visible", () => {
  const notRun = cell({ value: null, status: "not_run", missingReason: "not_run" });
  const unavailable = cell({ value: null, status: "unavailable", missingReason: "unavailable" });
  const same = classifyCells([notRun, { ...notRun }]);
  assert.equal(same.relation, "same_unresolved");
  assert.notEqual(same.relation, "identical");
  const mixed = classifyCells([notRun, unavailable]);
  assert.equal(mixed.relation, "differs");
  assert.ok(mixed.reasons.includes("state"));
  assert.equal(classifyCells([cell(), notRun]).relation, "differs");
});
test("stale evidence is always visible, including identical stale rows", () => {
  const stale = cell({ value: null, historicalValue: 1850, status: "stale", missingReason: "stale" });
  const same = classifyCells([stale, { ...stale }]);
  assert.equal(same.relation, "same_stale");
  assert.equal(visibleRows({ id: "market", title: "", description: "", rows: [{ id: "x", label: "X", cells: [stale, stale], ...same }] }, "differences").length, 1);
  assert.equal(classifyCells([cell(), stale]).relation, "differs");
  assert.equal(classifyCells([cell({ freshness: { ...cell().freshness, timeRelation: "stale" } }), cell()]).relation, "differs");
});
test("a single cell cannot establish sameness", () => {
  assert.equal(classifyCells([cell()]).relation, "differs");
});
test("standard pair: differences-only hides identical rows only, and counts every hidden row", () => {
  const model = standardPair();
  const diff = buildCompareDiff(model.sections);
  const rows = allRows(diff.sections);
  assert.equal(rows.length, model.sections.reduce((sum, section) => sum + section.rows.length, 0));
  assert.equal(diff.counts.total, rows.length);
  assert.equal(diff.counts.visible + diff.counts.identical + diff.counts.sameUnresolved, diff.counts.total);
  assert.ok(diff.counts.identical > 0, "fixture shares saved fields");
  assert.ok(diff.counts.visible > 0, "case B lacks market, finance and commute evidence");
  for (const section of diff.sections) {
    assert.equal(visibleRows(section, "all").length, section.rows.length);
    for (const row of visibleRows(section, "differences")) assert.ok(row.relation === "differs" || row.relation === "same_stale");
  }
  const asking = rows.find((row) => row.id === "market-total")!;
  assert.equal(asking.relation, "differs");
  assert.ok(asking.reasons.includes("state"));
});
test("diff preserves the original saved cells, order and provenance without mutation", () => {
  const model = standardPair();
  const before = JSON.stringify(model);
  const diff = buildCompareDiff(model.sections);
  assert.equal(JSON.stringify(model), before);
  model.sections.forEach((section, s) => section.rows.forEach((row, r) => {
    const out = diff.sections[s].rows[r];
    assert.equal(out.id, row.id);
    out.cells.forEach((value, i) => assert.equal(value, row.cells[i]));
  }));
  assert.deepEqual(buildCompareDiff(model.sections), diff);
});
test("pair diff uses only the selected case cells", () => {
  const a = evidence(); const b = evidence("case-b"); const c = evidence("case-c");
  c.finance.interestRate.value = 2.2;
  const model = buildComparisonModel([a, b, c], ["case-a", "case-b", "case-c"]);
  const rate = (indexes?: number[]) => allRows(buildCompareDiff(model.sections, indexes).sections).find((row) => row.id === "finance-rate")!;
  assert.equal(rate().relation, "differs");
  assert.equal(rate([0, 1]).relation, "identical");
  assert.equal(rate([0, 2]).relation, "differs");
  assert.equal(rate([0, 1]).cells.length, 2);
});
test("key differences are bounded, ordered by fixed group and carry no ranking fields", () => {
  const model = standardPair();
  const diff = buildCompareDiff(model.sections);
  const key = buildKeyDifferences(diff, model.cases.map((item) => item.gaps.length));
  assert.ok(key.items.length > 0 && key.items.length <= 5);
  const order = ["price", "market", "finance", "commute", "risk"];
  assert.deepEqual(key.items.map((item) => item.group), order.filter((group) => key.items.some((item) => item.group === group)));
  for (const item of key.items) {
    assert.ok(item.rows.length >= 1 && item.rows.length <= KEY_DIFFERENCE_ROW_LIMIT);
    for (const row of item.rows) assert.equal(row.relation, "differs");
  }
  assert.ok(key.items.some((item) => item.group === "commute"));
  assert.ok(key.gapCounts && key.gapCounts[0] !== key.gapCounts[1]);
  const text = JSON.stringify(key);
  assert.doesNotMatch(text, /best|winner|rank|score|recommend|better|worse|safer|cheaper/i);
});
test("identical cases yield no key differences and no gap count difference", () => {
  const a = evidence(); const b = evidence("case-b");
  b.title = a.title; b.displayAddress = a.displayAddress;
  const model = buildComparisonModel([a, b], ["case-a", "case-b"]);
  const key = buildKeyDifferences(buildCompareDiff(model.sections), model.cases.map((item) => item.gaps.length));
  assert.deepEqual(key, { items: [], gapCounts: null });
});
test("view parsing is closed and href keeps the case selection", () => {
  assert.equal(parseFieldsView(null), "differences");
  assert.equal(parseFieldsView("ALL"), "differences");
  assert.equal(parseFieldsView("all"), "all");
  assert.equal(compareFieldsHref("/compare?cases=case-a,case-b", "all"), "/compare?cases=case-a,case-b&fields=all");
  assert.equal(compareFieldsHref("/compare?cases=case-a,case-b", "differences"), "/compare?cases=case-a,case-b");
  assert.equal(compareFieldsHref("/compare", "all"), "/compare?fields=all");
});
