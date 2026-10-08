import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

async function prepare(page: Page, cases = [e9Case(), e9Case("case-b")]) {
  await page.addInitScript((rows) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
  }, cases);
  const providers: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "e2e.test") { providers.push(url.pathname); return route.fallback(); }
    if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") {
      providers.push(url.pathname);
      return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
    }
    return route.fallback();
  });
  return providers;
}

test("homepage starts a property review and exposes recent saved cases without a demo hero", async ({ page }) => {
  await prepare(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "看清物件證據，確認下一步" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "物件地址", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "繼續案件 A", exact: true })).toBeVisible();
  await expect(page.locator(".hero-orb, .hero-sequence")).toHaveCount(0);
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill("臺中市西屯區臺灣大道三段100號");
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  await expect(page.locator("#journey-stage-location")).toBeVisible();
  await expect(page.locator("#location-insight-calculator").getByRole("textbox").first()).toHaveValue("臺中市西屯區臺灣大道三段100號");
});

test("mobile methods are keyboard accessible and saved outputs stay reachable", async ({ page }) => {
  await prepare(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const methods = page.locator(".commercial-methods > summary");
  await methods.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "TaxOracle 稅務", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "TaxOracle 稅務", exact: true }).click();
  await expect(page.locator("[data-page-heading]")).toBeVisible();
  await page.goto("/cases/case-a/market");
  await expect(page.getByRole("button", { name: "保存目前案件快照", exact: true })).toBeVisible();
  await expect(page.locator(".workspace-navigation").getByRole("link", { name: "案件報告", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "保存目前案件快照", exact: true }).click();
  await expect(page.getByTestId("context-save-status")).toContainText("已保存");
});

test("starting another address clears the previous property assumptions", async ({ page }) => {
  await prepare(page);
  await page.goto("/");
  await page.getByRole("button", { name: "還沒有特定物件？搜尋官方成交資料", exact: true }).click();
  await expect(page.locator("#journey-stage-property")).toBeVisible();
  const row = e9Case();
  Object.assign(row.data.journeyContext!.propertyContext, { areaPing: 30 });
  await page.evaluate((detail) => {
    window.dispatchEvent(new CustomEvent("proptech:saved-case-loaded", { detail }));
    window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" }));
  }, row);
  const inputs = page.locator("#location-insight-calculator input[type=number]");
  await expect(inputs.nth(1)).toHaveValue("2480");
  await expect(inputs.nth(2)).toHaveValue("30");
  await page.locator(".commercial-home").getByRole("textbox", { name: "物件地址", exact: true }).fill("臺北市信義區松仁路100號");
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  await expect(inputs.nth(1)).toHaveValue("");
  await expect(inputs.nth(2)).toHaveValue("");
});

test("failed snapshot writes replace earlier success with an accessible error", async ({ page }) => {
  await prepare(page);
  await page.goto("/cases/case-a/overview");
  const save = page.getByRole("button", { name: "保存目前案件快照", exact: true });
  await save.click();
  await expect(page.getByTestId("context-save-status")).toContainText("已保存");
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException("Quota exceeded", "QuotaExceededError"); }; });
  await save.click();
  await expect(page.getByTestId("context-save-status")).toContainText("儲存失敗");
  await expect(page.getByTestId("context-save-status")).not.toContainText("已保存");
});

test("mobile navigation is one row and risk source names retain readable width", async ({ page }) => {
  await prepare(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/case-a/risk");
  expect(await page.locator(".workspace-navigation").evaluate((node) => node.getBoundingClientRect().height)).toBeLessThan(70);
  expect(await page.getByRole("table").first().locator("tbody td").first().evaluate((node) => node.getBoundingClientRect().width)).toBeGreaterThanOrEqual(150);
});

for (const width of [1440, 1024, 390]) {
  test(`long addresses, large amounts and four home locales fit ${width}px`, async ({ page }, testInfo) => {
    const row = e9Case();
    const address = "臺中市西屯區臺灣大道三段100號之123附456號商務大樓第十二樓國際客戶會議室";
    row.title = "國際客戶與業務團隊共同檢視的長名稱物件案件";
    row.inputSummary.road = address;
    row.data.inputs.road = address;
    Object.assign(row.data.journeyContext!.propertyContext, { addressSummary: address, road: address, askingPriceWan: 123456789.98 });
    row.data.journeyContext!.activePriceWan = 123456789.98;
    Object.assign(row.data.propertyIdentityAnchor!, { address_input: address, normalized_address: address });
    await prepare(page, [row]);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    for (const locale of ["zh-TW", "en", "ja", "ko"]) {
      await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.locator(".commercial-recent-cases")).toContainText(address);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    await page.goto("/cases/case-a/market");
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(address);
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("123,456,790");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`long-context-${width}.png`), fullPage: true });
  });
  test(`workspace methods menu stays above property context at ${width}px`, async ({ page }) => {
    await prepare(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/cases/case-a/market");
    await expect(page.getByRole("banner", { name: "目前物件" })).toBeVisible();
    await page.locator(".commercial-methods > summary").click();
    const method = page.locator(".commercial-methods").getByRole("link", { name: "Map Insight", exact: true });
    await expect(method).toBeVisible();
    expect(await method.evaluate((node) => {
      const box = node.getBoundingClientRect();
      return node.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2));
    })).toBe(true);
  });
  test(`commercial screens fit ${width}px and keep print/provider boundaries`, async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    const providers = await prepare(page);
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/", "/cases/case-a/overview", "/cases/case-a/market", "/cases/case-a/location", "/cases/case-a/risk", "/cases/case-a/finance", "/compare?cases=case-a,case-b", "/cases/case-a/report"]) {
      providers.length = 0;
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (path.includes("risk")) {
        expect(await page.getByRole("heading", { name: "證據表", exact: true }).evaluate((node) => node.getBoundingClientRect().top)).toBeLessThan(await page.getByRole("heading", { name: "風險／環境地圖", exact: true }).evaluate((node) => node.getBoundingClientRect().top));
      }
      if (path.includes("compare") || path.includes("report")) expect(providers).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`${path.split("?")[0].replaceAll("/", "-") || "home"}-${width}.png`), fullPage: true });
    }
    await page.emulateMedia({ media: "print" });
    await expect(page.locator(".commercial-global-header")).toBeHidden();
    await expect(page.getByTestId("report-evidence")).toBeVisible();
    await expect(page.getByTestId("report-evidence").getByRole("heading", { level: 2 })).toHaveCount(9);
  });
}
