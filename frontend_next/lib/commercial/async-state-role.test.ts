import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { resolveAsyncStateRole } from "./async-state-role.ts";
// @ts-expect-error Native TS runner extension.
import { resolveCommercialState } from "./state.ts";

test("the narrow async adapter preserves canonical roles and conservative unknown fallback", () => {
  for (const kind of ["not_started", "input_required", "loading", "error", "no_match", "no_coverage", "unavailable", "unsupported"]) {
    const query = ["not_started", "input_required", "loading", "error"].includes(kind);
    const value = kind === "loading" ? "in_progress" : kind === "error" ? "failed" : kind;
    assert.equal(resolveAsyncStateRole(kind), resolveCommercialState(query ? "query" : "evidence", value).role);
  }
  for (const kind of [undefined, null, {}, 0, "__proto__", "constructor", "succeeded", "in_progress"]) assert.equal(resolveAsyncStateRole(kind), "error");
});
