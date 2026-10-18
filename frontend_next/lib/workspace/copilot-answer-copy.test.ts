import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { emptyDecisionRoom } from "../decision-room-store.ts";
// @ts-expect-error Native TS runner extension.
import { assembleCopilotContext, answerQuestion } from "./grounded-copilot.ts";
// @ts-expect-error Native TS runner extension.
import { composeAnswer, type AnswerPresentation } from "./copilot-compose.ts";
// @ts-expect-error Native TS runner extension.
import { formatQuantity, formatRange, headlineText, nextActionLabel } from "./copilot-answer-copy.ts";

const locales = ["zh-TW", "en", "ja", "ko"] as const;
const view = (question: string, extras = {}) => { const ctx = assembleCopilotContext(adaptSavedCaseToWorkspace(e9Case()), extras); return composeAnswer(answerQuestion(ctx, question), ctx) as AnswerPresentation; };

test("human-readable units without technical multiplier strings", () => {
  assert.equal(formatQuantity(2480 / 30, "萬元／坪", "zh-TW"), "82.7 萬／坪");
  assert.equal(formatQuantity(55111, "元／月", "zh-TW"), "NT$55,111／月");
  assert.equal(formatQuantity(24, "分鐘", "zh-TW"), "24 分鐘");
  assert.equal(formatQuantity(2480, "萬元", "en"), "NT$24.8M");
  assert.equal(formatQuantity(2480 / 30, "萬元／坪", "en"), "NT$826.7K / ping");
  assert.equal(formatRange(49.8, 55.6, "萬元／坪", "zh-TW"), "49.8–55.6 萬／坪");
  for (const locale of locales) for (const unit of ["萬元", "萬元／坪", "元／月", "分鐘", "坪", "TWD"]) assert.doesNotMatch(formatQuantity(1234.5, unit, locale), /× ?10,000|TWD × /);
});

test("band position comes from raw values; rounding never moves it", () => {
  // 55.64 rounds to the P75 label but is still above it.
  const headline = { kind: "market_band" as const, position: "above" as const, askingUnit: 55.64, low: 49.8, high: 55.6, unit: "萬元／坪", refs: ["a"] };
  assert.match(headlineText(headline, "en").text, /above/);
  assert.match(headlineText(headline, "zh-TW").text, /高於/);
  // 90.04 vs P75 90: the displayed value must not look equal to the bound it exceeds.
  const tie = { ...headline, askingUnit: 2701.2 / 30, low: 70, high: 90 };
  assert.equal(formatQuantity(tie.askingUnit, tie.unit, "zh-TW"), formatQuantity(90, tie.unit, "zh-TW"), "fixture must be a rounding tie");
  assert.match(headlineText(tie, "zh-TW").text, /90\.04 萬／坪/);
  assert.match(headlineText(tie, "ja").text, /90\.04万/);
});

test("every locale renders every composed headline without purchase, safety or fair-value verdicts", () => {
  const room = emptyDecisionRoom("case-a"); room.askingPrice.priceWan = 2600;
  const views = [...["market", "finance", "commute", "risk", "scenario", "decision room", "summary", "zoning", "is this live?", "hello"].map((q) => view(q)), view("market", { roomRead: { status: "ready", room } })];
  for (const locale of locales) for (const item of views) {
    const { text, note } = headlineText(item.headline, locale);
    const all = `${text} ${note ?? ""}`;
    assert.ok(text.length > 0 && !/\{\w+\}/.test(all), `${locale} ${item.headline.kind}`);
    assert.doesNotMatch(all, /\b(buy|don't buy|good deal|bad deal|safe|unsafe|overpriced|underpriced|fair value)\b/i);
    assert.doesNotMatch(all, /划算|便宜|昂貴|值得買|割安|割高|저렴|비싸/);
    const action = nextActionLabel(item.nextAction.kind, locale);
    assert.ok(item.nextAction.kind === "none" ? action === null : action && action.length > 0);
  }
  assert.equal(headlineText(view("finance").headline, "en").note, "Affordability is still unknown because income is missing.");
  assert.equal(headlineText(view("commute").headline, "zh-TW").text, "已儲存路線：開車至「臺中車站」需 24 分鐘。");
});
