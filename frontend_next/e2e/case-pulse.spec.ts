import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { emptyDecisionRoom } from "../lib/decision-room-store";
import { isProviderRequest } from "./helpers/provider-request";

test.beforeEach(() => { test.setTimeout(90_000); });

async function seed(page: Page, locale = "en", located = true) {
  const saved = e9Case();
  if (!located) saved.data = { inputs: saved.data.inputs };
  const room = emptyDecisionRoom("case-a");
  room.items = [{ id: "inspect", kind: "checklist", title: "Inspect window", owner: "", dueDate: "", status: "open", resolution: "" }];
  room.updatedAt = "2026-10-20T03:00:00.000Z";
  await page.addInitScript(({ saved, room, locale }) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
    if (!localStorage.getItem("proptech.decisionRoom.v1.case-a")) localStorage.setItem("proptech.decisionRoom.v1.case-a", JSON.stringify(room));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, { saved, room, locale });
}

for (const [locale, title, labels] of [
  ["zh-TW", "案件動態", ["位置", "市場", "風險", "資金", "決策室"]],
  ["en", "Case Pulse", ["Location", "Market", "Risk", "Money", "Decision"]],
  ["ja", "案件の動き", ["所在地", "市場", "リスク", "資金", "意思決定"]],
  ["ko", "매물 현황", ["위치", "시장", "위험", "자금", "의사결정"]],
] as const) for (const width of [390, 430]) test(`${locale} at ${width}: localized, wrapping Pulse without horizontal overflow or score language`, async ({ page }, testInfo) => {
  await seed(page, locale);
  await page.setViewportSize({ width, height: 932 });
  await page.goto("/cases/case-a/overview");
  const pulse = page.getByTestId("case-pulse");
  await expect(pulse).toHaveAccessibleName(title);
  await expect(pulse.getByRole("link")).toHaveCount(5);
  for (const label of labels) await expect(pulse.getByRole("link", { name: new RegExp(label) })).toBeVisible();
  expect(await pulse.innerText()).not.toMatch(/%|％|score|confidence|readiness|complete|完成率|分數|スコア|점수/i);
  expect(await pulse.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const boxes = await pulse.getByRole("link").evaluateAll((links) => links.map((link) => { const rect = link.getBoundingClientRect(); return { top: rect.top, right: rect.right, left: rect.left, height: rect.height }; }));
  expect(new Set(boxes.map((box) => box.top)).size).toBe(2);
  for (const box of boxes) { expect(box.right).toBeLessThanOrEqual(width); expect(box.left).toBeGreaterThanOrEqual(0); expect(box.height).toBeGreaterThanOrEqual(44); }
  if (locale === "en" && width === 390) await pulse.screenshot({ path: testInfo.outputPath("case-pulse-390.png"), animations: "disabled" });
});

for (const [section, route] of [["location", "location"], ["market", "market"], ["risk", "risk"], ["money", "finance"], ["decision", "decision-room"]]) test(`${section} click navigates only, with zero provider calls or writes`, async ({ page, baseURL }) => {
  // Destination maps load their own tiles for located cases. Keep this navigation
  // contract independent of those existing map requests.
  await seed(page, "en", false);
  const calls: string[] = [];
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await page.goto("/cases/case-a/overview");
  const pulse = page.getByTestId("case-pulse");
  await expect(pulse).toBeVisible();
  const before = await page.evaluate(() => [localStorage.getItem("proptech.savedCases.v1"), localStorage.getItem("proptech.decisionRoom.v1.case-a")]);
  await pulse.locator(`[data-pulse-section="${section}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/cases/case-a/${route}$`));
  await expect(page.getByTestId("case-pulse")).toBeVisible();
  expect(await page.evaluate(() => [localStorage.getItem("proptech.savedCases.v1"), localStorage.getItem("proptech.decisionRoom.v1.case-a")])).toEqual(before);
  expect(calls).toEqual([]);
});

test("saved location, market, nearby, risk and money changes update immediately without reload or provider requests", async ({ page, baseURL }) => {
  await seed(page, "en", false);
  const calls: string[] = [];
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await page.goto("/cases/case-a/overview");
  const pulse = page.getByTestId("case-pulse");
  await expect(pulse).toContainText("Location unconfirmed");
  await page.evaluate(() => { (window as Window & { pulseMarker?: string }).pulseMarker = "same-document"; });
  await page.evaluate((saved) => { localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved])); window.dispatchEvent(new Event("proptech:saved-case-updated")); }, e9Case());
  await expect(pulse).toContainText("Address linked");
  await expect(pulse).toContainText("Saved · limited evidence");
  await expect(pulse).toContainText("1 matched · 2 to verify · 1 unknown");
  await expect(pulse).toContainText("Assumptions saved");
  await page.evaluate(() => {
    const saved = JSON.parse(localStorage.getItem("proptech.savedCases.v1")!)[0];
    saved.data.nearbyFacilities = { version: 1, source: "google_places", origin: { lat: 24.16525, lng: 120.64555 }, radiusM: 800, checkedAt: "2026-10-21T03:00:00.000Z", partial: false, successfulCategories: ["transport", "shopping", "food", "school", "medical", "park"], places: [] };
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
    window.dispatchEvent(new Event("proptech:saved-case-updated"));
  });
  await expect(pulse).toContainText("Nearby evidence saved");
  await expect(pulse).toContainText("Latest evidence: Nearby evidence");
  await expect(pulse.locator("time")).toHaveAttribute("datetime", "2026-10-21T03:00:00.000Z");
  expect(await page.evaluate(() => (window as Window & { pulseMarker?: string }).pulseMarker)).toBe("same-document");
  expect(calls).toEqual([]);
});

test("real Decision Room DONE save reduces Pulse outstanding count without reload", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/decision-room");
  const pulse = page.getByTestId("case-pulse");
  await expect(pulse).toContainText("1 outstanding");
  await page.getByTestId("checklist-items").getByRole("button", { name: "Edit", exact: true }).click();
  const edit = page.getByTestId("item-edit-form");
  for (const status of ["in_progress", "blocked"]) {
    await edit.getByLabel("Status", { exact: true }).selectOption(status);
    await edit.getByRole("button", { name: "Save", exact: true }).click();
    await expect(pulse).toContainText("1 outstanding");
    await page.getByTestId("checklist-items").getByRole("button", { name: "Edit", exact: true }).click();
  }
  await edit.getByLabel("Status", { exact: true }).selectOption("done");
  await edit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(pulse).toContainText("No open actions");
  await expect(pulse).toContainText("Latest update: Decision");
});

test("cross-tab saved-state and room events refresh Pulse; corrupt room stays unavailable", async ({ page, context }) => {
  await seed(page);
  await page.goto("/cases/case-a/overview");
  const pulse = page.getByTestId("case-pulse");
  await expect(pulse).toContainText("1 outstanding");
  const other = await context.newPage();
  await other.goto("/cases/case-a/overview");
  await other.evaluate(() => {
    const room = JSON.parse(localStorage.getItem("proptech.decisionRoom.v1.case-a")!);
    for (const status of ["open", "in_progress", "blocked", "done"]) room.items.push({ id: `verify-${status}`, kind: "verification", title: "Verify saved evidence", owner: "Buyer", dueDate: "", status, resolution: status === "done" ? "Checked" : "", origin: "risk", sourceKey: `risk:${status}`, note: "Ask seller", createdAt: "2026-10-21T03:00:00.000Z", updatedAt: "2026-10-21T03:00:00.000Z" });
    localStorage.setItem("proptech.decisionRoom.v1.case-a", JSON.stringify(room));
  });
  await expect(pulse).toContainText("4 outstanding");
  await other.evaluate(() => {
    const room = JSON.parse(localStorage.getItem("proptech.decisionRoom.v1.case-a")!);
    for (const item of room.items) { item.status = "done"; item.resolution = "Checked"; }
    localStorage.setItem("proptech.decisionRoom.v1.case-a", JSON.stringify(room));
  });
  await expect(pulse).toContainText("No open actions");
  await other.evaluate(() => {
    const saved = JSON.parse(localStorage.getItem("proptech.savedCases.v1")!)[0];
    saved.data.propertyIdentityAnchor.revalidation = { status: "needs_revalidation", conflicts: ["normalized_address"] };
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
    localStorage.setItem("proptech.decisionRoom.v1.case-a", "corrupt");
  });
  await expect(pulse).toContainText("Reconfirm location");
  await expect(pulse.locator('[data-pulse-section="decision"]')).toContainText("Unavailable");
  await other.close();
});
