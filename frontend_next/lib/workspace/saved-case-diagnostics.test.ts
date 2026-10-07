import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
const featureModule = await import("./saved-case-diagnostics.ts").catch(() => null);
const row = { id: "case-a", title: "案件 A", version: 1, workflowMode: "buying_wizard", activeWizardStep: "report", progress: 50, createdAt: "2026-10-01T00:00:00Z", updatedAt: "2026-10-07T00:00:00Z", inputSummary: { road: "市府路1號" }, data: { inputs: { city: "臺北市", district: "信義區", road: "市府路1號", area_ping: 30, building_type: "大樓", building_age_years: 5, floor: 8 } } };
const read = (raw: string | null) => featureModule?.parseSavedCasesDiagnostic(raw, (item) => item) ?? { status: "missing", cases: [], issues: [] };
test("valid unavailable location evidence remains an attempted query without requiring absent POI data", () => {
  const saved = { ...row, data: { ...row.data, locationInsight: { data_quality: { status: "unavailable", missing_sources: [], warnings: [] } } } };
  assert.equal(read(JSON.stringify([saved])).status, "ready");
});
test("empty storage is distinguishable from parse corruption", () => {
  assert.equal(read(null).status, "empty");
  assert.equal(read("[]").status, "empty");
  assert.equal(read("{broken").status, "parse_error");
  assert.equal(read("{}").status, "invalid_storage");
});
test("partial identity-free legacy case is valid; malformed core is not", () => {
  assert.equal(read(JSON.stringify([row])).cases.length, 1);
  for (const bad of [{ ...row, id: "../a" }, { ...row, updatedAt: "bad" }, { ...row, data: {} }, { ...row, data: { inputs: { ...row.data.inputs, area_ping: null } } }]) {
    assert.equal(read(JSON.stringify([bad])).status, "partial");
    assert.equal(read(JSON.stringify([bad])).cases.length, 0);
  }
});
test("duplicate opaque IDs quarantine every conflicting record", () => {
  const result = read(JSON.stringify([row, { ...row, title: "另一案件" }]));
  assert.equal(result.cases.length, 0);
  assert.equal(result.issues[0]?.reason, "duplicate_id");
});
test("normalization failure preserves a case-specific diagnostic", () => {
  const result = featureModule?.parseSavedCasesDiagnostic(JSON.stringify([row]), () => { throw new Error("private payload"); });
  assert.equal(result?.issues[0]?.caseId, "case-a");
  assert.equal(result?.issues[0]?.reason, "invalid_record");
  assert.doesNotMatch(JSON.stringify(result), /private payload/);
});
test("malformed preserved domain evidence is quarantined instead of becoming not-run", () => {
  for (const data of [
    { ...row.data, financeEvidence: { version: 1 } },
    { ...row.data, terrainReference: { kind: "terrain_reference" } },
    { ...row.data, locationInsight: { data_quality: { status: "limited", missing_sources: "broken" } } },
    { ...row.data, propertyIdentityAnchor: { version: 1 } },
  ]) {
    const result = read(JSON.stringify([{ ...row, data }]));
    assert.equal(result.status, "partial"); assert.equal(result.cases.length, 0);
    assert.equal(result.issues[0]?.caseId, "case-a");
  }
});
