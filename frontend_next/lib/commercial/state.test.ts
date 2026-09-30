import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { COMMERCIAL_STATE_REGISTRIES, deriveRiskInterpretation, resolveCommercialState, type CommercialStateAxis } from "./state.ts";

test("all six commercial axes expose bounded canonical states with zh-TW contracts", () => {
  const axes: CommercialStateAxis[] = ["query", "evidence", "completeness", "risk", "identity", "readiness"];

  assert.deepEqual(Object.keys(COMMERCIAL_STATE_REGISTRIES), axes);
  for (const axis of axes) {
    for (const contract of Object.values(COMMERCIAL_STATE_REGISTRIES[axis])) {
      assert.equal(contract.value.length > 0, true);
      assert.equal(contract.label["zh-TW"].length > 0, true);
      assert.equal(contract.meaning.length > 0, true);
      assert.equal(typeof contract.actionable, "boolean");
      assert.match(contract.role, /^(neutral|information|warning|error|success|disabled)$/);
    }
  }
});

test("unrecognized values fail closed on every axis without leaking the raw enum", () => {
  const expected = {
    query: "failed",
    evidence: "unavailable",
    completeness: "blocked",
    risk: "unknown",
    identity: "conflict",
    readiness: "blocked",
  } as const;

  for (const [axis, fallback] of Object.entries(expected) as Array<[CommercialStateAxis, string]>) {
    const resolved = resolveCommercialState(axis, "BACKEND_RAW_STATE");
    assert.equal(resolved.value, fallback);
    assert.equal(resolved.recognized, false);
    assert.equal(resolved.actionable, true);
    assert.doesNotMatch(resolved.label["zh-TW"], /BACKEND_RAW_STATE/);
  }
});

test("query success remains independent from evidence usability, analysis completeness, and safety", () => {
  const query = resolveCommercialState("query", "succeeded");
  const evidence = resolveCommercialState("evidence", "no_match");
  const completeness = resolveCommercialState("completeness", "insufficient", { task: "初步客戶討論" });

  assert.equal(query.value, "succeeded");
  assert.equal(evidence.value, "no_match");
  assert.equal(completeness.value, "insufficient");
  assert.equal(deriveRiskInterpretation({ evidenceStatus: "no_match", signal: "no_match" }), "unknown");
});

test("no match yields a scoped no-signal only when the domain explicitly defines that meaning", () => {
  assert.equal(deriveRiskInterpretation({ evidenceStatus: "no_match", signal: "no_match" }), "unknown");
  assert.equal(deriveRiskInterpretation({ evidenceStatus: "no_match", signal: "no_match", noMatchMeansNoDefinedSignal: true }), "no_identified_signal");
  assert.equal(deriveRiskInterpretation({ evidenceStatus: "unavailable", signal: "no_match", noMatchMeansNoDefinedSignal: true }), "unknown");

  assert.equal(resolveCommercialState("evidence", "no_match").label["zh-TW"], "查無符合資料");
  assert.equal(resolveCommercialState("evidence", "unavailable").label["zh-TW"], "目前無法取得證據");
  assert.doesNotMatch(resolveCommercialState("risk", "no_identified_signal").label["zh-TW"], /安全|低風險/);
});
