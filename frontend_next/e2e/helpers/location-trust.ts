import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export function trackSpatialAnalysis(page: Page) {
  const calls: string[] = [];
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST" && (/\/(location|terrain|terrain-risk|geocoding|places|satellite|commute)(\/|$)/.test(path) || /^\/map\/(search|nearby)$/.test(path))) calls.push(path);
  });
  return calls;
}

export async function expectConservativeLocation(page: Page, locale: "en" | "zh-TW") {
  const result = page.getByTestId("location-result");
  await expect(result).toBeVisible();
  const metric = (label: string) => result.locator(".ds-metric").filter({ has: page.getByText(label, { exact: true }) }).locator(".ds-metric__value");
  const unknown = locale === "en" ? "Insufficient data" : "資料不足";
  await expect(metric(locale === "en" ? "Location score" : "位置分數")).toHaveText(unknown);
  await expect(metric(locale === "en" ? "Risk data" : "風險資料")).toHaveText([unknown, unknown]);
  await expect(metric(locale === "en" ? "Transit" : "交通")).toHaveText(["80", "4"]);
  await expect(result).not.toContainText("72");
  return result;
}
