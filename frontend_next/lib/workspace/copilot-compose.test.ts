import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { emptyDecisionRoom } from "../decision-room-store.ts";
// @ts-expect-error Native TS runner extension.
import { assembleCopilotContext, answerQuestion, validateResponderOutput, type CopilotAnswer, type CopilotContext } from "./grounded-copilot.ts";
// @ts-expect-error Native TS runner extension.
import { composeAnswer, COMPOSE_LIMITS, type AnswerPresentation } from "./copilot-compose.ts";

const workspace = (id = "case-a") => adaptSavedCaseToWorkspace(e9Case(id));
const context = (ws = workspace(), extras = {}): CopilotContext => assembleCopilotContext(ws, extras);
const ask = (ctx: CopilotContext, question: string) => { const answer = answerQuestion(ctx, question); return { answer, view: composeAnswer(answer, ctx) as AnswerPresentation }; };
const numbersIn = (value: unknown) => JSON.stringify(value).match(/-?\d+(\.\d+)?/g) ?? [];

/** Every presentation ref must be cited by the deterministic answer and resolve in the same context. */
function assertGrounded(view: AnswerPresentation, answer: CopilotAnswer, ctx: CopilotContext) {
  const used = new Set(answer.used.map((row) => row.ref));
  const all = [...view.headline.refs, ...view.keyFacts.flatMap((fact) => fact.refs), ...view.fullEvidenceRefs, ...view.provenanceRefs];
  for (const ref of all) {
    assert.ok(used.has(ref), `${ref} is not in the deterministic answer`);
    assert.ok(ctx.evidence.some((row) => row.ref === ref), `${ref} does not resolve`);
  }
  assert.equal(view.status, answer.status);
  for (const fact of view.keyFacts) {
    assert.ok(fact.refs.length > 0);
    assert.equal(fact.states.length, fact.refs.length);
  }
  const numeric = Object.entries(view.headline).some(([name, value]) => !["refs", "kind", "qualified"].includes(name) && typeof value === "number");
  if (!["partial", "supported"].includes(view.headline.kind) && numeric) assert.ok(view.headline.refs.length > 0, "numeric headline without refs");
}

test("supported market answer leads with a cited unit-price band position, not valuation", () => {
  const ctx = context(); const { answer, view } = ask(ctx, "market");
  assertGrounded(view, answer, ctx);
  assert.equal(view.headline.kind, "market_band");
  assert.ok(view.headline.kind === "market_band");
  assert.equal(view.headline.position, "above");
  assert.equal(view.headline.askingUnit, 2480 / 30);
  assert.deepEqual(view.headline.refs, ["case-a:price-asking", "case-a:property-area", "case-a:market-p25", "case-a:market-p75"]);
  const unit = view.keyFacts.find((fact) => fact.kind === "asking_unit");
  assert.equal(unit?.origin, "derived");
  assert.deepEqual(unit?.refs, ["case-a:price-asking", "case-a:property-area"]);
  assert.equal(unit?.value, 2480 / 30);
  assert.deepEqual(view.keyFacts.find((fact) => fact.kind === "market_band")?.band, { low: 49.8, high: 55.6, unit: "萬元／坪" });
  assert.doesNotMatch(JSON.stringify(view), /fair|overpriced|underpriced|good deal|buy|safe/i);
});

test("a fully supported answer gets a direct, unqualified headline", () => {
  const base = context();
  const ctx = { ...base, evidence: base.evidence.map((row) => row.topic === "market" || row.id === "property-area" ? { ...row, status: "available" as const, limitation: "", value: row.value ?? 1, missingReason: null } : row) };
  const { answer, view } = ask(ctx, "market");
  assert.equal(answer.status, "supported");
  assert.equal(view.headline.kind, "market_band");
  assert.equal(view.headline.qualified, false);
  assert.equal(view.missingTotal, 0);
  assertGrounded(view, answer, ctx);
});

test("multi-topic questions route to Evidence and offer narrowing follow-ups", () => {
  const ctx = context(); const { view } = ask(ctx, "summary");
  assert.deepEqual(view.nextAction, { kind: "inspect_missing", href: "/cases/case-a/evidence" });
  assert.deepEqual(view.followups, ["market", "finance"]);
  assert.deepEqual(ask(ctx, "commute").view.followups, ["location", "risk"]);
});

test("partially supported answers carry a qualified headline", () => {
  const ctx = context(); const { answer, view } = ask(ctx, "commute");
  assert.equal(answer.status, "partially_supported");
  assert.equal(view.headline.qualified, true);
  assert.equal(view.headline.kind, "commute");
  assert.ok(view.headline.kind === "commute");
  assert.equal(view.headline.minutes, 24);
  assert.equal(view.headline.destination, "臺中車站");
  assertGrounded(view, answer, ctx);
});

test("insufficient evidence never invents a headline number or a key fact", () => {
  const ctx = context();
  for (const question of ["valuation", "what is the zoning parcel ownership?", "is this current live evidence?", "hello there"]) {
    const { answer, view } = ask(ctx, question);
    assert.equal(view.status, "insufficient_evidence");
    assert.deepEqual(view.keyFacts, []);
    assert.deepEqual(view.headline.refs, []);
    assert.deepEqual(numbersIn({ ...view.headline, refs: undefined }), []);
    assert.equal(view.openMissing, true);
    assertGrounded(view, answer, ctx);
  }
  assert.equal(ask(ctx, "zoning").view.headline.kind, "legal_unsupported");
  assert.equal(ask(ctx, "is this live?").view.headline.kind, "live_not_requested");
});

test("conflicting asking prices keep both observations and resolve neither", () => {
  const room = emptyDecisionRoom("case-a"); room.askingPrice.priceWan = 2600;
  const ctx = context(workspace(), { roomRead: { status: "ready", room } });
  const { answer, view } = ask(ctx, "market");
  assert.equal(view.status, "conflicting_evidence");
  assert.equal(view.headline.kind, "conflict_price");
  assert.deepEqual(view.keyFacts.map((fact) => fact.value), [2480, 2600]);
  assert.ok(!view.keyFacts.some((fact) => fact.kind === "asking_unit" || fact.kind === "market_band"));
  assert.equal(view.nextAction.kind, "review_price_conflict");
  assertGrounded(view, answer, ctx);
  const identity = workspace(); identity.identity.state = "conflict";
  const conflicted = context(identity); const result = ask(conflicted, "commute finance");
  assert.equal(result.view.headline.kind, "conflict_identity");
  assert.deepEqual(result.view.keyFacts, []);
});

test("every numeric key fact keeps refs, state and origin", () => {
  const ctx = context();
  for (const question of ["market", "finance", "commute", "risk", "summary", "market finance commute"]) {
    const { answer, view } = ask(ctx, question);
    assertGrounded(view, answer, ctx);
    for (const fact of view.keyFacts) {
      assert.ok(fact.origin);
      if (typeof fact.value === "number" || fact.band) assert.ok(fact.refs.length >= 1);
    }
  }
});

test("missing P25/P75, area or unit compatibility prevents a band-position claim", () => {
  for (const mutate of [
    (ws: ReturnType<typeof workspace>) => { ws.marketPrice.market.result!.p75_unit_price_per_ping = null as never; },
    (ws: ReturnType<typeof workspace>) => { ws.marketPrice.market.result!.p25_unit_price_per_ping = null as never; },
    (ws: ReturnType<typeof workspace>) => { ws.assumptions.areaPing = null as never; },
  ]) {
    const ws = workspace(); mutate(ws);
    const ctx = context(ws); const { answer, view } = ask(ctx, "market");
    assert.ok(!answer.insights.some((item: { kind: string }) => item.kind === "asking_unit_vs_band"));
    assert.notEqual(view.headline.kind, "market_band");
    assert.ok(!view.keyFacts.some((fact) => fact.kind === "market_band"));
    // No band means no market headline: total price vs regional median is not promoted.
    assert.equal(view.headline.kind, "partial");
    assertGrounded(view, answer, ctx);
  }
  const noArea = workspace(); noArea.assumptions.areaPing = null as never;
  const areaView = ask(context(noArea), "market").view;
  assert.deepEqual(areaView.nextAction, { kind: "enter_area", href: "/cases/case-a/overview" });
  const ws = workspace(); const ctx = context(ws);
  const tampered = { ...ctx, evidence: ctx.evidence.map((row) => row.id === "market-p25" ? { ...row, unit: "元／坪" } : row) };
  assert.ok(!answerQuestion(tampered, "market").insights.some((item: { kind: string }) => item.kind === "asking_unit_vs_band"));
});

test("stale market evidence cannot become a current market claim", () => {
  const ws = workspace(); ws.marketPrice.market.result!.freshness_status = "stale";
  const ctx = context(ws); const { answer, view } = ask(ctx, "market");
  assert.ok(!view.keyFacts.some((fact) => fact.refs.some((ref) => /market-(p25|p75|unit|total)/.test(ref))));
  assert.ok(!["market_band", "market_median_difference"].includes(view.headline.kind));
  assert.ok(view.missingItems.slice(0, 2).every((item) => item.status === "stale"));
  assert.equal(view.nextAction.kind, "refresh_market");
  assertGrounded(view, answer, ctx);
});

test("no-match risk is counted separately and never presented as safe", () => {
  const ctx = context(); const { answer, view } = ask(ctx, "risk");
  assert.equal(view.headline.kind, "risk");
  assert.ok(view.headline.kind === "risk");
  assert.equal(view.headline.noMatch, 1);
  assert.equal(view.headline.recorded, 1);
  assert.equal(view.headline.unresolved, 5);
  const flood = view.keyFacts.find((fact) => fact.evidenceId === "risk-flood");
  assert.deepEqual(flood?.states, ["no_match"]);
  assert.equal(view.nextAction.kind, "review_risk_sources");
  assert.doesNotMatch(JSON.stringify(view), /"safe"/);
  assertGrounded(view, answer, ctx);
});

test("missing income prevents an affordability conclusion and drives the next action", () => {
  const ctx = context(); const { answer, view } = ask(ctx, "finance");
  assert.equal(view.headline.kind, "finance_housing");
  assert.ok(view.headline.kind === "finance_housing");
  assert.equal(view.headline.incomeMissing, true);
  assert.equal(view.headline.monthly, 55111);
  assert.equal(view.missingItems[0].id, "finance-income");
  assert.deepEqual(view.nextAction, { kind: "enter_income", href: "/cases/case-a/finance" });
  assertGrounded(view, answer, ctx);
});

test("exactly one bounded, case-scoped next action", () => {
  const ctx = context();
  for (const question of ["market", "finance", "commute", "risk", "scenario", "decision room", "zoning", "summary", "hello"]) {
    const { view } = ask(ctx, question);
    assert.equal(typeof view.nextAction.kind, "string");
    assert.ok(view.nextAction.href === null ? view.nextAction.kind === "none" : view.nextAction.href.startsWith("/cases/case-a/"));
  }
});

test("fact, missing-preview and follow-up limits are enforced without hiding totals", () => {
  const ctx = context(); const { answer, view } = ask(ctx, "summary");
  assert.ok(view.keyFacts.length <= COMPOSE_LIMITS.keyFacts && view.keyFacts.length >= 2);
  assert.ok(view.missingItems.length <= COMPOSE_LIMITS.missingPreview);
  assert.equal(view.missingTotal, answer.missing.length);
  assert.ok(view.missingTotal > view.missingItems.length);
  assert.ok(view.followups.length <= COMPOSE_LIMITS.followups);
  assert.equal(view.fullEvidenceRefs.length, answer.used.length);
  assert.ok(!view.missingItems.some((item) => ["finance-grace-payment", "finance-post-grace"].includes(item.id)));
});

test("identical input produces an identical presentation", () => {
  const a = context(); const b = context();
  assert.deepEqual(composeAnswer(answerQuestion(a, "market finance"), a), composeAnswer(answerQuestion(b, "market finance"), b));
});

test("a foreign, stale or invalidated answer composes to a closed presentation", () => {
  const a = context(); const b = context(workspace("case-b"));
  const view = composeAnswer(answerQuestion(a, "market"), b);
  assert.equal(view.status, "insufficient_evidence");
  assert.deepEqual(view.keyFacts, []); assert.deepEqual(view.fullEvidenceRefs, []);
  assert.doesNotMatch(JSON.stringify(view), /case-a/);
  const invalid = validateResponderOutput(a, answerQuestion(a, "market"), { refs: ["case-a:invented"] });
  const closed = composeAnswer(invalid, a);
  assert.equal(closed.headline.kind, "invalid_output");
  assert.deepEqual(closed.keyFacts, []);
  // A presentation cannot cite a lookalike row that is not the context's own evidence.
  const forged = answerQuestion(a, "market");
  const swapped = { ...forged, used: forged.used.map((row) => ({ ...row })) };
  const forgedView = composeAnswer(swapped, a);
  assert.equal(forgedView.status, "insufficient_evidence");
  assert.deepEqual(forgedView.keyFacts, []); assert.deepEqual(forgedView.fullEvidenceRefs, []);
});

test("composition stays within a local CPU budget", (t) => {
  const ctx = context(); const answer = answerQuestion(ctx, "summary");
  const start = process.cpuUsage();
  for (let i = 0; i < 200; i++) composeAnswer(answer, ctx);
  const cpu = process.cpuUsage(start); const ms = (cpu.user + cpu.system) / 1000;
  t.diagnostic(`200 compositions: ${ms.toFixed(1)} CPU ms`);
  assert.ok(ms < 1000);
});

test("trust classes separate user input, saved assumptions and saved calculations", () => {
  const ctx = context(); const { view } = ask(ctx, "finance");
  const by = (id: string) => view.keyFacts.find((fact) => fact.evidenceId === id)?.origin;
  assert.equal(by("finance-housing"), "saved_calculation");
  assert.equal(by("finance-rate"), "saved_assumption");
  assert.equal(by("finance-price"), "saved_assumption");
  for (const question of ["market", "summary", "identity", "market finance commute"]) {
    assert.ok(!ask(ctx, question).view.keyFacts.some((fact) => ["price-active", "price-basis"].includes(fact.evidenceId)), question);
  }
});
