import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildInputFingerprint, canCommitEvidence, computeInvalidation } from "./invalidation.ts";

test("address changes invalidate every property-bound evidence slice", () => {
  assert.deepEqual(computeInvalidation("address"), ["market", "valuation", "location", "commute", "risk", "finance"]);
});

test("price and commute changes invalidate only their dependent slices", () => {
  assert.deepEqual(computeInvalidation("active_price"), ["finance"]);
  assert.deepEqual(computeInvalidation("commute_destination"), ["commute"]);
});

test("fingerprints are stable for equivalent key order and reject changed input", () => {
  const first = buildInputFingerprint({ caseId: "case-1", revision: 2, inputs: { road: "市府路", city: "臺北市" } });
  const same = buildInputFingerprint({ inputs: { city: "臺北市", road: "市府路" }, revision: 2, caseId: "case-1" });
  const changed = buildInputFingerprint({ caseId: "case-1", revision: 3, inputs: { city: "臺北市", road: "市府路" } });

  assert.equal(first, same);
  assert.notEqual(first, changed);
});

test("late evidence cannot commit after revision or input changes", () => {
  assert.equal(canCommitEvidence({ currentRevision: 4, responseRevision: 3, currentFingerprint: "new", responseFingerprint: "new" }), false);
  assert.equal(canCommitEvidence({ currentRevision: 4, responseRevision: 4, currentFingerprint: "new", responseFingerprint: "old" }), false);
  assert.equal(canCommitEvidence({ currentRevision: 4, responseRevision: 4, currentFingerprint: "new", responseFingerprint: "new" }), true);
});
