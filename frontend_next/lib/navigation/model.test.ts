import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { LEGACY_TOOL_PAGES, caseDestination, caseIdFromPath, isLegacyToolPage, nextCaseStep, parseCaseDestination } from "./model.ts";

test("legacy single-tool pages keep their direct ?tool= URLs without becoming navigation", () => {
  assert.deepEqual([...LEGACY_TOOL_PAGES], ["Market Insight Lite", "房價估算", "Map Insight Lite", "Terrain Risk", "TaxOracle", "Aegis-Credit Lite"]);
  for (const page of LEGACY_TOOL_PAGES) assert.ok(isLegacyToolPage(page), page);
  for (const value of [null, "", "儀表板", "Competition Demo", "Closed Pilot", "Professional Review", "taxoracle"]) assert.equal(isLegacyToolPage(value), false, String(value));
});

test("case destinations are allowlisted and never accept arbitrary redirects", () => {
  for (const value of [null, "", "https://evil.test", "//evil.test", "../account", "admin", "scenarios?run=true"]) assert.equal(parseCaseDestination(value), "overview");
  assert.equal(parseCaseDestination("scenarios"), "scenarios");
  assert.equal(caseDestination("a/b #?", "decision-room"), "/cases/a%2Fb%20%23%3F/decision-room");
});

test("case paths resolve the exact current case", () => {
  assert.equal(caseIdFromPath("/cases/a%2Fb/scenarios"), "a/b");
  assert.equal(caseIdFromPath("/cases"), undefined);
  assert.equal(caseIdFromPath("/cases/%E0%A4%A/overview"), undefined);
});

test("handoffs connect analysis, scenario, decision, comparison and report without inferring completion", () => {
  assert.equal(nextCaseStep("market"), "scenarios");
  assert.equal(nextCaseStep("scenarios"), "decision-room");
  assert.equal(nextCaseStep("decision-room"), "compare");
  assert.equal(nextCaseStep("report"), "overview");
});
