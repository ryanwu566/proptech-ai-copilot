import type { Page, Route } from "@playwright/test";

import { expect, test } from "./fixtures";

const DISCLAIMER = "Google visual context — not property identity, parcel geometry, cadastral boundary, ownership, or zoning evidence.";
const browserKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY?.trim() ?? "";

function locationResult(accepted = true) {
  return {
    input: { address: "Existing accepted fixture" },
    resolved_location: {
      address_label: "Accepted fixture location",
      latitude: 25.033,
      longitude: 121.5654,
      geocoding_confidence: "high",
    },
    geocoding_acceptance: {
      original_query: "Existing accepted fixture",
      normalized_address: "Accepted fixture location",
      resolved_lat: 25.033,
      resolved_lng: 121.5654,
      geocoding_source: "google_geocoding",
      match_quality: accepted ? "EXACT_OR_ACCEPTABLE" : "MISMATCH",
      accepted_for_analysis: accepted,
      requires_confirmation: !accepted,
      mismatch_reasons: accepted ? [] : ["house_number_mismatch"],
      message: accepted ? "Accepted fixture." : "Confirm this match.",
    },
    radius_m: 800,
    location_score: accepted ? 72 : null,
    category_scores: { transit_score: 80, convenience_score: 75, education_score: 70, green_space_score: 60, medical_score: 65, risk_score: 50 },
    poi_summary: { transit_count: 4, convenience_count: 6, school_count: 2, park_count: 1, medical_count: 3, risk_facility_count: 0 },
    nearest_pois: [{ category: "transit", name: "Fixture station", distance_m: 300, source: "fixture" }],
    strengths: ["Fixture strength"],
    weaknesses: [],
    buyer_fit: { self_use_family: "fit", commuter: "fit", investor: "unknown", elderly: "unknown" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "Location context only." },
    data_quality: { status: accepted ? "good" : "unavailable", missing_sources: [], warnings: accepted ? [] : ["Confirmation required."] },
    scoring_method: { weights: {}, explanation: "Fixture." },
    disclaimer: "Location analysis fixture.",
  };
}

async function openLocationInsight(page: Page, result = locationResult()) {
  await page.goto("/");
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" })));
  await expect(page.locator("#location-insight-calculator")).toBeVisible();
  await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("proptech:location-insight-result-ready", { detail })), result);
  return page.getByTestId("google-location-visual-context");
}

function fulfillGoogleEmbed(route: Route) {
  return route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>Controlled Google embed fixture</title>" });
}

test("browser key absent shows a bounded unavailable state @browser-key-missing", async ({ page }) => {
  test.skip(Boolean(browserKey), "This case runs against the no-browser-key build.");
  const googleRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith("https://www.google.com/maps/embed/")) googleRequests.push(request.url());
  });

  const panel = await openLocationInsight(page);

  await expect(panel).toHaveAttribute("data-google-visual-state", "unavailable");
  await expect(panel.getByText("Google preview is not configured.")).toBeVisible();
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
  await expect(panel.locator("iframe")).toHaveCount(0);
  expect(googleRequests).toEqual([]);
});

test("accepted coordinates render only fixed view and streetview embeds", async ({ page }) => {
  test.skip(!browserKey, "This case runs against the browser-key build.");
  await page.route("https://www.google.com/maps/embed/v1/**", fulfillGoogleEmbed);

  const panel = await openLocationInsight(page);
  const mapFrame = panel.getByTitle("Google map visual context");
  const streetViewFrame = panel.getByTitle("Google Street View visual context");
  await expect(mapFrame).toBeVisible();
  await expect(streetViewFrame).toBeVisible();
  await expect(mapFrame).toHaveAttribute("referrerpolicy", "strict-origin-when-cross-origin");
  await expect(streetViewFrame).toHaveAttribute("referrerpolicy", "strict-origin-when-cross-origin");

  const mapUrl = new URL(await mapFrame.getAttribute("src") ?? "");
  const streetViewUrl = new URL(await streetViewFrame.getAttribute("src") ?? "");
  expect(`${mapUrl.origin}${mapUrl.pathname}`).toBe("https://www.google.com/maps/embed/v1/view");
  expect(Object.fromEntries(mapUrl.searchParams)).toEqual({ key: browserKey, center: "25.033,121.5654", zoom: "17", maptype: "roadmap" });
  expect(`${streetViewUrl.origin}${streetViewUrl.pathname}`).toBe("https://www.google.com/maps/embed/v1/streetview");
  expect(Object.fromEntries(streetViewUrl.searchParams)).toEqual({ key: browserKey, location: "25.033,121.5654", radius: "50" });
  expect(mapUrl.searchParams.has("q")).toBe(false);
  expect(mapUrl.href).not.toContain("Existing+accepted+fixture");
  await expect(panel.getByText("Google Maps", { exact: true })).toBeVisible();
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
});

test("unconfirmed coordinates stay behind the confirmation gate", async ({ page }) => {
  const panel = await openLocationInsight(page, locationResult(false));

  await expect(panel).toHaveAttribute("data-google-visual-state", "confirmation_required");
  await expect(panel.getByText("Confirm the resolved location before loading Google visual context.")).toBeVisible();
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
  await expect(panel.locator("iframe")).toHaveCount(0);
  await expect(page.getByTestId("geocoding-acceptance-gate")).toBeVisible();
});

test("invalid accepted coordinates fail closed without a Google request", async ({ page }) => {
  const result = locationResult();
  result.resolved_location.latitude = Number.NaN;
  const panel = await openLocationInsight(page, result);

  await expect(panel).toHaveAttribute("data-google-visual-state", "preview_unavailable");
  await expect(panel.getByText("The accepted location does not contain valid preview coordinates.")).toBeVisible();
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
  await expect(panel.locator("iframe")).toHaveCount(0);
});

test("a local Street View iframe timeout becomes load_not_confirmed, not a no-imagery claim", async ({ page }) => {
  test.skip(!browserKey, "This case runs against the browser-key build.");
  await page.route("https://www.google.com/maps/embed/v1/view?**", fulfillGoogleEmbed);
  await page.route("https://www.google.com/maps/embed/v1/streetview?**", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1_200));
    await fulfillGoogleEmbed(route);
  });

  const panel = await openLocationInsight(page);
  const streetView = panel.getByRole("region", { name: "Google Street View preview" });
  await expect(streetView).toHaveAttribute("data-preview-state", "load_not_confirmed");
  await expect(streetView.getByText("Load not confirmed")).toBeVisible();
  await expect(streetView).toContainText("does not mean Street View imagery is unavailable");
  await expect(panel).not.toContainText("Street View not available");
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
  await expect(streetView).toHaveAttribute("data-preview-state", "loaded");
  await expect(streetView.getByText("Load not confirmed")).toHaveCount(0);
});

test("Street View container is accessible and mobile layout does not overflow", async ({ page }) => {
  test.skip(!browserKey, "This case runs against the browser-key build.");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("https://www.google.com/maps/embed/v1/**", fulfillGoogleEmbed);

  const panel = await openLocationInsight(page);
  await expect(panel.getByRole("region", { name: "Google Street View preview" })).toBeVisible();
  await expect(panel.getByTitle("Google Street View visual context")).toHaveAttribute("title", "Google Street View visual context");
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
  const dimensions = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, body: document.body.scrollWidth, root: document.documentElement.scrollWidth }));
  expect(dimensions.body).toBeLessThanOrEqual(dimensions.viewport + 1);
  expect(dimensions.root).toBeLessThanOrEqual(dimensions.viewport + 1);
});

test("Location Insight results and existing map navigation remain available", async ({ page }) => {
  if (browserKey) await page.route("https://www.google.com/maps/embed/v1/**", fulfillGoogleEmbed);
  const panel = await openLocationInsight(page);

  await expect(page.getByTestId("location-result")).toContainText("72");
  await expect(panel.getByText(DISCLAIMER)).toBeVisible();
  await expect(page.getByRole("button", { name: "Map Insight", exact: true }).last()).toBeVisible();
});
