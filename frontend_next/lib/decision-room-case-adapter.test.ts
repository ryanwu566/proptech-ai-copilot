import assert from "node:assert/strict";
import test from "node:test";
import type { PropertyCaseWorkspace } from "./workspace/workspace-model";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./workspace/e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./workspace/legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
const feature = await import("./decision-room-case-adapter.ts").catch(() => null);

test("read-only adapter preserves saved asking price, identity and evidence limitations", () => {
  assert.ok(feature, "Decision Room case adapter must exist");
  const saved = e9Case();
  const workspace = adaptSavedCaseToWorkspace(saved);
  const repository = { readDiagnostic: () => ({ status: "ready" as const, cases: [workspace], issues: [] }), subscribe: () => () => {} };
  const result = feature.createDecisionRoomCaseAdapter(repository).read("case-a");
  assert.equal(result.status, "ready");
  if (result.status === "ready") {
    assert.equal(result.context.savedAskingPriceWan, 2480);
    assert.equal(result.context.evidence.find((r: { key: string }) => r.key === "valuation")?.usability, "unavailable");
    assert.equal(result.context.parcelStatus, "unavailable");
  }
  assert.equal(feature.createDecisionRoomCaseAdapter(repository).read("other").status, "missing");
});
test("diagnostic adapter distinguishes unavailable/corrupt/quarantined cases from missing", () => {
  assert.ok(feature);
  for (const status of ["storage_unavailable", "parse_error", "partial"] as const) {
    const adapter = feature.createDecisionRoomCaseAdapter({ readDiagnostic: () => ({ status, cases: [] as PropertyCaseWorkspace[], issues: [{ caseId: "case-a", reason: "invalid_record" as const }] }), subscribe: () => () => {} });
    assert.equal(adapter.read("case-a").status, "unreadable");
  }
});
