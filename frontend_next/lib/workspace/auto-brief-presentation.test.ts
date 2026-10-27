import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { AUTO_BRIEF_BEAT_MS, AUTO_BRIEF_SCENES, nextScene, plotNearby, POI_REVEAL_ORDER, presentRail, railItems, sceneHold, sceneStep, SHOWCASE_SCENE_MS, targetScene } from "./auto-brief-presentation.ts";
// @ts-expect-error Native TS runner extension.
import { AUTO_BRIEF_STEP_IDS } from "./auto-brief.ts";
import type { AutoBriefRun, AutoBriefStepId, AutoBriefStepStatus } from "./auto-brief";
import type { AutoBriefScene } from "./auto-brief-presentation";
import type { NearbyFacilitiesEvidence } from "./nearby-facilities";

function run(status: AutoBriefRun["status"], currentStep: AutoBriefStepId | null, statuses: Partial<Record<AutoBriefStepId, AutoBriefStepStatus>> = {}): AutoBriefRun {
  return { runId: "r", caseId: "case-a", mode: "real_case", status, anchorId: status === "prechecking" ? null : "journey-browser-x", startedAt: "t", updatedAt: "t", currentStep, reason: null, gapCount: null,
    steps: AUTO_BRIEF_STEP_IDS.map((id: AutoBriefStepId) => ({ id, status: statuses[id] ?? "pending", startedAt: statuses[id] ? "t" : null, completedAt: null, reason: null, retryable: false })) };
}

test("target scene follows the real run: precheck, current step, ending, halt", () => {
  assert.equal(targetScene(run("prechecking", null)), "lockin");
  assert.equal(targetScene(run("running", "market", { market: "running" })), "market");
  assert.equal(targetScene(run("running", "location")), "location");
  assert.equal(targetScene(run("running", "brief")), "converge");
  assert.equal(targetScene(run("completed", null)), "complete");
  assert.equal(targetScene(run("completed_with_gaps", null)), "complete");
  for (const status of ["cancelled", "interrupted", "needs_location", "failed"] as const) assert.equal(targetScene(run(status, null)), "halted");
});

test("the displayed scene advances one beat at a time and is never ahead of the run", () => {
  const order = (scene: AutoBriefScene) => (AUTO_BRIEF_SCENES as readonly string[]).indexOf(scene);
  for (const target of AUTO_BRIEF_SCENES) {
    let shown: AutoBriefScene = "lockin";
    for (let beat = 0; beat < 10 && shown !== target; beat += 1) {
      const next = nextScene(shown, target, true);
      assert.ok(order(next.scene) <= order(target), `${next.scene} ahead of ${target}`);
      assert.equal(order(next.scene) - order(shown), 1);
      shown = next.scene;
    }
    assert.equal(shown, target);
  }
});

test("skip animation and reduced motion jump straight to the real scene; restarts and halts reset immediately", () => {
  assert.deepEqual(nextScene("lockin", "complete", false), { scene: "complete", wait: false });
  assert.deepEqual(nextScene("complete", "lockin", true), { scene: "lockin", wait: false });
  assert.deepEqual(nextScene("risk", "halted", true), { scene: "halted", wait: false });
  assert.deepEqual(nextScene("halted", "market", true), { scene: "market", wait: false });
  assert.deepEqual(nextScene("money", "money", true), { scene: "money", wait: false });
});

test("each evidence scene is bound to its own step", () => {
  assert.equal(sceneStep("market"), "market");
  assert.equal(sceneStep("location"), "location");
  assert.equal(sceneStep("risk"), "risk");
  assert.equal(sceneStep("money"), "money");
  assert.equal(sceneStep("converge"), "brief");
  assert.equal(sceneStep("lockin"), null);
  assert.equal(sceneStep("complete"), null);
});

test("progress rail keeps every state distinct and marks only the real current step", () => {
  const items = railItems(run("running", "risk", { market: "no_data", location: "partial", risk: "running" }));
  assert.deepEqual(items.map((item: { id: string }) => item.id), ["lockin", "market", "location", "risk", "money", "brief"]);
  assert.deepEqual(items.map((item: { status: string }) => item.status), ["available", "no_data", "partial", "running", "pending", "pending"]);
  assert.deepEqual(items.filter((item: { current: boolean }) => item.current).map((item: { id: string }) => item.id), ["risk"]);
  assert.equal(railItems(run("prechecking", null))[0].status, "running");
  assert.equal(railItems({ ...run("needs_location", null), anchorId: null })[0].status, "needs_location");
  assert.equal(railItems(run("completed_with_gaps", null, { money: "needs_input" })).find((item: { id: string }) => item.id === "money")?.status, "needs_input");
});

test("POIs come only from saved evidence, ordered property → transport → schools → daily → parks / medical / food", () => {
  const origin = { lat: 24.16525, lng: 120.64555 };
  const place = (id: string, kind: string, dLat: number, dLng: number, distanceM: number) => ({ id, name: id, category: "transport", kind, lat: origin.lat + dLat, lng: origin.lng + dLng, distanceM });
  const evidence = { version: 1, source: "google_places", origin, radiusM: 800, checkedAt: "t", partial: false, successfulCategories: [],
    places: [place("f", "food", 0.001, 0, 110), place("r", "rail", 0, 0.002, 200), place("e", "education", -0.002, 0, 220), place("far", "park", 0.5, 0.5, 799)] } as unknown as NearbyFacilitiesEvidence;
  const plot = plotNearby(evidence);
  assert.deepEqual(plot.groups.map((row: { group: string }) => row.group), ["transit", "education", "parks", "food"]);
  assert.deepEqual(plot.groups.map((row: { wave: number }) => row.wave), [0, 1, 2, 3]);
  for (const point of plot.points) { assert.ok(point.x >= 4 && point.x <= 96); assert.ok(point.y >= 4 && point.y <= 96); }
  const rail = plot.points.find((point: { id: string }) => point.id === "r")!;
  assert.ok(rail.x > 50 && Math.abs(rail.y - 50) < 1, "east of the property");
  assert.deepEqual(plotNearby(undefined), { points: [], groups: [] });
  assert.equal(POI_REVEAL_ORDER[0], "transit");
});

test("showcase pacing tells the story in about 45–60s; real cases keep the short beat", () => {
  const story = (["lockin", "market", "location", "risk", "money", "converge"] as const).reduce((total, scene) => total + sceneHold(scene, true), 0);
  assert.ok(story >= 45_000 && story <= 60_000, `showcase ${story}ms`);
  assert.equal(SHOWCASE_SCENE_MS.location > SHOWCASE_SCENE_MS.market, true);
  for (const scene of AUTO_BRIEF_SCENES) assert.equal(sceneHold(scene, false), AUTO_BRIEF_BEAT_MS);
  assert.equal(sceneHold("complete", true), AUTO_BRIEF_BEAT_MS);
});

test("showcase rail reveals chapters as they are presented and never ahead of the run", () => {
  const done = run("completed_with_gaps", null, { market: "available", location: "partial", risk: "partial", money: "needs_input", brief: "available" });
  const atMarket = presentRail(railItems(done), "market");
  assert.deepEqual(atMarket.map((item: { status: string }) => item.status), ["available", "available", "pending", "pending", "pending", "pending"]);
  assert.deepEqual(atMarket.filter((item: { current: boolean }) => item.current).map((item: { id: string }) => item.id), ["market"]);
  assert.deepEqual(presentRail(railItems(done), "money").map((item: { status: string }) => item.status), ["available", "available", "partial", "partial", "needs_input", "pending"]);
  assert.deepEqual(presentRail(railItems(done), "complete"), railItems(done));
});
