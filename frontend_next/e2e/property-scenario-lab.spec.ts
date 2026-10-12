import { expect, test, type Page } from "@playwright/test";

const row = {
  id: "scenario-case", title: "Scenario property", createdAt: "2026-10-12T08:00:00Z", updatedAt: "2026-10-12T08:00:00Z", version: 1,
  workflowMode: "buying_wizard", activeWizardStep: "affordability", progress: 60,
  inputSummary: { city: "臺北市", district: "信義區", road: "信義路五段7號", propertyPrice: 1850 },
  data: { inputs: { city: "臺北市", district: "信義區", road: "信義路五段7號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
    journeyContext: { version: 1, propertyContext: { city: "臺北市", district: "信義區", road: "信義路五段7號", addressSummary: "臺北市信義區信義路五段7號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 1850 }, priceBasis: "asking", activePriceWan: 1850 } },
};

async function setup(page: Page, seed: unknown = row) {
  const providerCalls: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (new URL(request.url()).origin !== "http://127.0.0.1:" + process.env.E2E_PORT) providerCalls.push(request.url());
  });
  await page.route("http://e2e.test/**", route => route.abort());
  await page.addInitScript(({ row }) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row]));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
  }, { row: seed });
  await page.goto("/cases/scenario-case/scenarios");
  await expect(page.getByTestId("scenario-lab")).toBeVisible();
  return { providerCalls, errors };
}

async function completeA(page: Page) {
  const card = page.getByTestId("scenario-A");
  for (const [field, value] of Object.entries({ offerTwd: "18500000", downValue: "20", ratePercent: "2.2", loanYears: "30", acquisitionTwd: "150000", recurringTwd: "4000", renovationTwd: "500000", holdingYears: "5" })) {
    await card.getByTestId(`input-${field}`).fill(value);
  }
}

const titles = { "zh-TW": "物件情境實驗室", en: "Property Scenario Lab", ja: "物件シナリオラボ", ko: "부동산 시나리오 랩" };
for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
  for (const width of [390, 430, 1024, 1440]) {
    test(`${locale} at ${width}: immediate comparison, immutable evidence and no providers`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      const { providerCalls, errors } = await setup(page);
      await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.getByRole("heading", { level: 1, name: titles[locale] })).toBeVisible();
      const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
      await completeA(page);
      const comparison = page.getByTestId("scenario-comparison");
      await expect(comparison.getByTestId("A-paymentTwd")).toContainText("56,196");
      await expect(comparison.getByTestId("A-purchaseCashTwd")).toContainText("4,350,000");
      await page.getByTestId("scenario-B").getByTestId("input-offerTwd").fill("18000000");
      await expect(comparison.getByTestId("B-askingDelta")).toContainText("500,000");
      await expect(page.getByTestId("scenario-A").getByTestId("input-offerTwd")).toHaveValue("18500000");
      await expect(page.getByTestId("scenario-C").getByTestId("input-offerTwd")).toHaveValue("18500000");
      await page.getByTestId("scenario-A").getByTestId("freeze-baseline").click();
      await page.getByTestId("scenario-A").getByTestId("input-offerTwd").fill("18000000");
      await expect(comparison.getByTestId("A-baselineDelta")).toContainText("500,000");
      await expect(page.getByTestId("scenario-baseline")).toContainText("18,500,000");
      await page.getByTestId("scenario-save").click();
      await expect(page.getByTestId("scenario-status")).not.toBeEmpty();
      expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      await page.screenshot({ path: testInfo.outputPath(`${locale}-${width}.png`), fullPage: true });
      expect(providerCalls).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
}

test("reload restores only separate scenario state; explicit zero and invalid inputs", async ({ page }) => {
  await setup(page);
  await page.getByTestId("locale-switcher").selectOption("en");
  await completeA(page);
  const card = page.getByTestId("scenario-A");
  await card.getByTestId("input-acquisitionTwd").fill("");
  await expect(card.getByTestId("scenario-unknown")).toContainText("Acquisition costs");
  await expect(page.getByTestId("A-purchaseCashTwd")).toContainText("Known subtotal");
  await card.getByTestId("input-acquisitionTwd").fill("0");
  await card.getByTestId("input-ratePercent").fill("0");
  await expect(page.getByTestId("A-paymentTwd")).toContainText("41,111");
  await card.getByTestId("input-downValue").fill("101");
  await expect(card.getByTestId("error-downValue")).toBeVisible();
  await expect(page.getByTestId("A-paymentTwd")).toContainText("Unknown");
  await expect(page.getByTestId("scenario-save")).toBeDisabled();
  await card.getByTestId("input-downValue").fill("20");
  await card.getByTestId("freeze-baseline").click();
  await page.getByTestId("scenario-save").click();
  await page.reload();
  await expect(card.getByTestId("input-ratePercent")).toHaveValue("0");
  await expect(page.getByTestId("A-paymentTwd")).toContainText("41,111");
  await expect(page.getByTestId("scenario-baseline")).toContainText("18,500,000");
});

test("amount/ratio switching preserves down payment and cash purchase needs no rate", async ({ page }) => {
  await setup(page);
  await completeA(page);
  const card = page.getByTestId("scenario-A");
  await card.getByTestId("input-downMode").selectOption("amount");
  await expect(card.getByTestId("input-downValue")).toHaveValue("3700000");
  await expect(page.getByTestId("A-principalTwd")).toContainText("14,800,000");
  await card.getByTestId("input-downMode").selectOption("ratio");
  await expect(card.getByTestId("input-downValue")).toHaveValue("20");
  await card.getByTestId("input-downValue").fill("100");
  await card.getByTestId("input-ratePercent").fill("");
  await card.getByTestId("input-loanYears").fill("");
  await expect(page.getByTestId("A-paymentTwd")).toHaveText("TWD 0");
  await expect(page.getByTestId("A-monthlyOwnershipTwd")).toContainText("4,000");
});

test("blocked scenario storage reports failure while leaving evidence untouched", async ({ page }) => {
  await setup(page);
  await page.getByTestId("locale-switcher").selectOption("en");
  const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) {
      if (key.startsWith("proptech.scenarios.v1")) throw new DOMException("blocked", "QuotaExceededError");
      return original.call(this, key, value);
    };
  });
  await page.getByTestId("scenario-save").click();
  await expect(page.getByTestId("scenario-status")).toContainText("storage unavailable");
  expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
});

test("malformed drafts and revised snapshots never silently restore old assumptions", async ({ page }) => {
  await setup(page);
  await completeA(page);
  await page.getByTestId("scenario-save").click();
  await page.evaluate(() => {
    const saved = JSON.parse(localStorage.getItem("proptech.savedCases.v1")!);
    saved[0].updatedAt = "2026-10-12T09:00:00Z";
    saved[0].data.journeyContext.propertyContext.askingPriceWan = 1900;
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(saved));
  });
  await page.reload();
  await expect(page.getByTestId("scenario-A").getByTestId("input-ratePercent")).toHaveValue("");
  await expect(page.getByTestId("scenario-A").getByTestId("input-offerTwd")).toHaveValue("19000000");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("scenario-status")).toContainText("could not be restored");
  await page.evaluate(() => localStorage.setItem("proptech.scenarios.v1:scenario-case", "{"));
  await page.reload();
  await expect(page.getByTestId("scenario-A").getByTestId("input-downValue")).toHaveValue("");
});

function withCommute(partial = false, wrongOrigin = false) {
  const anchor = {
    version: 1, scope: "journey_browser_anchor", journey_anchor_id: "journey-browser-77777777-2222-4333-8444-555555555555",
    address_input: "臺北市信義區信義路五段7號", normalized_address: "臺北市信義區信義路五段7號", coordinates: { latitude: 25.033, longitude: 121.5654 },
    administrative_location: { city: "臺北市", district: "信義區", village: null, village_code: null }, location_status: "candidate",
    parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
    building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
    confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["accepted_coordinates"], limitations: ["not_legal_identity"] },
    evidence: { sources: [], checked_at: "2026-10-12T08:00:00Z", limitations: [] }, revalidation: { status: "current", conflicts: [] },
  };
  const commuteRoute = {
    status: "resolved", source: "google_routes", mode: "transit", duration_min: 35, duration_seconds: 2100, distance_m: 5000,
    partial, fallback: false, reason_code: null, checked_at: "2026-10-12T08:00:00Z",
    origin: { latitude: wrongOrigin ? 24 : 25.033, longitude: 121.5654 }, destination: { address: "Office" },
  };
  return { ...row, data: { ...row.data, propertyIdentityAnchor: anchor, commuteRoute } };
}

test("accepted saved commute retains provenance; manual changes stay separate", async ({ page }) => {
  const { providerCalls } = await setup(page, withCommute());
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("scenario-lab")).toContainText("Google Routes");
  await expect(page.getByTestId("scenario-lab")).toContainText("Office");
  await expect(page.getByTestId("scenario-comparison")).toContainText("35 minutes one way");
  const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
  await page.getByTestId("scenario-A").getByTestId("input-commuteMinutes").fill("20");
  await expect(page.getByTestId("scenario-comparison")).toContainText("20 minutes one way");
  await expect(page.getByTestId("scenario-comparison")).toContainText("Manual assumption");
  expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
  expect(providerCalls).toEqual([]);
});

for (const [name, partial, wrongOrigin] of [["partial", true, false], ["wrong origin", false, true]] as const) {
  test(`${name} commute evidence is not accepted`, async ({ page }) => {
    await setup(page, withCommute(partial, wrongOrigin));
    await page.getByTestId("locale-switcher").selectOption("en");
    await expect(page.getByTestId("scenario-lab")).toContainText("No accepted commute evidence");
    await expect(page.getByTestId("scenario-comparison")).not.toContainText("35 minutes one way");
  });
}

for (const kind of ["current", "stale", "grace"] as const) {
  test(`${kind} saved finance stays frozen and only compatible assumptions are reused`, async ({ page }) => {
    const seed = withCommute();
    const price = kind === "stale" ? 1800 : 1850;
    const loan = {
      property_price_wan: price, down_payment_ratio: 0.2, down_payment_wan: price * 0.2, loan_amount_wan: price * 0.8,
      annual_interest_rate: 2.2, loan_years: 30, grace_period_years: kind === "grace" ? 2 : 0, monthly_income_wan: null,
      monthly_payment: 56196, grace_period_monthly_payment: kind === "grace" ? 27133 : null, post_grace_monthly_payment: kind === "grace" ? 56196 : null,
      total_payment: 20230560, total_interest: 5430560, income_burden_ratio: null,
      affordability_level: "unknown", affordability_message: "", sensitivity: [], disclaimer: "",
    };
    const { providerCalls } = await setup(page, { ...seed, data: { ...seed.data, loan, financePriceEvidence: { price_twd: price * 10000, source: "ASKING_PRICE", calculated_at: "2026-10-12T08:00:00Z" } } });
    await page.getByTestId("locale-switcher").selectOption("en");
    const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
    const card = page.getByTestId("scenario-A");
    await expect(card.getByTestId("input-downValue")).toHaveValue(kind === "current" ? "20" : "");
    await expect(card.getByTestId("input-ratePercent")).toHaveValue(kind === "current" ? "2.2" : "");
    await expect(card.getByTestId("input-loanYears")).toHaveValue(kind === "current" ? "30" : "");
    if (kind !== "current") await expect(page.getByTestId("scenario-lab")).toContainText("stale or unsupported");
    await card.getByTestId("input-offerTwd").fill(String(price * 10000));
    await expect(page.getByTestId("A-savedDelta")).toContainText("TWD 0");
    await card.getByTestId("freeze-baseline").click();
    await page.getByTestId("scenario-save").click();
    expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
    expect(providerCalls).toEqual([]);
  });
}
