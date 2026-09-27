import { expect, test } from "@playwright/test";

const NOW = "2026-09-27T08:00:00.000Z";
test.describe.configure({ mode: "serial" });

function identityAnchor(stale = false) {
  return {
    version: 1 as const,
    scope: "journey_browser_anchor" as const,
    journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
    address_input: "臺北市信義區市府路1號",
    normalized_address: "臺北市信義區市府路1號",
    coordinates: { latitude: 25.0375, longitude: 121.5637 },
    administrative_location: {
      city: "臺北市",
      district: "信義區",
      village: "西村里",
      village_code: "63000020-014",
    },
    location_status: stale ? "stale" as const : "candidate" as const,
    parcel: {
      status: "unavailable" as const,
      candidate_id: null,
      candidates: [],
      source_id: null,
      confidence: "unknown" as const,
      limitations: ["no_approved_parcel_identity_evidence"],
      confirmation: null,
    },
    building: {
      status: "unavailable" as const,
      candidate_id: null,
      candidates: [],
      source_id: null,
      confidence: "unknown" as const,
      limitations: ["no_approved_building_identity_evidence"],
      confirmation: null,
    },
    confidence: {
      level: stale ? "unknown" as const : "high" as const,
      domain: "address_spatial_correlation" as const,
      basis: ["normalized_address", "trusted_coordinates", "administrative_area", "resolved_village"],
      limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"],
    },
    evidence: {
      sources: [
        { source_id: "property_selection", kind: "user_selection" as const, checked_at: NOW },
        { source_id: "google_geocoding", kind: "geocoding" as const, checked_at: NOW },
        { source_id: "nlsc_village_boundary", kind: "administrative_boundary" as const, checked_at: NOW },
      ],
      checked_at: NOW,
      limitations: [
        "journey_browser_correlation_only",
        "not_a_government_or_vnext_property_identifier",
        "not_parcel_building_ownership_or_legal_boundary_confirmation",
      ],
    },
    revalidation: stale
      ? { status: "needs_revalidation" as const, conflicts: ["normalized_address" as const] }
      : { status: "current" as const, conflicts: [] },
  };
}

function savedCase(stale = false) {
  return {
    id: "saved-case-1",
    title: "市府路案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1 as const,
    workflowMode: "buying_wizard" as const,
    activeWizardStep: "report" as const,
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號" },
    data: {
      inputs: {
        city: "臺北市",
        district: "信義區",
        road: "市府路1號",
        building_type: "住宅大樓",
        area_ping: 30,
        building_age_years: 5,
        floor: 8,
      },
      propertyIdentityAnchor: identityAnchor(stale),
      journeyContext: {
        version: 1 as const,
        propertyContext: {
          city: "臺北市",
          district: "信義區",
          road: "市府路1號",
          addressSummary: "臺北市信義區市府路1號",
          sourceLabel: "Saved case",
          selectionStatus: "selected" as const,
        },
        priceBasis: "asking" as const,
      },
    },
  };
}

async function openSavedJourney(page: import("@playwright/test").Page, stale = false) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const detail = savedCase(stale);
  await expect.poll(async () => {
    await page.evaluate((saved) => {
      window.dispatchEvent(new CustomEvent("proptech:saved-case-loaded", { detail: saved }));
      window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" }));
    }, detail);
    return page.locator("#journey-stage-location").getByTestId("journey-property-identity-card").count();
  }, { timeout: 15_000 }).toBe(1);
}

async function selectStep(page: import("@playwright/test").Page, step: string) {
  await page.evaluate((detail) => {
    window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail }));
  }, step);
}

test.beforeEach(async ({ page }) => {
  await page.route("http://e2e.test/**", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "not configured in identity UI test" }),
  }));
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

test("Location and Decision expose one bounded journey identity without cadastral claims", async ({ page }) => {
  await openSavedJourney(page);

  const locationCard = page.locator("#journey-stage-location").getByTestId("journey-property-identity-card");
  await expect(locationCard).toBeVisible();
  await expect(locationCard).toContainText("Journey property identity");
  await expect(locationCard).toContainText("臺北市信義區市府路1號");
  await expect(locationCard).toContainText("臺北市 · 信義區");
  await expect(locationCard).toContainText("西村里");
  await expect(locationCard).toContainText("Parcel: Unavailable");
  await expect(locationCard).toContainText("Building: Unavailable");
  await expect(locationCard).toContainText("High — address/location evidence only");
  await expect(locationCard).toContainText("Google geocoding");
  await expect(locationCard).toContainText("NLSC village boundary");
  await expect(locationCard).toContainText("not an official cadastral, government, legal, or durable VNext property ID");
  await expect(locationCard).toContainText("does not confirm parcel, building, ownership, title, or legal boundary");

  await selectStep(page, "decision");
  const decisionCard = page.locator("#journey-stage-decision").getByTestId("journey-property-identity-card");
  await expect(decisionCard).toBeVisible();
  await expect(decisionCard).toContainText("63000020-014");
});

test("parcel and building unavailability do not gate later journey stages", async ({ page }) => {
  await openSavedJourney(page);

  for (const step of ["location", "price", "affordability", "decision"]) {
    await selectStep(page, step);
    await expect(page.locator(`#journey-stage-${step}`)).toBeVisible();
  }

  const decisionCard = page.locator("#journey-stage-decision").getByTestId("journey-property-identity-card");
  await expect(decisionCard).toContainText("Parcel: Unavailable");
  await expect(decisionCard).toContainText("Building: Unavailable");
});

test("stale saved identity is visibly marked for revalidation", async ({ page }) => {
  await openSavedJourney(page, true);
  await selectStep(page, "decision");

  const card = page.locator("#journey-stage-decision").getByTestId("journey-property-identity-card");
  await expect(card).toContainText("Needs revalidation");
  await expect(card).toContainText("Stored identity evidence conflicts with newly resolved evidence");
  await expect(card.getByText("Unknown — address/location evidence only", { exact: true })).toBeVisible();
});
