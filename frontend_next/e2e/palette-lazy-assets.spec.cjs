const { test, expect } = require("@playwright/test");
const { readdirSync, readFileSync } = require("node:fs");
const path = require("node:path");
const { allowRequest, assertRouteView } = require("../../scripts/measure_route_assets.cjs");
const { e9Case } = require("../lib/workspace/e9-test-fixtures.ts");

let runtimeFiles;
let calculationFiles;
test.beforeAll(() => {
  const root = path.resolve(__dirname, "../.next/static");
  const scripts = readdirSync(root, { recursive: true }).filter((file) => file.endsWith(".js"))
    .map((file) => ({ file: `static/${file.replaceAll("\\", "/")}`, source: readFileSync(path.join(root, file), "utf8") }));
  const markers = ["case-commands-title", "Handle {{count}} outstanding items"];
  for (const marker of markers) expect(scripts.some(({ source }) => source.includes(marker)), `Missing palette runtime marker: ${marker}`).toBe(true);
  runtimeFiles = new Set(scripts.filter(({ source }) => markers.some((marker) => source.includes(marker))).map(({ file }) => file));
  calculationFiles = new Set(scripts.filter(({ source }) => source.includes("invalid loan assumptions")).map(({ file }) => file));
  expect(calculationFiles.size).toBeGreaterThan(0);
});

async function prepare(page, baseURL) {
  const requested = new Set();
  const providers = [];
  await page.addInitScript((rows) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale: "en" }));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech.my-places.v1", JSON.stringify({ version: 1, places: [{ id: "lazy-place", label: "Synthetic workplace", category: "work", address: "Synthetic destination", transportMode: "transit", weeklyTrips: 5, priority: "important", createdAt: "2026-10-13T00:00:00.000Z", updatedAt: "2026-10-13T00:00:00.000Z" }] }));
    window.paletteRoomReads = 0;
    const getItem = Storage.prototype.getItem;
    Storage.prototype.getItem = function (key) {
      if (key === "proptech.decisionRoom.v1.case-a") window.paletteRoomReads++;
      return getItem.call(this, key);
    };
  }, [e9Case("case-a"), e9Case("case-b")]);
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin === baseURL && url.pathname.startsWith("/_next/static/")) requested.add(decodeURIComponent(url.pathname).replace("/_next/", ""));
  });
  await page.route("**/*", (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== baseURL || /^\/api(?:\/|$)/.test(url.pathname)) providers.push(request.url());
    return allowRequest(request, baseURL) ? route.continue() : route.abort();
  });
  return { requested, providers, runtimeRequests: () => [...requested].filter((file) => runtimeFiles.has(file)) };
}

const coldRoutes = ["/", "/admin", "/login", "/preferences", "/places", "/cases/case-a/overview", "/cases/case-a/finance", "/compare?cases=case-a,case-b"];
for (const destination of coldRoutes) {
  test(`${destination}: cold route never requests palette runtime`, async ({ page, baseURL }) => {
    const traffic = await prepare(page, baseURL);
    await page.goto(destination, { waitUntil: "networkidle" });
    const route = destination.split("?")[0].replace("/case-a/", "/[caseId]/");
    await assertRouteView(page, route, 1280, [e9Case()]);
    await expect(page.getByTestId("command-palette-trigger")).toBeVisible();
    expect(traffic.runtimeRequests()).toEqual([]);
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
    expect(traffic.providers).toEqual([]);
  });
}

for (const intent of ["shortcut", "tap"]) {
  test(`${intent} loads runtime and opens correct current-case commands without providers`, async ({ page, baseURL }) => {
    const traffic = await prepare(page, baseURL);
    await page.goto("/cases/case-a/overview", { waitUntil: "networkidle" });
    expect(traffic.runtimeRequests()).toEqual([]);
    if (intent === "tap") await page.getByTestId("command-palette-trigger").click();
    else await page.keyboard.press("Control+k");
    await expect(page.getByTestId("command-palette")).toBeVisible();
    expect(traffic.runtimeRequests().length).toBeGreaterThan(0);
    await expect(page.locator('[data-command-id="overview"]')).toContainText("Current page");
    await expect(page.locator('[data-command-id="report"]')).toContainText("View case report");
    expect(traffic.providers).toEqual([]);
  });
}

test("Finance calculation helpers load only on Calculate and invalid assumptions never call providers", async ({ page, baseURL }) => {
  const traffic = await prepare(page, baseURL);
  await page.goto("/cases/case-a/finance", { waitUntil: "networkidle" });
  expect([...traffic.requested].filter((file) => calculationFiles.has(file))).toEqual([]);
  const form = page.getByTestId("loan-form");
  await form.getByRole("spinbutton").nth(3).fill("30");
  await page.getByTestId("calculate-loan").click();
  await expect(form.getByRole("alert")).toBeVisible();
  expect([...traffic.requested].filter((file) => calculationFiles.has(file)).length).toBeGreaterThan(0);
  expect(traffic.providers).toEqual([]);
});

test("open runtime is event-driven; closed runtime unsubscribes and reopening reads latest room state", async ({ page, baseURL }) => {
  const traffic = await prepare(page, baseURL);
  // Overview has its own live Decision Room checklist readers; isolate palette IO here.
  await page.goto("/cases/case-a/finance", { waitUntil: "networkidle" });
  expect(await page.evaluate(() => window.paletteRoomReads)).toBe(0);
  await page.clock.install();
  await page.getByTestId("command-palette-trigger").click();
  await expect(page.getByTestId("command-palette")).toBeVisible();
  const reads = await page.evaluate(() => window.paletteRoomReads);
  expect(reads).toBeGreaterThan(0);
  await page.clock.runFor(60_000);
  expect(await page.evaluate(() => window.paletteRoomReads)).toBe(reads);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  const closedReads = await page.evaluate(() => window.paletteRoomReads);
  await page.evaluate(() => {
    localStorage.setItem("proptech.decisionRoom.v1.case-a", JSON.stringify({ version: 1, caseId: "case-a", revision: 0, updatedAt: "", notes: [], items: ["open", "in_progress", "blocked"].map((status, id) => ({ id: String(id), kind: "task", title: "Saved task", owner: "", dueDate: "", status, resolution: "" })), verifications: [], askingPrice: { priceWan: null, sourceUrl: "", sourceNote: "", checkedDate: "" }, history: [] }));
    window.dispatchEvent(new CustomEvent("proptech:decision-room-changed", { detail: "case-a" }));
  });
  await page.clock.runFor(60_000);
  expect(await page.evaluate(() => window.paletteRoomReads)).toBe(closedReads);
  await page.getByTestId("command-palette-trigger").click();
  await expect(page.locator('[data-command-id="decision-room"]')).toContainText("Handle 3 outstanding items");
  expect(traffic.providers).toEqual([]);
});

async function holdRuntime(page) {
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  await page.route("**/_next/static/**/*.js", async (route) => {
    const file = decodeURIComponent(new URL(route.request().url()).pathname).replace("/_next/", "");
    if (runtimeFiles.has(file)) await held;
    await route.continue();
  });
  return () => release();
}

test("Escape cancels a pending runtime load without a late dialog or lost focus", async ({ page, baseURL }) => {
  const traffic = await prepare(page, baseURL);
  await page.goto("/", { waitUntil: "networkidle" });
  expect(traffic.runtimeRequests()).toEqual([]);
  const release = await holdRuntime(page);
  const address = page.locator("#commercial-address");
  await address.focus();
  await page.keyboard.press("Control+k");
  await expect.poll(() => traffic.runtimeRequests().length).toBeGreaterThan(0);
  await expect(page.getByTestId("command-palette-trigger")).toHaveAttribute("aria-busy", "true");
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("command-palette-trigger")).toHaveAttribute("aria-expanded", "false");
  release();
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await expect(address).toBeFocused();
  await page.keyboard.press("Control+k");
  await expect(page.getByTestId("command-palette")).toBeVisible();
  expect(await page.getByTestId("command-palette").getByRole("combobox").evaluate((input) => input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", isComposing: true, bubbles: true, cancelable: true })))).toBe(true);
  await expect(page.getByTestId("command-palette")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(address).toBeFocused();
});

test("Escape cancels opening before React commits the pending runtime state", async ({ page, baseURL }) => {
  await prepare(page, baseURL);
  await page.goto("/", { waitUntil: "networkidle" });
  const release = await holdRuntime(page);
  const address = page.locator("#commercial-address");
  await address.focus();
  try {
    await page.evaluate(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }));
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    await expect(page.getByTestId("command-palette-trigger")).toHaveAttribute("aria-expanded", "false");
  } finally { release(); }
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await expect(address).toBeFocused();
  await page.keyboard.press("Control+k");
  await expect(page.getByTestId("command-palette")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await page.evaluate(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  });
  await expect(page.getByTestId("command-palette-trigger")).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
});

test("a dialog opened during runtime loading keeps modal and focus ownership", async ({ page, baseURL }) => {
  const traffic = await prepare(page, baseURL);
  await page.goto("/", { waitUntil: "networkidle" });
  const release = await holdRuntime(page);
  await page.keyboard.press("Control+k");
  await expect.poll(() => traffic.runtimeRequests().length).toBeGreaterThan(0);
  await page.getByTestId("tour-start").click();
  const tour = page.locator("dialog.onboarding-dialog");
  await expect(tour).toBeVisible();
  release();
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("command-palette")).toHaveCount(0);
  await expect(page.getByTestId("command-palette-trigger")).toHaveAttribute("aria-expanded", "false");
  await expect(tour).toBeVisible();
  expect(await tour.evaluate((dialog) => dialog.contains(document.activeElement))).toBe(true);
});
