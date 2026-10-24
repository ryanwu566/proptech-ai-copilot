import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildEvidenceChecklist } from "./evidence-checklist.ts";
// @ts-expect-error Native TS runner extension.
const feature = await import("./compare-difference-brief.ts").catch(() => null);
const evidence = (id = "case-a") => projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case(id)));

test("an incomplete negative remains unknown in Compare instead of becoming no-match", () => {
  const item = evidence();
  item.risk = [{ ...item.risk[1], matched: false, evidence: { ...item.risk[1].evidence, status: "limited", value: "部分來源尚未完成，無法判定。" } }];
  const counts = brief(item, evidence("case-b")).categories.find((row) => row.id === "risk")!.statements[0].counts!;
  assert.equal(counts.unknown, 1);
  assert.equal(counts.noMatch, 0);
});
const brief = (...cases: ReturnType<typeof evidence>[]) => {
  assert.ok(feature, "Difference Brief builder exists");
  return feature.buildDifferenceBrief(cases);
};

test("brief retains selection order and explains the saved asking-price delta without choosing a case", () => {
  const a = evidence(); const b = evidence("case-b"); b.price.asking.value = 2180;
  const before = JSON.stringify([b, a]);
  const model = brief(b, a);
  assert.deepEqual(model.cases.map((item) => item.caseId), ["case-b", "case-a"]);
  const price = model.categories.find((item) => item.id === "price")!;
  assert.match(price.difference, /300/);
  assert.match(price.statements[0].text, /2,180/);
  assert.ok(price.statements[0].fieldIds.includes("price-asking"));
  assert.equal(JSON.stringify([b, a]), before);
  assert.doesNotMatch(JSON.stringify(model), /winner|recommend|ranking|score|最佳|勝出|較安全|值得買/i);
});

test("missing and stale market evidence never become zero or a current price-band claim", () => {
  const a = evidence(); const b = evidence("case-b");
  for (const field of [b.price.marketMedianUnit, b.price.marketP25, b.price.marketP75, b.price.sampleSize]) {
    field.historicalValue = field.value; field.value = null; field.status = "stale";
  }
  b.price.area.value = 0;
  const row = brief(a, b).categories[0];
  assert.match(row.statements[0].text, /P25|P75/);
  assert.match(row.statements[1].text, /過期/);
  assert.doesNotMatch(row.statements[1].text, /Infinity|NaN|55\.6|49\.8|0 萬元／坪/);
  assert.match(row.difference, /市場證據/);
});

test("risk counts keep matched, unknown, unavailable, unqueried, no-match and stale separate", () => {
  const a = evidence(); const b = evidence("case-b");
  const statuses = ["available", "limited", "unavailable", "not_run", "no_match", "unsupported", "stale"] as const;
  a.risk.forEach((row, index) => { row.evidence.status = statuses[index]; row.evidence.value = "saved finding"; row.matched = index === 0 || index === 6 ? true : index === 4 ? false : null; });
  const row = brief(a, b).categories.find((item) => item.id === "risk")!;
  assert.deepEqual(row.statements[0].counts, { matched: 1, unknown: 1, unavailable: 1, notQueried: 1, noMatch: 1, unsupported: 1, stale: 1 });
  assert.match(row.caution!, /未知.*安全/);
  assert.match(row.caution!, /未命中.*零風險/);
});

test("commute duration is contrasted only for the same saved destination and mode", () => {
  const a = evidence(); const b = evidence("case-b"); b.commute.duration.value = 40;
  let row = brief(a, b).categories.find((item) => item.id === "location")!;
  assert.match(row.difference, /16.*分鐘/);
  b.commute.destination.value = "高鐵臺中站";
  row = brief(a, b).categories.find((item) => item.id === "location")!;
  assert.match(row.difference, /目的地或交通方式不同/);
  assert.doesNotMatch(row.difference, /16|較快|較慢/);
  b.commute.destination.value = a.commute.destination.value; b.commute.mode.value = "大眾運輸";
  assert.match(brief(a, b).categories.find((item) => item.id === "location")!.difference, /目的地或交通方式不同/);
});

test("Money uses only saved current calculations, labels down payment and preserves unknown assumptions", () => {
  const a = evidence(); const b = evidence("case-b"); b.finance.monthlyPayment.value = 60000;
  let row = brief(a, b).categories.find((item) => item.id === "money")!;
  assert.match(row.statements[0].text, /自備款.*496/);
  assert.match(row.statements[0].text, /房貸月付.*55,111/);
  assert.match(row.difference, /4,889/);
  assert.match(row.caution!, /假設|成本/);
  b.finance.monthlyPayment.status = "stale"; // Even an inconsistent value must not escape the state gate.
  row = brief(a, b).categories.find((item) => item.id === "money")!;
  assert.match(row.statements[1].text, /過期/);
  assert.doesNotMatch(row.statements[1].text, /60,000/);
  assert.doesNotMatch(row.difference, /4,889/);
});

test("verification counts distinct evidence gaps separately from reconciled open checklist actions", () => {
  const a = evidence(); const b = evidence("case-b");
  const item = buildEvidenceChecklist(a).find((item) => item.id === "finance-scenario")!;
  a.checklistReview = { version: 1, caseId: a.caseId, entries: [{ id: item.id, state: "reviewed", identityToken: a.checklistIdentityToken!, evidenceToken: item.evidenceToken, reviewedAt: a.savedAt, updatedAt: a.savedAt }] };
  const row = brief(a, b).categories.find((item) => item.id === "verification")!;
  assert.equal(row.statements[0].counts!.gaps, a.gaps.length);
  assert.equal(row.statements[0].counts!.actions, row.statements[1].counts!.actions - 1);
  a.finance.interestRate.value = 4;
  const changed = brief(a, b).categories.find((item) => item.id === "verification")!;
  assert.equal(changed.statements[0].counts!.actions, changed.statements[1].counts!.actions);
  assert.doesNotMatch(changed.difference, /%|就緒率/);
});

test("all-missing evidence remains explicit, and three or four cases never silently reduce to a pair", () => {
  const rows = ["case-a", "case-b", "case-c", "case-d"].map((id) => {
    const saved = e9Case(id); delete saved.data.marketInsight; delete saved.data.financeEvidence; delete saved.data.commuteRoute;
    return projectCaseEvidence(adaptSavedCaseToWorkspace(saved));
  });
  for (const count of [2, 3, 4]) {
    const model = brief(...rows.slice(0, count));
    assert.ok(model.categories.every((item) => item.statements.length === count));
    assert.match(model.categories.find((item) => item.id === "money")!.difference, /缺少.*無法/);
    assert.match(model.categories.find((item) => item.id === "location")!.difference, /路線.*無法/);
  }
  assert.deepEqual(feature!.buildDifferenceBrief([rows[0]]).categories, []);
});

test("saved nearby evidence, administrative gaps and saved Money tasks survive projection without session fallback", () => {
  const saved = e9Case();
  saved.data.nearbyFacilities = { version: 1, source: "google_places", origin: { lat: 24.16525, lng: 120.64555 }, radiusM: 800, checkedAt: saved.updatedAt, partial: true, successfulCategories: ["park"], places: [] };
  const a = projectCaseEvidence(adaptSavedCaseToWorkspace(saved));
  const b = evidence("case-b"); b.comparisonContext!.administration = null;
  const model = brief(a, b);
  assert.match(model.categories.find((item) => item.id === "location")!.statements[0].text, /Google Places.*800.*部分來源/);
  assert.match(model.categories.find((item) => item.id === "location")!.statements[1].text, /行政資訊未完整保存/);
  assert.deepEqual(a.savedFinanceActions, ["提供月收入"]);
  assert.equal(model.categories.find((item) => item.id === "verification")!.statements[0].counts!.savedTasks, 1);
  const noMoney = e9Case("case-c"); delete noMoney.data.financeEvidence;
  const noMoneyEvidence = projectCaseEvidence(adaptSavedCaseToWorkspace(noMoney));
  assert.deepEqual(noMoneyEvidence.savedFinanceActions, []);
});

test("localized briefs preserve values and safety qualifications in all supported locales", () => {
  const a = evidence(); const b = evidence("case-b");
  brief(a, b);
  for (const locale of ["en", "ja", "ko"] as const) {
    const model = feature!.buildDifferenceBrief([a, b], locale);
    assert.equal(model.categories.length, 5);
    assert.match(model.categories.find((item) => item.id === "money")!.statements[0].text, /55,111/);
    assert.doesNotMatch(model.categories.find((item) => item.id === "risk")!.caution!, /未知|未命中/);
  }
});

test("equal asking prices with different saved areas explain the derived unit-price contrast", () => {
  const a = evidence(); const b = evidence("case-b"); b.price.area.value = 40;
  assert.match(brief(a, b).categories.find((item) => item.id === "price")!.difference, /單價.*20\.67/);
});

test("Money explains differing saved housing costs and capital even when mortgage payments match", () => {
  const a = evidence(); const b = evidence("case-b"); b.finance.knownMonthlyHousing.value = 65111;
  assert.match(brief(a, b).categories.find((item) => item.id === "money")!.difference, /住宅支出.*10,000/);
  b.finance.knownMonthlyHousing.value = a.finance.knownMonthlyHousing.value;
  b.finance.downPayment.value = 600;
  assert.match(brief(a, b).categories.find((item) => item.id === "money")!.difference, /自備款.*104/);
});
