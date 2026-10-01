import { expect, test } from "@playwright/test";

const NOW = "2026-09-27T08:00:00.000Z";

function savedCase() {
  return {
    id: "market-price-case",
    title: "市府路案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "report",
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號", propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 },
        priceBasis: "asking",
        activePriceWan: 2480,
      },
      marketInsight: {
        city: "臺北市",
        county: "臺北市",
        district: "信義區",
        period: "2025-01–2026-07",
        average_unit_price: 53.1,
        avg_price_per_ping: 53.1,
        transaction_count: 18,
        transaction_volume: 18,
        record_count: 18,
        summary: "近期成交單價集中於每坪 50 至 55 萬元。",
        source_name: "內政部不動產實價登錄",
        source_updated_at: "2026-08-31",
        coverage_status: "covered",
        data_status: "available",
        caveat: "樣本僅供初步比較。",
        disclaimer: "成交資料不等同正式估價。",
        history: [
          { period: "2026-07", average_unit_price: 53.1, transaction_count: 8 },
          { period: "2026-06", average_unit_price: 51.8, transaction_count: 10 },
        ],
        sample_status: "sufficient",
        freshness_status: "fresh",
        period_min: "2025-01",
        period_max: "2026-07",
        newest_effective_period: "2026-07",
        median_unit_price_per_ping: 52.4,
        p25_unit_price_per_ping: 49.8,
        p75_unit_price_per_ping: 55.6,
        median_total_price: 1850,
        effective_scope_label: "臺北市信義區",
        effective_analysis_level: "DISTRICT",
        effective_sample_count: 18,
        fallback_applied: true,
      },
    },
  };
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(({ storageKey, row }) => {
    window.localStorage.setItem(storageKey, JSON.stringify([row]));
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  }, { storageKey: "proptech.savedCases.v1", row: savedCase() });
});

test("Market & Price route distinguishes price bases and presents saved evidence", async ({ page }) => {
  await page.goto("/cases/market-price-case/market");

  await expect(page.getByRole("heading", { level: 1, name: "價格與市場" })).toBeVisible();
  await expect(page.getByText("可取得的市場證據對這個物件的價格提供了什麼訊息？")).toBeVisible();
  const context = page.getByTestId("market-price-context");
  const scope = page.getByTestId("market-scope-context");
  await expect(scope).toContainText("臺北市信義區");
  await expect(scope).toContainText("行政區（已回退）");
  await expect(scope).toContainText("18 筆");
  await expect(context).toContainText("開價");
  await expect(context).toContainText("2,480 萬元");
  await expect(context).toContainText("市場成交中位數");
  await expect(context).toContainText("1,850 萬元");
  await expect(context).toContainText("52.4 萬元／坪");

  await expect(page.getByTestId("market-primary-finding")).toContainText("開價高於");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("已恢復有限摘要");
  await expect(page.getByRole("heading", { name: "可比成交證據" })).toBeVisible();
  await expect(page.getByText("已儲存案件未保留逐筆可比成交")).toBeVisible();
  await expect(page.locator('[data-evidence-key="valuation"]')).toContainText("尚未查詢此區段");
  await expect(page.getByText("內政部不動產實價登錄")).toBeVisible();
  await expect(page.getByText("2025/01–2026/07")).toBeVisible();
  await expect(page.getByText("2026-08-31")).toBeVisible();
});

test("Market & Price route does not create document overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/market-price-case/market");

  await expect(page.getByTestId("market-price-context")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});
