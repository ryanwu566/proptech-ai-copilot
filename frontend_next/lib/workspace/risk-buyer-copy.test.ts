import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native Node TypeScript tests require source extensions.
import { riskBuyerCopy, buyerStateCopy, hazardBuyerCopy, riskBuyerSummary } from "./risk-buyer-copy.ts";

test("all four locales have complete copy, state explanations and hazard actions", () => {
  const locales = ["zh-TW", "en", "ja", "ko"] as const;
  const states = ["MATCHED", "NO MATCH", "NO COVERAGE", "UNKNOWN", "UNAVAILABLE", "UNSUPPORTED", "LIMITED", "STALE", "NOT QUERIED"] as const;
  const hazards = ["flood", "liquefaction", "landslide", "debris_flow", "geological_sensitivity", "active_fault"] as const;
  for (const locale of locales) {
    const copy = riskBuyerCopy(locale);
    assert.deepEqual(Object.keys(copy), Object.keys(riskBuyerCopy("zh-TW")));
    assert.ok(Object.values(copy).every((value) => typeof value === "string" && value.trim()));
    for (const state of states) {
      const c = buyerStateCopy(state, locale);
      assert.ok(c.meaning && c.limits && c.next);
      assert.notEqual(c.meaning, "SAFE");
    }
    for (const hazard of hazards) {
      const c = hazardBuyerCopy(hazard, locale);
      assert.ok(c.name && c.actions.length >= 1);
      assert.ok(c.actions.every((a) => a.trim()));
    }
    assert.equal(riskBuyerSummary(null, locale), copy.preQuery);
    assert.notEqual(riskBuyerSummary(null, locale), riskBuyerSummary(0, locale));
    assert.match(riskBuyerSummary(6, locale), /6/);
  }
});

test("required labels and localized safety principle remain explicit", () => {
  const labels = [
    ["zh-TW", "已知", "不能證明", "下一步查證"],
    ["en", "What we know", "What this does not prove", "Verify next"],
    ["ja", "分かっていること", "この結果だけでは分からないこと", "次に確認すること"],
    ["ko", "확인된 내용", "이 결과로 입증되지 않는 내용", "다음 확인 사항"],
  ] as const;
  for (const [locale, known, limits, next] of labels) {
    const c = riskBuyerCopy(locale);
    assert.deepEqual([c.known, c.limits, c.next], [known, limits, next]);
    assert.doesNotMatch(c.principle, /\bUNKNOWN\b/);
    assert.notEqual(buyerStateCopy("NO COVERAGE", locale).meaning, buyerStateCopy("UNAVAILABLE", locale).meaning);
    assert.ok(buyerStateCopy("NO MATCH", locale).next);
  }
});
