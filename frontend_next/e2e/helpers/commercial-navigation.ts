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
