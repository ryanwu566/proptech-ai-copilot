import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
const featureModule = await import("./case-evidence.ts").catch(() => null);
function project(saved = e9Case()) { return featureModule?.projectCaseEvidence(adaptSavedCaseToWorkspace(saved)); }
test("price concepts remain separate and failed valuation is unavailable", () => {
  const model = project();
  assert.equal(model?.price.asking.value, 2480);
  assert.equal(model?.price.marketMedianTotal.value, 1850);
  assert.equal(model?.price.valuationEstimate.status, "unavailable");
  assert.equal(model?.price.valuationEstimate.value, null);
  assert.equal(model?.price.valuationEstimate.missingReason, "unavailable");
});
test("zero is evidence, null is missing, and mortgage is not added twice", () => {
  const model = project();
  assert.equal(model?.finance.interestRate.value, 0);
  assert.equal(model?.finance.monthlyIncome.value, null);
  assert.equal(model?.finance.knownMonthlyHousing.value, 55111);
  assert.equal(model?.finance.breakdown[0]?.amount.value, 0);
});
test("origin mismatch invalidates route; TDX failure alone does not", () => {
  assert.equal(project()?.commute.duration.value, 24);
  assert.equal(project()?.commute.transitContext.status, "unavailable");
  const saved = e9Case(); saved.data.commuteRoute!.origin.latitude = 25;
  assert.equal(project(saved)?.commute.duration.value, null);
  assert.equal(project(saved)?.commute.duration.status, "stale");
});
test("not queried and attempted unavailable routes never become zero", () => {
  const saved = e9Case(); delete saved.data.commuteRoute;
  assert.equal(project(saved)?.commute.duration.status, "not_run");
  saved.data.commuteRoute = { ...e9Case().data.commuteRoute!, status: "unavailable", duration_min: null };
  assert.equal(project(saved)?.commute.duration.status, "unavailable");
  assert.equal(project(saved)?.commute.duration.value, null);
});
test("market time policy and finance input freshness suppress stale primary values", () => {
  const saved = e9Case(); saved.data.marketInsight!.freshness_status = "stale"; saved.data.journeyContext!.activePriceWan = 2600;
  const model = project(saved);
  assert.equal(model?.price.marketMedianTotal.value, null);
  assert.equal(model?.price.marketMedianTotal.historicalValue, 1850);
  assert.equal(model?.price.marketMedianTotal.freshness.timeRelation, "stale");
  assert.equal(model?.finance.monthlyPayment.value, null);
  assert.equal(model?.finance.monthlyPayment.historicalValue, 55111);
});
test("all seven risk sources stay fixed and no-match is not a safe conclusion", () => {
  const rows = project()?.risk;
  assert.deepEqual(rows?.map((row) => row.key), ["terrain", "flood", "landslide", "debris_flow", "liquefaction", "geological_sensitivity", "active_fault"]);
  assert.equal(rows?.[1].evidence.status, "no_match");
  assert.match(rows?.[1].evidence.limitation ?? "", /不代表安全|不等於/);
  assert.equal(rows?.[5].evidence.status, "unavailable");
  assert.equal(rows?.[6].evidence.status, "unsupported");
  assert.equal(project() && "score" in project()!, false);
});
test("gaps are deterministic and include absent domains and deleted snapshot detail", () => {
  const model = project();
  assert.ok(model?.gaps.some((gap) => gap.id === "valuation-comparables" && gap.reason === "not_preserved"));
  assert.ok(model?.gaps.some((gap) => gap.id === "demographics-population"));
  assert.deepEqual(model?.gaps, project()?.gaps);
  assert.ok(model?.gaps.every((gap) => gap.caseId === "case-a" && gap.href.startsWith("/cases/case-a/")));
});
test("snapshot tokens track evidence content independent of object key order", () => {
  assert.equal(project()?.snapshotToken, project()?.snapshotToken);
  const saved = e9Case(); saved.title = "更新標題";
  assert.notEqual(project()?.snapshotToken, project(saved)?.snapshotToken);
  const workspace = adaptSavedCaseToWorkspace(e9Case());
  assert.equal(featureModule?.projectCaseEvidence({ ...workspace, assumptions: { ...workspace.assumptions } }).snapshotToken, project()?.snapshotToken);
});
test("identity conflicts are explicit and do not promote old evidence", () => {
  const saved = e9Case(); saved.data.journeyContext!.propertyContext.addressSummary = "臺北市信義區市府路1號";
  assert.equal(project(saved)?.identity.state, "revalidation_required");
  assert.equal(project(saved)?.commute.duration.value, null);
});
test("case area changes invalidate saved finance, keeping original price basis as historical", () => {
  const saved = e9Case(); saved.inputSummary.areaPing = 40; saved.data.inputs.area_ping = 40;
  assert.equal(project(saved)?.finance.monthlyPayment.status, "stale");
  saved.data.journeyContext!.priceBasis = "manual"; saved.data.journeyContext!.activePriceWan = 2600;
  assert.equal(project(saved)?.finance.basis.historicalValue, "開價");
});
test("source links cannot expose credentials, coordinates or query-bound private data", () => {
  for (const url of ["javascript:alert(1)", "https://example.org/?api_key=secret", "https://example.org/?latitude=24&longitude=120", "https://user:secret@example.org/", "https://example.org/#token=secret"]) assert.equal(featureModule?.safeEvidenceUrl(url), null);
  assert.equal(featureModule?.safeEvidenceUrl("https://example.org/official-map"), "https://example.org/official-map");
});
test("saved identity conflict flags block evidence even when the status flag says current", () => {
  const saved = e9Case(); saved.data.propertyIdentityAnchor!.revalidation.conflicts = ["coordinates"];
  assert.equal(project(saved)?.identity.state, "revalidation_required");
  assert.equal(project(saved)?.commute.duration.value, null);
});
test("risk source update date stays distinct from its observation period", () => {
  const saved = e9Case(); saved.data.terrainReference!.layers[0].data_updated_at = "2026-09-01";
  const model = project(saved);
  assert.equal(model?.risk.find((row) => row.key === "flood")?.evidence.freshness.sourceUpdatedAt, "2026-09-01");
  assert.equal(model?.sources.find((source) => source.id === "risk-flood")?.updatedAt, "2026-09-01");
  assert.equal(model?.sources.find((source) => source.id === "risk-flood")?.period, null);
});
test("removing current area cannot borrow the saved calculation area", () => {
  const saved = e9Case(); delete saved.inputSummary.areaPing; saved.data.inputs.area_ping = 0;
  assert.equal(project(saved)?.price.area.value, null);
  assert.equal(project(saved)?.finance.monthlyPayment.status, "stale");
  assert.equal(project(saved)?.finance.monthlyPayment.value, null);
  assert.equal(project(saved)?.finance.monthlyPayment.historicalValue, 55111);
});
test("stored finance unusability survives a matching calculation fingerprint", () => {
  for (const usability of ["stale", "unavailable", "unsupported", "no_coverage"] as const) {
    const saved = e9Case(); saved.data.financeEvidence!.calculation.usability = usability;
    assert.equal(project(saved)?.finance.monthlyPayment.status, usability);
    assert.equal(project(saved)?.finance.monthlyPayment.value, null);
  }
});
