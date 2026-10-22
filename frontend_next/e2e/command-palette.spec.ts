import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { emptyDecisionRoom } from "../lib/decision-room-store";
import { isProviderRequest } from "./helpers/provider-request";

test.setTimeout(60_000);
async function seed(page: Page, active = true, locale = "en", unconfirmed = false) {
  const saved = e9Case();
  if (unconfirmed) delete saved.data.propertyIdentityAnchor;
  await page.addInitScript(({ rows, locale }) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, { rows: active ? [saved, e9Case("case-b")] : [], locale });
}
async function open(page: Page) {
  await page.getByTestId("command-palette-trigger").click();
  await expect(page.getByTestId("command-palette")).toBeVisible();
}
const option = (page: Page, id: string) => page.locator(`[role="option"][data-command-id="${id}"]`);

test("Ctrl+K opens; Escape closes and restores the prior input focus", async ({ page }) => {
  await seed(page, false); await page.goto("/");
  const address = page.locator("#commercial-address"); await address.focus();
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog", { name: "Case commands" })).toBeVisible();
  await expect(page.getByTestId("command-palette").getByRole("combobox")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await expect(address).toBeFocused();
});
test("Cmd+K opens using a Meta keyboard event", async ({ page }) => {
  await seed(page, false); await page.goto("/");
  await page.getByTestId("command-palette-trigger").waitFor();
  await page.keyboard.press("Meta+k"); await expect(page.getByTestId("command-palette").getByRole("combobox")).toBeFocused();
});
test("arrow navigation wraps, Enter executes, and Tab stays inside dialog", async ({ page }) => {
  await seed(page, false); await page.goto("/"); await open(page);
  const input = page.getByTestId("command-palette").getByRole("combobox");
  await expect(input).toHaveAttribute("aria-activedescendant", "case-command-new");
  await page.keyboard.press("ArrowUp"); await expect(input).toHaveAttribute("aria-activedescendant", "case-command-tour");
  await page.keyboard.press("ArrowDown"); await expect(input).toHaveAttribute("aria-activedescendant", "case-command-new");
  await page.keyboard.press("Shift+Tab"); await expect(page.getByRole("button", { name: "Close commands", exact: true })).toBeFocused();
  await page.keyboard.press("Tab"); await expect(input).toBeFocused();
  await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/cases$/);
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
});
test("search matches aliases, announces counts and handles no results", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/overview"); await open(page);
  const input = page.getByTestId("command-palette").getByRole("combobox");
  await input.fill("report"); await expect(page.getByTestId("command-palette").getByRole("option")).toHaveCount(1);
  await expect(option(page, "report")).toHaveText(/View case report/);
  await expect(page.getByTestId("command-results-status")).toHaveText("1 matching actions");
  await input.fill("money"); await expect(option(page, "finance")).toBeVisible();
  await input.fill("nothing matches this"); await expect(page.getByTestId("command-palette").getByRole("option")).toHaveCount(0);
  await expect(input).not.toHaveAttribute("aria-activedescendant");
  await page.keyboard.press("Enter"); await expect(page.getByTestId("command-palette")).toBeVisible();
});
test("no case commands stay global and new case focuses the existing address input", async ({ page }) => {
  await seed(page, false); await page.goto("/"); await open(page);
  await expect(page.getByTestId("command-palette").getByRole("option")).toHaveCount(5);
  await expect(option(page, "report")).toHaveCount(0);
  await option(page, "new").click();
  await expect(page.locator("#commercial-address")).toBeFocused();
});
test("current case has section commands and current route context", async ({ page }, testInfo) => {
  await seed(page); await page.goto("/cases/case-a/overview"); await open(page);
  for (const id of ["overview", "market", "location", "risk", "finance", "decision-room", "report", "compare", "market-evidence"]) await expect(option(page, id)).toHaveCount(1);
  await expect(option(page, "overview")).toContainText("Current page");
  await expect(page.getByTestId("command-palette").getByRole("option").first()).toHaveAttribute("data-command-id", "risk-review");
  await page.screenshot({ path: testInfo.outputPath("palette-desktop.png") });
});
test("unconfirmed location is first; same-tab confirmation removes action live", async ({ page }) => {
  await seed(page, true, "en", true); await page.goto("/cases/case-a/overview"); await open(page);
  await expect(page.getByTestId("command-palette").getByRole("option").first()).toHaveAttribute("data-command-id", "confirm-location");
  await page.evaluate((saved) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
    window.dispatchEvent(new Event("proptech:saved-case-updated"));
  }, e9Case());
  await expect(option(page, "confirm-location")).toHaveCount(0);
  await expect(page.getByTestId("command-palette").getByRole("combobox")).toHaveAttribute("aria-activedescendant", "case-command-risk-review");
});
test("Decision Room count updates live and removes completed items", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/decision-room"); await open(page);
  const room = emptyDecisionRoom("case-a");
  room.items = Array.from({ length: 4 }, (_, i) => ({ id: String(i), kind: "task", title: "Saved task", owner: "", dueDate: "", status: "open", resolution: "" }));
  await page.evaluate((room) => {
    localStorage.setItem("proptech.decisionRoom.v1.case-a", JSON.stringify(room));
    window.dispatchEvent(new CustomEvent("proptech:decision-room-changed", { detail: "case-a" }));
  }, room);
  await expect(option(page, "decision-room")).toContainText("Handle 4 outstanding items");
  await page.evaluate(() => {
    localStorage.removeItem("proptech.decisionRoom.v1.case-a");
    window.dispatchEvent(new StorageEvent("storage", { key: "proptech.decisionRoom.v1.case-a" }));
  });
  await expect(option(page, "decision-room")).toContainText("Open Decision Room");
});
test("storage removal and corrupt cases fail closed without stale case actions", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report"); await open(page);
  await expect(option(page, "report")).toHaveCount(1);
  await page.evaluate(() => { localStorage.setItem("proptech.savedCases.v1", "{broken"); window.dispatchEvent(new StorageEvent("storage", { key: "proptech.savedCases.v1" })); });
  await expect(page.getByTestId("command-palette").getByRole("option")).toHaveCount(5);
  await expect(option(page, "report")).toHaveCount(0);
});
test("actual cross-tab saved-state changes refresh commands without reloading", async ({ page, context }) => {
  await seed(page, true, "en", true); await page.goto("/cases/case-a/overview"); await open(page);
  const other = await context.newPage(); await other.goto("/cases");
  await other.evaluate((saved) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved])), e9Case());
  await expect(option(page, "confirm-location")).toHaveCount(0);
  await other.evaluate(() => localStorage.clear());
  await expect(page.getByTestId("command-palette").getByRole("option")).toHaveCount(5); await other.close();
});
test("Create new case restores address focus when the URL already has its hash", async ({ page }) => {
  await seed(page, false); await page.goto("/#commercial-address"); await open(page);
  await option(page, "new").click(); await expect(page.locator("#commercial-address")).toBeFocused();
});
test("Create new case from an active case lands on the existing address input", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report"); await open(page);
  await option(page, "new").click(); await expect(page).toHaveURL(/\/#commercial-address$/);
  await expect(page.locator("#commercial-address")).toBeFocused();
});
test("navigation from a removed page input leaves focus on a persistent control", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/decision-room");
  await page.getByTestId("new-note-form").locator("textarea").focus(); await page.keyboard.press("Control+k");
  await option(page, "report").click(); await expect(page).toHaveURL(/\/report$/);
  await expect(page.getByTestId("new-note-form")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.activeElement !== document.body)).toBe(true);
});
for (const [id, path] of [["report", "/cases/case-a/report"], ["compare", "/compare?cases=case-a"], ["market", "/cases/case-a/market"], ["location", "/cases/case-a/location"], ["risk", "/cases/case-a/risk"], ["finance", "/cases/case-a/finance"], ["decision-room", "/cases/case-a/decision-room"], ["confirm-location", "/cases/case-a/location"]]) {
  test(`${id} navigation makes zero provider calls and preserves saved state`, async ({ page, baseURL }) => {
    await seed(page, true, "en", id === "confirm-location");
    const calls: string[] = [];
    await page.route("**/*", (route) => { if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); } return route.continue(); });
    await page.goto("/cases/case-a/decision-room");
    const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
    await open(page); await page.getByTestId("command-palette").getByRole("combobox").fill(id === "confirm-location" ? "confirm location" : id);
    await option(page, id).click(); await expect(page).toHaveURL(new RegExp(path.replace(/[?]/g, "\\?") + "(?:#.*)?$"));
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
    await expect(page.locator("main").first()).toBeVisible();
    if (id === "location") {
      await expect(page.getByTestId("show-location-map")).toBeVisible();
      await expect(page.locator(".leaflet-container")).toHaveCount(0);
    }
    if (id === "confirm-location") await expect(page.getByTestId("location-find")).toBeVisible();
    if (id === "risk") {
      await expect(page.getByTestId("show-risk-map")).toBeVisible();
      await expect(page.locator(".leaflet-container")).toHaveCount(0);
    }
    expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
    expect(calls).toEqual([]);
  });
}
test("basemaps load only after explicit action and reset when coordinates change", async ({ page }) => {
  await seed(page); await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 204 }));
  await page.goto("/cases/case-a/risk"); await expect(page.locator(".leaflet-container")).toHaveCount(0);
  await page.getByTestId("show-risk-map").click(); await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.evaluate(() => {
    const rows = JSON.parse(localStorage.getItem("proptech.savedCases.v1")!);
    rows[0].data.propertyIdentityAnchor.coordinates.latitude += 0.001;
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    window.dispatchEvent(new Event("proptech:saved-case-updated"));
  });
  await expect(page.getByTestId("show-risk-map")).toBeVisible();
  await expect(page.locator(".leaflet-container")).toHaveCount(0);
});
for (const id of ["new", "saved", "account", "tour"]) {
  test(`global ${id} opens without provider calls`, async ({ page, baseURL }) => {
    await seed(page, false);
    const calls: string[] = [];
    await page.route("**/*", (route) => { if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); } return route.continue(); });
    await page.goto("/"); await open(page); await option(page, id).click();
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
    if (id === "tour") await expect(page.locator("dialog.onboarding-dialog")).toBeVisible();
    else if (id === "new") await expect(page.locator("#commercial-address")).toBeFocused();
    else await expect(page).toHaveURL(new RegExp(`/${id === "saved" ? "cases" : "account"}$`));
    expect(calls).toEqual([]);
  });
}
for (const width of [390, 430]) {
  for (const [locale, title, report] of [["zh-TW", "案件快速操作", "查看案件報告"], ["en", "Case commands", "View case report"], ["ja", "案件コマンド", "案件レポートを表示"], ["ko", "사례 명령", "사례 보고서 보기"]]) {
    test(`${locale} at ${width}px: tap trigger, localized search, no overflow`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 844 }); await seed(page, true, locale); await page.goto("/cases/case-a/decision-room"); await open(page);
      const dialog = page.getByRole("dialog", { name: title, exact: true }); await expect(dialog).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await dialog.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
      await page.getByTestId("command-palette").getByRole("combobox").fill(report); await expect(option(page, "report")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await dialog.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
      const box = await dialog.boundingBox(); expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      await page.screenshot({ path: testInfo.outputPath(`palette-${locale}-${width}.png`) });
      await page.getByTestId("command-palette-close").click(); await expect(page.getByTestId("command-palette-trigger")).toBeFocused();
    });
  }
}
test("tour uses the existing explicit onboarding surface and restores focus", async ({ page }) => {
  await seed(page, false); await page.goto("/"); await open(page); await option(page, "tour").click();
  await expect(page.locator("dialog.onboarding-dialog")).toBeVisible();
  await page.keyboard.press("Control+k"); await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await page.keyboard.press("Escape"); await expect(page.getByTestId("command-palette-trigger")).toBeFocused();
});
