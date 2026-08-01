import { test, expect } from "./fixtures";

test("three-minute TaxOracle demo is editable and causal", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("competition-mvp-banner")).toBeVisible();
  await page.getByTestId("competition-demo-start").getByRole("button").click();
  await expect(page.getByTestId("competition-demo")).toBeVisible();
  await page.getByTestId("demo-property-price").fill("2500");
  await page.getByTestId("demo-residency_condition_met").uncheck();
  await page.locator("button.demo-calculate-button").click();
  await expect(page.getByTestId("human-tax-outcome")).toContainText(/Preliminary tax screening|初步稅務篩選|税務の予備|예비 세무/);
  await expect(page.getByTestId("competition-demo")).not.toContainText("sold_self_occupied");
  await expect(page.getByTestId("competition-demo")).not.toContainText("compatibility-screening-v1");
  await page.getByRole("button", { name: /Evidence|證據|証拠|근거/ }).click();
  await expect(page.getByTestId("evidence-center")).toBeVisible();
});
