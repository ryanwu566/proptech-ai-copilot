import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { buildDemoCases, buildDemoRooms, planDemoInstall } from "./demo-cases.ts";
// @ts-expect-error Native TS runner extension.
import { DEMO_CASE_A_ID, DEMO_CASE_B_ID, isDemoCaseId } from "./demo-case-ids.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildDifferenceBrief } from "./compare-difference-brief.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportCore } from "./report-core.ts";
// @ts-expect-error Native TS runner extension.
import { buildCasePulse } from "./case-pulse.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeNearbyFacilities } from "./nearby-facilities.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeStoredFinanceEvidence } from "./finance-persistence.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeStoredTerrainReferenceEvidence } from "../terrain-reference-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeJourneyPropertyIdentityAnchor } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { validateRoom } from "../decision-room-reader.ts";
// @ts-expect-error Native TS runner extension.
import { evidenceActionCandidates } from "../decision-room-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
import type { SavedCase } from "../case-storage";
import type { DemoInstallPlan } from "./demo-cases";
import type { WorkItem } from "../decision-room-store";

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const FORBIDDEN = /winner|recommend|ranking|score|best buy|最佳|勝出|較安全|值得買|推薦購買/i;
/** Mirror the saved-case read normalizers that do not depend on the browser. */
function normalized(saved: SavedCase): SavedCase {
  const data = saved.data;
  return { ...saved, data: { ...data,
    propertyIdentityAnchor: normalizeJourneyPropertyIdentityAnchor(data.propertyIdentityAnchor) ?? undefined,
    nearbyFacilities: normalizeNearbyFacilities(data.nearbyFacilities),
    terrainReference: normalizeStoredTerrainReferenceEvidence(data.terrainReference),
    financeEvidence: normalizeStoredFinanceEvidence(data.financeEvidence) ?? undefined,
  } };
}
function written(plan: DemoInstallPlan) {
  assert.equal(plan.kind, "write");
  return plan as Extract<DemoInstallPlan, { kind: "write" }>;
}
const workspaces = () => buildDemoCases().map((saved: SavedCase) => adaptSavedCaseToWorkspace(normalized(saved)));

test("demo snapshots use stable reserved IDs and survive every saved-evidence normalizer", () => {
  const [a, b] = buildDemoCases();
  assert.deepEqual([a.id, b.id], [DEMO_CASE_A_ID, DEMO_CASE_B_ID]);
  assert.ok(isDemoCaseId(a.id) && isDemoCaseId(b.id) && !isDemoCaseId("case-a"));
  assert.equal(JSON.stringify(buildDemoCases()), JSON.stringify(buildDemoCases()), "deterministic");
  for (const saved of [a, b]) {
    assert.ok(normalizeJourneyPropertyIdentityAnchor(saved.data.propertyIdentityAnchor), `${saved.id} anchor`);
    const nearby = normalizeNearbyFacilities(saved.data.nearbyFacilities);
    assert.ok(nearby, `${saved.id} nearby`);
    assert.equal(nearby.places.length, saved.data.nearbyFacilities!.places.length, "every demo facility is inside the 800 m radius");
    assert.equal(nearby.partial, false);
    assert.ok(normalizeStoredTerrainReferenceEvidence(saved.data.terrainReference), `${saved.id} risk`);
    assert.ok(normalizeStoredFinanceEvidence(saved.data.financeEvidence), `${saved.id} finance`);
  }
});

test("Demo A populates every workspace surface from the saved snapshot", () => {
  const [a] = workspaces();
  assert.equal(a.identity.state, "confirmed");
  for (const key of ["market", "location", "commute", "risk", "finance"] as const) assert.equal(a.evidence[key].query, "succeeded", key);
  assert.equal(a.evidence.valuation.query, "failed", "valuation stays unavailable — never fabricated");
  assert.equal(a.finance?.loan.status, "available", "finance fingerprint matches, so Money is current, not stale");
  assert.equal(a.risk?.rows.length, 5);
  const states = Object.fromEntries(a.risk!.rows.map((row: { key: string; usability: string }) => [row.key, row.usability]));
  assert.equal(states.landslide, "no_match");
  assert.equal(states.geological_sensitivity, "unavailable", "unknown stays unknown");
  const evidence = projectCaseEvidence(a);
  assert.equal(evidence.price.asking.value, 1680);
  assert.ok(evidence.price.marketMedianUnit.value);
  assert.equal(a.location.nearbyFacilities?.places.length, 8, "nearby facilities are current for the confirmed location");
  assert.equal(evidence.commute.duration.value, 24);
  assert.equal(evidence.commute.transitContext.value, "府中");
  const report = buildReportCore(evidence);
  assert.ok(JSON.stringify(report).length > 1000);
  assert.doesNotMatch(JSON.stringify(report), FORBIDDEN);
});

test("Demo B differs meaningfully and the Difference Brief names the contrasts without a winner", () => {
  const [a, b] = workspaces();
  assert.notEqual(a.assumptions.askingPriceWan, b.assumptions.askingPriceWan);
  for (const locale of LOCALES) {
    const brief = buildDifferenceBrief([projectCaseEvidence(a), projectCaseEvidence(b)], locale);
    const ids = brief.categories.map((category: { id: string }) => category.id);
    for (const id of ["price", "location", "risk", "money"]) assert.ok(ids.includes(id), `${locale} ${id}`);
    const price = brief.categories.find((category: { id: string }) => category.id === "price")!;
    assert.match(price.difference, /300/, "asking prices differ by 300 萬");
    assert.doesNotMatch(JSON.stringify(brief), FORBIDDEN);
  }
});

test("Decision Room seeds are valid, small, and link only to evidence keys the case actually offers", () => {
  const [a, b] = workspaces();
  for (const locale of LOCALES) {
    const rooms = buildDemoRooms(locale);
    for (const [index, workspace] of [a, b].entries()) {
      const room = rooms[index];
      assert.equal(validateRoom(room, workspace.caseId), null, `${locale} ${workspace.caseId}`);
      assert.ok(room.items.length >= 3 && room.items.length <= 6);
      const offered = new Set(evidenceActionCandidates(workspace).map((item: { sourceKey: string }) => item.sourceKey));
      for (const item of room.items.filter((row: WorkItem) => row.sourceKey)) {
        assert.ok(offered.has(item.sourceKey!), `${locale} ${item.sourceKey} is an outstanding evidence key`);
        const candidate = evidenceActionCandidates(workspace).find((row: { sourceKey: string }) => row.sourceKey === item.sourceKey);
        assert.equal(item.origin, candidate?.origin);
      }
    }
    const kinds = new Set(rooms[0].items.map((item: { kind: string }) => item.kind));
    for (const kind of ["verification", "question", "task"]) assert.ok(kinds.has(kind));
    const statuses = new Set(rooms[0].items.map((item: { status: string }) => item.status));
    for (const status of ["open", "in_progress", "blocked", "done"]) assert.ok(statuses.has(status));
  }
  const pulse = buildCasePulse(a, { status: "ready", room: buildDemoRooms()[0] });
  assert.ok(pulse.items.length > 0);
});

test("install plan is idempotent, isolates real cases and never evicts to make room", () => {
  const demos = buildDemoCases();
  const real = [e9Case("real-1"), e9Case("real-2")];
  const first = written(planDemoInstall({ status: "ready", cases: real }, "ensure", demos, 10));
  assert.deepEqual(first.rows.map((row: SavedCase) => row.id), [DEMO_CASE_A_ID, DEMO_CASE_B_ID, "real-1", "real-2"]);
  assert.equal(JSON.stringify(first.rows.slice(2)), JSON.stringify(real), "real cases untouched");
  assert.deepEqual(planDemoInstall({ status: "ready", cases: first.rows }, "ensure", demos, 10), { kind: "unchanged" });
  // A viewer's edit to a demo is kept by ensure and reset only by an explicit restore.
  const edited = first.rows.map((row: SavedCase) => row.id === DEMO_CASE_A_ID ? { ...row, title: "edited" } : row);
  assert.deepEqual(planDemoInstall({ status: "ready", cases: edited }, "ensure", demos, 10), { kind: "unchanged" });
  const restored = written(planDemoInstall({ status: "ready", cases: edited }, "restore", demos, 10));
  assert.equal(restored.rows.find((row: SavedCase) => row.id === DEMO_CASE_A_ID)?.title, demos[0].title);
  assert.equal(restored.rows.length, 4);
  // Deleted demo B is reinstalled alone.
  const partial = written(planDemoInstall({ status: "ready", cases: edited.filter((row: SavedCase) => row.id !== DEMO_CASE_B_ID) }, "ensure", demos, 10));
  assert.deepEqual(partial.installed, [DEMO_CASE_B_ID]);
  const full = Array.from({ length: 9 }, (_, i) => e9Case(`real-${i}`));
  assert.deepEqual(planDemoInstall({ status: "ready", cases: full }, "ensure", demos, 10), { kind: "blocked", reason: "limit_reached" });
  assert.deepEqual(planDemoInstall({ status: "parse_error", cases: [] }, "ensure", demos, 10), { kind: "blocked", reason: "storage_invalid" });
  assert.deepEqual(planDemoInstall({ status: "storage_unavailable", cases: [] }, "ensure", demos, 10), { kind: "blocked", reason: "storage_unavailable" });
});

test("titles are localized and every snapshot discloses demo status", () => {
  for (const locale of LOCALES) {
    const [a, b] = buildDemoCases(locale);
    assert.notEqual(a.title, b.title);
    assert.doesNotMatch(a.title + b.title, /proptech-demo|fixture|e9/i, "no internal codes in titles");
  }
  const [a] = buildDemoCases();
  assert.match(a.data.marketInsight!.summary, /示範快照/);
  assert.match(a.data.terrainReference!.notice, /示範快照/);
  assert.equal(a.data.journeyContext!.propertyContext.sourceLabel, "示範快照");
});
