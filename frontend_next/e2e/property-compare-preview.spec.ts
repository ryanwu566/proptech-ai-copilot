import { expect, test, type Page } from "@playwright/test";

const PREVIEW_PATH = "/dev/property-compare-preview";

async function scenario(page: Page, value: "two-known" | "mixed-evidence" | "incompatible" | "invalid-inputs") {
  await page.getByTestId("scenario-select").selectOption(value);
  await expect(page.getByTestId("selection-count")).toContainText("0 / 3");
}

async function selectCases(page: Page, ...ids: string[]) {
  for (const id of ids) await page.getByTestId(`case-option-${id}`).click();
}

test.beforeEach(async ({ page }) => {
  await page.goto(PREVIEW_PATH);
  await expect(page.locator("[data-preview-marker='property-compare-synthetic-preview']")).toBeVisible();
  await expect(page.getByText("全頁皆為合成資料")).toBeVisible();
});

test("zero, one, two and three selections; fourth is rejected; remove does not delete", async ({ page }) => {
  await scenario(page, "mixed-evidence");
  await expect(page.getByTestId("selection-guidance")).toContainText("尚未選擇");
  await expect(page.getByTestId("comparison-desktop")).toHaveCount(0);

  await selectCases(page, "synthetic-river-01");
  await expect(page.getByTestId("selection-guidance")).toContainText("再選 1 個");

  await selectCases(page, "synthetic-incomplete-03");
  await expect(page.getByTestId("selection-count")).toContainText("2 / 3");
  await expect(page.getByTestId("comparison-desktop")).toBeVisible();

  await selectCases(page, "synthetic-risk-04");
  await expect(page.getByTestId("selection-count")).toContainText("3 / 3");
  await page.getByTestId("case-option-synthetic-conflict-05").click();
  await expect(page.getByTestId("selection-limit-message")).toContainText("最多只能選擇 3 個案件");
  await expect(page.getByTestId("case-option-synthetic-conflict-05")).toHaveAttribute("aria-pressed", "false");

  await page.getByTestId("compare-column-synthetic-incomplete-03").getByRole("button", { name: /從比較中移除/ }).click();
  await expect(page.getByTestId("selection-count")).toContainText("2 / 3");
  await expect(page.getByTestId("case-option-synthetic-incomplete-03")).toBeVisible();
  await expect(page.getByTestId("case-option-synthetic-incomplete-03")).toHaveAttribute("aria-pressed", "false");
});

test("stable case identity survives column reordering and picker filtering", async ({ page }) => {
  await scenario(page, "mixed-evidence");
  await selectCases(page, "synthetic-river-01", "synthetic-incomplete-03", "synthetic-risk-04");
  const desktop = page.getByTestId("comparison-desktop");
  const columns = desktop.locator("[data-testid^='compare-column-']");
  await expect(columns).toHaveCount(3);
  await expect(columns.nth(0)).toHaveAttribute("data-case-id", "synthetic-river-01");

  await desktop.getByTestId("compare-column-synthetic-risk-04").getByRole("button", { name: /向左移/ }).click();
  await expect(columns.nth(1)).toHaveAttribute("data-case-id", "synthetic-risk-04");
  await expect(columns.nth(2)).toHaveAttribute("data-case-id", "synthetic-incomplete-03");

  await page.getByTestId("case-filter").fill("資料衝突");
  await expect(page.getByTestId("case-option-synthetic-conflict-05")).toBeVisible();
  await expect(page.getByTestId("case-option-synthetic-river-01")).toHaveCount(0);
  await expect(desktop.getByTestId("compare-column-synthetic-river-01")).toBeVisible();
  await expect(desktop.getByTestId("compare-column-synthetic-risk-04")).toBeVisible();
});

test("differences-only preserves gaps, high risk, no-match terrain, sources and legacy identity", async ({ page }) => {
  await scenario(page, "mixed-evidence");
  await selectCases(page, "synthetic-river-01", "synthetic-incomplete-03", "synthetic-risk-04");
  await page.getByTestId("differences-only").check();

  for (const field of ["warnings", "freshness", "sources", "nextChecks", "terrain", "valuation", "monthlyMortgage"]) {
    await expect(page.getByTestId(`row-${field}`)).toBeVisible();
  }
  await expect(page.getByTestId("cell-warnings-synthetic-risk-04")).toContainText("已知高風險訊號");
  await expect(page.getByTestId("cell-monthlyMortgage-synthetic-incomplete-03")).toContainText("未知");
  await expect(page.getByTestId("cell-monthlyMortgage-synthetic-incomplete-03").locator("strong").first()).toHaveText("未知");
  await expect(page.getByTestId("cell-valuation-synthetic-incomplete-03")).toContainText("不可供比較");
  await expect(page.getByTestId("cell-valuation-synthetic-incomplete-03")).not.toContainText("1,700");
  await expect(page.getByTestId("cell-terrain-synthetic-incomplete-03")).toContainText("未命中");
  await expect(page.getByTestId("cell-terrain-synthetic-incomplete-03")).toContainText("不等於沒有災害風險");
  await expect(page.getByTestId("cell-identity-synthetic-incomplete-03")).toContainText("舊版案件／未驗證");
  await expect(page.getByTestId("cell-identity-synthetic-incomplete-03")).not.toContainText("PropertyEntity ·");

  const disclosure = page.getByTestId("cell-sources-synthetic-risk-04").getByTestId("source-disclosure").first();
  await disclosure.locator("summary").click();
  await expect(disclosure).toContainText("合成且可能過期");
  await expect(page.getByTestId("cell-freshness-synthetic-risk-04")).toContainText("案件更新");
  await expect(page.getByTestId("cell-freshness-synthetic-risk-04")).toContainText("資料時點");
});

test("incompatible currencies, units, periods and price bases never produce a numeric delta", async ({ page }) => {
  await scenario(page, "incompatible");
  await selectCases(page, "synthetic-basis-01", "synthetic-basis-02", "synthetic-basis-03");
  await page.getByTestId("reference-case-select").selectOption("synthetic-basis-01");

  await expect(page.getByTestId("cell-askingPrice-synthetic-basis-02")).toContainText("62 萬美元");
  await expect(page.getByTestId("cell-askingPrice-synthetic-basis-02")).toContainText("無法比較：幣別不同");
  await expect(page.getByTestId("cell-area-synthetic-basis-02")).toContainText("99.2 平方公尺");
  await expect(page.getByTestId("cell-area-synthetic-basis-02")).toContainText("無法比較：單位不同");
  await expect(page.getByTestId("cell-askingPrice-synthetic-basis-03")).toContainText("基礎：成交價");
  await expect(page.getByTestId("cell-askingPrice-synthetic-basis-03")).toContainText("無法比較：價格或數值基礎不同");
  await expect(page.getByTestId("cell-monthlyMortgage-synthetic-basis-03")).toContainText("元／年");
  await expect(page.getByTestId("cell-monthlyMortgage-synthetic-basis-03")).toContainText("無法比較：計算期間不同");
});

test("compatible values show arithmetic deltas without recommendation language", async ({ page }) => {
  await selectCases(page, "synthetic-river-01", "synthetic-garden-02");
  await page.getByTestId("reference-case-select").selectOption("synthetic-river-01");
  await expect(page.getByTestId("cell-askingPrice-synthetic-river-01")).toContainText("參考基準");
  await expect(page.getByTestId("cell-askingPrice-synthetic-garden-02")).toContainText("相較基準 +140 萬元");
  await expect(page.getByTestId("cell-area-synthetic-garden-02")).toContainText("相較基準 +6.6 坪");
  await expect(page.getByTestId("property-compare-workspace")).toContainText("不評分、不排序");
  await expect(page.getByTestId("property-compare-workspace")).not.toContainText("最佳物件");
});

test("duplicate/empty ids and malformed numbers are rejected without zero substitution", async ({ page }) => {
  await scenario(page, "invalid-inputs");
  await expect(page.getByTestId("dataset-issues")).toContainText("重複");
  await expect(page.getByTestId("dataset-issues")).toContainText("缺少案件 ID");
  await expect(page.locator("[data-testid^='case-option-']")).toHaveCount(2);
  await selectCases(page, "synthetic-legacy-empty", "synthetic-malformed");
  for (const id of ["synthetic-legacy-empty", "synthetic-malformed"]) {
    await expect(page.getByTestId(`cell-askingPrice-${id}`)).toContainText("格式不正確");
    await expect(page.getByTestId(`cell-askingPrice-${id}`)).not.toContainText("0 元");
  }
  await expect(page.getByTestId("cell-identity-synthetic-legacy-empty")).toContainText("舊版案件／未驗證");
});

test("keyboard selection and contained mobile layout use no storage or live providers", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!url.hostname.includes("127.0.0.1") && url.hostname !== "localhost") externalRequests.push(request.url());
  });
  await page.addInitScript(() => {
    const calls: string[] = [];
    Object.defineProperty(window, "__compareStorageCalls", { value: calls, configurable: false });
    for (const method of ["getItem", "setItem", "removeItem", "clear"] as const) {
      const original = Storage.prototype[method];
      Object.defineProperty(Storage.prototype, method, {
        configurable: true,
        value: function (...args: unknown[]) {
          calls.push(`${method}:${String(args[0] ?? "")}`);
          return Reflect.apply(original, this, args);
        },
      });
    }
  });
  await page.goto(PREVIEW_PATH);
  await page.evaluate(() => { ((window as Window & { __compareStorageCalls?: string[] }).__compareStorageCalls ?? []).length = 0; });
  const first = page.getByTestId("case-option-synthetic-river-01");
  await first.focus();
  await page.keyboard.press("Space");
  const second = page.getByTestId("case-option-synthetic-garden-02");
  await second.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("selection-count")).toContainText("2 / 3");
  await expect(page.getByTestId("comparison-mobile")).toBeVisible();
  await expect(page.getByTestId("comparison-desktop")).toBeHidden();
  const widths = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client);
  const storageCalls = await page.evaluate(() => (window as Window & { __compareStorageCalls?: string[] }).__compareStorageCalls ?? []);
  expect(storageCalls).toEqual([]);
  expect(externalRequests).toEqual([]);
});
