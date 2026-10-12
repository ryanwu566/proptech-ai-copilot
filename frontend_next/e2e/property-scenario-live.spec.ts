import { expect, test } from "@playwright/test";

test("primary consequences stay visible while editing on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.addInitScript(() => {
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([{
      id: "live-case", title: "Live scenario", createdAt: "2026-10-12T08:00:00Z", updatedAt: "2026-10-12T08:00:00Z", version: 1,
      workflowMode: "buying_wizard", activeWizardStep: "affordability", progress: 60,
      inputSummary: { city: "臺北市", district: "信義區", road: "信義路五段7號", propertyPrice: 1850 },
      data: { inputs: { city: "臺北市", district: "信義區", road: "信義路五段7號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 } },
    }]));
  });
  await page.goto("/cases/live-case/scenarios");
  const card = page.getByTestId("scenario-A");
  for (const [field, value] of Object.entries({ offerTwd: "18500000", downValue: "20", ratePercent: "2.2", loanYears: "30", acquisitionTwd: "150000", recurringTwd: "4000", renovationTwd: "500000", holdingYears: "5" })) await card.getByTestId(`input-${field}`).fill(value);
  const live = card.getByTestId("live-results");
  await expect(live).toContainText("56,196");
  await expect(live).toContainText("4,350,000");
  await card.getByTestId("input-recurringTwd").scrollIntoViewIfNeeded();
  const bounds = await live.boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds!.y).toBeGreaterThanOrEqual(0);
  expect(bounds!.y + bounds!.height).toBeLessThan(900);
  await card.getByTestId("input-recurringTwd").fill("5000");
  await expect(live).toContainText("61,196");
  await page.keyboard.press("Tab");
  await expect(card.getByTestId("input-renovationTwd")).toBeFocused();
});
