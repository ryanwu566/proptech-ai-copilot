import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { loadValuationPrerequisites } from "./valuation-prerequisites.ts";

test("accepted road remains available when the provider omits it from options", async () => {
  const result = await loadValuationPrerequisites({
    cities: async () => ["Taipei"],
    districts: async () => ["Xinyi"],
    roads: async () => [],
  }, { city: "Taipei", district: "Xinyi", road: "Accepted Road" });

  assert.deepEqual(result.roads, ["Accepted Road"]);
});

test("accepted selection remains available when prerequisite providers fail", async () => {
  const calls: string[] = [];
  const unavailable = async (name: string): Promise<string[]> => {
    calls.push(name);
    throw new Error("provider unavailable");
  };
  const result = await loadValuationPrerequisites({
    cities: () => unavailable("cities"),
    districts: () => unavailable("districts"),
    roads: () => unavailable("roads"),
  }, { city: "Taipei", district: "Xinyi", road: "Accepted Road" });

  assert.deepEqual(calls, ["cities", "districts", "roads"]);
  assert.deepEqual(result, { cities: ["Taipei"], districts: ["Xinyi"], roads: ["Accepted Road"] });
});
