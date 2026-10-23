import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native Node tests use source extensions.
import { overviewViewCopy, presentOverviewItem, presentWanText, presentMonthlyTwd, presentRiskResult, presentChecklistAction } from "./overview-presentation.ts";
import type { OverviewItem } from "./overview-model";

test("presentation preserves evidence state, links, user text and the canonical wording", () => {
  const item: OverviewItem = { id: "identity-confirm-location", label: "確認物件位置", reason: "位置尚未確認", state: "action_required", section: "location", href: "/cases/a/location", evidenceKeys: [] };
  const before = structuredClone(item);
  assert.deepEqual(presentOverviewItem(item, "zh-TW"), { label: item.label, reason: item.reason });
  for (const locale of ["en", "ja", "ko"] as const) {
    assert.notEqual(presentOverviewItem(item, locale).label, item.label);
    assert.equal(presentOverviewItem({ ...item, id: "user-supplied", label: "My note" }, locale).label, "My note");
    assert.ok(overviewViewCopy[locale].identityBoundaryText);
    assert.deepEqual(item, before);
  }
});

test("amount presentation preserves zero, missing values and units", () => {
  assert.equal(presentMonthlyTwd(null, "en"), "Not yet available");
  assert.equal(presentMonthlyTwd(0, "en"), "NT$0 / month");
  assert.equal(presentWanText("2,480 萬元", "en"), "NT$24,800,000");
  assert.equal(presentWanText("49.8–55.6 萬元／坪", "en"), "NT$498,000–NT$556,000 / ping");
  assert.equal(presentWanText("未提供", "zh-TW"), "未提供");
});

test("risk results retain no-match and unavailable distinctions in every locale", () => {
  for (const locale of ["en", "ja", "ko"] as const) {
    assert.notEqual(presentRiskResult("未命中", locale), "未命中");
    assert.notEqual(presentRiskResult("目前無法取得", locale), "目前無法取得");
    assert.notEqual(presentRiskResult("未命中", locale), presentRiskResult("目前無法取得", locale));
    assert.equal(presentRiskResult("Provider original text", locale), "Provider original text");
  }
});

test("saved destination, travel mode and manual verification boundaries survive translation", () => {
  const item: OverviewItem = { id: "commute-route", label: "已保存前往臺中車站的路線", reason: "已保存 driving 路線距離與時間摘要；不會在總覽自動重查。", state: "saved_snapshot", section: "location", href: "/cases/a/location", evidenceKeys: ["commute"] };
  const view = presentOverviewItem(item, "en");
  assert.match(view.label, /臺中車站/);
  assert.match(view.reason, /Driving/);
  const action = "先確認本案件地址與定位；地籍、建物與權利文件需另行人工查證。";
  assert.equal(presentChecklistAction(action, "zh-TW"), action);
  assert.match(presentChecklistAction(action, "en"), /separate manual verification/);
  assert.equal(presentChecklistAction("Unrecognized source action", "ja"), "Unrecognized source action");
});

test("overview translations keep price direction and detailed risk evidence", () => {
  const entry: OverviewItem = { id: "market-evidence", label: "已保存市場成交摘要", reason: "開價高於目前觀察到的市場成交總價中位數，仍需以物件條件與可比成交確認差異。", state: "saved_snapshot", section: "market", href: "/cases/a/market", evidenceKeys: ["market"] };
  assert.match(presentOverviewItem(entry, "en").reason, /above/);
  entry.reason = "開價低於目前觀察到的市場成交總價中位數，仍需確認物件條件與證據範圍。";
  assert.match(presentOverviewItem(entry, "en").reason, /below/);
  const risk = { ...entry, id: "risk-material-geological_sensitivity", section: "risk" as const, reason: "符合 2 項官方公告類別：山崩與地滑、地下水補注。公告交集不代表高、中或低風險分級。" };
  for (const locale of ["en", "ja", "ko"] as const) {
    const reason = presentOverviewItem(risk, locale).reason;
    assert.match(reason, /2/);
    assert.match(reason, /山崩與地滑、地下水補注/);
    const stale = presentOverviewItem({ ...risk, id: "risk-unknown-flood", reason: "此摘要屬於先前物件狀態，不能作為目前證據。" }, locale);
    const coverage = presentOverviewItem({ ...risk, id: "risk-unknown-flood", reason: "此位置不在目前資料涵蓋範圍，無法形成風險判讀。" }, locale);
    assert.notEqual(stale.reason, coverage.reason);
  }
  assert.equal(presentOverviewItem({ ...entry, reason: "New source finding" }, "ja").reason, "New source finding");
});
