import { expect, test } from "@playwright/test";

const NOW = "2026-09-27T08:00:00.000Z";

function savedCase() {
  return {
    id: "saved-case-1",
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
    },
  };
}

test("the overview preserves access to the existing case workbench", async ({ page }) => {
  await page.goto("/cases/saved-case-1/overview");
  await page.getByRole("link", { name: "開啟既有案件規劃工具" }).click();
  await expect(page).toHaveURL(/\/cases\/saved-case-1\/planning$/);
  await expect(page.getByTestId("legacy-case-workbench")).toBeVisible();
  await expect(page.getByRole("button", { name: "列印目前摘要" })).toBeVisible();
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(({ storageKey, row }) => {
    window.localStorage.setItem(storageKey, JSON.stringify([row]));
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  }, { storageKey: "proptech.savedCases.v1", row: savedCase() });
});

test("saved case entry opens the canonical overview route", async ({ page }) => {
  await page.goto("/cases");
  await page.getByRole("link", { name: /市府路案件/ }).click();
  await expect(page).toHaveURL(/\/cases\/saved-case-1\/overview$/);
  await expect(page.getByRole("heading", { level: 1, name: "物件總覽" })).toBeVisible();
});

test("section links are URL-native across refresh and browser history", async ({ page }) => {
  await page.goto("/cases/saved-case-1/overview");
  await page.getByRole("link", { name: "價格與市場", exact: true }).click();
  await expect(page).toHaveURL(/\/market$/);
  await expect(page.getByRole("heading", { level: 1, name: "價格與市場" })).toBeVisible();

  await page.getByRole("link", { name: "區位與通勤", exact: true }).click();
  await expect(page).toHaveURL(/\/location$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/market$/);
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "價格與市場" })).toBeVisible();
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("臺北市信義區市府路1號");
});

test("the case root redirects to overview and an unknown local case fails locally", async ({ page }) => {
  await page.goto("/cases/saved-case-1");
  await expect(page).toHaveURL(/\/cases\/saved-case-1\/overview$/);

  await page.goto("/cases/not-saved/overview");
  await expect(page.getByRole("heading", { name: "找不到已儲存案件" })).toBeVisible();
  await expect(page.getByRole("link", { name: "返回已儲存案件" })).toBeVisible();
});
