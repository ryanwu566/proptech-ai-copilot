import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getExperienceCommercialState } from "./experience-architecture.ts";

test("legacy ready maps to usable evidence without claiming complete analysis, safety, or universal readiness", () => {
  assert.deepEqual(getExperienceCommercialState("ready"), {
    query: "succeeded",
    evidence: "usable",
    completeness: "partial",
    risk: "not_assessed",
  });
});
test("legacy no-match and unavailable states remain conservative", () => {
  assert.deepEqual(getExperienceCommercialState("no_match"), {
    query: "succeeded",
    evidence: "no_match",
    completeness: "insufficient",
    risk: "unknown",
  });
  assert.equal(getExperienceCommercialState("unavailable").risk, "unknown");
});
