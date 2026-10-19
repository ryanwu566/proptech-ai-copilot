import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence, evidenceFields } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportModel } from "./compare-report-model.ts";
// @ts-expect-error Native TS runner extension.
import { reportEvidenceReferences } from "./document-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportCore, REPORT_CORE_LIMITS } from "./report-core.ts";
// @ts-expect-error Native TS runner extension.
import { reportCoreCopy } from "./report-core-copy.ts";

import type { ReportCore } from "./report-core";

type Mutate = (row: ReturnType<typeof e9Case>) => void;
function build(mutate: Mutate = () => {}, id = "case-a") {
  const row = e9Case(id); mutate(row);
  const evidence = projectCaseEvidence(adaptSavedCaseToWorkspace(row));
  return { evidence, core: buildReportCore(evidence) as ReportCore };
}
const groups = (core: ReportCore) => [...core.pages[1].groups, ...core.pages[2].groups];
const facts = (core: ReportCore, id: string) => groups(core).find((group) => group.id === id)!.facts;

test("core report orders decision brief, market/location/risk, then finance and next steps", () => {
  const { core } = build();
  assert.equal(core.contract, "report-core-v1");
  assert.deepEqual(core.pages.map((page) => [page.id, page.number]), [["decision", 1], ["market_location_risk", 2], ["finance_next", 3]]);
  assert.deepEqual(core.pages[1].groups.map((group) => group.id), ["market", "location", "risk"]);
  assert.deepEqual(core.pages[2].groups.map((group) => group.id), ["finance"]);
});

test("appendix keeps every detailed report section in the report's own order", () => {
  const { evidence, core } = build();
  const model = buildReportModel(evidence, "2026-10-07T04:00:00Z");
  assert.deepEqual(core.appendix, model.sections.map((section: { id: string }) => section.id));
  assert.equal(new Set(core.appendix).size, 9);
});

test("core facts are the saved evidence fields themselves, never new or altered values", () => {
  const { evidence, core } = build();
  const saved = new Map(evidenceFields(evidence).map((field: { id: string }) => [field.id, field]));
  for (const group of groups(core)) for (const field of group.facts) {
    assert.ok(saved.has(field.id), `${group.id} ${field.id} is a saved field`);
    assert.equal(field, saved.get(field.id), `${field.id} is passed through unchanged`);
  }
  assert.equal(facts(core, "market").find((field) => field.id === "price-asking")!.value, 2480);
});

test("every core value resolves to the report's existing citation list", () => {
  const { evidence, core } = build();
  const citations = reportEvidenceReferences(evidence);
  for (const field of groups(core).flatMap((group) => group.facts).filter((item) => item.value !== null)) {
    assert.ok(citations.some((citation: { observationId: string; caseId: string }) => citation.observationId === field.id && citation.caseId === evidence.caseId), `${field.id} is cited`);
  }
});

test("missing market evidence stays listed with its unknown state instead of being dropped or filled", () => {
  const { core } = build((row) => { delete row.data.marketInsight; });
  const market = facts(core, "market");
  for (const id of ["market-unit", "market-p25", "market-p75", "market-samples"]) {
    const field = market.find((item) => item.id === id)!;
    assert.ok(field, `${id} still listed`);
    assert.equal(field.value, null);
    assert.notEqual(field.status, "available");
  }
});

test("every risk source is listed; a current match leads and nothing unresolved is dropped", () => {
  const { evidence, core } = build();
  const risk = facts(core, "risk");
  assert.equal(risk.length, evidence.risk.length);
  assert.deepEqual(new Set(risk.map((field) => field.id)), new Set(evidence.risk.map((row: { evidence: { id: string } }) => row.evidence.id)));
  const target = evidence.risk[evidence.risk.length - 1];
  for (const row of evidence.risk) row.matched = row === target ? true : row.matched === true ? false : row.matched;
  target.evidence.value ??= "符合"; target.evidence.status = "available";
  assert.equal(facts(buildReportCore(evidence), "risk")[0].id, target.evidence.id);
  // A stale match is not promoted ahead of other sources.
  target.evidence.status = "stale";
  assert.deepEqual(facts(buildReportCore(evidence), "risk").map((field) => field.id), evidence.risk.map((row: { evidence: { id: string } }) => row.evidence.id));
});

test("next steps cover every listed gap by area without losing counts", () => {
  const { evidence, core } = build();
  const steps = core.pages[2].nextSteps;
  const gaps = evidence.gaps.filter((gap: { caseId: string }) => gap.caseId === evidence.caseId);
  assert.equal(core.pages[2].gapTotal, gaps.length);
  assert.equal(steps.reduce((sum, step) => sum + step.count, 0), gaps.length);
  for (const step of steps) {
    assert.ok(step.items.length <= REPORT_CORE_LIMITS.itemsPerStep);
    assert.equal(step.items.length + step.more, step.count);
    const own = gaps.filter((gap: { domain: string }) => gap.domain === step.domain);
    assert.deepEqual(new Set(step.actions), new Set(own.map((gap: { nextAction: string }) => gap.nextAction)));
    assert.equal(step.href, `/cases/${encodeURIComponent(evidence.caseId)}/${step.domain}`);
  }
  // Identity is always an open verification item, never silently confirmed.
  assert.ok(steps.find((step) => step.domain === "overview")!.items.some((item) => item.gapId === "identity-legal"));
});

test("core model is deterministic, input-preserving and provider-free", () => {
  const { evidence } = build();
  const before = JSON.stringify(evidence);
  const original = globalThis.fetch;
  globalThis.fetch = (() => { throw new Error("provider call"); }) as typeof fetch;
  try {
    assert.equal(JSON.stringify(buildReportCore(evidence)), JSON.stringify(buildReportCore(structuredClone(evidence))));
  } finally { globalThis.fetch = original; }
  assert.equal(JSON.stringify(evidence), before);
  const source = readFileSync(new URL("./report-core.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /fetch\(|localStorage|sessionStorage|Date\.now|new Date\(|XMLHttpRequest|api\//);
});

test("report view keeps the appendix, its full provenance and the single citation register", () => {
  const view = readFileSync(new URL("../../components/evidence/report-view.tsx", import.meta.url), "utf8");
  const order = ["<ReportExecutive", "<ReportCorePages", 'data-testid="report-appendix"', "<ReportCitationReferences"].map((marker) => view.indexOf(marker));
  assert.ok(order.every((index) => index > 0), "all report parts render");
  assert.deepEqual([...order].sort((a, b) => a - b), order, "executive → core → appendix → references");
  assert.match(view, /<EvidenceValue field=\{row\.cells\[0\]\} \/>/, "appendix tables keep full per-field provenance");
  const core = readFileSync(new URL("../../components/evidence/report-core.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(core, /<tr|role="row"|report-manual-review|report-limits|report-comparable-explanation/, "core pages never duplicate appendix rows or single-instance anchors");
  const css = readFileSync(new URL("../../components/evidence/evidence.module.css", import.meta.url), "utf8");
  assert.match(css, /\.corePage, \.appendix \{ display: block; break-before: page; \}/, "pages 2, 3 and the appendix start new print sheets");
  assert.match(css, /counter\(page\)/, "printed pages are numbered");
});

const LOCALES = ["en", "zh-TW", "ja", "ko"] as const;
const HAN = /[㐀-鿿]/;
const COPY = reportCoreCopy as Record<(typeof LOCALES)[number], Record<string, string>>;
test("new core copy covers all four locales with identical keys and no zh-TW leakage", () => {
  const keys = Object.keys(COPY.en).sort();
  for (const locale of LOCALES) assert.deepEqual(Object.keys(COPY[locale]).sort(), keys, locale);
  for (const key of keys) {
    const zh = COPY["zh-TW"][key];
    assert.doesNotMatch(COPY.en[key], HAN, `en.${key}`);
    assert.doesNotMatch(COPY.ko[key], HAN, `ko.${key}`);
    if (key !== "sep") assert.notEqual(COPY.ja[key], zh, `ja.${key} is not the zh-TW string`);
  }
  // Every gap reason and evidence status has a localized label.
  for (const reason of ["missing_input", "not_run", "unavailable", "unsupported", "no_coverage", "stale", "insufficient", "not_preserved"]) for (const locale of LOCALES) assert.ok(COPY[locale][`gap_${reason}`]);
  for (const status of ["available", "limited", "not_run", "unavailable", "unsupported", "no_coverage", "no_match", "stale", "insufficient"]) for (const locale of LOCALES) assert.ok(COPY[locale][`status_${status}`]);
});

test("trust wording survives translation: unknown is not safe, the marker and report are not a valuation", () => {
  const notSafe = { en: /never means safe/, "zh-TW": /不代表安全/, ja: /安全を意味しません/, ko: /안전을 의미하지 않습니다/ };
  const notValuation = { en: /not a valuation/, "zh-TW": /不是估價/, ja: /査定.*ではありません/, ko: /감정.*아닙니다/ };
  const noAdvice = { en: /no purchase recommendation/, "zh-TW": /不提供購買建議/, ja: /購入推奨ではなく/, ko: /구매 추천이 아니며/ };
  for (const locale of LOCALES) {
    assert.match(COPY[locale].riskNote, notSafe[locale], locale);
    assert.match(COPY[locale].markerCaveat, notValuation[locale], locale);
    assert.match(COPY[locale].checklistFooter, noAdvice[locale], locale);
    assert.match(COPY[locale].status_no_match, /safe|安全|안전/, locale);
  }
});

test("core view renders no hard-coded zh-TW interface copy", () => {
  const source = readFileSync(new URL("../../components/evidence/report-core.tsx", import.meta.url), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "").replace(/^\s*\/\/.*$/gm, "");
  assert.doesNotMatch(source, HAN);
  const view = readFileSync(new URL("../../components/evidence/report-view.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(view, /附錄/, "appendix heading comes from the copy catalogue");
});
