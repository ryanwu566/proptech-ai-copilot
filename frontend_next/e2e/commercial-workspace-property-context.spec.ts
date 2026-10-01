import { expect, test } from "@playwright/test";

const NOW = "2026-09-27T08:00:00.000Z";

function savedCase(stale = false, evidence: "none" | "valuation" | "commute" | "primary" = "none") {
  return {
    id: "saved-case-identity",
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
      propertyIdentityAnchor: {
        version: 1,
        scope: "journey_browser_anchor",
        journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
        address_input: "臺北市信義區市府路1號",
        normalized_address: "臺北市信義區市府路1號",
        coordinates: { latitude: 25.0375, longitude: 121.5637 },
        administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" },
        location_status: stale ? "stale" : "candidate",
        parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
        building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_building_identity_evidence"], confirmation: null },
        confidence: { level: stale ? "unknown" : "high", domain: "address_spatial_correlation", basis: ["normalized_address", "trusted_geocoding_coordinates", "administrative_area", "resolved_village"], limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"] },
        evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: NOW }, { source_id: "nlsc_village_boundary", kind: "administrative_boundary", checked_at: NOW }], checked_at: NOW, limitations: ["journey_browser_correlation_only"] },
        revalidation: stale ? { status: "needs_revalidation", conflicts: ["normalized_address"] } : { status: "current", conflicts: [] },
      },
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 },
        priceBasis: "asking",
        activePriceWan: 2480,
      },
      valuation: evidence === "valuation" ? { status: "partial" } : undefined,
      commuteRoute: evidence === "commute" ? { status: "partial" } : undefined,
      marketInsight: evidence === "primary" ? { status: "partial" } : undefined,
      locationInsight: evidence === "primary" ? { status: "partial" } : undefined,
    },
  };
}

test("section placeholders expose each evidence slice in a mixed restored section", async ({ page }) => {
  await page.addInitScript(({ storageKey, row }) => window.localStorage.setItem(storageKey, JSON.stringify([row])), {
    storageKey: "proptech.savedCases.v1",
    row: savedCase(false, "primary"),
  });
  await page.goto("/cases/saved-case-identity/market");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("市場資料");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("目前無法取得證據");
  await expect(page.locator('[data-evidence-key="valuation"]')).toContainText("價格推估");
  await expect(page.locator('[data-evidence-key="valuation"]')).toContainText("尚未查詢此區段");

  await page.goto("/cases/saved-case-identity/location");
  await expect(page.locator('[data-evidence-key="location"]')).toContainText("地點資料");
  await expect(page.locator('[data-evidence-key="location"]')).toContainText("已恢復有限摘要");
  await expect(page.locator('[data-evidence-key="commute"]')).toContainText("通勤資料");
  await expect(page.locator('[data-evidence-key="commute"]')).toContainText("尚未查詢此區段");
});

async function seed(page: import("@playwright/test").Page, stale = false) {
  await page.addInitScript(({ storageKey, row }) => {
    window.localStorage.setItem(storageKey, JSON.stringify([row]));
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  }, { storageKey: "proptech.savedCases.v1", row: savedCase(stale) });
}

test("property header shows bounded identity, price basis, saved state, and provenance", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/saved-case-identity/overview");

  const header = page.getByRole("banner", { name: "目前物件" });
  await expect(header).toContainText("臺北市信義區市府路1號");
  await expect(header).toContainText("物件已確認");
  await expect(header).toContainText("開價");
  await expect(header).toContainText("2,480 萬元");
  await expect(header).toContainText("已儲存");
  await header.getByText("物件與來源詳細資料").click();
  await expect(header).toContainText("瀏覽器案件關聯錨點");
  await expect(header).toContainText("不代表地號、建物、所有權或法律身分");
});

test("stale identity remains explicit in the header and Overview blocker", async ({ page }) => {
  await seed(page, true);
  await page.goto("/cases/saved-case-identity/overview");

  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("物件資料已變更，需重新確認");
  await expect(page.getByRole("heading", { name: "需先處理" })).toBeVisible();
  await expect(page.getByText("重新確認目前物件")).toBeVisible();
});

test("workspace shell has no document overflow at 390px", async ({ page }) => {
  await seed(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/saved-case-identity/overview");

  await expect(page.getByRole("banner", { name: "目前物件" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "案件工作區" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});
