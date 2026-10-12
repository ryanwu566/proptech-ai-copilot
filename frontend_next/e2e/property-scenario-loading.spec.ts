import { expect, test } from "@playwright/test";

test("Scenario Lab code and full locale copy load only after entering the lab", async ({ page }) => {
  const scripts: Promise<string>[] = [];
  const documents: Promise<string>[] = [];
  const scenarioRequests: string[] = [];
  page.on("response", response => {
    if (new URL(response.url()).pathname.endsWith(".js")) scripts.push(response.text());
    if (response.request().resourceType() === "document" && response.status() === 200) documents.push(response.text());
  });
  page.on("request", request => {
    if (new URL(request.url()).pathname.endsWith("/scenarios")) scenarioRequests.push(request.url());
  });
  await page.route("http://e2e.test/**", route => route.abort());
  await page.addInitScript(() => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([{
      id: "loading-case", title: "Loading property", version: 1,
      createdAt: "2026-10-12T08:00:00Z", updatedAt: "2026-10-12T08:00:00Z",
      workflowMode: "buying_wizard", activeWizardStep: "affordability", progress: 60,
      inputSummary: { city: "Taipei", district: "Xinyi", road: "Road", propertyPrice: 1850 },
      data: { inputs: { city: "Taipei", district: "Xinyi", road: "Road", building_type: "Apartment", area_ping: 30, building_age_years: 5, floor: 8 } },
    }]));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
  });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  // Read completed homepage bodies before navigation invalidates their browser
  // resource identifiers. RSC prefetches can be cancelled; reject any Scenario
  // prefetch by its request below, without needing to read a cancelled body.
  await Promise.all([...scripts, ...documents]);
  await page.goto("/cases/loading-case/finance");
  await page.getByTestId("locale-switcher").selectOption("en");
  const entry = page.getByRole("link", { name: "Scenario Lab", exact: true }).last();
  await expect(entry).toBeVisible();
  await entry.scrollIntoViewIfNeeded();
  await entry.hover();
  await page.waitForLoadState("networkidle");
  const before = (await Promise.all([...scripts, ...documents])).join("\n");
  expect(before.includes("Fixed-rate principal-and-interest"), "full scenario catalogue downloaded before entry").toBe(false);
  expect(before.includes("proptech.scenarios.v1"), "scenario engine downloaded before entry").toBe(false);
  expect(scenarioRequests, "no Scenario route or RSC prefetch before entry").toEqual([]);

  await entry.click();
  await expect(page.getByTestId("scenario-lab")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Property Scenario Lab" })).toBeVisible();
  expect((await Promise.all(scripts)).some(script => script.includes("proptech.scenarios.v1"))).toBe(true);
});
