import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { initialValuationSelection, loadValuationPrerequisites } from "./valuation-prerequisites.ts";

test("embedded Valuation inherits the accepted property city, district, and road", () => {
  assert.deepEqual(initialValuationSelection({ city: "臺北市", district: "大安區", road: "敦化南路二段" }, true), {
    city: "臺北市", district: "大安區", road: "敦化南路二段",
  });
});

test("embedded Valuation without a trusted road remains unconfirmed", () => {
  assert.deepEqual(initialValuationSelection({ city: "臺北市", district: "大安區" }, true), {
    city: "臺北市", district: "大安區", road: "",
  });
});

test("Valuation never restores an unrelated fallback road", () => {
  assert.equal(initialValuationSelection(undefined, false).road, "");
});

test("Valuation prerequisite loading uses one selected context", async () => {
  const calls: string[] = [];
  const result = await loadValuationPrerequisites({
    cities: async () => { calls.push("cities"); return ["臺北市"]; },
    districts: async (city) => { calls.push(`districts:${city}`); return ["大安區"]; },
    roads: async (city, district) => { calls.push(`roads:${city}:${district}`); return ["敦化南路二段"]; },
  }, { city: "臺北市", district: "大安區", road: "敦化南路二段" });
  assert.deepEqual(calls, ["cities", "districts:臺北市", "roads:臺北市:大安區"]);
  assert.deepEqual(result, { cities: ["臺北市"], districts: ["大安區"], roads: ["敦化南路二段"] });
});
