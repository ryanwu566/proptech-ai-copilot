import { expect, test, type Page } from "@playwright/test";

const NOW = "2026-10-07T03:00:00.000Z";
const ADDRESS = "臺中市西屯區臺灣大道三段100號";

function identityAnchor(address = ADDRESS, id = "journey-browser-11111111-2222-4333-8444-555555555555") {
  return {
    version: 1,
    scope: "journey_browser_anchor",
    journey_anchor_id: id,
    address_input: address,
    normalized_address: address,
    coordinates: { latitude: 24.16525, longitude: 120.64555 },
    administrative_location: { city: "臺中市", district: "西屯區", village: "潮洋里", village_code: "66000060-020" },
    location_status: "candidate",
    parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
    building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_building_identity_evidence"], confirmation: null },
    confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["normalized_address", "trusted_geocoding_coordinates"], limitations: ["not_parcel_building_ownership_or_legal_boundary_confirmation"] },
    evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: NOW }], checked_at: NOW, limitations: ["journey_browser_correlation_only"] },
    revalidation: { status: "current", conflicts: [] },
  };
}

function representativeCase() {
  return {
    id: "overview-case",
    title: "臺灣大道案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "report",
    progress: 70,
    inputSummary: { city: "臺中市", district: "西屯區", road: "臺灣大道三段100號", propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺中市", district: "西屯區", road: "臺灣大道三段100號", building_type: "住宅大樓", area_ping: 30, building_age_years: 8, floor: 12 },
      propertyIdentityAnchor: identityAnchor(),
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺中市", district: "西屯區", road: "臺灣大道三段", addressSummary: ADDRESS, sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 },
        priceBasis: "asking",
        activePriceWan: 2480,
        valuationStatus: "unavailable",
      },
      marketInsight: {
        city: "臺中市", county: "臺中市", district: "西屯區", period: "2025-01–2026-07",
        average_unit_price: 53.1, avg_price_per_ping: 53.1, transaction_count: 18, transaction_volume: 18, record_count: 18,
        summary: "近期成交摘要。", source_name: "內政部不動產實價登錄", source_updated_at: "2026-08-31",
        coverage_status: "covered", data_status: "available", caveat: "樣本僅供初步比較。", disclaimer: "成交資料不等同正式估價。",
        history: [], sample_status: "sufficient", freshness_status: "fresh", period_min: "2025-01", period_max: "2026-07", newest_effective_period: "2026-07",
        median_unit_price_per_ping: 52.4, p25_unit_price_per_ping: 49.8, p75_unit_price_per_ping: 55.6, median_total_price: 1850,
        effective_scope_label: "臺中市西屯區", effective_analysis_level: "DISTRICT", effective_sample_count: 18, fallback_applied: false,
      },
      commuteRoute: {
        source: "google_routes", origin: { latitude: 24.16525, longitude: 120.64555 }, destination: { address: "臺中車站" },
        mode: "driving", distance_m: 9800, duration_seconds: 1440, duration_min: 24, checked_at: NOW,
        reason_code: "route_found", status: "resolved", partial: false, fallback: false,
      },
      commuteTransit: { status: "unavailable", source: "tdx", station_name: null, line_ids: [], distance_meters: null, source_updated_at: null, snapshot_generated_at: NOW, message: "unavailable" },
      terrainReference: {
        schema_version: 1, kind: "terrain_reference", status: "partial", summary: "部分風險來源已保存。", notice: "未知仍為未知。",
        layers: [
          { layer_id: "flood", display_name: "淹水潛勢", state: "no_match", source_name: "經濟部水利署", coverage_status: "covered", caveat: "未命中不代表安全。" },
          { layer_id: "geological_sensitivity", display_name: "地質敏感區", state: "unavailable", source_name: "地質調查及礦業管理中心", coverage_status: "unknown", caveat: "來源目前無法取得。" },
        ],
      },
      riskEvidenceCheckedAt: NOW,
      financeEvidence: {
        version: 1, case_id: "overview-case", revision: 1,
        input_fingerprint: "finance-v1|overview-case|1|journey-browser-11111111-2222-4333-8444-555555555555|asking|2480|30",
        assumptions: { price_basis: "asking", active_price_wan: 2480, area_ping: 30 },
        calculation: { query: "succeeded", usability: "usable", completeness: "partial" },
        loan: { property_price_wan: 2480, down_payment_ratio: 0.2, down_payment_wan: 496, principal_wan: 1984, annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null, monthly_payment_twd: 75312, grace_period_monthly_payment_twd: null, post_grace_monthly_payment_twd: null, total_interest_twd: 7272320 },
        holding: { known_monthly_subtotal_twd: 75312, known_annual_subtotal_twd: 903744, total_kind: "known_subtotal", assumptions: { loan_monthly_payment_twd: 75312, monthly_income_wan: null, area_ping: 30, management_fee_per_ping_twd: null, repair_reserve_per_ping_twd: null, annual_home_tax_rate_percent: null, annual_land_tax_rate_percent: null, annual_insurance_twd: null }, breakdown: [] },
        affordability: { status: "unassessed", ratio: null, reason: "未提供月收入", basis: null },
        tax: { query: "not_started", summary: null },
        missing_costs: ["管理費（尚未提供）", "交易成本（未納入）"],
        unresolved_actions: ["提供月收入以評估負擔"],
        calculated_at: NOW,
      },
    },
  };
}

async function installCase(page: Page, row = representativeCase()) {
  await installCases(page, [row]);
}

async function installCases(page: Page, rows: unknown[]) {
  await page.addInitScript(({ saved }) => {
    window.localStorage.setItem("proptech.savedCases.v1", JSON.stringify(saved));
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  }, { saved: rows });
}

function partialCase() {
  const saved = representativeCase();
  saved.id = "partial-case";
  saved.title = "部分證據案件";
  saved.data.financeEvidence.case_id = saved.id;
  const data = saved.data as unknown as Record<string, unknown>;
  delete data.marketInsight;
  delete data.commuteRoute;
  delete data.commuteTransit;
  delete data.terrainReference;
  delete data.riskEvidenceCheckedAt;
  delete data.financeEvidence;
  return saved;
}

function staleCase() {
  const saved = representativeCase();
  saved.id = "stale-case";
  saved.data.financeEvidence.case_id = saved.id;
  saved.title = "需重新確認案件";
  saved.data.propertyIdentityAnchor.location_status = "stale";
  saved.data.propertyIdentityAnchor.revalidation = { status: "needs_revalidation", conflicts: ["normalized_address" as never] };
  return saved;
}

function unconfirmedCase() {
  const saved = representativeCase();
  saved.id = "unconfirmed-case";
  saved.data.financeEvidence.case_id = saved.id;
  saved.title = "身分尚未確認案件";
  saved.data.propertyIdentityAnchor.confidence.level = "unknown";
  return saved;
}

function addressConflictCase() {
  const saved = representativeCase();
  saved.id = "address-conflict-case";
  saved.data.financeEvidence.case_id = saved.id;
  saved.title = "地址衝突案件";
  saved.data.journeyContext.propertyContext.addressSummary = "臺北市信義區松仁路88號";
  return saved;
}

const ANALYSIS_ENDPOINT = /\/(?:market-insights|valuation|commute|location\/insight|terrain(?:-risk)?|taxoracle|loan|holding-cost)(?:\/|\?|$)/i;

function observeAnalysisRequests(page: Page) {
  const requested: string[] = [];
  page.on("request", (request) => {
    if (!["fetch", "xhr"].includes(request.resourceType())) return;
    const url = new URL(request.url());
    if (ANALYSIS_ENDPOINT.test(url.pathname)) requested.push(`${request.method()} ${url.pathname}`);
  });
  return requested;
}

test("Overview renders bounded decision groups, domain links, and accessible save state", async ({ page }) => {
  await installCase(page);
  await page.goto("/cases/overview-case/overview");

  await expect(page.getByRole("heading", { level: 1, name: "物件總覽" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "已掌握" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "尚未確認" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "需要特別留意" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "下一步" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "價格與市場" })).toBeVisible();
  const market = page.getByTestId("overview-market-summary");
  await expect(market.getByText("開價", { exact: true })).toBeVisible();
  await expect(market.getByText("目前無法取得價格推估", { exact: true })).toBeVisible();
  const location = page.getByTestId("overview-location-summary");
  await expect(location.getByText(/已保存前往臺中車站的路線/)).toBeVisible();
  await expect(location.getByText(/次要大眾運輸證據目前無法取得/)).toBeVisible();
  await expect(location).toContainText("開車");
  await expect(location).not.toContainText("driving");

  const risk = page.getByTestId("overview-risk-summary");
  await expect(risk.getByText(/未命中.*不代表安全/)).toBeVisible();

  const finance = page.getByTestId("overview-finance-summary");
  await expect(finance.getByText(/試算完成.*負擔能力.*不同狀態/)).toBeVisible();
  await expect(page.getByText(/已儲存的案件快照.*不是即時重新查詢/)).toBeVisible();
  await expect(page.locator("body")).not.toContainText("JourneyPropertyIdentityAnchorV1");

  for (const [name, path] of [["查看價格與市場", "/market"], ["查看區位與通勤", "/location"], ["查看風險與環境", "/risk"], ["查看資金與持有成本", "/finance"]] as const) {
    await expect(page.getByRole("link", { name })).toHaveAttribute("href", `/cases/overview-case${path}`);
  }

  const saveStatus = page.getByTestId("overview-save-status");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await expect(saveStatus).toContainText("已保存目前已知狀態");
  await expect(saveStatus).toHaveAttribute("aria-live", "polite");
});

test("saved cases stays compact while disclosing snapshot freshness and unresolved work", async ({ page }) => {
  await installCase(page);
  await page.goto("/cases");

  const row = page.getByRole("article", { name: "臺灣大道案件" });
  await expect(row).toContainText(ADDRESS);
  await expect(row).toContainText("已儲存快照");
  await expect(row).toContainText(/待確認/);
  await expect(row.getByRole("link", { name: "開啟臺灣大道案件" })).toHaveAttribute("href", "/cases/overview-case/overview");
  await expect(row).not.toContainText("NT$75,312");
});

test("opening and reopening Overview makes zero external analysis requests", async ({ page }) => {
  await installCase(page);
  const analysisRequests = observeAnalysisRequests(page);

  await page.goto("/cases/overview-case/overview");
  await expect(page.getByRole("heading", { level: 1, name: "物件總覽" })).toBeVisible();
  expect(analysisRequests).toEqual([]);

  await page.goto("/cases");
  await page.getByRole("link", { name: "開啟臺灣大道案件" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "物件總覽" })).toBeVisible();
  expect(analysisRequests).toEqual([]);
});

test("an identity-valid partial case saves its known state without claiming completion", async ({ page }) => {
  await installCase(page, partialCase());
  await page.goto("/cases/partial-case/overview");

  await expect(page.getByTestId("overview-market-summary")).toContainText("尚未取得");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await expect(page.getByTestId("overview-save-status")).toContainText("已保存目前已知狀態");
  await expect(page.getByTestId("overview-save-status")).toContainText("尚未完成的項目仍保持原狀");

  const stored = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0]);
  expect(stored.id).toBe("partial-case");
  expect(stored.updatedAt).not.toBe(NOW);
  expect(stored.data.marketInsight).toBeUndefined();
  expect(stored.data.financeEvidence).toBeUndefined();
});

test("unavailable valuation and independent route evidence survive save and reopen", async ({ page }) => {
  await installCase(page);
  await page.goto("/cases/overview-case/overview");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();

  const savedState = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0]);
  expect(savedState.data.journeyContext.valuationStatus).toBe("unavailable");
  expect(savedState.data.commuteRoute.source).toBe("google_routes");
  expect(savedState.data.commuteTransit.status).toBe("unavailable");

  await page.reload();
  const market = page.getByTestId("overview-market-summary");
  await expect(market.getByText("目前無法取得價格推估", { exact: true })).toBeVisible();
  const location = page.getByTestId("overview-location-summary");
  await expect(location).toContainText("已保存前往臺中車站的路線");
  await expect(location).toContainText("次要大眾運輸證據目前無法取得");
});

test("save preserves revalidation-required identity as a distinct blocked state", async ({ page }) => {
  await installCase(page, staleCase());
  await page.goto("/cases/stale-case/overview");
  const finance = page.getByTestId("overview-finance-summary");
  await expect(finance).toContainText("先前快照已過期");
  await expect(finance).not.toContainText("NT$75,312");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await expect(page.getByTestId("overview-save-status")).toContainText("物件資料已變更");
  await expect(page.getByTestId("overview-save-status")).toContainText("重新確認地址與定位");
});

test("save rejects a low-confidence unconfirmed browser identity", async ({ page }) => {
  await installCase(page, unconfirmedCase());
  await page.goto("/cases/unconfirmed-case/overview");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await expect(page.getByTestId("overview-save-status")).toContainText("需要先完成地址定位並確認目前物件");
});

test("save rejects a display-address conflict even when the stored anchor flags are current", async ({ page }) => {
  await installCase(page, addressConflictCase());
  await page.goto("/cases/address-conflict-case/overview");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await expect(page.getByTestId("overview-save-status")).toContainText("物件資料已變更");
});

test("save blocks when the stored snapshot changed after Overview opened", async ({ page }) => {
  await installCase(page);
  await page.goto("/cases/overview-case/overview");
  const saveButton = page.getByRole("button", { name: "保存目前案件快照" });
  await expect(saveButton).toBeVisible();
  await page.evaluate(() => {
    const rows = JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]");
    rows[0].updatedAt = "2026-10-07T04:00:00.000Z";
    rows[0].title = "另一個畫面更新後的案件";
    window.localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
  });

  await saveButton.click();
  await expect(page.getByTestId("overview-save-status")).toContainText("案件已在另一個畫面更新");
  const stored = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0]);
  expect(stored.updatedAt).toBe("2026-10-07T04:00:00.000Z");
  expect(stored.title).toBe("另一個畫面更新後的案件");
});

test("switching from property A to property B does not leak A evidence", async ({ page }) => {
  const propertyA = representativeCase();
  const propertyB = representativeCase();
  propertyB.id = "property-b";
  propertyB.title = "第二物件";
  propertyB.inputSummary = { city: "臺北市", district: "信義區", road: "松仁路88號", propertyPrice: 3200, areaPing: 28 };
  propertyB.data.inputs = { city: "臺北市", district: "信義區", road: "松仁路88號", building_type: "住宅大樓", area_ping: 28, building_age_years: 5, floor: 8 };
  propertyB.data.propertyIdentityAnchor = identityAnchor("臺北市信義區松仁路88號", "journey-browser-bbbbbbbb-2222-4333-8444-555555555555");
  propertyB.data.journeyContext = {
    version: 1,
    propertyContext: { city: "臺北市", district: "信義區", road: "松仁路88號", addressSummary: "臺北市信義區松仁路88號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 3200 },
    priceBasis: "asking",
    activePriceWan: 3200,
    valuationStatus: "not_started",
  };
  const propertyBData = propertyB.data as unknown as Record<string, unknown>;
  for (const key of ["marketInsight", "commuteRoute", "commuteTransit", "terrainReference", "riskEvidenceCheckedAt", "financeEvidence"]) delete propertyBData[key];
  await installCases(page, [propertyA, propertyB]);

  await page.goto("/cases/overview-case/overview");
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("臺中市西屯區臺灣大道三段100號");
  await expect(page.getByTestId("overview-location-summary")).toContainText("臺中車站");

  await page.goto("/cases/property-b/overview");
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("臺北市信義區松仁路88號");
  await expect(page.locator("body")).not.toContainText("臺中車站");
  await expect(page.locator("body")).not.toContainText("53.1");
  await expect(page.locator("body")).not.toContainText("NT$75,312");
  await expect(page.getByTestId("overview-location-summary")).toContainText("尚未保存可用的目的地路線");
});

test("all four Overview module links open their existing detailed workspaces", async ({ page }) => {
  await installCase(page);
  const destinations = [
    ["查看價格與市場", "價格與市場"],
    ["查看區位與通勤", "區位與通勤"],
    ["查看風險與環境", "風險與環境"],
    ["查看資金與持有成本", "資金與持有成本"],
  ] as const;

  for (const [linkName, heading] of destinations) {
    await page.goto("/cases/overview-case/overview");
    await page.getByRole("link", { name: linkName }).click();
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  }
});

test("Overview remains operable and readable at 390px with keyboard disclosure", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installCase(page);
  await page.goto("/cases/overview-case/overview");

  await expect(page.getByRole("heading", { level: 1, name: "物件總覽" })).toBeVisible();
  await expect(page.getByRole("button", { name: "保存目前案件快照" })).toBeVisible();
  await expect(page.getByRole("link", { name: "查看資金與持有成本" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  const disclosure = page.getByText("查看快照與證據鮮度", { exact: true });
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("details", { has: disclosure })).toHaveAttribute("open", "");
  await expect(page.getByText("瀏覽器案件關聯錨點只用於連結這次案件", { exact: false })).toBeVisible();
  await expect(page.getByTestId("overview-save-status")).toHaveAttribute("aria-live", "polite");
});

test("Risk pre-query summary stays unknown instead of displaying zero findings", async ({ page }) => {
  await installCases(page, [partialCase()]);
  await page.goto("/cases/partial-case/risk");
  const summary = page.getByLabel("風險證據摘要");
  await expect(summary).toContainText("符合來源定義");
  await expect(summary).toContainText("未知／無法取得");
  await expect(summary).toContainText("尚未查詢");
  await expect(summary).not.toContainText("0 項");
  await expect(page.locator("body")).not.toContainText(/\b(?:not_started|partial|available|unavailable|no_match|POINT_REFERENCE)\b/);
});
