import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getMarketCommercialState } from "./market-result-state.ts";

test("successful covered market no-data stays no-match and insufficient, not safe or complete", () => {
  assert.deepEqual(getMarketCommercialState({ data_status: "no_data", coverage_status: "covered" } as never), {
    query: "succeeded",
    evidence: "no_match",
    completeness: "insufficient",
  });
});
test("market coverage and runtime failure remain distinct", () => {
  assert.deepEqual(getMarketCommercialState({ data_status: "no_data", coverage_status: "not_covered" } as never), {
    query: "succeeded",
    evidence: "no_coverage",
    completeness: "insufficient",
  });
  assert.deepEqual(getMarketCommercialState({ data_status: "unavailable", coverage_status: "covered" } as never), {
    query: "failed",
    evidence: "unavailable",
    completeness: "blocked",
  });
});
