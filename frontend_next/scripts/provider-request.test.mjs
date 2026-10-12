import { test } from "node:test";
import assert from "node:assert/strict";
import { isProviderRequest } from "../e2e/helpers/provider-request.ts";

const base = "http://127.0.0.1:3100";
const request = (path, headers = {}, method = "GET") => ({
  url: () => new URL(path, base).href, headers: () => headers, method: () => method, resourceType: () => "fetch",
});
test("known Case navigation is internal only with the complete RSC signature", () => {
  for (const section of ["overview", "decision-room", "scenarios", "market", "location", "risk", "finance", "report", "planning"]) {
    const path = `/cases/case-a/${section}?_rsc=abc`;
    assert.equal(isProviderRequest(request(path, { rsc: "1" }), base), false);
    assert.equal(isProviderRequest(request(path), base), true);
    assert.equal(isProviderRequest(request(path, { rsc: "1" }, "POST"), base), true);
  }
  assert.equal(isProviderRequest(request("/compare?_rsc=abc", { rsc: "1" }), base), false);
});
test("APIs, unknown routes and external RSC remain counted", () => {
  for (const path of ["/api/analysis?_rsc=abc", "/cases/a/custom?_rsc=abc", "https://provider.example/cases/a/overview?_rsc=abc"]) {
    assert.equal(isProviderRequest(request(path, { rsc: "1" }), base), true);
  }
  assert.equal(isProviderRequest(request("/cases/a/overview", { rsc: "1" }), base), true);
});
