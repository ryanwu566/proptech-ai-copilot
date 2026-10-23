import { expect, test } from "./fixtures";
import type { Locator, Page, TestInfo } from "@playwright/test";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { translateRuntimeCopy } from "../lib/runtime-copy";
import { translateExperience, type ExperienceLocale } from "../lib/experience-i18n";
import { compactCaseData, type SavedCase } from "../lib/case-storage";
import { parseSavedCasesDiagnostic } from "../lib/workspace/saved-case-diagnostics";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { getSurfaceCopy } from "../lib/surface-copy";
import { join } from "node:path";
import { comparableCopy } from "../lib/comparable-explanation-copy";
import { navigationCopy } from "../lib/navigation/copy";

// These are synthetic UI contract responses, not proof of official production coverage.
// The supported real-data acquisition gate is exercised separately against the backend.
const KEY = "proptech.savedCases.v1";
const NOW = "2026-10-11T02:00:00.000Z";
const comparableFixture = JSON.parse(readFileSync("../tests/fixtures/comparable-explanation-result.json", "utf8"));
Object.assign(comparableFixture.data_status, { is_demo_data: false, is_full_taiwan: false, data_composition: "official", official_records_count: 13, sample_records_count: 0, coverage: { cities: ["臺北市"], districts: ["大安區"], roads_count: 1, records_count: 13 }, last_updated: "2026-10-01", update_frequency_note: "Synthetic frozen contract", source_note: "Synthetic fixture, not live production evidence", user_message: "Synthetic contract fixture", freshness_status: "fresh", freshness_reason_code: "SYNTHETIC_CONTRACT", operator_attention_required: false });
// The public API supplies data_status even when there are no comparable rows.
const unsupportedDataStatus = { ...comparableFixture.data_status, active_source: "postgres", official_records_count: 0, sample_records_count: 0, coverage: { cities: [], districts: [], roads_count: 0, records_count: 0 }, freshness_status: "unavailable", freshness_reason_code: "SYNTHETIC_NO_DATA", source_note: "Synthetic unsupported coverage contract", user_message: "Synthetic unsupported coverage contract" };
const scenarios = [
  { name: "A", address: "台北市大安區敦化南路二段100號", displayAddress: "106台灣臺北市大安區群賢里敦化南路二段100號", district: "大安區", price: 2480, area: 30, age: 15, floor: 8, rate: 2.2, years: 30, down: 0.2, payment: 75412, review: "reviewed", supported: true },
  { name: "B", address: "臺北市信義區市府路200號", displayAddress: "臺北市信義區市府路200號", district: "信義區", price: 3650, area: 42, age: 9, floor: 12, rate: 2.6, years: 25, down: 0.35, payment: 107624, review: "pending", supported: false },
] as const;
type Scenario = typeof scenarios[number];
type RecordedRequests = string[] & { zeroWindows: { phase: string; requests: string[] }[] };
const copy = (locale: ExperienceLocale, key: Parameters<typeof translateRuntimeCopy>[1]) => translateRuntimeCopy(locale, key);
const t = (locale: ExperienceLocale, key: Parameters<typeof translateExperience>[1]) => translateExperience(locale, key);

function location(s: Scenario) {
  const latitude = s.name === "A" ? 25.0279284 : 25.0375;
  const longitude = s.name === "A" ? 121.5483265 : 121.5637;
  return {
    input: { address: s.address }, resolved_location: { address_label: s.displayAddress, latitude, longitude, geocoding_confidence: "high" },
    geocoding_acceptance: { original_query: s.address, normalized_address: s.displayAddress, resolved_lat: latitude, resolved_lng: longitude, geocoding_source: "google_geocoding", match_quality: "EXACT_OR_ACCEPTABLE", accepted_for_analysis: true, requires_confirmation: false, mismatch_reasons: [], message: "Synthetic accepted contract location" },
    village_resolution: { status: "resolved", county: "臺北市", town: s.district, village: s.name === "A" ? "群賢里" : "西村里", village_code: s.name === "A" ? "63000030-020" : "63000020-014", source: "nlsc_village_boundary", candidate_count: 1 },
    demographics: { status: "no_data", reason: "not_requested" }, radius_m: 800, location_score: null,
    poi_summary: { transit_count: 3, convenience_count: 4, school_count: 2, park_count: 1, medical_count: 3, risk_facility_count: s.name === "A" ? null : 0 },
    risk_facility_evidence: s.name === "A"
      ? { status: "unavailable", count: null, source: null, checked_at: null, reason: "risk_facilities_source_unavailable", limitation: "Synthetic unknown evidence must stay unknown" }
      : { status: "no_match", count: 0, source: "Synthetic bounded risk register", checked_at: NOW, reason: "successful_query", limitation: "Synthetic radius only; no safety conclusion" },
    category_scores: { transit_score: 50, convenience_score: 80, education_score: 50, green_space_score: 25, medical_score: 60, risk_score: null }, nearest_pois: [], strengths: [], weaknesses: [],
    buyer_fit: { self_use_family: "Review", commuter: "Review", investor: "Review", elderly: "Review" }, valuation_context: { supports_price_reasonableness: "unknown", explanation: "Synthetic location contract" },
    data_quality: { status: "good", missing_sources: s.name === "A" ? ["risk_facilities"] : [], warnings: [], source: "synthetic_contract", checked_at: NOW }, scoring_method: { weights: {}, explanation: "Synthetic reference only" }, disclaimer: "Synthetic contract fixture, not official acquisition evidence",
  };
}

async function installContracts(page: Page) {
  const acquisitions = [] as unknown as RecordedRequests;
  acquisitions.zeroWindows = [];
  page.on("request", request => {
    const url = new URL(request.url());
    // Count GET metadata/health/directory requests as well as analysis POSTs.
    if (url.hostname === "e2e.test"
      || /^\/(?:api\/)?(?:loan|holding-cost|valuation|location|market-insights|terrain|terrain-risk|roads|map|mortgage-rates|bank-rates|commute)(?:\/|$)/.test(url.pathname)
      || /googleapis|maps\.google|openstreetmap|mapbox|cartocdn|arcgisonline|tdx\.transportdata|nlsc|tgos/.test(url.hostname)) acquisitions.push(`${request.method()} ${url.pathname}`);
  });
  await page.route("**/location/insight", route => {
    const s = scenarios.find(item => item.address === route.request().postDataJSON().address)!;
    expect(s).toBeDefined(); return route.fulfill({ json: location(s) });
  });
  await page.route("**/valuation/estimate", route => {
    const payload = route.request().postDataJSON();
    const s = scenarios.find(item => item.district === payload.district)!;
    expect(s).toBeDefined();
    expect(payload.area_ping).toBe(s.area); expect(payload.building_age_years).toBe(s.age); expect(payload.floor).toBe(s.floor);
    expect(payload.building_type).toBe("住宅大樓");
    return route.fulfill({ json: s.supported ? comparableFixture : { valuation_status: "no_data", valuation_reason_code: "insufficient_official_sample", result_origin: "none", is_actionable: false, source: "postgres", data_status: unsupportedDataStatus, comparables: [], estimate_total_price: null, estimate_unit_price_per_ping: null, price_range: { low: null, mid: null, high: null }, confidence_score: null, confidence: "insufficient", methodology: [], disclaimer: "Synthetic unsupported coverage contract" } });
  });
  await page.route("**/valuation/trend", route => route.fulfill({ json: { trend_status: "unavailable", is_actionable: false, monthly_series: [], yearly_series: [], methodology: [], disclaimer: "Synthetic trend unavailable" } }));
  await page.route("**/market-insights/query", route => {
    const s = scenarios.find(item => item.district === route.request().postDataJSON().district)!;
    expect(s).toBeDefined();
    return route.fulfill({ json: { city: "臺北市", district: s.district, period: "2026-10", average_unit_price: s.supported ? 72 : null, avg_price_per_ping: s.supported ? 72 : null, transaction_count: s.supported ? 18 : 0, transaction_volume: s.supported ? 18 : 0, record_count: s.supported ? 18 : 0, summary: "Synthetic market persistence contract", source_name: "Synthetic contract fixture", source_updated_at: NOW, coverage_status: s.supported ? "covered" : "unknown", data_status: s.supported ? "available" : "no_data", sample_status: s.supported ? "sufficient" : "no_data", caveat: "Not official acquisition evidence", disclaimer: "Synthetic browser contract only", history: [], median_total_price: s.supported ? 2160 : null, median_unit_price_per_ping: s.supported ? 72 : null, effective_sample_count: s.supported ? 18 : 0, effective_scope_label: `臺北市${s.district}`, effective_analysis_level: "DISTRICT" } });
  });
  await page.route("**/loan/calculate", route => {
    const payload = route.request().postDataJSON(); const s = scenarios.find(item => item.price === payload.property_price)!;
    expect(s).toBeDefined(); expect(payload.annual_interest_rate).toBe(s.rate); expect(payload.loan_years).toBe(s.years); expect(payload.down_payment_ratio).toBe(s.down);
    return route.fulfill({ json: { property_price_wan: s.price, down_payment_ratio: s.down, down_payment_wan: s.price * s.down, loan_amount_wan: s.price * (1 - s.down), annual_interest_rate: s.rate, loan_years: s.years, grace_period_years: 0, monthly_income_wan: null, monthly_payment: s.payment, total_payment: s.payment * s.years * 12, total_interest: s.payment * s.years * 12 - s.price * (1 - s.down) * 10000, sensitivity: [], income_burden_ratio: null, affordability_level: "unknown", disclaimer: "Synthetic finance contract" } });
  });
  return acquisitions;
}

async function rows(page: Page): Promise<SavedCase[]> { return page.evaluate(key => JSON.parse(localStorage.getItem(key) ?? "[]"), KEY); }
function assertZeroRequests(calls: RecordedRequests, before: string[], phase: string) {
  const observed = calls.slice(before.length);
  calls.zeroWindows.push({ phase, requests: observed });
  expect(observed, `Automatic provider requests during ${phase}`).toEqual([]);
}
async function noOverflow(page: Page) { expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); }
async function stage(page: Page, locale: ExperienceLocale, name: "location" | "price" | "affordability" | "decision") {
  const nav = page.locator("#guided-property-journey aside nav");
  const disclosure = nav.locator("details");
  if (await disclosure.isVisible() && !await disclosure.evaluate(el => (el as HTMLDetailsElement).open)) await disclosure.locator("summary").click();
  const key = name === "decision" ? "journey.decision.title" : name === "price" ? "journey.price.title" : name === "location" ? "journey.location.title" : "journey.affordability.title";
  await nav.getByRole("button", { name: new RegExp(t(locale, key)) }).filter({ visible: true }).click();
  await expect(page.locator(`#journey-stage-${name}`)).toBeVisible();
}

async function createThroughUI(page: Page, locale: ExperienceLocale, s: Scenario, calls: RecordedRequests, info: TestInfo, capturedUnavailable = false, afterLocation?: () => Promise<void>, onBoundary?: (phase: string) => Promise<void>, valuationOverride?: { applyScenarioInputs?: boolean; skipEstimate?: boolean; prepare?: (form: Locator) => Promise<void> }, beforeLocation?: () => Promise<void>) {
  // Home Start now creates a local case; this legacy journey closure enters through its explicit deep link.
  await page.goto("/?workflow=property"); await page.getByTestId("locale-switcher").selectOption(locale);
  await stage(page, locale, "location");
  const locationForm = page.locator("#location-insight-calculator");
  await locationForm.getByRole("textbox").first().fill(s.address);
  await beforeLocation?.();
  await locationForm.getByLabel(copy(locale, "location.area")).fill(String(s.area));
  await locationForm.getByRole("button", { name: copy(locale, "location.start"), exact: true }).click();
  await expect(page.getByTestId("journey-property-identity-card")).toContainText(s.displayAddress);
  await afterLocation?.();
  await stage(page, locale, "price");
  const valuation = page.locator("#valuation-calculator");
  if (valuationOverride?.applyScenarioInputs !== false) {
    const buildingType = valuation.getByRole("combobox", { name: copy(locale, "finder.buildingType"), exact: true });
    await expect(buildingType).toBeVisible();
    await buildingType.selectOption("住宅大樓");
    await valuation.getByRole("spinbutton", { name: "屋齡", exact: true }).fill(String(s.age));
    await valuation.getByRole("spinbutton", { name: "樓層", exact: true }).fill(String(s.floor));
  }
  await valuationOverride?.prepare?.(valuation);
  await info.attach(`case-${s.name}-valuation-input-state`, { body: JSON.stringify(await valuation.evaluate((element, address) => ({ fields: Array.from(element.querySelectorAll<HTMLInputElement | HTMLSelectElement>("input,select")).map(node => ({ kind: node.tagName, type: node.type, label: node.getAttribute("aria-label"), valuePresent: Boolean(node.value), numericValue: node.type === "number" && node.value ? Number(node.value) : undefined, selectedIndex: node instanceof HTMLSelectElement ? node.selectedIndex : undefined, disabled: node.disabled })), normalizedIdentityMatches: document.querySelector('[data-testid="journey-property-identity-card"]')?.textContent?.includes(address) === true }), s.displayAddress), null, 2), contentType: "application/json" });
  const estimate = valuation.getByRole("button", { name: copy(locale, "valuation.estimate"), exact: true });
  if (!valuationOverride?.skipEstimate) {
    await expect(estimate).toBeEnabled();
    await estimate.click();
    if (s.supported && !capturedUnavailable) await expect(page.getByTestId("valuation-result").first()).toBeVisible();
    else await expect(page.locator("#journey-stage-price").getByRole("status").filter({ hasText: /估價資料目前無法取得|官方成交證據不足|目前只有部分成交證據/ }).first()).toBeVisible();
  }
  await onBoundary?.("after-valuation");
  await page.getByTestId("journey-manual-price").fill(String(s.price));
  const manualApply = { "zh-TW": "使用手動價格", en: "Use manual price", ja: "手動価格を使用", ko: "수동 가격 사용" }[locale];
  await page.getByRole("button", { name: manualApply, exact: true }).click();
  await onBoundary?.("after-manual-price");
  await stage(page, locale, "affordability");
  const loan = page.locator("#loan-calculator");
  await loan.getByLabel(copy(locale, "loan.downPayment"), { exact: true }).fill(String(s.down));
  await loan.getByLabel(copy(locale, "loan.rate"), { exact: true }).fill(String(s.rate));
  await loan.getByLabel(copy(locale, "loan.years"), { exact: true }).fill(String(s.years));
  await loan.getByRole("button", { name: copy(locale, "loan.calculate"), exact: true }).click();
  await expect(page.getByTestId("loan-result")).toContainText(s.payment.toLocaleString("en"));
  await onBoundary?.("after-synthetic-finance");
  await stage(page, locale, "decision");
  await page.getByRole("button", { name: new RegExp(`^${copy(locale, "journey.caseActionNew")}`) }).filter({ visible: true }).click();
  const before = calls.slice();
  await page.getByRole("button", { name: copy(locale, "case.save"), exact: true }).click();
  await expect.poll(async () => (await rows(page)).some(item => item.title === s.displayAddress)).toBe(true);
  assertZeroRequests(calls, before, `Save ${s.name}`);
  const saved = (await rows(page)).find(item => item.title === s.displayAddress)!;
  expect(saved).toBeDefined();
  return saved;
}

async function reopen(page: Page, s: Scenario, id: string, locale: ExperienceLocale) {
  await page.goto("/cases"); await page.reload();
  await page.getByTestId("locale-switcher").selectOption(locale);
  const savedCase = page.getByRole("link", { name: `${navigationCopy[locale].open}${s.displayAddress}`, exact: true });
  await expect(savedCase).toHaveAttribute("href", `/cases/${encodeURIComponent(id)}/overview`);
  await savedCase.click();
  await expect(page).toHaveURL(new RegExp(`/cases/${id}/overview$`));
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(s.displayAddress);
  await expect(page.getByTestId("overview-finance-summary")).toContainText(s.payment.toLocaleString("en"));
  await noOverflow(page);
}

async function pdf(page: Page, s: Scenario, info: TestInfo, syntheticMarket = true) {
  const report = page.getByTestId("report-evidence");
  await expect(report).toContainText(s.displayAddress); await expect(report).toContainText(s.payment.toLocaleString("en"));
  await expect(report).not.toContainText(scenarios.find(item => item.name !== s.name)!.payment.toLocaleString("en"));
  await page.emulateMedia({ media: "print" });
  await expect(page.getByTestId("report-controls")).toBeHidden(); await noOverflow(page);
  const output = info.outputPath(`case-${s.name}-a4.pdf`);
  const bytes = await page.pdf({ path: output, format: "A4", preferCSSPageSize: true, printBackground: true }); expect(bytes.byteLength).toBeGreaterThan(10000);
  // Inspect the actual PDF pages rather than infer PDF validity from the screen.
  // MuPDF font diagnostics may write to stdout; keep the machine-readable audit
  // in its own artifact so diagnostics cannot corrupt the JSON protocol.
  const auditPath = `${output}.audit.json`;
  const audit = spawnSync("python", ["-X", "utf8", "-c", "import pymupdf as fitz,json,sys; d=fitz.open(sys.argv[1]); json.dump([{'width':p.rect.width,'height':p.rect.height,'text':p.get_text(),'clipped':any(b[0]<-1 or b[2]>p.rect.width+1 or b[1]<-1 or b[3]>p.rect.height+1 for b in p.get_text('blocks'))} for p in d],open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False); d[0].get_pixmap().save(sys.argv[1]+'.first.png'); d[-1].get_pixmap().save(sys.argv[1]+'.last.png')", output, auditPath], { encoding: "utf8", windowsHide: true });
  expect(audit.status, audit.stderr).toBe(0);
  const pages = JSON.parse(readFileSync(auditPath, "utf8")) as { width: number; height: number; text: string; clipped: boolean }[];
  expect(pages.length).toBeGreaterThan(0);
  for (const sheet of pages) {
    // Chromium's format=A4 baseline emitted 595.92 × 842.88 points with an
    // explicit CSS @page A4 rule: allow the observed sub-point rounding only.
    expect(Math.abs(sheet.width - 595.28)).toBeLessThanOrEqual(1);
    expect(Math.abs(sheet.height - 841.89)).toBeLessThanOrEqual(1);
    expect(sheet.text.trim().length).toBeGreaterThan(20);
    expect(sheet.clipped).toBe(false);
    expect(sheet.text).not.toContain("列印／另存 PDF");
  }
  const pdfText = pages.map(sheet => sheet.text).join("\n");
  expect(pdfText).toContain(s.payment.toLocaleString("en"));
  expect(pdfText).toContain(s.price.toLocaleString("en"));
  expect(pdfText.replace(/\s+/g, "")).toContain("使用者設定基準");
  expect(pdfText.replace(/\s+/g, "")).toContain("未命中不等於安全");
  expect(pdfText.replace(/\s+/g, "")).toContain("人工核對");
  if (s.supported && syntheticMarket) expect(pdfText).toContain("Synthetic contract fixture");
  await info.attach(`case-${s.name}-pdf-audit`, { body: JSON.stringify(pages.map(({ text, ...sheet }) => ({ ...sheet, characterCount: text.trim().length })), null, 2), contentType: "application/json" });
  await info.attach(`case-${s.name}-actual-pdf-first-page`, { path: `${output}.first.png`, contentType: "image/png" });
  await info.attach(`case-${s.name}-actual-pdf-last-page`, { path: `${output}.last.png`, contentType: "image/png" });
  await page.screenshot({ path: info.outputPath(`case-${s.name}-print.png`), fullPage: true });
  await page.emulateMedia({ media: "screen" });
}

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430, 1024, 1440]) {
  test(`${locale} ${width}px real Create Save Reload Reopen two isolated cases Compare Report A4 zero automatic providers`, async ({ page }, info) => {
    // Observed default-30s failure at 31.2s after both real UI journeys, during
    // the final B Market refresh (before either PDF). Preserve 5s assertions;
    // only the total two-journey / two-PDF orchestration receives a bounded budget.
    test.setTimeout(90_000);
    await page.setViewportSize({ width, height: 900 });
    const calls = await installContracts(page);
    const created: SavedCase[] = [];
    for (const s of scenarios) {
      const saved = await test.step(`Create ${s.name} through real UI`, () => createThroughUI(page, locale, s, calls, info)); created.push(saved);
      const before = calls.slice();
      await reopen(page, s, saved.id, locale);
      await page.locator("#evidence-checklist summary").click();
      await page.getByTestId("checklist-identity-legal").getByRole("combobox").selectOption(s.review);
      await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
      await expect(page.getByTestId("commercial-overview-workspace").getByRole("status")).toContainText("人工核對狀態已保存");
      await page.reload(); await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(s.displayAddress);
      const persisted = (await rows(page)).find(item => item.id === saved.id)!;
      expect(persisted.data.journeyContext?.priceBasis).toBe("manual"); expect(persisted.data.journeyContext?.manualPriceWan).toBe(s.price);
      expect(persisted.data.inputs.building_age_years).toBe(s.age); expect(persisted.data.inputs.floor).toBe(s.floor);
      expect(persisted.data.inputs.area_ping).toBe(s.area); expect(persisted.data.inputs.building_type).toBe("住宅大樓");
      expect(persisted.data.journeyContext?.propertyContext.buildingAgeYears).toBe(s.age);
      expect(persisted.data.journeyContext?.propertyContext.floor).toBe(s.floor);
      expect(persisted.data.financeEvidence?.loan.annual_interest_rate).toBe(s.rate); expect(persisted.data.financeEvidence?.loan.loan_years).toBe(s.years);
      expect(persisted.data.financeEvidence?.loan.monthly_income_wan).toBeNull();
      expect(persisted.data.financeEvidence?.loan.monthly_payment_twd).toBe(s.payment);
      expect(persisted.data.financeEvidence?.affordability.status).toBe("unassessed");
      expect(persisted.data.financeEvidence?.affordability.ratio).toBeNull();
      expect(persisted.data.locationInsight?.risk_facility_evidence).toEqual(location(s).risk_facility_evidence);
      expect(persisted.data.locationInsight?.poi_summary.risk_facility_count).toBe(s.name === "A" ? null : 0);
      expect(persisted.data.locationInsight?.category_scores.risk_score).toBeNull();
      expect(persisted.data.locationInsight?.data_quality.checked_at).toBe(NOW);
      expect(persisted.data.checklistReview?.entries.find(item => item.id === "identity-legal")?.state).toBe(s.review);
      await page.goto(`/cases/${saved.id}/market`);
      assertZeroRequests(calls, before, `Reload Reopen Checklist Market navigation ${s.name}`);
      await page.getByTestId("market-refresh-button").click();
      await expect(page.getByTestId("market-refresh-state")).toContainText(s.supported ? "市場資料已更新" : "目前範圍的市場覆蓋有限");
      const afterExplicitRefresh = calls.slice();
      await page.reload();
      const refreshed = (await rows(page)).find(item => item.id === saved.id)!;
      expect(refreshed.data.marketInsight?.data_status).toBe(s.supported ? "available" : "no_data");
      await page.getByTestId("comparable-explanation").locator(":scope > summary").click();
      if (s.supported) { await expect(page.getByTestId("selected-comparable-explanations").locator("article")).toHaveCount(10); expect(persisted.data.valuation?.comparable_decision_trace).toEqual(comparableFixture.comparable_decision_trace); }
      else { await expect(page.getByTestId("comparable-explanation")).toContainText(comparableCopy(locale).unavailable); expect(persisted.data.journeyContext?.valuationStatus).not.toBe("available"); }
      assertZeroRequests(calls, afterExplicitRefresh, `Reload explanation ${s.name}`); await noOverflow(page);
    }
    expect(created[0].id).not.toBe(created[1].id);
    const before = calls.slice();
    await page.goto(`/compare?cases=${created.map(item => item.id).join(",")}`);
    const comparison = page.getByTestId(width < 768 ? "compare-mobile" : "compare-desktop");
    await expect(comparison).toContainText(scenarios[0].displayAddress); await expect(comparison).toContainText(scenarios[1].displayAddress);
    if (width < 768) await comparison.getByRole("combobox", { name: "比較領域", exact: true }).selectOption("finance");
    for (const s of scenarios) await expect(comparison).toContainText(s.payment.toLocaleString("en"));
    await noOverflow(page);
    if (width < 768) await comparison.getByRole("combobox", { name: "比較領域", exact: true }).selectOption("market");
    for (const s of scenarios) await expect(comparison).toContainText(s.price.toLocaleString("en"));
    await expect(comparison).toContainText("使用者設定基準");
    await noOverflow(page);
    for (let index = 0; index < scenarios.length; index++) {
      await page.goto(`/cases/${created[index].id}/report`); await page.getByTestId("locale-switcher").selectOption(locale);
      await pdf(page, scenarios[index], info);
    }
    for (let index = 0; index < scenarios.length; index++) await reopen(page, scenarios[index], created[index].id, locale);
    expect(await rows(page)).toHaveLength(2); assertZeroRequests(calls, before, "Compare Report PDF final Reload Reopen A B");
    await info.attach("provider-calls", { body: JSON.stringify({ requestsDuringCreateAndExplicitAcquisition: Array.from(calls), zeroProviderWindows: calls.zeroWindows, automaticRequestCount: calls.zeroWindows.reduce((sum, window) => sum + window.requests.length, 0) }, null, 2), contentType: "application/json" });
  });
}

test("opening valuation and clearing numeric assumptions preserves unknown saved facts", async ({ page }, info) => {
  const calls = await installContracts(page);
  const created: SavedCase[] = [];
  for (const s of scenarios) {
    const saved = await createThroughUI(page, "zh-TW", s, calls, info, false, undefined, undefined, {
      applyScenarioInputs: false, skipEstimate: true,
      // A opens the form without touching defaults; B explicitly clears them.
      prepare: s.name === "A" ? undefined : async form => {
        await form.getByRole("spinbutton", { name: "屋齡", exact: true }).fill("");
        await form.getByRole("spinbutton", { name: "樓層", exact: true }).fill("");
        await expect(form.getByRole("button", { name: copy("zh-TW", "valuation.estimate"), exact: true })).toBeDisabled();
      },
    });
    created.push(saved);
    expect(saved.data.journeyContext?.propertyContext.buildingAgeYears).toBeUndefined();
    expect(saved.data.journeyContext?.propertyContext.floor).toBeUndefined();
  }
  expect(calls.filter(request => request === "POST /valuation/estimate")).toEqual([]);
  const before = calls.slice();
  for (let index = 0; index < scenarios.length; index++) {
    await reopen(page, scenarios[index], created[index].id, "zh-TW");
    const persisted = (await rows(page)).find(row => row.id === created[index].id)!;
    expect(persisted.data.journeyContext?.propertyContext.buildingAgeYears).toBeUndefined();
    expect(persisted.data.journeyContext?.propertyContext.floor).toBeUndefined();
  }
  assertZeroRequests(calls, before, "Unknown numeric assumptions Reload Reopen");
});

test("explicit zero valuation assumptions are submitted and preserved as known zero", async ({ page }, info) => {
  const calls = await installContracts(page);
  let submissions = 0;
  await page.route("**/valuation/estimate", route => {
    const payload = route.request().postDataJSON();
    expect(payload.building_age_years).toBe(0); expect(payload.floor).toBe(0); submissions++;
    return route.fulfill({ json: { valuation_status: "no_data", valuation_reason_code: "insufficient_official_sample", result_origin: "none", is_actionable: false, source: "postgres", data_status: unsupportedDataStatus, comparables: [], estimate_total_price: null, estimate_unit_price_per_ping: null, price_range: { low: null, mid: null, high: null }, confidence_score: null, confidence: "insufficient", methodology: [], disclaimer: "Synthetic zero-assumption contract" } });
  });
  const saved = await createThroughUI(page, "zh-TW", scenarios[0], calls, info, true, undefined, undefined, {
    applyScenarioInputs: false,
    prepare: async form => {
      await form.getByRole("spinbutton", { name: "屋齡", exact: true }).fill("");
      await form.getByRole("spinbutton", { name: "樓層", exact: true }).fill("");
      await expect(form.getByRole("button", { name: copy("zh-TW", "valuation.estimate"), exact: true })).toBeDisabled();
      await form.getByRole("spinbutton", { name: "屋齡", exact: true }).fill("0");
      await form.getByRole("spinbutton", { name: "樓層", exact: true }).fill("0");
      await expect(form.getByRole("button", { name: copy("zh-TW", "valuation.estimate"), exact: true })).toBeEnabled();
    },
  });
  expect(submissions).toBe(1);
  expect(saved.data.journeyContext?.propertyContext.buildingAgeYears).toBe(0);
  expect(saved.data.journeyContext?.propertyContext.floor).toBe(0);
  expect(saved.data.inputs.building_age_years).toBe(0); expect(saved.data.inputs.floor).toBe(0);
  const before = calls.slice();
  await reopen(page, scenarios[0], saved.id, "zh-TW");
  const persisted = (await rows(page)).find(row => row.id === saved.id)!;
  expect(persisted.data.journeyContext?.propertyContext.buildingAgeYears).toBe(0);
  expect(persisted.data.journeyContext?.propertyContext.floor).toBe(0);
  assertZeroRequests(calls, before, "Known zero assumptions Reload Reopen");
});

test("queued Checklist save protects its draft until the storage lock completes", async ({ page }) => {
  const saved = e9Case();
  const original = JSON.stringify([saved]);
  await page.addInitScript(({ key, original }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, original); }, { key: KEY, original });
  const calls = await installContracts(page);
  await page.goto(`/cases/${saved.id}/overview`);
  await page.locator("#evidence-checklist summary").click();
  const review = page.getByTestId("checklist-identity-legal");
  await review.getByRole("combobox").selectOption("reviewed");
  const before = calls.slice();
  await page.evaluate(async key => {
    await new Promise<void>(acquired => {
      void navigator.locks.request(key, { mode: "exclusive" }, () => new Promise<void>(release => {
        (window as unknown as { releaseChecklistTestLock: () => void }).releaseChecklistTestLock = release;
        acquired();
      }));
    });
  }, KEY);
  try {
    await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
    await expect(review.getByRole("combobox")).toBeDisabled();
    await expect(review.getByRole("checkbox")).toBeDisabled();
    await expect(page.getByRole("button", { name: "保存人工核對", exact: true })).toBeDisabled();
    await expect(page.getByRole("button", { name: "載入已保存核對狀態", exact: true })).toBeDisabled();
    expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(original);
  } finally {
    await page.evaluate(() => (window as unknown as { releaseChecklistTestLock: () => void }).releaseChecklistTestLock());
  }
  await expect(page.getByTestId("commercial-overview-workspace").getByRole("status")).toContainText("人工核對狀態已保存");
  expect((await rows(page))[0].data.checklistReview?.entries.find(item => item.id === "identity-legal")?.state).toBe("reviewed");
  await expect(review.getByRole("combobox")).toBeEnabled();
  assertZeroRequests(calls, before, "Queued Checklist save");
});

test("failed Checklist save retains the draft and restores controls for a successful retry", async ({ page }) => {
  const saved = e9Case();
  const original = JSON.stringify([saved]);
  await page.addInitScript(({ key, original }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, original); }, { key: KEY, original });
  const calls = await installContracts(page);
  await page.goto(`/cases/${saved.id}/overview`);
  await page.locator("#evidence-checklist summary").click();
  const review = page.getByTestId("checklist-identity-legal");
  await review.getByRole("combobox").selectOption("reviewed");
  const before = calls.slice();
  await page.evaluate(key => {
    const write = Storage.prototype.setItem;
    (window as unknown as { restoreChecklistTestStorage: () => void }).restoreChecklistTestStorage = () => { Storage.prototype.setItem = write; };
    Storage.prototype.setItem = function(storageKey, value) { if (storageKey === key) throw new DOMException("Synthetic quota denial", "QuotaExceededError"); return write.call(this, storageKey, value); };
  }, KEY);
  await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
  await expect(page.locator("#evidence-checklist")).toContainText("人工核對狀態未保存");
  await expect(page.locator("#evidence-checklist")).toContainText("尚未保存人工核對變更");
  await expect(review.getByRole("combobox")).toBeEnabled();
  await expect(review.getByRole("combobox")).toHaveValue("reviewed");
  await expect(review.getByRole("checkbox")).toBeEnabled();
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(original);
  await page.evaluate(() => (window as unknown as { restoreChecklistTestStorage: () => void }).restoreChecklistTestStorage());
  await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
  await expect(page.getByTestId("commercial-overview-workspace").getByRole("status")).toContainText("人工核對狀態已保存");
  expect((await rows(page))[0].data.checklistReview?.entries.find(item => item.id === "identity-legal")?.state).toBe("reviewed");
  assertZeroRequests(calls, before, "Failed Checklist save and explicit retry");
});

test("failed Market refresh write retains original saved evidence and shows truthful failure", async ({ page }) => {
  const saved = e9Case();
  const original = JSON.stringify([saved]);
  await page.addInitScript(({ key, original }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, original); }, { key: KEY, original });
  await page.route("**/market-insights/query", route => route.fulfill({ json: { ...saved.data.marketInsight, source_updated_at: NOW, summary: "Synthetic explicit refresh response" } }));
  await page.goto(`/cases/${saved.id}/market`);
  await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
  await page.evaluate(key => {
    const write = Storage.prototype.setItem;
    Storage.prototype.setItem = function(storageKey, value) { if (storageKey === key) throw new DOMException("Synthetic quota denial", "QuotaExceededError"); return write.call(this, storageKey, value); };
  }, KEY);
  await page.getByTestId("market-refresh-button").click();
  await expect(page.getByTestId("market-refresh-state")).toContainText("市場資料未保存");
  await expect(page.getByTestId("market-refresh-state")).toContainText("既有市場摘要仍保留");
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(original);
  await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
});

test("older Market response cannot overwrite newer same-case evidence with unchanged identity inputs and timestamps", async ({ page }, info) => {
  // This focused concurrency regression uses synthetic storage fixtures; the
  // main two-case acceptance above continues to create both cases through UI.
  const saved = e9Case();
  const other = e9Case("case-b");
  const original = JSON.stringify([saved, other]);
  const newerMarket = { ...saved.data.marketInsight!, average_unit_price: 83.4, avg_price_per_ping: 83.4, median_unit_price_per_ping: 82.6, summary: "Synthetic newer same-case Market evidence", source_name: "Synthetic newer same-case Market source" };
  const olderMarket = { ...saved.data.marketInsight!, average_unit_price: 11.2, avg_price_per_ping: 11.2, median_unit_price_per_ping: 10.8, summary: "Synthetic older deferred Market evidence", source_name: "Synthetic older deferred Market source" };
  await page.addInitScript(({ key, original }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, original); }, { key: KEY, original });
  const calls = await installContracts(page);
  let releaseResponse!: () => void;
  const responseGate = new Promise<void>(resolve => { releaseResponse = resolve; });
  let requested = 0;
  await page.route("**/market-insights/query", async route => {
    requested++;
    await responseGate;
    await route.fulfill({ json: olderMarket });
  });
  await page.goto(`/cases/${saved.id}/market`);
  await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
  expect(calls.slice()).toEqual([]);
  await page.getByTestId("market-refresh-button").click();
  await expect.poll(() => requested).toBe(1);
  await expect(page.getByTestId("market-refresh-state")).toContainText("正在更新市場資料");

  const writer = await page.context().newPage();
  const writerCalls = await installContracts(writer);
  try {
    await writer.goto("/cases");
    // A real second page commits under the same origin-wide Web Lock. The
    // browser delivers its native storage event to the pending Market page.
    // Keep timestamp, revision, identity, and all acquisition inputs unchanged.
    const newerRaw = await writer.evaluate(async ({ key, caseId, market }) => navigator.locks.request(key, async () => {
      const records = JSON.parse(localStorage.getItem(key)!) as SavedCase[];
      const index = records.findIndex(record => record.id === caseId);
      records[index] = { ...records[index], data: { ...records[index].data, marketInsight: market } };
      const next = JSON.stringify(records);
      localStorage.setItem(key, next);
      return next;
    }), { key: KEY, caseId: saved.id, market: newerMarket });
    await expect(page.getByTestId("market-price-workspace")).toContainText(newerMarket.source_name);
    const newerSaved = (await rows(page)).find(record => record.id === saved.id)!;
    expect(newerSaved.updatedAt).toBe(saved.updatedAt);
    expect(newerSaved.version).toBe(saved.version);
    expect(newerSaved.data.inputs).toEqual(saved.data.inputs);
    expect(newerSaved.data.propertyIdentityAnchor).toEqual(saved.data.propertyIdentityAnchor);
    expect(newerSaved.data.journeyContext).toEqual(saved.data.journeyContext);

    const before = calls.slice();
    releaseResponse();
    await expect(page.getByTestId("market-refresh-state")).toContainText("市場資料未保存");
    await expect(page.getByTestId("market-refresh-state")).toContainText("既有市場摘要仍保留");
    await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
    expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(newerRaw);
    await expect(page.getByTestId("market-price-workspace")).not.toContainText(olderMarket.source_name);
    await page.reload();
    await expect(page.getByTestId("market-price-workspace")).toContainText(newerMarket.source_name);
    await expect(page.getByTestId("market-price-context")).toContainText("82.6");
    await page.goto(`/cases/${saved.id}/report`);
    await expect(page.getByTestId("report-evidence")).toContainText(newerMarket.source_name);
    await expect(page.getByTestId("report-evidence")).not.toContainText(olderMarket.source_name);
    await expect(page.getByTestId("report-evidence").getByRole("row").filter({ hasText: "市場成交單價中位數" })).toContainText("82.6");
    const persisted = await rows(page);
    expect(persisted).toHaveLength(2);
    expect(persisted.find(record => record.id === saved.id)!.data.marketInsight).toEqual(newerMarket);
    expect(persisted.find(record => record.id === other.id)).toEqual(other);
    expect(calls.filter(call => call === "POST /market-insights/query")).toHaveLength(1);
    assertZeroRequests(calls, before, "Stale same-case Market response rejection reload Report");
    assertZeroRequests(writerCalls, [], "Concurrent same-case synthetic evidence commit");
    await info.attach("stale-same-case-market-boundary", { body: JSON.stringify({ olderResponseRejected: true, sameIdentity: true, sameInputs: true, sameRevision: true, sameUpdatedAt: true, unrelatedCaseUnchanged: true, explicitMarketRequests: requested, zeroWindows: [...calls.zeroWindows, ...writerCalls.zeroWindows] }), contentType: "application/json" });
  } finally {
    releaseResponse();
    await writer.close();
  }
});

test("failed Delete retains a valid case and unrelated quarantined storage and shows truthful failure", async ({ page }) => {
  // Recovery tests intentionally inject corruption; the primary journey above never seeds cases.
  const original = JSON.stringify([e9Case(), { id: "quarantined-record", version: 99, private_note: "synthetic preserved record" }]);
  await page.addInitScript(({ key, original }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, original); }, { key: KEY, original });
  await page.goto("/?workflow=property");
  await stage(page, "zh-TW", "location");
  await page.locator("#location-insight-calculator").getByRole("textbox").first().fill(scenarios[0].address);
  await stage(page, "zh-TW", "decision");
  await page.getByRole("button", { name: /^已儲存案件/ }).filter({ visible: true }).click();
  const savedList = page.locator("#journey-stage-decision").getByRole("region", { name: copy("zh-TW", "case.title"), exact: true });
  const card = savedList.getByRole("article").filter({ hasText: "案件 A" });
  await expect(card).toBeVisible();
  await page.evaluate(key => {
    const write = Storage.prototype.setItem;
    Storage.prototype.setItem = function(storageKey, value) { if (storageKey === key) throw new DOMException("Synthetic quota denial", "QuotaExceededError"); return write.call(this, storageKey, value); };
  }, KEY);
  await card.getByRole("button", { name: "刪除", exact: true }).click();
  await card.getByRole("button", { name: "再次點擊確認刪除", exact: true }).click();
  await expect(savedList.getByRole("status")).toContainText(/未刪除|刪除失敗/);
  await expect(card).toBeVisible();
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(original);
});

// Private response bodies remain outside versioned sources. This lane replays
// an explicitly acquired release-matched response; it does not call providers.
const capturedLanes = [
  { name: "captured current LIVE unavailable original-manual-road response", supported: false, valuationPath: process.env.HOSTED_CASE_UNAVAILABLE_CAPTURE },
  ...(process.env.HOSTED_CASE_SUPPORTED_CAPTURE ? [{ name: "captured approved local GREEN successful original-manual-road response", supported: true, valuationPath: process.env.HOSTED_CASE_SUPPORTED_CAPTURE }] : []),
];
if (process.env.HOSTED_CASE_CAPTURE_DIR) for (const lane of capturedLanes) test(`${lane.name} Create Save Reload Reopen Report A4 keeps evidence truthful`, async ({ page }, info) => {
  // Observed a 41.2s default-30s failure after exact query, Save/Reopen, and
  // actual PDF audits completed. Budget this full replay/PDF orchestration;
  // retain the existing 5s assertions and 180s browser-launch timeout.
  test.setTimeout(90_000);
  const directory = process.env.HOSTED_CASE_CAPTURE_DIR!;
  const capturedLocation = JSON.parse(readFileSync(join(directory, "location-response.private.json"), "utf8"));
  const capturedTerrain = JSON.parse(readFileSync(join(directory, "terrain-response.private.json"), "utf8"));
  const capturedValuation = JSON.parse(readFileSync(lane.valuationPath ?? join(directory, "valuation-response.private.json"), "utf8"));
  expect(capturedValuation.valuation_status).toBe(lane.supported ? "available" : "unavailable");
  expect(capturedValuation.is_actionable).toBe(lane.supported);
  expect(capturedValuation.comparables).toHaveLength(lane.supported ? 10 : 0);
  if (lane.supported) { expect(capturedValuation.estimate_total_price).toBeGreaterThan(0); expect(capturedValuation.comparable_decision_trace).toBeDefined(); }
  else expect(capturedValuation.estimate_total_price).toBeNull();
  expect(capturedTerrain.data_quality.status).toBe("limited");
  const calls = await installContracts(page);
  const boundaries: { phase: string; status: string; validCount: number; issues: string[]; optionalTypes: Record<string, string>[] }[] = [];
  const boundary = async (phase: string) => {
    const raw = await page.evaluate(key => localStorage.getItem(key), KEY);
    const diagnostic = parseSavedCasesDiagnostic(raw, row => ({ ...row, data: compactCaseData(row.data) }));
    boundaries.push({ phase, status: diagnostic.status, validCount: diagnostic.cases.length, issues: diagnostic.issues.map(issue => issue.reason), optionalTypes: diagnostic.cases.map(row => Object.fromEntries(["locationInsight", "terrainReference", "financeEvidence", "journeyContext", "propertyIdentityAnchor"].map(key => [key, row.data[key as keyof typeof row.data] === null ? "null" : typeof row.data[key as keyof typeof row.data]]))) });
    await info.attach(`captured-boundary-${phase}`, { body: JSON.stringify(boundaries.at(-1)), contentType: "application/json" });
  };
  await page.route("**/roads/roads**", route => route.fulfill({ json: { city: capturedLocation.input.city, district: capturedLocation.input.district, roads: [capturedLocation.input.road, capturedValuation.source_details.requested_road], message: "Synthetic directory for the exact captured manual query scope" } }));
  await page.route("**/location/insight", route => {
    const payload = route.request().postDataJSON();
    expect(String(payload.city).replace(/^台/, "臺")).toBe(String(capturedLocation.input.city).replace(/^台/, "臺"));
    expect(payload.district).toBe(capturedLocation.input.district);
    expect(payload.road).toBe(capturedLocation.input.road);
    expect(payload.address).toBe(scenarios[0].address);
    expect(payload.area_ping).toBe(capturedLocation.input.area_ping);
    return route.fulfill({ json: capturedLocation });
  });
  await page.route("**/terrain-risk/analyze", route => route.fulfill({ json: capturedTerrain }));
  await page.route("**/valuation/estimate", route => {
    const payload = route.request().postDataJSON();
    // A real captured result may be replayed only for its actual query scope.
    expect(String(payload.city).replace(/^台/, "臺")).toBe(String(capturedValuation.source_details.requested_city).replace(/^台/, "臺"));
    expect(payload.district).toBe(capturedValuation.source_details.requested_district);
    expect(payload.road).toBe(capturedValuation.source_details.requested_road);
    expect(payload.area_ping).toBe(scenarios[0].area);
    expect(payload.building_age_years).toBe(scenarios[0].age);
    expect(payload.floor).toBe(scenarios[0].floor);
    expect(payload.building_type).toBe(capturedLocation.input.building_type);
    return route.fulfill({ json: capturedValuation });
  });
  const terrainCopy = getSurfaceCopy("zh-TW").terrain;
  const s = scenarios[0];
  const saved = await createThroughUI(page, "zh-TW", s, calls, info, !lane.supported, async () => {
    await boundary("after-location");
    await page.locator('[aria-labelledby="location-market-tools-heading"]').getByRole("button").nth(1).click();
    await page.locator("#terrain-risk-analysis").getByRole("button", { name: terrainCopy.compactAnalyze, exact: true }).click();
    await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
    // This real response has unavailable layers. The UI must prohibit attaching
    // it as complete evidence rather than promote it to a successful result.
    await expect(page.locator("#terrain-risk-analysis").getByRole("button", { name: terrainCopy.attachDisabled, exact: true })).toBeDisabled();
    await boundary("after-terrain");
  }, boundary, undefined, async () => {
    // The real response has no resolved village. Enter the captured manual
    // geography before location acquisition using the existing valuation UI.
    // This preserves logical inputs, without claiming the historical UI order.
    await stage(page, "zh-TW", "price");
    const form = page.locator("#valuation-calculator");
    await form.getByRole("combobox", { name: copy("zh-TW", "common.selectCounty"), exact: true }).selectOption(String(capturedLocation.input.city).replace(/^台/, "臺"));
    await form.getByRole("combobox", { name: copy("zh-TW", "common.selectDistrict"), exact: true }).selectOption(capturedLocation.input.district);
    await form.getByRole("combobox", { name: copy("zh-TW", "common.selectRoad"), exact: true }).selectOption(capturedLocation.input.road);
    await form.getByPlaceholder(copy("zh-TW", "location.address"), { exact: true }).fill(s.address);
    await stage(page, "zh-TW", "location");
    await page.locator("#location-insight-calculator").getByLabel(copy("zh-TW", "location.address"), { exact: true }).fill(s.address);
  });
  await boundary("after-save");
  expect(boundaries.at(-1)?.status).toBe("ready");
  expect(boundaries.at(-1)?.validCount).toBe(1);
  const before = calls.slice();
  await reopen(page, s, saved.id, "zh-TW");
  await boundary("after-reopen");
  expect(boundaries.at(-1)?.status).toBe("ready"); expect(boundaries.at(-1)?.validCount).toBe(1);
  await page.reload();
  await boundary("after-reload");
  expect(boundaries.at(-1)?.status).toBe("ready"); expect(boundaries.at(-1)?.validCount).toBe(1);
  const persisted = (await rows(page)).find(item => item.id === saved.id)!;
  expect(persisted.data.journeyContext?.priceBasis).toBe("manual");
  expect(persisted.data.journeyContext?.manualPriceWan).toBe(s.price);
  expect(persisted.data.inputs.building_age_years).toBe(s.age); expect(persisted.data.inputs.floor).toBe(s.floor);
  expect(persisted.data.journeyContext?.valuationStatus).toBe(lane.supported ? "available" : "unavailable");
  if (lane.supported) expect(persisted.data.valuation?.comparable_decision_trace).toEqual(capturedValuation.comparable_decision_trace);
  expect(persisted.data.locationInsight?.geocoding_acceptance).toEqual(capturedLocation.geocoding_acceptance);
  expect(persisted.data.locationInsight?.risk_facility_evidence).toEqual(capturedLocation.risk_facility_evidence);
  expect(persisted.data.locationInsight?.data_quality.checked_at).toBe(capturedLocation.data_quality.checked_at);
  expect(persisted.data.terrainReference).toBeUndefined();
  await page.goto(`/cases/${saved.id}/report`);
  await expect(page.getByTestId("report-evidence")).toContainText(s.displayAddress);
  if (lane.supported) await expect(page.getByTestId("report-comparable-explanation")).toContainText(`${comparableCopy("zh-TW").included}: 10`);
  await pdf(page, s, info, false);
  assertZeroRequests(calls, before, `${lane.name} Save Reload Reopen Report PDF`);
  await info.attach("captured-response-replay-result", { body: JSON.stringify({ lane: lane.name, savedCount: (await rows(page)).length, valuationStatus: persisted.data.journeyContext?.valuationStatus, priceBasis: persisted.data.journeyContext?.priceBasis, selectedComparableCount: persisted.data.valuation?.comparable_decision_trace?.selected.length ?? 0, terrainAttached: !!persisted.data.terrainReference, locationSource: capturedLocation.geocoding_acceptance.geocoding_source, geocodingBoundary: "Captured response accepted supplied Work coordinates; no fresh Google lookup is claimed", financeSource: "synthetic deterministic loan fixture; not live finance evidence", boundaries, automaticRequests: calls.zeroWindows }), contentType: "application/json" });
});
