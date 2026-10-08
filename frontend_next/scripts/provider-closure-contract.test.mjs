import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function compile(relative, dependencies = {}) {
  const source = fs.readFileSync(new URL(`../${relative}`, import.meta.url), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, require: (name) => {
    if (!(name in dependencies)) throw new Error(`Unexpected dependency: ${name}`);
    return dependencies[name];
  } });
  return module.exports;
}
const state = compile("lib/valuation-result-state.ts");
const { buildPropertySearchVisualModel } = compile("lib/property-search-visualization.ts", { "./valuation-result-state": state });
function result(sampleCount) {
  const suggestion = { city: "台北市", district: "大安區", road: "和平東路二段", sample_count: sampleCount, p25_total_price: 1200, median_total_price: 1500, p75_total_price: 1800 };
  return { search_status: "available", search_reason_code: "official_result_available", is_actionable: true, summary: { matched_count: sampleCount, district_count: 1, road_count: 1, data_source_label: "官方 PLVR" }, road_suggestions: [suggestion], district_suggestions: [], matched_transactions: [suggestion], methodology: "Historical", disclaimer: "Reference" };
}
test("Finder excludes ranges from fewer than three samples even with numeric quartiles", () => {
  assert.equal(buildPropertySearchVisualModel(result(2)).roadRanges.length, 0);
});
test("Finder renders an ordered road range with sufficient evidence", () => {
  const range = buildPropertySearchVisualModel(result(3)).roadRanges[0];
  assert.equal(range.low, 1200); assert.equal(range.median, 1500); assert.equal(range.high, 1800);
});
test("Finder provider failure cannot render stale available ranges", () => {
  const value = { ...result(5), search_status: "unavailable", search_reason_code: "provider_query_failed", is_actionable: false };
  assert.equal(buildPropertySearchVisualModel(value).roadRanges.length, 0);
});
