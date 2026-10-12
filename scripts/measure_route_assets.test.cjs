const assert = require("node:assert/strict");
const { test } = require("node:test");
const { spawnSync } = require("node:child_process");
const { allowRequest, assertRouteView, failureDiagnostic, withCleanup } = require("./measure_route_assets.cjs");
const origin = "http://127.0.0.1:43210";
const request = (url, { headers = {}, navigation = false, method = "GET" } = {}) => ({
  url: () => url, headers: () => headers, isNavigationRequest: () => navigation, method: () => method,
});

test("failure diagnostics retain structural evidence without private error content", () => {
  const error = new Error("token=secret provider response saved address");
  error.name = "TimeoutError";
  error.code = "private-environment-value";
  const diagnostic = failureDiagnostic(error, { stage: "route_view_validation", route: "/preferences" });
  assert.deepEqual(diagnostic, { failure_stage: "route_view_validation", exception_type: "TimeoutError", current_route: "/preferences", error_code: "timeout" });
  assert.equal(JSON.stringify(diagnostic).includes("secret"), false);
});

test("failure diagnostics reject private input masquerading as a route or stage", () => {
  const diagnostic = failureDiagnostic(new Error("private"), { stage: "token-secret", route: "/cases/private-address" });
  assert.equal(diagnostic.failure_stage, "input");
  assert.equal(diagnostic.current_route, null);
});

test("invalid measurement input exits fail closed with a private diagnostic", () => {
  const result = spawnSync(process.execPath, [require.resolve("./measure_route_assets.cjs")], { input: "private invalid json", encoding: "utf8" });
  assert.equal(result.status, 1);
  assert.equal(result.stdout, "");
  assert.equal(result.stderr.includes("private"), false);
  const diagnostic = JSON.parse(result.stderr.trim().replace("ROUTE_ASSET_DIAGNOSTIC=", ""));
  assert.equal(diagnostic.failure_stage, "input");
  assert.equal(diagnostic.exception_type, "SyntaxError");
});

test("cleanup cannot replace the original route failure or its diagnostic stage", async () => {
  const state = { stage: "route_view_validation", route: "/preferences" };
  const primary = new Error("Saved fixture not hydrated: /preferences");
  await assert.rejects(withCleanup(async () => { throw primary; }, async () => { throw new TypeError("private cleanup"); }, state), (error) => {
    assert.equal(error, primary);
    assert.equal(error.routeAssetDiagnostic.failure_stage, "route_view_validation");
    assert.equal(error.routeAssetDiagnostic.error_code, "fixture_not_hydrated");
    return true;
  });
});

test("a cleanup-only failure is attributed to cleanup and remains fail closed", async () => {
  await assert.rejects(withCleanup(async () => "measured", async () => { throw new TypeError("private cleanup"); }, { stage: "route_assets", route: "/" }), (error) => {
    assert.equal(error.routeAssetDiagnostic.failure_stage, "process_cleanup");
    assert.equal(error.routeAssetDiagnostic.exception_type, "TypeError");
    assert.equal(JSON.stringify(error.routeAssetDiagnostic).includes("private"), false);
    return true;
  });
});
test("only owned local documents and static assets reach the network", () => {
  assert.equal(allowRequest(request(`${origin}/preferences`, { navigation: true }), origin), true);
  assert.equal(allowRequest(request(`${origin}/_next/static/chunks/shared.js`), origin), true);
  for (const url of [`${origin}/api/valuation`, `${origin}/cases/a?&_rsc=abc`, "https://maps.googleapis.com/maps", "http://127.0.0.1:8000/market", "https://example.com/_next/static/chunk.js"]) {
    assert.equal(allowRequest(request(url), origin), false);
  }
  assert.equal(allowRequest(request("https://example.com/", { navigation: true }), origin), false);
  assert.equal(allowRequest(request(`${origin}/api/valuation`, { navigation: true }), origin), false);
  assert.equal(allowRequest(request(`${origin}/_next/static/file.js`, { method: "POST" }), origin), false);
});
test("unrelated route prefetch is excluded even for a static chunk", () => {
  for (const headers of [{ "next-router-prefetch": "1" }, { purpose: "prefetch" }, { "sec-purpose": "prefetch;prerender" }]) {
    assert.equal(allowRequest(request(`${origin}/_next/static/chunks/scenarios.js`, { headers }), origin), false);
  }
});
test("unexpected destinations cannot masquerade as the requested route", async () => {
  await assert.rejects(assertRouteView({ url: () => `${origin}/` }, "/cases/[caseId]/risk", 1440, []), /Unexpected route destination/);
});

test("case entry waits for the required overview redirect before validating the populated view", async () => {
  let destination = `${origin}/cases/case-a`;
  const page = {
    url: () => destination,
    waitForURL: async (predicate, options) => {
      assert.equal(predicate(new URL(destination)), false);
      assert.ok(options.timeout > 0 && options.timeout <= 10_000);
      await new Promise((resolve) => setTimeout(resolve, 10));
      destination = `${origin}/cases/case-a/overview`;
      assert.equal(predicate(new URL(destination)), true);
    },
    locator: (selector) => {
      assert.ok(['[data-testid="commercial-overview-workspace"]', ".workspace-property-header"].includes(selector));
      return { waitFor: async () => {}, textContent: async () => "Synthetic case" };
    },
  };
  await assertRouteView(page, "/cases/[caseId]", 1440, [{ title: "Synthetic case" }]);
});

test("case entry cannot pass when the expected redirect never completes", async () => {
  const page = {
    url: () => `${origin}/cases/case-a`,
    waitForURL: async (predicate) => {
      assert.equal(predicate(new URL(`${origin}/cases/case-a/risk`)), false);
      throw new Error("Expected redirect timed out");
    },
  };
  await assert.rejects(assertRouteView(page, "/cases/[caseId]", 1440, []), /Expected redirect timed out/);
});
test("a successful missing-case shell cannot pass fixture view validation", async () => {
  const missingShell = {
    url: () => `${origin}/cases/case-a/risk`,
    locator: () => ({ waitFor: async () => { throw new Error("Expected populated view missing"); } }),
  };
  await assert.rejects(assertRouteView(missingShell, "/cases/[caseId]/risk", 1440, [{ title: "Synthetic case" }]), /populated view missing/);
});
