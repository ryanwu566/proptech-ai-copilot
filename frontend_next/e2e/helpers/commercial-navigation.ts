import { expect, type Page } from "@playwright/test";

/** Secondary tools stay reachable through the public Methods disclosure. */
export async function openMethod(page: Page, name: string | RegExp) {
  const methods = page.locator(".commercial-methods");
  if (!(await methods.evaluate((node) => (node as HTMLDetailsElement).open))) {
    await methods.locator(":scope > summary").click();
  }
  const action = methods.getByRole("button", { name, exact: typeof name === "string" });
  await expect(action).toBeVisible();
  await action.click();
}

/** The retained competition demo is a secondary Methods reference in each locale. */
export async function openDemoReference(page: Page) {
  await openMethod(page, /^(競賽展示參考|Demo reference|デモ参照|데모 참고)$/);
  await expect(page.getByTestId("competition-demo")).toBeVisible();
}

/** Official transaction search is an explicit optional entry from E10 Home. */
export async function openPropertyEntry(page: Page) {
  await page.locator(".commercial-home").getByRole("button", {
    name: /還沒有特定物件？搜尋官方成交資料|No property yet\? Search official transactions|物件が未定ですか？公式取引を検索|물건이 없나요\? 공식 거래 검색/,
  }).click();
  await expect(page.locator("#journey-stage-property")).toBeVisible();
}

const LEGACY_LOCATION_STEP = /^(位置與資料證據|Location and evidence|位置と根拠|위치와 근거) · /;

/**
 * Home Start now creates a local case. The legacy guided journey stays reachable
 * through its explicit deep link; this enters it and types the address in its
 * own Location step, exactly as a legacy user would.
 */
export async function openLegacyJourneyWithAddress(page: Page, address: string, url = "/?workflow=property") {
  await page.goto(url);
  await expect(page.locator("#journey-stage-property")).toBeVisible();
  const steps = page.locator("#guided-property-journey nav").first();
  const disclosure = steps.locator("details");
  if (await disclosure.isVisible() && !(await disclosure.evaluate((node) => (node as HTMLDetailsElement).open))) await disclosure.locator("summary").click();
  await steps.getByRole("button", { name: LEGACY_LOCATION_STEP }).filter({ visible: true }).click();
  await expect(page.locator("#journey-stage-location")).toBeVisible();
  const input = page.locator("#location-insight-calculator").getByRole("textbox").first();
  await input.fill(address);
  await expect(input).toHaveValue(address);
}
