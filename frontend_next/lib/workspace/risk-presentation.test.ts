import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { riskSummaryCounts } from "./risk-presentation.ts";

test("pre-query risk summary is explicit unknown rather than zero findings", () => {
  assert.deepEqual(riskSummaryCounts(null), { material: "尚未查詢", unknown: "尚未查詢" });
});

test("queried risk summary preserves real zero counts", () => {
  assert.deepEqual(riskSummaryCounts({ materialEvidenceCount: 0, unknownEvidenceCount: 2 }), { material: 0, unknown: 2 });
});
