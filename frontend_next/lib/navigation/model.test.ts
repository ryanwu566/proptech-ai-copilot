import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { PRODUCT_ENTRIES, caseDestination, caseIdFromPath, filterEntries, nextCaseStep, parseCaseDestination, productHref } from "./model.ts";

test("all implemented product areas have one discoverable destination", () => {
  const ids: string[] = PRODUCT_ENTRIES.map((entry) => entry.id);
  for (const id of ["home", "property", "market", "valuation", "location", "risk", "finance", "scenarios", "decision-room", "compare", "report", "preferences", "places", "commute-planner", "cases", "account", "tax", "credit", "identity", "planning"]) assert.ok(ids.includes(id), id);
  assert.equal(new Set(ids).size, ids.length);
  assert.ok(!ids.some((id) => /admin|billing|copilot/i.test(id)));
});

test("case destinations are allowlisted and never accept arbitrary redirects", () => {
  for (const value of [null, "", "https://evil.test", "//evil.test", "../account", "admin", "scenarios?run=true"]) assert.equal(parseCaseDestination(value), "overview");
  assert.equal(parseCaseDestination("scenarios"), "scenarios");
  assert.equal(caseDestination("a/b #?", "decision-room"), "/cases/a%2Fb%20%23%3F/decision-room");
});

test("case actions keep the exact current case or ask the user to choose", () => {
  const entry = PRODUCT_ENTRIES.find((entry) => entry.id === "scenarios")!;
  assert.equal(productHref(entry), "/cases?next=scenarios");
  assert.equal(productHref(entry, "case-a"), "/cases/case-a/scenarios");
  assert.equal(caseIdFromPath("/cases/a%2Fb/scenarios"), "a/b");
  assert.equal(caseIdFromPath("/cases"), undefined);
  assert.equal(caseIdFromPath("/cases/%E0%A4%A/overview"), undefined);
});

test("search uses localized visible labels, ignores case and matches all words", () => {
  const entries = PRODUCT_ENTRIES.filter((entry) => ["market", "report"].includes(entry.id));
  const label = (id: string) => id === "market" ? "Price and market" : "Case report";
  assert.deepEqual(filterEntries(entries, " MARKET price ", label).map((entry) => entry.id), ["market"]);
  assert.equal(filterEntries(entries, "no-such-feature", label).length, 0);
  assert.equal(filterEntries(entries, " ", label).length, 2);
});

test("handoffs connect analysis, scenario, decision, comparison and report without inferring completion", () => {
  assert.equal(nextCaseStep("market"), "scenarios");
  assert.equal(nextCaseStep("scenarios"), "decision-room");
  assert.equal(nextCaseStep("decision-room"), "compare");
  assert.equal(nextCaseStep("report"), "overview");
});
