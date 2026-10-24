import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { AMBIENT_VARIANTS, PHASE_START, WAKE, ambientVariantForPath, nextWake, wakeDelay } from "./scene-model.ts";

test("place-led case routes map to their own ambient scene", () => {
  for (const [segment, variant] of [["overview", "overview"], ["market", "market"], ["location", "location"], ["risk", "risk"]]) {
    assert.equal(ambientVariantForPath(`/cases/case%2Fa/${segment}`), variant, segment);
  }
});

test("other routes stay plain; Home places its own scene", () => {
  // Decision surfaces read as paper: no photograph behind Money, Decision Room, Report or Compare.
  for (const path of ["/compare", "/compare/", "/cases/a/finance", "/cases/a/decision-room", "/cases/a/report"]) assert.equal(ambientVariantForPath(path), null, path);
  for (const path of [null, undefined, "", "/", "/cases", "/cases/a", "/cases/a/evidence", "/cases/a/scenarios", "/cases/a/planning", "/cases/a/commute-planner", "/cases/a/market/extra", "/account", "/admin/users", "/compare-old"]) {
    assert.equal(ambientVariantForPath(path), null, String(path));
  }
});

test("every scene shares one ordered REVEAL → FOCUS → LOCK → RESOLVE timeline", () => {
  assert.deepEqual(Object.keys(PHASE_START), ["reveal", "focus", "lock", "resolve"]);
  assert.equal(PHASE_START.focus, 700);
  const starts = Object.values(PHASE_START);
  assert.deepEqual(starts, [...starts].sort((a, b) => a - b));
  assert.ok(PHASE_START.resolve <= 4000);
});

test("photographs never schedule decorative wakes", () => {
  assert.deepEqual(Object.keys(WAKE).sort(), [...AMBIENT_VARIANTS].sort());
  assert.equal(WAKE.home, null);
  assert.equal(WAKE.report, null);
  assert.ok(Object.values(WAKE).every((rhythm) => rhythm === null), "photography settles once; no decorative wake or loop");
  for (const rhythm of Object.values(WAKE)) {
    if (!rhythm) continue;
    assert.ok(rhythm.every[0] >= 8000 && rhythm.every[1] <= 16000);
    assert.ok(rhythm.hold < rhythm.every[0], "a wake ends well before the next can start");
    assert.ok(rhythm.count >= 1 && rhythm.count <= 4);
  }
});

test("the next wake never repeats the previous relationship and delays stay in range", () => {
  for (const value of [0, 0.25, 0.5, 0.99]) {
    const random = () => value;
    for (let previous = 0; previous < 4; previous++) {
      const next = nextWake(previous, 4, random);
      assert.ok(next >= 0 && next < 4);
      assert.notEqual(next, previous);
    }
    assert.equal(nextWake(0, 1, random), 0);
    const delay = wakeDelay({ count: 1, every: [8000, 12000], hold: 3600 }, random);
    assert.ok(delay >= 8000 && delay <= 12000);
  }
});
