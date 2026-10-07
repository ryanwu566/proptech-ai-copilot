import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
const featureModule = await import("./compare-report-model.ts").catch(() => null);
const evidence = (id = "case-a") => projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case(id)));
test("selection permits 2,3,4 and preserves explicit order, rejecting 5 and duplicates", () => {
  const cases = ["case-a", "case-b", "case-c", "case-d", "case-e"].map(evidence);
  for (const ids of [["case-b", "case-a"], ["case-c", "case-a", "case-b"], ["case-d", "case-c", "case-b", "case-a"]]) {
    const model = featureModule?.buildComparisonModel(cases, ids);
    assert.equal(model?.status, "ready");
    assert.deepEqual(model?.cases.map((row) => row.caseId), ids);
  }
  assert.equal(featureModule?.buildComparisonModel(cases, cases.map((row) => row.caseId)).status, "too_many");
  assert.equal(featureModule?.buildComparisonModel(cases, ["case-a", "case-a"]).status, "duplicate");
  assert.equal(featureModule?.buildComparisonModel(cases, ["case-a"]).status, "too_few");
  assert.equal(featureModule?.buildComparisonModel(cases, ["case-a", "missing"]).status, "case_not_found");
});
test("commute warns for different destinations, modes and unavailable route evidence", () => {
  const a = evidence(); const b = evidence("case-b");
  assert.ok(featureModule?.buildComparisonModel([a, b], [a.caseId, b.caseId]).warnings.some((warning) => /保存路線|路況/.test(warning)));
  b.commute.destination.value = "高鐵臺中站";
  assert.ok(featureModule?.buildComparisonModel([a, b], [a.caseId, b.caseId]).warnings.some((warning) => /目的地不同/.test(warning)));
  b.commute.destination.value = "臺中車站"; b.commute.mode.value = "大眾運輸";
  assert.ok(featureModule?.buildComparisonModel([a, b], [a.caseId, b.caseId]).warnings.some((warning) => /交通方式不同/.test(warning)));
  b.commute.duration.value = null;
  assert.ok(featureModule?.buildComparisonModel([a, b], [a.caseId, b.caseId]).warnings.some((warning) => /有效路線/.test(warning)));
});
test("finance differences remain adjacent assumptions without affordability conclusion", () => {
  const a = evidence(); const b = evidence("case-b"); b.finance.interestRate.value = 2.2; b.finance.term.value = 20; b.finance.downPaymentRatio.value = 30;
  const model = featureModule?.buildComparisonModel([a, b], [a.caseId, b.caseId]);
  assert.ok(model?.warnings.some((warning) => /假設不同/.test(warning)));
  assert.ok(model?.sections.find((section) => section.id === "finance")?.rows.some((row) => row.id === "finance-rate"));
  assert.equal(model && "bestCaseId" in model, false);
});
test("report has all nine sections, deterministic summary and limits without valuation requirement", () => {
  const a = evidence(); const model = featureModule?.buildReportModel(a, "2026-10-07T04:00:00Z");
  assert.equal(model?.status, "ready_with_limits");
  assert.equal(model?.sections.length, 9);
  assert.equal(model?.generatedAt, "2026-10-07T04:00:00Z");
  assert.deepEqual(model?.summary, featureModule?.buildReportModel(a, "2026-10-07T04:00:00Z").summary);
  assert.equal(featureModule?.buildReportModel(null).status, "case_not_found");
  a.identity.state = "revalidation_required";
  assert.equal(featureModule?.buildReportModel(a).status, "identity_requires_revalidation");
});
test("fully bounded usable report reaches ready; identity-free legacy remains blocked", () => {
  const full = evidence(); full.gaps = [];
  assert.equal(featureModule?.buildReportModel(full).status, "ready");
  full.identity.state = "unconfirmed";
  assert.equal(featureModule?.buildReportModel(full).status, "identity_requires_revalidation");
  assert.equal(featureModule?.buildComparisonModel([full, evidence("case-b")], ["case-a", "case-b"]).status, "identity_requires_revalidation");
});
test("report checks change/deletion/invalidity without mutating frozen evidence", () => {
  const frozen = evidence(); const current = evidence(); const token = frozen.snapshotToken;
  assert.equal(featureModule?.assessReportSnapshot(frozen, current, false), "unchanged");
  current.snapshotToken = "new"; current.finance.monthlyPayment.value = 99999;
  assert.equal(featureModule?.assessReportSnapshot(frozen, current, false), "snapshot_changed");
  assert.equal(frozen.finance.monthlyPayment.value, 55111);
  assert.equal(frozen.snapshotToken, token);
  assert.equal(featureModule?.assessReportSnapshot(frozen, null, false), "case_not_found");
  assert.equal(featureModule?.assessReportSnapshot(frozen, null, true), "invalid_case");
});
