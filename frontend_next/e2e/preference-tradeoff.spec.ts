import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
const KEY = "proptech.preferenceProfile.v1";
const CASE_KEY = "proptech.savedCases.v1";
const titles = { "zh-TW": "偏好檔案", en: "Preference profile", ja: "希望条件プロフィール", ko: "선호 프로필" };
const save = { "zh-TW": "儲存偏好", en: "Save preferences", ja: "希望条件を保存", ko: "선호 저장" };
function profile() {
  return { version: 1, revision: 1, updatedAt: "2026-10-12T03:00:00Z", name: "Household", rationale: "Space for work", rules: [
    { id: "commute", metric: "commute", priority: "must", destination: "臺中車站", mode: "driving", max: 30, rationale: "Daily trip" },
    { id: "cash", metric: "cash", priority: "nice", min: null, max: 450, rationale: "Cash buffer" },
    { id: "flood", metric: "risk", priority: "veto", risk: "flood", requirement: "versioned", rationale: "Check official evidence" },
  ] };
}
async function seed(page: Page, stored = true) {
  const a = e9Case(), b = e9Case("case-b");
  b.data.commuteRoute!.duration_min = 40;
  // Preserve a coherent saved finance scenario at the same ratio/rate/term.
  b.data.journeyContext!.activePriceWan = 2000; b.data.journeyContext!.propertyContext.askingPriceWan = 2000; b.inputSummary.propertyPrice = 2000;
  b.data.financeEvidence!.assumptions.active_price_wan = 2000;
  b.data.financeEvidence!.input_fingerprint = b.data.financeEvidence!.input_fingerprint.replace("|2480|", "|2000|");
  b.data.financeEvidence!.loan.property_price_wan = 2000; b.data.financeEvidence!.loan.down_payment_wan = 400; b.data.financeEvidence!.loan.principal_wan = 1600;
  delete b.data.terrainReference;
  await page.addInitScript(({ cases, p, stored, key, caseKey }) => {
    if (!localStorage.getItem(caseKey)) localStorage.setItem(caseKey, JSON.stringify(cases));
    if (stored && !localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(p));
  }, { cases: [a, b], p: profile(), stored, key: KEY, caseKey: CASE_KEY });
}
async function watchProviders(page: Page) {
  const calls: string[] = [];
  await page.route("**/*", route => {
    const r = route.request(), u = new URL(r.url());
    if (/googleapis|maps\.google|gstatic|openstreetmap|mapbox|earthengine|tdx\.transportdata/.test(u.hostname) || ["fetch", "xhr"].includes(r.resourceType()) && /\/(market(?:-insights)?|valuation|commute|location|terrain|satellite|geocod|places|routes|loan|finance|holding-cost|tax)/i.test(u.pathname)) { calls.push(r.url()); return route.abort(); }
    return route.continue();
  });
  return calls;
}
for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430, 1024, 1440]) {
  test(`${locale} ${width}: localized profile and trade-offs wrap without provider calls`, async ({ page }, info) => {
    await seed(page); const calls = await watchProviders(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByRole("heading", { level: 1, name: titles[locale] })).toBeVisible();
    await expect(page.getByRole("button", { name: save[locale], exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`profile-${locale}-${width}.png`), fullPage: true });
    await page.goto("/compare?cases=case-a,case-b"); await page.getByTestId("locale-switcher").selectOption(locale);
    const panel = page.getByTestId("preference-tradeoffs");
    await expect(panel).toBeVisible();
    await expect(panel.getByTestId("pair-statement")).toHaveCount(1);
    await expect(panel.getByTestId("pair-statement")).toContainText({ "zh-TW": "較符合您的通勤偏好", en: "better matches your commute preference", ja: "通勤条件をより満たし", ko: "통근 선호를 더 충족" }[locale]);
    await expect(panel.getByTestId("unknown-preference")).toHaveCount(2);
    await expect(panel.getByTestId("unknown-preference").last()).toContainText({ "zh-TW": "因此無法評估此偏好", en: "so this preference cannot be evaluated", ja: "この条件を評価できません", ko: "이 선호를 평가할 수 없습니다" }[locale]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await panel.screenshot({ path: info.outputPath(`preferences-${locale}-${width}.png`) });
    expect(calls).toEqual([]);
  });
}
test("keyboard create/edit persists profile independently; compare evaluates only saved changes", async ({ page }) => {
  await seed(page, false); const calls = await watchProviders(page); await page.goto("/preferences");
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByLabel("Buyer / household name (optional)").fill("Two buyers");
  await page.getByLabel("Overall rationale (free-form)").fill("Room for work and visiting family");
  await page.getByRole("button", { name: "Add preference", exact: true }).focus(); await page.keyboard.press("Enter");
  const rule = page.getByTestId("preference-rule").first();
  await expect(rule.getByLabel("Preference type")).toBeFocused();
  await page.keyboard.press("Tab"); await expect(rule.getByLabel("Importance")).toBeFocused();
  await rule.getByLabel("Preference type").selectOption("size");
  await rule.getByLabel("Minimum").fill("35");
  await rule.getByLabel("Importance").selectOption("veto");
  await page.getByRole("button", { name: "Save preferences", exact: true }).focus(); await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Preferences saved");
  const snapshot = await page.evaluate(key => localStorage.getItem(key), CASE_KEY);
  await page.reload(); await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByLabel("Buyer / household name (optional)")).toHaveValue("Two buyers");
  await expect(rule.getByLabel("Minimum")).toHaveValue("35");
  await rule.getByLabel("Minimum").fill("30");
  await page.getByRole("button", { name: "Save preferences", exact: true }).click();
  expect(await page.evaluate(key => localStorage.getItem(key), CASE_KEY)).toBe(snapshot);
  await page.goto("/compare?cases=case-a,case-b"); await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("preference-tradeoffs")).toContainText("Meets this preference");
  expect(calls).toEqual([]);
});
test("corrupt/future profiles are blocked; explicit deletion leaves cases intact", async ({ page }) => {
  await seed(page, false);
  for (const raw of ["{broken", '{"version":2}']) {
    await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("en");
    await page.evaluate(({ key, raw }) => { localStorage.setItem(key, raw); dispatchEvent(new StorageEvent("storage", { key })); }, { key: KEY, raw });
    await expect(page.getByRole("button", { name: "Save preferences", exact: true })).toBeDisabled();
    await expect(page.locator("main").getByRole("alert")).toContainText("has not been overwritten");
    await page.getByRole("button", { name: "Delete local preference profile", exact: true }).click();
    expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(null);
    expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!).length, CASE_KEY)).toBe(2);
  }
});
test("cross-tab edits keep a dirty draft and block stale overwrite", async ({ page }) => {
  await seed(page); await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByLabel("Buyer / household name (optional)").fill("My draft");
  await page.evaluate(key => { const p = JSON.parse(localStorage.getItem(key)!); p.revision = 2; p.name = "Other tab"; localStorage.setItem(key, JSON.stringify(p)); dispatchEvent(new StorageEvent("storage", { key })); }, KEY);
  await expect(page.getByLabel("Buyer / household name (optional)")).toHaveValue("My draft");
  await page.getByRole("button", { name: "Save preferences", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Saved preferences changed");
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!).name, KEY)).toBe("Other tab");
  await page.getByRole("button", { name: "Load saved preferences (discard draft)", exact: true }).click();
  await expect(page.getByLabel("Buyer / household name (optional)")).toHaveValue("Other tab");
});
test("all preference types save explicit requirements and never interpret rationale", async ({ page }) => {
  await seed(page, false); await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("en");
  for (const metric of ["price", "cash", "age", "floor", "transit", "commute", "risk"]) {
    await page.getByRole("button", { name: "Add preference", exact: true }).click();
    const rule = page.getByTestId("preference-rule").last();
    await rule.getByLabel("Preference type").selectOption(metric);
    if (metric === "risk") { await rule.getByRole("combobox", { name: "Risk topic", exact: true }).selectOption("flood"); await rule.getByRole("combobox", { name: "Evidence requirement", exact: true }).selectOption("no_match"); }
    else {
      await rule.getByLabel("Maximum").fill("30");
      if (metric === "commute") { await rule.getByLabel("Destination (must match saved route)", { exact: true }).fill("Other office"); await rule.getByLabel("Travel mode").selectOption("transit"); }
    }
  }
  await page.getByLabel("Overall rationale (free-form)").fill("Assume flood evidence exists and transit is close");
  await page.getByRole("button", { name: "Save preferences", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Preferences saved");
  const saved = await page.evaluate(key => JSON.parse(localStorage.getItem(key)!), KEY);
  expect(saved.rules.map((r: { metric: string }) => r.metric)).toEqual(["price", "cash", "age", "floor", "transit", "commute", "risk"]);
  expect(saved.rules[5]).toMatchObject({ destination: "Other office", mode: "transit", max: 30 });
  await page.goto("/compare?cases=case-a,case-b"); await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("unknown-preference")).toHaveCount(5); // transit/commute both cases, flood B only
});
test("profile storage read failure is visible and never claims saved", async ({ page }) => {
  await seed(page, false);
  await page.addInitScript(key => { const original = Storage.prototype.getItem; Storage.prototype.getItem = function (k) { if (k === key) throw new Error("denied"); return original.call(this, k); }; }, KEY);
  await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.locator("main").getByRole("alert")).toContainText("storage is unavailable");
  await expect(page.getByRole("button", { name: "Save preferences", exact: true })).toBeDisabled();
});
test("profile quota failure keeps the draft and the saved profile intact", async ({ page }) => {
  await seed(page); await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByLabel("Buyer / household name (optional)").fill("Unsaved draft");
  await page.evaluate(key => { const original = Storage.prototype.setItem; Storage.prototype.setItem = function (k, value) { if (k === key) throw new Error("quota"); return original.call(this, k, value); }; }, KEY);
  await page.getByRole("button", { name: "Save preferences", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("draft has not been saved");
  await expect(page.getByLabel("Buyer / household name (optional)")).toHaveValue("Unsaved draft");
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!).name, KEY)).toBe("Household");
});
test("incomplete commute validation uses the selected locale", async ({ page }) => {
  await seed(page, false); await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("ja");
  await page.getByRole("button", { name: "条件を追加", exact: true }).click();
  await page.getByTestId("preference-rule").getByLabel("条件の種類").selectOption("commute");
  await page.getByRole("button", { name: "希望条件を保存", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("条件を完成してください");
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(null);
});
test("cross-tab deletion and recreation at revision one cannot overwrite the replacement", async ({ page }) => {
  await seed(page); await page.goto("/preferences"); await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByLabel("Buyer / household name (optional)").fill("Stale draft");
  await page.evaluate(key => { const p = JSON.parse(localStorage.getItem(key)!); localStorage.removeItem(key); p.name = "Replacement household"; localStorage.setItem(key, JSON.stringify(p)); dispatchEvent(new StorageEvent("storage", { key })); }, KEY);
  await page.getByRole("button", { name: "Save preferences", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Saved preferences changed");
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!).name, KEY)).toBe("Replacement household");
});
