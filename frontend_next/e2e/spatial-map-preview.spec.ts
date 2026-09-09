import { expect, test } from "@playwright/test";

const previewPath = "/dev/spatial-map-preview";
const productionTarget = process.env.SPATIAL_PREVIEW_E2E_TARGET === "production";

if (productionTarget) {
  test("production preview exclusion returns 404 and stays out of product navigation", async ({ page }) => {
    const homeResponse = await page.goto("/");
    expect(homeResponse?.status()).toBe(200);
    await expect(page.locator(`a[href="${previewPath}"]`)).toHaveCount(0);

    const previewResponse = await page.goto(previewPath);
    expect(previewResponse?.status()).toBe(404);
    await expect(page.getByTestId("map-workspace-shell")).toHaveCount(0);
  });
} else {
  test.beforeEach(async ({ page }) => {
    const response = await page.goto(previewPath);
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId("map-workspace-shell")).toBeVisible();
  });

  test("presents an unmistakable synthetic Case-scoped workspace", async ({ page }) => {
    await expect(page.getByText("Development-only preview", { exact: true })).toBeVisible();
    await expect(page.getByText("Synthetic / Demo data", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Investigate location evidence");
    await expect(page.getByText("Synthetic property scenario C", { exact: true })).toBeVisible();
    await expect(page.getByText(/No live API, external map tile, production session, or customer data/)).toBeVisible();
  });

  test("parcel selection preserves the candidate versus reviewed distinction", async ({ page }) => {
    const candidate = page.getByTestId("parcel-card-demo-geometry-candidate-b-v1");
    const reviewed = page.getByTestId("parcel-card-demo-geometry-confirmed-v3");
    await expect(candidate).toContainText("Candidate · inspect only");
    await expect(reviewed).toContainText("Reviewed · working geometry");

    await candidate.click();
    await expect(candidate).toHaveAttribute("aria-pressed", "true");
    await expect(reviewed).toHaveAttribute("aria-pressed", "false");
    const summary = page.getByTestId("selected-feature-summary");
    await expect(summary).toContainText("Candidate — not confirmed");
    await expect(summary).toContainText("creates no PropertyEntity, CasePropertyLink, confirmation, ownership claim, or safety finding");
  });

  test("layer toggles update the overlay and legend while retaining evidence", async ({ page }) => {
    const control = page.getByTestId("layer-control-planning_reference");
    const checkbox = control.getByRole("checkbox");
    await expect(checkbox).toBeChecked();
    await expect(page.getByTestId("map-overlay-planning_reference")).toBeVisible();
    await expect(page.getByTestId("legend-planning_reference")).toBeVisible();

    await checkbox.uncheck();
    await expect(page.getByTestId("map-overlay-planning_reference")).toHaveCount(0);
    await expect(page.getByTestId("legend-planning_reference")).toHaveCount(0);
    const retainedEvidence = page.locator('[data-evidence-id="demo-observation-planning"]');
    await expect(retainedEvidence).toBeVisible();
    await expect(retainedEvidence.locator("xpath=..")).toContainText("Layer hidden · evidence retained");
    await expect(page.getByTestId("empty-layer-boundary")).toContainText("never means “safe” or “no risk.”");
  });

  test("evidence rail keeps unknown, unavailable, partial, stale, and no-match states distinct", async ({ page }) => {
    for (const state of ["unknown", "unavailable", "partial_coverage", "stale", "no_match"]) {
      await expect(page.getByTestId(`evidence-state-${state}`).first()).toBeVisible();
    }
    await expect(page.getByTestId("evidence-state-unknown")).toContainText("Unknown");
    await expect(page.getByTestId("evidence-state-unavailable")).toContainText("Provider unavailable");
    await expect(page.getByTestId("evidence-state-partial_coverage")).toContainText("Partial coverage");
    await expect(page.getByTestId("evidence-state-stale")).toContainText("Stale");
    await expect(page.getByTestId("evidence-state-no_match")).toContainText("No match");

    const unavailable = page.getByTestId("evidence-state-unavailable");
    await unavailable.getByRole("button", { name: "Show evidence details" }).click();
    await expect(unavailable).toContainText("Unavailable does not establish absence");
  });

  test("loading state is announced without contacting a provider", async ({ page }) => {
    await page.getByTestId("refresh-demo-observations").click();
    const loading = page.getByTestId("map-loading-state");
    await expect(loading).toBeVisible();
    await expect(loading).toContainText("No provider or network request is made.");
    await expect(loading).toHaveCount(0, { timeout: 3_000 });
    await expect(page.getByTestId("investigation-map").locator("xpath=..")).toHaveAttribute("aria-busy", "false");
  });

  test("map features and layer controls support keyboard interaction", async ({ page }) => {
    const feature = page.getByTestId("map-feature-demo-geometry-candidate-a-v1");
    await feature.focus();
    await expect(feature).toBeFocused();
    await feature.press("Enter");
    await expect(feature).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("selected-feature-summary")).toContainText("Candidate parcel A");

    const accessToggle = page.getByTestId("layer-control-access_context").getByRole("checkbox");
    await accessToggle.focus();
    await accessToggle.press("Space");
    await expect(accessToggle).not.toBeChecked();
  });

  test("hiding a selected parcel layer clears only the inspection focus", async ({ page }) => {
    await page.getByTestId("parcel-card-demo-geometry-candidate-a-v1").click();
    await expect(page.getByTestId("selected-feature-summary")).toBeVisible();
    await page.getByTestId("layer-control-parcel_candidates").getByRole("checkbox").uncheck();
    await expect(page.getByTestId("selected-feature-summary")).toHaveCount(0);
    await expect(page.getByTestId("no-feature-selected")).toBeVisible();
    await expect(page.getByText(/No record was changed/)).toBeAttached();
  });

  test("mobile viewport keeps map, controls, and evidence within the page", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expect(page.getByTestId("investigation-map")).toBeVisible();
    await expect(page.getByRole("button", { name: "Zoom in" })).toBeVisible();
    await expect(page.getByTestId("evidence-panel")).toBeVisible();
    const metrics = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      mapWidth: document.querySelector<HTMLElement>('[data-testid="investigation-map"]')?.getBoundingClientRect().width ?? 0,
      zoomTarget: document.querySelector<HTMLElement>('button[aria-label="Zoom in"]')?.getBoundingClientRect().height ?? 0,
    }));
    expect(metrics.overflow).toBeLessThanOrEqual(0);
    expect(metrics.mapWidth).toBeGreaterThan(340);
    expect(metrics.mapWidth).toBeLessThanOrEqual(390);
    expect(metrics.zoomTarget).toBeGreaterThanOrEqual(38);
  });

  test("preview is absent from homepage links and normal navigation", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);
    await expect(page.locator(`a[href="${previewPath}"]`)).toHaveCount(0);
    await expect(page.locator("nav", { hasText: "Spatial Map Workspace component preview" })).toHaveCount(0);
  });
}
