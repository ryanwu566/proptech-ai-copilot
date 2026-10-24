import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

test.beforeEach(({}, testInfo) => { test.setTimeout(Math.max(60_000, testInfo.project.timeout)); });

const CORE_KEY = "proptech.savedCases.v1";
const ROOM_KEY = "proptech.decisionRoom.v1.case-a";
async function installCases(page: Page) {
  await page.addInitScript((rows) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, [e9Case(), e9Case("case-b")]);
}
async function openRoom(page: Page) {
  await page.goto("/cases/case-a/decision-room");
  await expect(page.getByTestId("room-heading")).toBeVisible();
  await page.getByTestId("locale-switcher").selectOption("en");
}

test("room uses shared Case navigation and preserves keyboard-entered text across locales", async ({ page, baseURL }) => {
  await installCases(page);
  const calls: string[] = [], errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await openRoom(page);
  const nav = page.locator(".workspace-navigation");
  await expect(nav.getByRole("link", { name: "Property Decision Room", exact: true })).toHaveAttribute("aria-current", "page");
  const form = page.getByTestId("new-note-form");
  await form.getByLabel("Viewing observation").focus();
  await page.keyboard.type("Keep original buyer wording");
  await page.keyboard.press("Tab");
  await expect(form.getByLabel("Viewing date (optional)")).toBeFocused();
  const save = form.getByRole("button", { name: "Save", exact: true });
  // Native date inputs have multiple keyboard segments; prove Save is reachable.
  for (let tabs = 0; tabs < 6 && !(await save.evaluate((element) => element === document.activeElement)); tabs++) await page.keyboard.press("Tab");
  await expect(save).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("viewing-notes")).toContainText("Keep original buyer wording");
  for (const locale of ["ja", "ko", "zh-TW", "en"]) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByTestId("viewing-notes")).toContainText("Keep original buyer wording");
    expect(await page.locator("main").innerText()).not.toMatch(/decisionRoom\.|decision_room\./);
  }
  for (const section of ["scenarios", "market", "finance", "report", "overview"]) {
    await page.locator(`.workspace-navigation a[href="/cases/case-a/${section}"]`).click();
    await expect(page).toHaveURL(new RegExp(`/cases/case-a/${section}$`));
    await page.goto("/cases/case-a/decision-room");
    await expect(form).toBeVisible();
  }
  await page.reload();
  await expect(page.getByTestId("viewing-notes")).toContainText("Keep original buyer wording");
  expect(calls).toEqual([]);
  expect(errors).toEqual([]);
});
test("workspace entry opens a real editable room", async ({ page }) => {
  await installCases(page);
  await page.goto("/cases/case-a/overview");
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByRole("link", { name: "Property Decision Room", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/case-a\/decision-room$/);
  await expect(page.getByTestId("room-heading")).toHaveText("Property Decision Room");
  await expect(page.getByTestId("new-note-form")).toBeVisible();
});
test("records, edits, resolves and reopens manual work without touching cases or requesting providers", async ({ page, baseURL }) => {
  await installCases(page);
  const providerCalls: string[] = [];
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { providerCalls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await openRoom(page);
  const core = await page.evaluate((key) => localStorage.getItem(key), CORE_KEY);
  const note = page.getByTestId("new-note-form");
  await note.getByLabel("Viewing observation").fill("Window noise at 17:00; revisit during rush hour.");
  await note.getByLabel("Viewing date (optional)").fill("2026-10-12");
  await note.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("viewing-notes")).toContainText("Window noise at 17:00");

  for (const [kind, title] of [["checklist", "Inspect damp wall"], ["question", "Current management fee?"], ["task", "Request latest deed"]]) {
    const section = page.getByTestId(`${kind}-items`);
    await section.getByRole("button", { name: "Add", exact: true }).click();
    const form = page.getByTestId(`new-${kind}-form`);
    await form.getByLabel("Item details").fill(title);
    await form.getByLabel("Owner", { exact: true }).fill("Buyer");
    await form.getByLabel("Due date", { exact: true }).fill("2026-10-15");
    await form.getByRole("button", { name: "Save", exact: true }).click();
    await expect(section).toContainText(title);
  }
  const task = page.getByTestId("task-items");
  await task.getByRole("button", { name: "Edit", exact: true }).click();
  const edit = task.getByTestId("item-edit-form");
  await edit.getByLabel("Status", { exact: true }).selectOption("done");
  await edit.getByLabel("Resolution", { exact: true }).fill("Received copy; ownership still needs current official confirmation.");
  await edit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(task).toContainText("Completed");
  await expect(task).toContainText("Received copy");

  const price = page.getByTestId("asking-price-form");
  await price.getByLabel("Manual asking price (TWD 10,000)", { exact: true }).fill("2390");
  await price.getByLabel("Source URL (optional)").fill("https://example.com/listing");
  await price.getByLabel("Source and check note").fill("Agent's asking price on viewing day; not a transaction price.");
  await price.getByLabel("Actual checked date").fill("2026-10-12");
  await price.getByRole("button", { name: "Save", exact: true }).click();

  const checks = page.getByTestId("manual-checks");
  await checks.getByRole("button", { name: "Add", exact: true }).click();
  const check = page.getByTestId("new-check-form");
  await check.getByLabel("Check topic").fill("Management fee statement");
  await check.getByLabel("Source URL (optional)").fill("https://example.com/statement");
  await check.getByLabel("Source and check note").fill("Read supplied statement. Need a current original.");
  await check.getByLabel("Checked by").fill("Buyer");
  await check.getByLabel("Actual checked date").fill("2026-10-12");
  await check.getByLabel("Manual check outcome").selectOption("needs_follow_up");
  await check.getByRole("button", { name: "Save", exact: true }).click();
  await expect(checks).toContainText("Needs follow-up");
  await expect(page.getByTestId("saved-evidence")).toContainText("Evidence unavailable");
  await expect(page.getByTestId("activity-history")).toContainText("Manual check added");
  await expect(page.getByTestId("evidence-gaps")).toContainText("Manual check needs follow-up");
  await page.reload();
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("viewing-notes")).toContainText("Window noise at 17:00");
  await expect(page.getByTestId("asking-price-form").getByLabel("Manual asking price (TWD 10,000)", { exact: true })).toHaveValue("2390");
  await expect(page.getByTestId("task-items")).toContainText("Received copy");
  await expect(page.getByTestId("manual-checks")).toContainText("Read supplied statement");
  expect(await page.evaluate((key) => localStorage.getItem(key), CORE_KEY)).toBe(core);
  await page.goto("/cases/case-b/decision-room");
  await expect(page.getByTestId("room-heading")).toBeVisible();
  await expect(page.getByTestId("viewing-notes")).not.toContainText("Window noise");
  expect(providerCalls).toEqual([]);
  expect(errors).toEqual([]);
});

for (const width of [390, 430, 1024, 1440]) {
  for (const [locale, title] of [["zh-TW", "購屋決策室"], ["en", "Property Decision Room"], ["ja", "購入意思決定ルーム"], ["ko", "부동산 의사결정 룸"]]) {
    test(`${locale} usable at ${width}px`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      await installCases(page);
      await openRoom(page);
      await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.getByTestId("room-heading")).toHaveText(title);
      await expect(page.locator('.workspace-navigation a[href="/cases/case-a/overview"]')).toHaveText({ "zh-TW": "物件總覽", en: "Case overview", ja: "物件概要", ko: "물건 개요" }[locale]!);
      await expect(page.getByTestId("new-note-form").locator("textarea")).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      expect(overflow).toBe(false);
      const form = page.getByTestId("new-note-form");
      await form.locator("textarea").fill("User observation / 使用者觀察 / 内見メモ / 방문 메모");
      await form.getByRole("button").click();
      await expect(page.getByTestId("viewing-notes")).toContainText("User observation");
      await page.screenshot({ path: testInfo.outputPath(`decision-room-${locale}-${width}.png`), fullPage: true });
    });
  }
}
test("missing and unreadable cases do not create orphan room records", async ({ page }) => {
  await installCases(page);
  await page.goto("/cases/missing/decision-room");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("not found");
  await expect(page.getByTestId("new-note-form")).toHaveCount(0);
  await page.evaluate((key) => localStorage.setItem(key, "{bad"), CORE_KEY);
  await page.goto("/cases/case-a/decision-room");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("cannot be read");
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBeNull();
});
test("corrupt room is preserved and cannot be silently reset", async ({ page }) => {
  await installCases(page);
  await page.addInitScript((key) => localStorage.setItem(key, "{broken-room"), ROOM_KEY);
  await page.goto("/cases/case-a/decision-room");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Original data is preserved");
  await expect(page.getByTestId("new-note-form")).toHaveCount(0);
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBe("{broken-room");
});
test("quota error retains unsaved input and retry can save it", async ({ page }) => {
  await installCases(page);
  await openRoom(page);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    let failOnce = true;
    Storage.prototype.setItem = function(key, value) { if (key.startsWith("proptech.decisionRoom") && failOnce) { failOnce = false; throw new DOMException("Full", "QuotaExceededError"); } original.call(this, key, value); };
  });
  const form = page.getByTestId("new-note-form");
  await form.getByLabel("Viewing observation").fill("Keep this unsaved observation");
  await form.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("not saved");
  await expect(form.getByLabel("Viewing observation")).toHaveValue("Keep this unsaved observation");
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBeNull();
  await form.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("viewing-notes")).toContainText("Keep this unsaved observation");
  await expect(form.getByLabel("Viewing observation")).toHaveValue("");
  await expect(page.getByTestId("decision-room").getByRole("alert")).toHaveCount(0);
});

test("editing and removing records preserves actual activity; resolving requires a result", async ({ page }) => {
  await installCases(page);
  await openRoom(page);
  const note = page.getByTestId("new-note-form");
  await note.getByLabel("Viewing observation").fill("First observation");
  await note.getByRole("button", { name: "Save", exact: true }).click();
  const notes = page.getByTestId("viewing-notes");
  await notes.getByRole("button", { name: "Edit", exact: true }).click();
  const edit = notes.getByTestId("note-edit-form");
  await edit.getByLabel("Viewing observation").fill("Corrected observation");
  await edit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(notes).toContainText("Corrected observation");
  await notes.getByRole("button", { name: "Remove", exact: true }).click();
  await expect(notes).not.toContainText("Corrected observation");
  const questions = page.getByTestId("question-items");
  await questions.getByRole("button", { name: "Add", exact: true }).click();
  const question = page.getByTestId("new-question-form");
  await question.getByLabel("Item details").fill("Any outstanding fees?");
  await question.getByLabel("Status", { exact: true }).selectOption("done");
  await question.getByRole("button", { name: "Save", exact: true }).click();
  expect(await question.evaluate((form) => (form as HTMLFormElement).checkValidity())).toBe(false);
  await question.getByLabel("Resolution", { exact: true }).fill("Seller says none; request written statement.");
  await question.getByRole("button", { name: "Save", exact: true }).click();
  await expect(questions).toContainText("Completed");
  const history = page.getByTestId("activity-history");
  await expect(history).toContainText("Viewing note edited");
  await expect(history).toContainText("Viewing note removed");
  const stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), ROOM_KEY);
  expect(stored.verifications).toEqual([]);
});

test("unsafe source URLs cannot be saved as a manual check", async ({ page }) => {
  await installCases(page);
  await openRoom(page);
  await page.getByTestId("manual-checks").getByRole("button", { name: "Add", exact: true }).click();
  const check = page.getByTestId("new-check-form");
  await check.getByLabel("Check topic").fill("Title document");
  await check.getByLabel("Source URL (optional)").fill("javascript:alert(1)");
  await check.getByLabel("Source and check note").fill("User note");
  await check.getByLabel("Actual checked date").fill("2026-10-12");
  await check.getByLabel("Checked by").fill("Buyer");
  await check.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("http/https");
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBeNull();
  await expect(check.getByLabel("Source and check note")).toHaveValue("User note");
});
test("another tab cannot silently overwrite this room; reload keeps current form input", async ({ page, context }) => {
  await installCases(page);
  await openRoom(page);
  const second = await context.newPage();
  await openRoom(second);
  const firstForm = page.getByTestId("new-note-form");
  await firstForm.getByLabel("Viewing observation").fill("First tab pending observation");
  const secondForm = second.getByTestId("new-note-form");
  await secondForm.getByLabel("Viewing observation").fill("Second tab saved observation");
  await secondForm.getByRole("button", { name: "Save", exact: true }).click();
  await expect(second.getByTestId("viewing-notes")).toContainText("Second tab saved observation");
  await page.bringToFront();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  await page.getByRole("button", { name: "Load latest data", exact: true }).click();
  await expect(firstForm.getByLabel("Viewing observation")).toHaveValue("First tab pending observation");
  await firstForm.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("viewing-notes")).toContainText("Second tab saved observation");
  await expect(page.getByTestId("viewing-notes")).toContainText("First tab pending observation");
});

test("reload refreshes pristine asking price and preserves untouched newer provenance", async ({ page, context }) => {
  await installCases(page);
  await openRoom(page);
  const second = await context.newPage();
  await openRoom(second);
  const secondPrice = second.getByTestId("asking-price-form");
  await secondPrice.getByLabel("Manual asking price (TWD 10,000)", { exact: true }).fill("2390");
  await secondPrice.getByLabel("Source and check note").fill("New agent quote");
  await secondPrice.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  await page.getByRole("button", { name: "Load latest data", exact: true }).click();
  const firstPrice = page.getByTestId("asking-price-form");
  await expect(firstPrice.getByLabel("Manual asking price (TWD 10,000)", { exact: true })).toHaveValue("2390");
  await firstPrice.getByLabel("Manual asking price (TWD 10,000)", { exact: true }).fill("2350");
  await secondPrice.getByLabel("Source and check note").fill("Latest written quotation");
  await secondPrice.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  await page.getByRole("button", { name: "Load latest data", exact: true }).click();
  await expect(firstPrice.getByLabel("Manual asking price (TWD 10,000)", { exact: true })).toHaveValue("2350");
  await firstPrice.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("status")).toContainText("Saved in this browser");
  const stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), ROOM_KEY);
  expect(stored.askingPrice.priceWan).toBe(2350);
  expect(stored.askingPrice.sourceNote).toBe("Latest written quotation");
});

test("asking-price edits rebase untouched fields, reset after save and stay case isolated", async ({ page, context, baseURL }) => {
  await installCases(page);
  const providers: string[] = [];
  const watch = (tab: Page) => tab.on("request", (request) => { if (isProviderRequest(request, baseURL!)) providers.push(request.url()); });
  watch(page);
  await openRoom(page);
  await expect(page.getByTestId("asking-price-form")).toBeVisible();
  const originalCases = await page.evaluate((key) => localStorage.getItem(key), CORE_KEY);
  const second = await context.newPage(); watch(second);
  await openRoom(second);
  const form = page.getByTestId("asking-price-form"), remote = second.getByTestId("asking-price-form");
  const price = form.getByLabel("Manual asking price (TWD 10,000)", { exact: true });
  const remotePrice = remote.getByLabel("Manual asking price (TWD 10,000)", { exact: true });
  async function saveRemote() {
    await second.bringToFront();
    await remote.getByRole("button", { name: "Save", exact: true }).click();
    await expect(second.getByTestId("decision-room").getByRole("status")).toContainText("Saved in this browser");
    await page.bringToFront();
    await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  }
  async function reload() { await page.bringToFront(); await page.getByRole("button", { name: "Load latest data", exact: true }).click(); }
  async function saveLocal() {
    await page.bringToFront();
    await form.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByTestId("decision-room").getByRole("status")).toContainText("Saved in this browser");
  }
  await remotePrice.fill("2390");
  await remote.getByLabel("Source and check note").fill("Original quotation");
  await remote.getByLabel("Source URL").fill("https://example.org/quotation");
  await saveRemote(); await reload();
  await expect(price).toHaveValue("2390");
  await price.fill("2350");
  await second.bringToFront();
  await remote.getByLabel("Source and check note").fill("Latest external provenance");
  await saveRemote();
  const newerRoom = await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY);
  await form.getByRole("button", { name: "Save", exact: true }).click();
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBe(newerRoom);
  await expect(price).toHaveValue("2350");
  await reload();
  await expect(price).toHaveValue("2350");
  type PriceLockWindow = Window & { priceLockHeld?: boolean; releasePriceLock?: () => void };
  await second.bringToFront();
  const heldLock = second.evaluate(async (key) => {
    await navigator.locks.request(key, async () => {
      const win = window as PriceLockWindow;
      win.priceLockHeld = true;
      await new Promise<void>((resolve) => { win.releasePriceLock = resolve; });
    });
  }, ROOM_KEY);
  await expect.poll(() => second.evaluate(() => (window as PriceLockWindow).priceLockHeld)).toBe(true);
  await page.bringToFront();
  try {
    await form.getByRole("button", { name: "Save", exact: true }).click();
    await expect(price).toBeDisabled();
    await expect(price).toHaveValue("2350");
    const pending = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).askingPrice, ROOM_KEY);
    expect(pending.priceWan).toBe(2390);
    expect(pending.sourceNote).toBe("Latest external provenance");
  } finally {
    await second.evaluate(() => (window as PriceLockWindow).releasePriceLock?.());
    await heldLock;
  }
  await expect(page.getByTestId("decision-room").getByRole("status")).toContainText("Saved in this browser");
  await expect(form.getByLabel("Source and check note")).toHaveValue("Latest external provenance");
  const merged = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).askingPrice, ROOM_KEY);
  expect(merged).toEqual({ priceWan: 2350, sourceUrl: "https://example.org/quotation", sourceNote: "Latest external provenance", checkedDate: "" });
  await second.bringToFront();
  await second.getByRole("button", { name: "Load latest data", exact: true }).click();
  await remotePrice.fill("2450"); await remote.getByLabel("Source and check note").fill("Second external update");
  await saveRemote(); await reload();
  await expect(price).toHaveValue("2450");
  await expect(form.getByLabel("Source and check note")).toHaveValue("Second external update");
  await form.getByLabel("Source and check note").fill("Buyer-authored provenance");
  await second.bringToFront();
  await remotePrice.fill("2550"); await remote.getByLabel("Actual checked date").fill("2026-10-14");
  await saveRemote(); await reload();
  await expect(form.getByLabel("Source and check note")).toHaveValue("Buyer-authored provenance");
  await saveLocal();
  await expect(price).toHaveValue("2550");
  await expect(form.getByLabel("Actual checked date")).toHaveValue("2026-10-14");
  expect(await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).askingPrice, ROOM_KEY)).toEqual({ priceWan: 2550, sourceUrl: "https://example.org/quotation", sourceNote: "Buyer-authored provenance", checkedDate: "2026-10-14" });
  await form.getByLabel("Source and check note").fill("Unsaved case A draft");
  type NavigationWindow = Window & { priceNavigationToken?: string };
  await page.evaluate(() => { (window as NavigationWindow).priceNavigationToken = "same document"; });
  async function switchCase(caseId: string) {
    await page.locator('.commercial-global-nav a[href="/cases"]').click();
    await page.locator(`a[href="/cases/${caseId}/overview"]`).click();
    await page.locator(`.workspace-navigation a[href="/cases/${caseId}/decision-room"]`).click();
    await expect(page.getByTestId("room-heading")).toBeVisible();
    expect(await page.evaluate(() => (window as NavigationWindow).priceNavigationToken)).toBe("same document");
  }
  await switchCase("case-b");
  await expect(price).toHaveValue("");
  await expect(form.getByLabel("Source and check note")).toHaveValue("");
  await switchCase("case-a");
  await expect(price).toHaveValue("2550");
  await expect(form.getByLabel("Source and check note")).toHaveValue("Buyer-authored provenance");
  expect(await page.evaluate((key) => localStorage.getItem(key), CORE_KEY)).toBe(originalCases);
  expect(providers).toEqual([]);
});

test("case and latest-room read failures retain pending form input", async ({ page }) => {
  await installCases(page);
  await openRoom(page);
  const form = page.getByTestId("new-note-form");
  await form.getByLabel("Viewing observation").fill("Retain this observation through read failure");
  await page.evaluate((key) => {
    localStorage.setItem(key, "{bad");
    window.dispatchEvent(new StorageEvent("storage", { key }));
  }, CORE_KEY);
  await form.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("input is retained");
  await expect(form.getByLabel("Viewing observation")).toHaveValue("Retain this observation through read failure");
  await page.evaluate(({ key, rows }) => {
    localStorage.setItem(key, JSON.stringify(rows));
    window.dispatchEvent(new StorageEvent("storage", { key }));
  }, { key: CORE_KEY, rows: [e9Case()] });
  await page.evaluate((key) => {
    localStorage.setItem(key, "{bad-room");
    window.dispatchEvent(new StorageEvent("storage", { key }));
  }, ROOM_KEY);
  await page.getByRole("button", { name: "Load latest data", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Original data is preserved");
  await expect(form.getByLabel("Viewing observation")).toHaveValue("Retain this observation through read failure");
});

test("overlapping saves wait for a case lock and cannot overwrite each other", async ({ page, context }) => {
  await installCases(page);
  await openRoom(page);
  const second = await context.newPage();
  await openRoom(second);
  const firstForm = page.getByTestId("new-note-form");
  const secondForm = second.getByTestId("new-note-form");
  await page.bringToFront();
  await firstForm.getByLabel("Viewing observation").fill("First queued observation");
  await second.bringToFront();
  await secondForm.getByLabel("Viewing observation").fill("Second queued observation");
  await page.bringToFront();
  type LockWindow = Window & { lockHeld?: boolean; releaseRoomLock?: () => void };
  await page.bringToFront();
  const heldLock = page.evaluate(async (key) => {
    await navigator.locks.request(key, async () => {
      const win = window as LockWindow;
      win.lockHeld = true;
      await new Promise<void>((resolve) => { win.releaseRoomLock = resolve; });
    });
  }, ROOM_KEY);
  await expect.poll(() => page.evaluate(() => (window as LockWindow).lockHeld)).toBe(true);
  await firstForm.getByRole("button", { name: "Save", exact: true }).click();
  await second.bringToFront();
  await secondForm.getByRole("button", { name: "Save", exact: true }).click();
  await expect(firstForm.getByLabel("Viewing observation")).toBeDisabled();
  await expect(secondForm.getByLabel("Viewing observation")).toBeDisabled();
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBeNull();
  await page.bringToFront();
  await page.evaluate(() => (window as LockWindow).releaseRoomLock?.());
  await heldLock;
  await expect.poll(() => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "{}").notes?.length, ROOM_KEY)).toBe(1);
  await second.bringToFront();
  await expect(second.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  await expect(secondForm.getByLabel("Viewing observation")).toHaveValue("Second queued observation");
  await second.getByRole("button", { name: "Load latest data", exact: true }).click();
  await secondForm.getByRole("button", { name: "Save", exact: true }).click();
  await expect(second.getByTestId("viewing-notes")).toContainText("First queued observation");
  await expect(second.getByTestId("viewing-notes")).toContainText("Second queued observation");
});

test("existing task edits merge with newer fields and survive remote removal", async ({ page, context }) => {
  await installCases(page);
  await openRoom(page);
  const tasks = page.getByTestId("task-items");
  await tasks.getByRole("button", { name: "Add", exact: true }).click();
  const add = page.getByTestId("new-task-form");
  await add.getByLabel("Item details").fill("Request deed");
  await add.getByLabel("Owner", { exact: true }).fill("Buyer");
  await add.getByRole("button", { name: "Save", exact: true }).click();
  const second = await context.newPage();
  await openRoom(second);
  await page.bringToFront();
  await tasks.getByRole("button", { name: "Edit", exact: true }).click();
  const firstEdit = tasks.getByTestId("item-edit-form");
  await firstEdit.getByLabel("Owner", { exact: true }).fill("Partner");
  const secondTasks = second.getByTestId("task-items");
  await second.bringToFront();
  await secondTasks.getByRole("button", { name: "Edit", exact: true }).click();
  const secondEdit = secondTasks.getByTestId("item-edit-form");
  await secondEdit.getByLabel("Status", { exact: true }).selectOption("done");
  await secondEdit.getByLabel("Resolution", { exact: true }).fill("Received copy for further checking");
  await secondEdit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(second.getByTestId("decision-room").getByRole("status")).toContainText("Saved in this browser");
  await page.bringToFront();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  await page.getByRole("button", { name: "Load latest data", exact: true }).click();
  await expect(firstEdit.getByLabel("Owner", { exact: true })).toHaveValue("Partner");
  await firstEdit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(firstEdit).toHaveCount(0);
  let stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), ROOM_KEY);
  expect(stored.items[0]).toMatchObject({ owner: "Partner", status: "done", resolution: "Received copy for further checking" });
  await tasks.getByRole("button", { name: "Edit", exact: true }).click();
  await firstEdit.getByLabel("Owner", { exact: true }).fill("Retain after deletion");
  await second.bringToFront();
  await second.getByRole("button", { name: "Load latest data", exact: true }).click();
  await secondTasks.getByRole("button", { name: "Remove", exact: true }).click();
  await expect(second.getByTestId("decision-room").getByRole("status")).toContainText("Saved in this browser");
  await page.bringToFront();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("Another page");
  await page.getByRole("button", { name: "Load latest data", exact: true }).click();
  await expect(firstEdit.getByLabel("Owner", { exact: true })).toHaveValue("Retain after deletion");
  await firstEdit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("record was removed");
  await expect(firstEdit.getByLabel("Owner", { exact: true })).toHaveValue("Retain after deletion");
  stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), ROOM_KEY);
  expect(stored.items).toEqual([]);
});

test("case removal while save waits for a lock cannot create an orphan room", async ({ page }) => {
  await installCases(page);
  await openRoom(page);
  const form = page.getByTestId("new-note-form");
  await form.getByLabel("Viewing observation").fill("Observation survives pending case deletion");
  type LockWindow = Window & { lockHeld?: boolean; releaseRoomLock?: () => void };
  const heldLock = page.evaluate(async (key) => navigator.locks.request(key, async () => {
    const win = window as LockWindow;
    win.lockHeld = true;
    await new Promise<void>((resolve) => { win.releaseRoomLock = resolve; });
  }), ROOM_KEY);
  await expect.poll(() => page.evaluate(() => (window as LockWindow).lockHeld)).toBe(true);
  await form.getByRole("button", { name: "Save", exact: true }).click();
  await expect(form.getByLabel("Viewing observation")).toBeDisabled();
  await page.evaluate((key) => {
    localStorage.setItem(key, "[]");
    window.dispatchEvent(new StorageEvent("storage", { key }));
    (window as LockWindow).releaseRoomLock?.();
  }, CORE_KEY);
  await heldLock;
  await expect(form.getByLabel("Viewing observation")).toBeEnabled();
  await expect(page.getByTestId("decision-room").getByRole("alert")).toContainText("input is retained");
  await expect(form.getByLabel("Viewing observation")).toHaveValue("Observation survives pending case deletion");
  expect(await page.evaluate((key) => localStorage.getItem(key), ROOM_KEY)).toBeNull();
});
