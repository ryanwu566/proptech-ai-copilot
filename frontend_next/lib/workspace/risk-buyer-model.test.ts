import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
// @ts-expect-error Native Node TypeScript tests require source extensions.
import { buildRiskBuyerModel, buyerState } from "./risk-buyer-model.ts";
import type { RiskEvidenceModel, RiskEvidenceRow } from "./risk-evidence-model";

const row: RiskEvidenceRow = { key: "flood", label: "source label", queryStatus: "succeeded", usability: "no_match", interpretation: "unknown", matched: false, result: "bounded result", source: "source", sourceLevel: "unknown", effectivePeriod: "unknown", limitation: "source limitation", nextVerification: "old action", coverage: "covered" };
const evidence = (rows: RiskEvidenceRow[], status: RiskEvidenceModel["freshness"]["status"] = "current_query") => ({ rows, freshness: { status, checkedAt: "2026-10-01" } }) as RiskEvidenceModel;

test("every usability state stays distinct and never becomes a safety finding", () => {
  const states = { no_match: "NO MATCH", no_coverage: "NO COVERAGE", unverified: "UNKNOWN", unavailable: "UNAVAILABLE", unsupported: "UNSUPPORTED", limited: "LIMITED", stale: "STALE", usable: "UNKNOWN" } as const;
  for (const [usability, expected] of Object.entries(states)) {
    assert.equal(buyerState({ ...row, usability } as RiskEvidenceRow), expected);
  }
  assert.equal(buyerState({ ...row, usability: "usable", matched: true }), "MATCHED");
  assert.equal(buyerState(undefined), "NOT QUERIED");
});

test("pre-query has no numeric count and six unqueried topics", () => {
  const model = buildRiskBuyerModel(null);
  assert.equal(model.verificationCount, null);
  assert.equal(model.cards.length, 6);
  assert.ok(model.cards.every((card) => card.state === "NOT QUERIED"));
});

test("NO MATCH keeps routine actions; count is distinct hazards, excluding terrain and building", () => {
  const model = buildRiskBuyerModel(evidence([row, row, { ...row, key: "terrain" }]));
  assert.equal(model.verificationCount, 6);
  assert.equal(model.cards.find((card) => card.key === "flood")?.state, "NO MATCH");
  assert.ok(model.cards.every((card) => card.actionKey === card.key));
  assert.ok(model.cards.every((card) => !["terrain", "building"].includes(card.key)));
});

test("saved summaries and stale evidence never acquire current freshness or missing provenance", () => {
  for (const status of ["saved_summary", "stale"] as const) {
    const projected = buildRiskBuyerModel(evidence([row], status)).cards[0];
    assert.equal(projected.freshness, status);
    assert.equal(projected.evidence, row);
    assert.equal(projected.evidence?.sourceUrl, undefined);
    assert.equal(projected.evidence?.datasetVersion, undefined);
    assert.equal(projected.state, status === "stale" ? "STALE" : "NO MATCH");
    const missing = buildRiskBuyerModel(evidence([row], status)).cards[1];
    assert.equal(missing.state, "NOT QUERIED");
    assert.equal(missing.freshness, "not_queried");
  }
});

test("projection preserves original provenance without reconstructing it", () => {
  const original = { ...row, sourceAgency: "agency", sourceUrl: "https://example.gov/evidence", sourceClassification: "official category", datasetVersion: "v2", queryCondition: "original condition", sourceUpdatedAt: "2026", categories: [{ official: "original", canonical: "category" }] };
  const before = JSON.stringify(original);
  const projected = buildRiskBuyerModel(evidence([original])).cards[0];
  assert.equal(projected.freshness, "current_query");
  assert.equal(projected.evidence, original);
  assert.equal(JSON.stringify(original), before);
  assert.equal(buildRiskBuyerModel(evidence([])).cards[0].evidence, undefined);
});

test("buyer model has only type dependencies and no API, provider or storage writes", () => {
  const source = readFileSync(new URL("./risk-buyer-model.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /import\s+(?!type\b)|fetch\s*\(|localStorage|terrainRiskAnalyze|updateSavedCase|from\s+["'][^"']*(?:api|storage|provider)/);
});
