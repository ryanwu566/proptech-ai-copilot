import { mkdir } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

const shots = path.resolve(process.cwd(), "../.local/page-help");
const TRIGGER = "page-help-trigger";
const SHEET = "page-help";

test.setTimeout(90_000);

async function seed(page: Page, locale = "zh-TW") {
  await page.addInitScript(({ rows, locale }) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, { rows: [e9Case("case-a"), e9Case("case-b")], locale });
}

function guard(page: Page, baseURL: string) {
  const calls: string[] = [];
  return page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  }).then(() => calls);
}

function watchErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  return errors;
}

/** Opens the guide from its trigger and waits for the sheet to own focus. */
async function openGuide(page: Page) {
  await page.getByTestId(TRIGGER).click();
  const sheet = page.getByTestId(SHEET);
  await expect(sheet).toBeVisible();
  await expect(sheet.getByRole("heading", { level: 2 })).toBeFocused();
  return sheet;
}

const ROUTES = [
  ["/", "home", "首頁：從一個地址開始"],
  ["/cases/case-a/location", "location", "區位與通勤"],
  ["/cases/case-a/market", "market", "價格與市場"],
  ["/cases/case-a/risk", "risk", "風險與環境"],
  ["/cases/case-a/finance", "money", "購屋資金"],
  ["/cases/case-a/overview", "overview", "物件總覽 · 看屋前簡報"],
  ["/compare?cases=case-a,case-b", "compare", "比較案件"],
  ["/cases/case-a/report", "report", "案件報告"],
] as const;

test("every decision page has a guide that opens as a labelled modal sheet and returns focus on Escape", async ({ page, baseURL }) => {
  await seed(page);
  const calls = await guard(page, baseURL!);
  const errors = watchErrors(page);
  for (const [route, topic, title] of ROUTES) {
    await page.goto(route);
    const trigger = page.getByTestId(TRIGGER);
    await expect(trigger, route).toHaveAttribute("data-help-topic", topic);
    await expect(trigger).toHaveAccessibleName("這頁怎麼看");
    await expect(trigger).toHaveAttribute("aria-haspopup", "dialog");
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    const sheet = await openGuide(page);
    await expect(trigger).toHaveAttribute("aria-expanded", "true");
    await expect(sheet).toHaveAttribute("data-help-topic", topic);
    await expect(page.getByRole("dialog", { name: title })).toBeVisible();
    // Role, what is on the page, how to read it, and where to go next.
    await expect(sheet.getByRole("heading", { level: 3 })).toHaveText(["在決策流程中的角色", "這裡可以看什麼", "怎麼讀這頁的證據", "下一步"]);
    await expect(sheet.locator("ol > li")).toHaveCount(3);
    await expect(sheet.locator("dl dt")).toHaveText(["已確認", "仍未知", "不要過度解讀"]);
    expect(await sheet.evaluate((node: HTMLDialogElement) => node.open && node.matches(":modal"))).toBe(true);
    await page.keyboard.press("Escape");
    await expect(sheet).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
  }
  expect(calls).toEqual([]);
  expect(errors).toEqual([]);
});

test("pages without a guide show no help entry", async ({ page }) => {
  await seed(page);
  for (const route of ["/privacy", "/cases", "/cases/case-a/evidence"]) {
    await page.goto(route);
    await expect(page.locator("main").first()).toBeAttached();
    await expect(page.getByTestId(TRIGGER), route).toHaveCount(0);
  }
});

test("keyboard: ? opens the guide outside text fields, the close button and backdrop close it", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/risk");
  await expect(page.getByTestId(TRIGGER)).toBeVisible();
  await page.locator("body").press("?");
  const sheet = page.getByTestId(SHEET);
  await expect(sheet).toHaveAttribute("data-help-topic", "risk");
  await expect(sheet).toContainText("未命中不等於安全");
  // Focus stays inside the modal sheet while tabbing through its controls.
  for (let index = 0; index < 5; index += 1) {
    await page.keyboard.press("Tab");
    expect(await sheet.evaluate((node) => node.contains(document.activeElement))).toBe(true);
  }
  for (let index = 0; index < 3; index += 1) {
    await page.keyboard.press("Shift+Tab");
    expect(await sheet.evaluate((node) => node.contains(document.activeElement))).toBe(true);
  }
  await sheet.getByTestId("page-help-close").click();
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId(TRIGGER)).toBeFocused();
  // Backdrop click closes too.
  await openGuide(page);
  const viewport = page.viewportSize()!;
  await page.mouse.click(20, viewport.height / 2);
  await expect(sheet).toHaveCount(0);
  // Typing "?" into a field never opens the guide.
  await page.goto("/");
  const address = page.locator("#commercial-address");
  await address.fill("");
  await address.press("?");
  await expect(address).toHaveValue("?");
  await expect(sheet).toHaveCount(0);
});

test("next steps move in-app without running anything; Home's step focuses the address field", async ({ page, baseURL }) => {
  await seed(page);
  const calls = await guard(page, baseURL!);
  await page.goto("/cases/case-a/market");
  let sheet = await openGuide(page);
  await expect(sheet.getByTestId("page-help-next")).toHaveText(["區位與通勤→"]);
  await page.evaluate(() => { (window as unknown as { __sameDocument: boolean }).__sameDocument = true; });
  await sheet.getByTestId("page-help-next").click();
  await expect(page).toHaveURL(/\/cases\/case-a\/location$/);
  await expect(sheet).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as { __sameDocument?: boolean }).__sameDocument)).toBe(true);
  await expect(page.getByTestId(TRIGGER)).toHaveAttribute("data-help-topic", "location");
  await page.goto("/");
  sheet = await openGuide(page);
  await sheet.getByTestId("page-help-next").click();
  await expect(sheet).toHaveCount(0);
  await expect(page.locator("#commercial-address")).toBeFocused();
  expect(calls).toEqual([]);
});

test("the guide and the command palette never stack", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/overview");
  const sheet = await openGuide(page);
  await page.keyboard.press("Control+k");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(sheet).toHaveCount(0);
  await page.getByTestId("command-palette-trigger").click();
  await expect(page.getByTestId("command-palette")).toBeVisible();
  await page.keyboard.press("?");
  await expect(sheet).toHaveCount(0);
});

test("the guide follows the selected language", async ({ page }) => {
  await seed(page, "en");
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId(TRIGGER)).toHaveAccessibleName("Page guide");
  const sheet = await openGuide(page);
  await expect(page.getByRole("dialog", { name: "Compare cases" })).toBeVisible();
  await expect(sheet).toContainText("Nothing here picks a winner");
  await expect(sheet.getByTestId("page-help-next")).toHaveCount(0);
});

for (const [width, height] of [[390, 844], [1440, 900]] as const) {
  test(`${width}px: trigger sits clear of quick actions and the sheet fits without page scroll`, async ({ page }) => {
    await seed(page);
    await page.setViewportSize({ width, height });
    await page.goto("/cases/case-a/overview");
    const help = (await page.getByTestId(TRIGGER).boundingBox())!;
    const quick = (await page.getByTestId("command-palette-trigger").boundingBox())!;
    expect(help.width).toBeGreaterThanOrEqual(44);
    expect(help.height).toBeGreaterThanOrEqual(44);
    expect(help.y + help.height).toBeLessThanOrEqual(quick.y - 4);
    expect(help.x + help.width).toBeLessThanOrEqual(width - 12);
    const sheet = await openGuide(page);
    await sheet.evaluate((node) => Promise.all(node.getAnimations({ subtree: true }).map((animation) => animation.finished)));
    const box = (await sheet.boundingBox())!;
    if (width < 600) {
      expect(box.x).toBe(0);
      expect(box.width).toBe(width);
      expect(Math.round(box.y + box.height)).toBe(height);
      expect(box.height).toBeLessThanOrEqual(height * 0.87);
    } else {
      expect(box.x + box.width).toBeLessThanOrEqual(width - 12);
      expect(box.width).toBeLessThanOrEqual(420);
      expect(box.y).toBeGreaterThanOrEqual(12);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await mkdir(shots, { recursive: true });
    await page.screenshot({ path: path.join(shots, `guide-${width}.png`) });
  });
}

test("opening motion is opt-in, finite and compositor-only; reduced motion opens still", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/overview");
  let sheet = await openGuide(page);
  const timing = await sheet.evaluate((node) => node.getAnimations({ subtree: true }).map((animation) => {
    const computed = animation.effect!.getComputedTiming();
    const frames = (animation.effect as KeyframeEffect).getKeyframes().flatMap((frame) => Object.keys(frame)).filter((key) => !["offset", "computedOffset", "easing", "composite"].includes(key));
    return { end: Number(computed.endTime), iterations: computed.iterations, frames };
  }));
  expect(timing.length).toBeGreaterThan(0);
  for (const item of timing) {
    expect(item.iterations).toBe(1);
    expect(item.end).toBeLessThanOrEqual(600);
    for (const property of item.frames) expect(["opacity", "transform"]).toContain(property);
  }
  await page.keyboard.press("Escape");
  await page.emulateMedia({ reducedMotion: "reduce" });
  sheet = await openGuide(page);
  expect(await sheet.evaluate((node) => node.getAnimations({ subtree: true }).length)).toBe(0);
});

test("print hides the help entry", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId(TRIGGER)).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(page.getByTestId(TRIGGER)).toBeHidden();
});
