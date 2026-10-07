import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { evidenceStatusLabel, officialRuntimeStatusLabel, pointReferencePresentation } from "./presentation.ts";

test("provider and data-quality enums use commercial presentation vocabulary", () => {
  assert.equal(evidenceStatusLabel("good", "zh-TW"), "證據可供判讀");
  assert.equal(evidenceStatusLabel("partial", "zh-TW"), "分析僅完成部分");
  assert.equal(evidenceStatusLabel("unavailable", "zh-TW"), "目前無法取得證據");
  assert.equal(evidenceStatusLabel("no_match", "zh-TW"), "查無符合資料");
  assert.equal(officialRuntimeStatusLabel("not_checked", "zh-TW"), "尚未查詢");
});

test("point-reference implementation tokens never become customer copy", () => {
  assert.equal(pointReferencePresentation("POINT_REFERENCE_ONLY", "Reference point only"), "Reference point only");
  assert.equal(pointReferencePresentation("Provider label", "Reference point only"), "Provider label");
});
