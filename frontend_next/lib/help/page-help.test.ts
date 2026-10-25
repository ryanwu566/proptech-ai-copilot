import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { HELP_TOPICS, helpNextSteps, helpTopicForPath } from "./page-help.ts";
// @ts-expect-error Node's native test runner uses source extensions.
import { pageGuides, pageHelpChrome, pageHelpNextLabels } from "./page-help-copy.ts";
// @ts-expect-error Node's native test runner uses source extensions.
import { pageHelpTriggerCopy } from "./page-help-trigger-copy.ts";
// @ts-expect-error Node's native test runner uses source extensions.
import { nextCaseStep } from "../navigation/model.ts";

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const href = (step: { kind: string; href?: string }) => step.href;

test("each required page resolves to its guide; pages without one show no help entry", () => {
  const expected: Record<string, string | null> = {
    "/": "home",
    "/compare": "compare",
    "/cases/case-a/overview": "overview",
    "/cases/case-a/market": "market",
    "/cases/case-a/location": "location",
    "/cases/case-a/commute-planner": "location",
    "/cases/case-a/risk": "risk",
    "/cases/case-a/finance": "money",
    "/cases/case-a/report": "report",
    "/cases/a%2Fb/risk": "risk",
    "/cases": null,
    "/cases/case-a": null,
    "/cases/case-a/evidence": null,
    "/cases/case-a/decision-room": null,
    "/cases/%E0%A4%A/overview": null,
    "/privacy": null,
    "/login": null,
  };
  for (const [path, topic] of Object.entries(expected)) assert.equal(helpTopicForPath(path), topic, path);
  assert.deepEqual([...HELP_TOPICS].sort(), ["compare", "home", "location", "market", "money", "overview", "report", "risk"]);
});

test("next steps follow the workflow handoff and stay inside the current case", () => {
  const path = (section: string) => `/cases/a%2Fb/${section}`;
  for (const [topic, section] of [["market", "market"], ["risk", "risk"], ["money", "finance"]] as const) {
    const [first] = helpNextSteps(topic, path(section));
    assert.equal(first.kind, "route");
    assert.equal(href(first), path(nextCaseStep(section)), topic);
  }
  assert.deepEqual(helpNextSteps("location", path("location")).map(href), [path("market"), path("risk")]);
  assert.deepEqual(helpNextSteps("overview", path("overview")).map(href), ["/compare", path("report")]);
  assert.deepEqual(helpNextSteps("report", path("report")).map(href), [path("overview"), "/compare"]);
  // Compare chooses its own cases; Home only moves focus to the address field and runs nothing.
  assert.deepEqual(helpNextSteps("compare", "/compare"), []);
  assert.deepEqual(helpNextSteps("home", "/"), [{ kind: "focus", selector: "#commercial-address", label: "address" }]);
});

test("every guide is complete in every locale", () => {
  for (const locale of LOCALES) {
    assert.ok(pageHelpTriggerCopy[locale].trim(), locale);
    for (const value of Object.values(pageHelpChrome[locale]) as string[]) assert.ok(value.trim(), locale);
    for (const value of Object.values(pageHelpNextLabels[locale]) as string[]) assert.ok(value.trim(), locale);
    assert.deepEqual(Object.keys(pageGuides[locale]).sort(), [...HELP_TOPICS].sort(), locale);
    for (const topic of HELP_TOPICS) {
      const guide = pageGuides[locale][topic];
      for (const field of ["title", "role", "known", "unknown", "caution", "next"] as const) assert.ok(guide[field].trim().length > 3, `${locale} ${topic} ${field}`);
      assert.equal(guide.see.length, 3, `${locale} ${topic} see`);
      for (const item of guide.see) assert.ok(item.trim(), `${locale} ${topic} see item`);
    }
  }
});

test("guides keep buyer-decision semantics: no verdicts, no safety claims, no winner", () => {
  // Words that would let a guide claim certainty the evidence does not have. Negated uses ("not safe", "不等於安全") are allowed.
  const banned = [/保證|一定安全|很安全|推薦購買|最佳選擇|值得買/, /\b(guarantee[sd]?|recommended buy|best choice|is safe)\b/i, /保証|安全です|おすすめ/, /보장|안전합니다|추천/];
  for (const locale of LOCALES) for (const topic of HELP_TOPICS) {
    const text = JSON.stringify(pageGuides[locale][topic]);
    for (const pattern of banned) assert.doesNotMatch(text, pattern, `${locale} ${topic}`);
  }
  // The pages where over-reading is most likely carry explicit boundaries.
  assert.match(pageGuides["zh-TW"].risk.caution, /未命中不等於安全/);
  assert.match(pageGuides.en.risk.caution, /Not matched does not mean safe/);
  assert.match(pageGuides["zh-TW"].compare.caution, /不會指定贏家/);
  assert.match(pageGuides.en.compare.caution, /picks a winner/);
  assert.match(pageGuides["zh-TW"].market.caution, /不是正式鑑價/);
  assert.match(pageGuides["zh-TW"].money.unknown, /不會當成零/);
});

test("the help payload stays out of every route until the guide is opened", () => {
  const launcher = fs.readFileSync(new URL("../../components/page-help/page-help-launcher.tsx", import.meta.url), "utf8");
  const imports = [...launcher.matchAll(/^import[^;]+from\s+"([^"]+)"/gm)].map((match) => match[1]);
  assert.ok(!imports.some((source) => /page-help-copy|page-help-sheet/.test(source)), "launcher statically imports the guide");
  assert.match(launcher, /import\("\.\/page-help-sheet"\)/);
  assert.doesNotMatch(launcher, /fetch\(|localStorage|sessionStorage/);
  const sheet = fs.readFileSync(new URL("../../components/page-help/page-help-sheet.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(sheet, /fetch\(|localStorage|sessionStorage|@\/lib\/api/);
});
