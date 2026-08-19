import { expect, test } from "./fixtures";

/**
 * B2-B5 Recovery: Four-locale browser recertification.
 * Verified: locale switching, no raw key leakage, no Chinese leakage in EN/KO/JA,
 * mobile viewports, console/page/hydration errors.
 */

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

// Known Chinese-only phrases that should NEVER appear as product-generated text in EN/KO pages
const CHINESE_LEAK_PHRASES = [
  "找房雷達", "估價與趨勢", "貸款與持有成本", "區位分析", "風險總評",
  "看屋決策報告", "可進一步看屋", "需謹慎評估", "暫不建議",
  "完成估價", "帶入物件開價", "完成貸款月付試算", "補入月收入",
  "完成每月持有成本試算", "完成區位分析", "補查市場趨勢",
  "使用找房雷達", "補查嫌惡設施", "確認區位資料限制", "安排實地看屋",
  "針對主要風險補查", "先比較其他路段",
  "這個流程會帶你", "請先完成目前步驟", "查看已完成步驟摘要", "返回修改",
];

// Japanese-safe: Known Chinese-only constructions for JA leakage detection
const CHINESE_ONLY_FOR_JA = [
  "找房雷達", "看屋決策報告", "估價與趨勢", "貸款與持有成本",
  "可進一步看屋", "需謹慎評估", "暫不建議",
  "這個流程會帶你", "請先完成目前步驟", "查看已完成步驟摘要", "返回修改",
];

async function switchLocale(page: import("@playwright/test").Page, locale: string) {
  const select = page.locator("select").first();
  await select.selectOption(locale);
  await expect.poll(() => page.locator("html").getAttribute("lang")).toBe(locale);
}

test.describe("B2-B5 Four-Locale Desktop @1440x900", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of LOCALES) {
    test(`${locale}: page loads, locale switches, content rendered, no raw keys`, async ({ page }) => {
      await page.goto("/");
      await switchLocale(page, locale);

      // Main content area is rendered
      const main = page.locator("#main-content");
      await expect(main).toBeVisible();

      // Sidebar navigation is rendered with aria-label
      const aside = page.locator("aside[aria-label]").first();
      await expect(aside).toBeVisible();

      // Body text should not contain raw runtime copy keys
      const bodyText = await main.innerText();
      expect(bodyText).not.toMatch(/riskSummary\.label[A-Z]/);
      expect(bodyText).not.toMatch(/riskSummary\.missing[A-Z]/);
      expect(bodyText).not.toMatch(/riskSummary\.next[A-Z]/);
      expect(bodyText).not.toMatch(/wizardStep\.[a-z]/);
      expect(bodyText).not.toContain("undefined");
      expect(bodyText.length).toBeGreaterThan(100);
    });
  }

  test("EN: no Chinese product-generated copy in visible page", async ({ page }) => {
    await page.goto("/");
    await switchLocale(page, "en");
    await page.waitForTimeout(300);

    const bodyText = await page.locator("#main-content").innerText();
    for (const phrase of CHINESE_LEAK_PHRASES) {
      expect(bodyText, `EN page leaked Chinese: "${phrase}"`).not.toContain(phrase);
    }
  });

  test("KO: no Chinese product-generated copy in visible page", async ({ page }) => {
    await page.goto("/");
    await switchLocale(page, "ko");
    await page.waitForTimeout(300);

    const bodyText = await page.locator("#main-content").innerText();
    for (const phrase of CHINESE_LEAK_PHRASES) {
      expect(bodyText, `KO page leaked Chinese: "${phrase}"`).not.toContain(phrase);
    }
  });

  test("JA: no Chinese-only phrases in visible page", async ({ page }) => {
    await page.goto("/");
    await switchLocale(page, "ja");
    await page.waitForTimeout(300);

    const bodyText = await page.locator("#main-content").innerText();
    for (const phrase of CHINESE_ONLY_FOR_JA) {
      expect(bodyText, `JA page leaked Chinese: "${phrase}"`).not.toContain(phrase);
    }
  });

  test("all locales: main content text changes with locale", async ({ page }) => {
    await page.goto("/");
    const descriptions: string[] = [];
    for (const locale of LOCALES) {
      await switchLocale(page, locale);
      const main = page.locator("#main-content");
      const text = await main.innerText();
      descriptions.push(text.slice(0, 200));
    }
    // zh-TW and EN should differ
    expect(descriptions[0]).not.toBe(descriptions[1]);
  });
});

test.describe("B2-B5 Mobile Viewport Tests", () => {
  const viewports = [
    { width: 360, height: 844, name: "360x844" },
    { width: 390, height: 844, name: "390x844" },
    { width: 430, height: 932, name: "430x932" },
  ];

  for (const vp of viewports) {
    test(`${vp.name} EN: no horizontal overflow, main content visible`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await switchLocale(page, "en");

      // No horizontal overflow
      const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(docWidth).toBeLessThanOrEqual(vp.width + 2);

      // Main content visible
      await expect(page.locator("#main-content")).toBeVisible();
    });

    test(`${vp.name} JA: no horizontal overflow, main content visible`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await switchLocale(page, "ja");

      const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(docWidth).toBeLessThanOrEqual(vp.width + 2);

      await expect(page.locator("#main-content")).toBeVisible();
    });

    test(`${vp.name} KO: no horizontal overflow`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await switchLocale(page, "ko");

      const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(docWidth).toBeLessThanOrEqual(vp.width + 2);

      await expect(page.locator("#main-content")).toBeVisible();
    });
  }
});

test.describe("B2-B5 Console and Error Monitoring", () => {
  test("initial load: no hydration errors, no page errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
    page.on("pageerror", (err) => pageErrors.push(err.message));

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const hydrationErrors = [...consoleErrors, ...pageErrors].filter((e) =>
      /hydration|mismatch|did not match/i.test(e)
    );
    expect(hydrationErrors, "Hydration errors").toEqual([]);
    expect(pageErrors, "Unhandled page errors").toEqual([]);
  });

  for (const locale of LOCALES) {
    test(`${locale}: no page errors after locale switch`, async ({ page }) => {
      const pageErrors: string[] = [];
      page.on("pageerror", (err) => pageErrors.push(err.message));

      await page.goto("/");
      await switchLocale(page, locale);
      await page.waitForTimeout(500);

      expect(pageErrors, `Page errors in ${locale}`).toEqual([]);
    });
  }
});
