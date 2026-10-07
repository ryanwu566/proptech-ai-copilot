import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { normalizeStoredTerrainReferenceEvidence } from "../terrain-reference-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildStoredRiskEvidenceModel, buildStoredRiskEvidenceSnapshot } from "./risk-evidence-model.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
test("versioned risk metadata preserves unsupported, matched, source URL and query condition", () => {
  const reference = e9Case().data.terrainReference!;
  reference.layers = [{ ...reference.layers[0], layer_id: "active_fault", state: "limited", evidence_metadata: { version: 1, usability: "unsupported", matched: null, source_url: "https://example.org/official", query_condition: "查詢半徑 500 公尺" } }];
  const normalized = normalizeStoredTerrainReferenceEvidence(reference);
  assert.ok(normalized);
  const model = buildStoredRiskEvidenceModel(normalized, { stale: false, checkedAt: null });
  assert.equal(model.rows[0].usability, "unsupported");
  assert.equal(model.rows[0].sourceUrl, "https://example.org/official");
  assert.equal(model.rows[0].queryCondition, "查詢半徑 500 公尺");
  assert.equal(buildStoredRiskEvidenceSnapshot(model).layers[0].evidence_metadata?.usability, "unsupported");
});
test("risk metadata rejects payload additions, unsafe URLs and contradictory no-match", () => {
  for (const metadata of [
    { version: 1, usability: "no_match", matched: true, source_url: null, query_condition: "500m" },
    { version: 1, usability: "unsupported", matched: null, source_url: "javascript:alert(1)", query_condition: "500m" },
    { version: 1, usability: "unsupported", matched: null, source_url: null, query_condition: "500m", payload: "secret" },
    { version: 1, usability: "unsupported", matched: null, source_url: null, query_condition: "x".repeat(501) },
  ]) {
    const reference = e9Case().data.terrainReference!;
    reference.layers[0] = { ...reference.layers[0], evidence_metadata: metadata as never };
    assert.equal(normalizeStoredTerrainReferenceEvidence(reference), undefined);
  }
});
