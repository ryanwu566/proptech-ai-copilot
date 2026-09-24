// Pure-logic unit tests for demographics-insight-card formatting helpers.
// Run with: node --test lib/demographics-format.test.mjs
// These cover the deterministic presentation rules that must never render
// null/insufficient values as 0, and must render a real 0 correctly.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import ts from "../node_modules/typescript/lib/typescript.js";

// Compile the TSX helpers to JS on the fly and import via data URL, so the test
// exercises the exact source used by the component (no duplicated logic).
const here = path.dirname(fileURLToPath(import.meta.url));
const source = readFileSync(path.join(here, "..", "components", "demographics-insight-card.tsx"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, jsxImportSource: "react" },
  fileName: "demographics-insight-card.tsx",
}).outputText;

// Neutralize the React/UI imports the helpers don't need at runtime.
const runnable = compiled
  .replace(/import[^;]*from\s*["']react\/jsx-runtime["'];?/g, "")
  .replace(/import[^;]*from\s*["']@\/lib\/api["'];?/g, "")
  .replace(/import[^;]*from\s*["']@\/components\/product-ui["'];?/g, "const SectionCard=()=>null, MetricTile=()=>null;")
  .replace(/import[^;]*from\s*["']@\/components\/ui["'];?/g, "const Notice=()=>null;")
  .replace(/import\s+type[^;]*;?/g, "");

const moduleUrl = "data:text/javascript;base64," + Buffer.from(runnable).toString("base64");
const {
  formatRatio,
  formatHouseholdSize,
  formatCount,
  formatSignedCount,
  formatSignedRatio,
  formatRocMonth,
  trendLabel,
  hasSufficientTrend,
  INSUFFICIENT_LABEL,
} = await import(moduleUrl);

test("ratio formatting: 0.187 -> 18.7%", () => {
  assert.equal(formatRatio(0.187), "18.7%");
  assert.equal(formatRatio(0.8), "80.0%");
});

test("null ratio -> 資料不足 (never 0)", () => {
  assert.equal(formatRatio(null), INSUFFICIENT_LABEL);
  assert.equal(formatRatio(undefined), INSUFFICIENT_LABEL);
  assert.notEqual(formatRatio(null), "0.0%");
});

test("zero ratio -> 0.0% (a real value)", () => {
  assert.equal(formatRatio(0), "0.0%");
});

test("household size null -> 資料不足, value -> N 人", () => {
  assert.equal(formatHouseholdSize(null), INSUFFICIENT_LABEL);
  assert.equal(formatHouseholdSize(2.5), "2.50 人");
  assert.equal(formatHouseholdSize(0), "0.00 人");
});

test("count formatting keeps zero and localizes", () => {
  assert.equal(formatCount(0), "0");
  assert.equal(formatCount(12345), "12,345");
  assert.equal(formatCount(null), INSUFFICIENT_LABEL);
});

test("signed count shows +/- and 0", () => {
  assert.equal(formatSignedCount(120), "+120");
  assert.equal(formatSignedCount(-45), "-45");
  assert.equal(formatSignedCount(0), "0");
  assert.equal(formatSignedCount(null), INSUFFICIENT_LABEL);
});

test("signed ratio shows +/- percent and null", () => {
  assert.equal(formatSignedRatio(0.018), "+1.8%");
  assert.equal(formatSignedRatio(-0.004), "-0.4%");
  assert.equal(formatSignedRatio(0), "0.0%");
  assert.equal(formatSignedRatio(null), INSUFFICIENT_LABEL);
});

test("ROC month formatting", () => {
  assert.equal(formatRocMonth("11507"), "民國115年07月");
  assert.equal(formatRocMonth("11512"), "民國115年12月");
  assert.equal(formatRocMonth(null), INSUFFICIENT_LABEL);
});

test("trend label mapping", () => {
  assert.equal(trendLabel("increasing"), "人口增加");
  assert.equal(trendLabel("decreasing"), "人口減少");
  assert.equal(trendLabel("stable"), "人口大致持平");
});

test("trend sufficiency needs >= 2 observed months", () => {
  assert.equal(hasSufficientTrend({ observed_month_count: 1 }), false);
  assert.equal(hasSufficientTrend({ observed_month_count: 2 }), true);
  assert.equal(hasSufficientTrend({ observed_month_count: 13 }), true);
});
