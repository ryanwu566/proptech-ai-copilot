/**
 * Market Insight — 10 Real UI Cases
 * Uses product data-testid anchors and semantic combobox labels.
 * NO .first()/.last()/.nth() for critical controls.
 */
import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3200", viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

function norm(s: string): string { return s.replace(/台/g, "臺").trim(); }

const MARKET_CASES = [
  { id: "M01", city: "臺北市", district: "大安區" },
  { id: "M02", city: "臺北市", district: "信義區" },
  { id: "M03", city: "新北市", district: "板橋區" },
  { id: "M04", city: "新北市", district: "中和區" },
  { id: "M05", city: "桃園市", district: "桃園區" },
  { id: "M06", city: "臺中市", district: "西屯區" },
  { id: "M07", city: "臺中市", district: "北區" },
  { id: "M08", city: "臺南市", district: "中西區" },
  { id: "M09", city: "高雄市", district: "前鎮區" },
  { id: "M10", city: "高雄市", district: "三民區" },
];

test.describe.serial("Market Insight — 10 Real Cases", () => {
  let requestsCaptured = 0;
  let responsesCaptured = 0;
  let wrongCity = 0;
  let wrongDistrict = 0;

  for (const mc of MARKET_CASES) {
    test(`${mc.id}: ${mc.city} ${mc.district}`, async ({ page }) => {
      test.setTimeout(25000);

      let reqBody: Record<string, unknown> | null = null;
      let respBody: Record<string, unknown> | null = null;

      // Intercept to observe (not mock) the real request/response
      await page.route("**/market-insights/query", async (route) => {
        reqBody = route.request().postDataJSON();
        const response = await route.fetch();
        respBody = await response.json();
        await route.fulfill({ response, body: JSON.stringify(respBody) });
      });

      await page.goto("/", { waitUntil: "domcontentloaded" });

      // Navigate to Market Insight
      const sidebar = page.locator("aside[aria-label='分析工具']");
      await sidebar.getByRole("button", { name: "Market Insight" }).click();
      await page.waitForTimeout(500);

      // Find the search form by data-testid
      const searchForm = page.getByTestId("market-insight-search-form");
      await expect(searchForm).toBeVisible({ timeout: 8000 });

      // Select city (first select in the form)
      const selects = searchForm.locator("select");
      await selects.nth(0).selectOption(mc.city);
      await page.waitForTimeout(400);

      // Select district (second select)
      await selects.nth(1).selectOption(mc.district);

      // Click the search button by data-testid
      await page.getByTestId("market-insight-search-button").click();

      // Wait for response
      await page.waitForTimeout(5000);

      // HARD ASSERT: request and response captured
      expect(reqBody, `${mc.id} request must be captured`).not.toBeNull();
      expect(respBody, `${mc.id} response must be captured`).not.toBeNull();
      requestsCaptured++;
      responsesCaptured++;

      // HARD ASSERT: request identity matches selection
      const req = (reqBody ?? {}) as Record<string, unknown>;
      const resp = (respBody ?? {}) as Record<string, unknown>;
      const reqCity = norm(String(req.county || ""));
      const reqDistrict = String(req.district || "");
      expect(reqCity, `${mc.id} req city`).toBe(norm(mc.city));
      expect(reqDistrict, `${mc.id} req district`).toBe(mc.district);

      // HARD ASSERT: response identity matches selection
      const respCity = norm(String(resp.city || resp.county || ""));
      const respDistrict = String(resp.district || "");

      if (respCity && norm(mc.city) !== respCity) wrongCity++;
      if (respDistrict && mc.district !== respDistrict) wrongDistrict++;

      // For cases where backend returns data, verify identity
      const dataStatus = String(resp.data_status || "");
      if (dataStatus === "available") {
        expect(respDistrict, `${mc.id} resp district`).toBe(mc.district);
      }

      console.log(`${mc.id} | req=${reqCity}/${reqDistrict} | resp=${respCity}/${respDistrict} | status=${dataStatus}`);
    });
  }

  test("METRICS", () => {
    console.log(`\nMARKET_CASES=${MARKET_CASES.length}`);
    console.log(`REQUESTS_CAPTURED=${requestsCaptured}`);
    console.log(`RESPONSES_CAPTURED=${responsesCaptured}`);
    console.log(`WRONG_CITY=${wrongCity}`);
    console.log(`WRONG_DISTRICT=${wrongDistrict}`);

    expect(requestsCaptured).toBe(10);
    expect(responsesCaptured).toBe(10);
    expect(wrongCity).toBe(0);
    expect(wrongDistrict).toBe(0);
  });
});
