import { test, expect } from "./fixtures";

test("three-minute TaxOracle demo is editable and causal", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("competition-mvp-banner")).toBeVisible();
  await page.getByTestId("competition-demo-start").getByRole("button").click();
  await expect(page.getByTestId("competition-demo")).toBeVisible();
  await page.getByTestId("demo-property-price").fill("2500");
  await page.getByTestId("demo-residency_condition_met").uncheck();
  await page.getByTestId("competition-demo").getByRole("button", { name: /recalculate|重新計算|再計算|다시 계산/ }).click();
  await expect(page.getByText("manual_review", { exact: true })).toBeVisible();
  await expect(page.getByTestId("competition-demo").getByText(/compatibility-screening-v1/).first()).toBeVisible();
  await page.getByRole("button", { name: /Evidence|證據|証拠|근거/ }).click();
  await expect(page.getByTestId("evidence-center")).toBeVisible();
});
