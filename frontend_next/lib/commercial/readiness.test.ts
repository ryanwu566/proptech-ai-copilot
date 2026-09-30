import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { resolveTaskReadiness } from "./readiness.ts";

test("readiness always names the task and never becomes a universal ready label", () => {
  assert.equal(resolveTaskReadiness("comparison", "ready").label["zh-TW"], "可進行「物件比較」");
  assert.equal(resolveTaskReadiness("report", "not_ready").label["zh-TW"], "尚不足以進行「產生分析摘要」");
  assert.match(resolveTaskReadiness("client_discussion", "ready_with_limits", { limitation: "市場樣本有限" }).label["zh-TW"], /初步客戶討論.*市場樣本有限/);
  assert.equal(resolveTaskReadiness("comparison", "ready").label.ja, "「物件比較」を実行できます");
  assert.equal(resolveTaskReadiness("comparison", "ready").label.ko, "‘매물 비교’을(를) 진행할 수 있습니다");
});
test("unknown readiness fails closed and requires a named blocker", () => {
  const result = resolveTaskReadiness("offer_preparation", "RAW_READY", { blocker: "物件資料需重新確認" });

  assert.equal(result.value, "blocked");
  assert.equal(result.recognized, false);
  assert.equal(result.actionable, true);
  assert.equal(result.label["zh-TW"], "需先解決「物件資料需重新確認」，才能進行「出價前準備」");
});
