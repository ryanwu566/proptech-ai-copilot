import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

// Complete example: one Home click installs two local demo snapshots and opens the real workspace.
// Every route reads saved evidence only; any provider/API request is recorded and aborted.
test.beforeEach(({}, testInfo) => { test.setTimeout(Math.max(120_000, testInfo.project.timeout)); });

const KEY = "proptech.savedCases.v1";
const A = "proptech-demo-a";
const B = "proptech-demo-b";
const ROOM_A = `proptech.decisionRoom.v1.${A}`;
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const CTA = { "zh-TW": "查看完整範例案件", en: "View complete example cases", ja: "完全な事例を見る", ko: "전체 예시 사례 보기" } as const;
const NOTICE = { "zh-TW": "示範案件", en: "Demo case", ja: "デモ案件", ko: "예시 사례" } as const;
const FORBIDDEN = /winner|recommended|ranking|best buy|最佳|勝出|較安全|值得買|推薦購買/i;
type Locale = keyof typeof CTA;

async function seed(page: Page, { locale = "zh-TW", rows = [] as unknown[] }: { locale?: Locale; rows?: unknown[] } = {}) {
  await page.addInitScript(({ key, rows, locale }) => {
    if (sessionStorage.getItem("demo-seeded")) return;
    sessionStorage.setItem("demo-seeded", "1");
    if (rows.length) localStorage.setItem(key, JSON.stringify(rows)); else localStorage.removeItem(key);
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
  }, { key: KEY, rows, locale });
}
/** Basemap tiles follow existing map rules; every other provider/API request is a failure. */
async function watch(page: Page, baseURL: string) {
  const state = { recording: false, calls: [] as string[] };
  await page.route("**/*", async (route) => {
    const request = route.request(); const url = new URL(request.url());
    if (BASEMAP.test(url.hostname)) return route.fulfill({ contentType: "image/png", body: PNG });
    if (isProviderRequest(request, baseURL)) { if (state.recording) state.calls.push(`${request.method()} ${url.origin}${url.pathname}`); return route.abort(); }
    return route.continue();
  });
  return state;
}
const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "[]") as Array<{ id: string; title: string }>, KEY);
const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
async function openExample(page: Page, locale: Locale = "zh-TW") {
  await page.goto("/");
  const cta = page.getByTestId("complete-example-start");
  await expect(cta).toHaveText(CTA[locale]);
  await cta.click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
}

test("one click installs Demo A/B, opens the real Overview, and every surface is populated with zero provider calls", async ({ page, baseURL }) => {
  const real = [e9Case("real-1"), e9Case("real-2")];
  await seed(page, { rows: real });
  const watcher = await watch(page, baseURL!);
  await page.goto("/");
  await expect(page.getByTestId("complete-example-start")).toBeVisible();
  watcher.recording = true;
  await page.getByTestId("complete-example-start").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));

  // Installed beside, never over, the viewer's own cases.
  const rows = await stored(page);
  expect(rows.map((row) => row.id)).toEqual([A, B, "real-1", "real-2"]);
  expect(await page.evaluate(({ key }) => JSON.parse(localStorage.getItem(key)!).slice(2), { key: KEY })).toEqual(real);

  // Overview: actual production shell, disclosure, pulse.
  await expect(page.getByRole("heading", { level: 1, name: "物件總覽", exact: true })).toBeVisible();
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("新北市板橋區文化路一段");
  const notice = page.getByTestId("demo-case-notice");
  await expect(notice).toContainText("示範案件");
  await expect(page.getByTestId("demo-snapshot-disclosure")).toContainText("2026-10-01");
  await expect(page.getByTestId("demo-snapshot-disclosure")).toContainText("不是即時查詢");
  await expect(notice).toContainText("未命中不代表安全");
  const pulse = page.getByTestId("case-pulse");
  await expect(pulse.getByRole("link")).toHaveCount(5);
  await expect(pulse).not.toContainText(/%|score|分數/);

  await page.goto(`/cases/${A}/market`);
  await expect(page.getByRole("heading", { level: 1, name: "價格與市場", exact: true })).toBeVisible();
  await expect(page.locator("main")).toContainText("內政部不動產實價登錄");
  await expect(page.locator("main")).toContainText("53.6");

  await page.goto(`/cases/${A}/location`);
  await expect(page.getByRole("heading", { level: 1, name: "區位與通勤", exact: true })).toBeVisible();
  await expect(page.getByTestId("nearby-facilities")).toContainText("社區國小");
  await expect(page.locator("main")).toContainText("臺北車站");

  await page.goto(`/cases/${A}/risk`);
  await expect(page.getByRole("heading", { level: 1, name: "風險與環境", exact: true })).toBeVisible();
  await expect(page.locator("main")).toContainText("淹水");
  await expect(page.locator("main")).toContainText("液化");

  await page.goto(`/cases/${A}/finance`);
  await expect(page.locator("main")).toContainText("50,929");
  await expect(page.locator("main")).toContainText("修繕準備");

  await page.goto(`/cases/${A}/decision-room`);
  await expect(page.getByTestId("demo-case-notice")).toBeVisible();
  await expect(page.getByTestId("room-action")).toHaveCount(6);
  await expect(page.getByTestId("room-readiness")).toContainText("5");
  await expect(page.locator(`[data-source-key="risk-flood"]`).first()).toHaveAttribute("data-origin", "risk");
  await expect(page.getByTestId("room-action").filter({ hasText: "取得最新建物與土地登記謄本" })).toHaveAttribute("data-status", "blocked");

  await page.goto(`/cases/${A}/report`);
  await expect(page.getByTestId("executive-room-readiness")).toHaveAttribute("data-outstanding", "5");
  for (const id of ["report-executive", "report-core-page-2", "report-core-page-3", "report-appendix", "report-room-appendix"]) await expect(page.getByTestId(id)).toBeVisible();
  // Page 3 shows the first four outstanding actions; the appendix keeps every action.
  await expect(page.getByTestId("core-room-action")).toHaveCount(4);
  expect(await page.getByTestId("report-room-appendix").getByTestId("appendix-room-action").count()).toBeGreaterThanOrEqual(5);
  await expect(page.getByTestId("core-room-completed")).toContainText("記錄開價來源與日期");
  await expect(page.getByTestId("report-core-page-2").locator('[data-testid="core-room-ref"][data-source-key="risk-flood"]')).toHaveCount(1);
  await expect(page.locator("main")).not.toContainText(FORBIDDEN);

  await page.goto(`/cases/${B}/overview`);
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("臺北市文山區木柵路三段");

  // Compare A+B straight from the disclosure link.
  await page.getByTestId("demo-compare").click();
  await expect(page).toHaveURL(new RegExp(`/compare\\?cases=${A},${B}$`));
  const brief = page.getByTestId("compare-difference-brief");
  await expect(brief).toBeVisible();
  await expect(brief.getByTestId("brief-price")).toContainText("300");
  await expect(brief.getByTestId("brief-risk")).toContainText("未命中不代表零風險");
  await expect(brief.getByTestId("brief-money")).toBeVisible();
  await expect(brief.getByTestId("brief-verification")).toBeVisible();
  await expect(brief).not.toContainText(FORBIDDEN);
  await expect(page.getByTestId("demo-case-notice")).toBeVisible();
  await expect(page.getByTestId("compare-desktop")).toBeVisible();

  // Saved cases list shows both demos alongside real cases.
  await page.goto("/cases");
  await expect(page.locator("main")).toContainText("示範案件 A｜板橋電梯大樓");
  await expect(page.locator("main")).toContainText("示範案件 B｜木柵公寓");
  expect(watcher.calls).toEqual([]);
});

test("repeat clicks never duplicate, viewer edits survive, restore resets only demo rows, and reopen stays provider-free", async ({ page, baseURL }) => {
  await seed(page, { rows: [e9Case("real-1")] });
  const watcher = await watch(page, baseURL!);
  watcher.recording = true;
  await openExample(page);
  await page.evaluate(({ key, A }) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows.find((row: { id: string }) => row.id === A).title = "我改過的示範";
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, A });
  for (let i = 0; i < 2; i++) await openExample(page);
  let rows = await stored(page);
  expect(rows.map((row) => row.id).sort()).toEqual([A, B, "real-1"].sort());
  expect(rows.find((row) => row.id === A)!.title).toBe("我改過的示範");
  const real = await page.evaluate((key) => JSON.stringify(JSON.parse(localStorage.getItem(key)!).find((row: { id: string }) => row.id === "real-1")), KEY);

  await page.getByTestId("demo-restore").click();
  await expect(page.getByTestId("demo-restore-status")).toContainText("其他案件未變更");
  rows = await stored(page);
  expect(rows.find((row) => row.id === A)!.title).toBe("示範案件 A｜板橋電梯大樓");
  expect(rows).toHaveLength(3);
  expect(await page.evaluate((key) => JSON.stringify(JSON.parse(localStorage.getItem(key)!).find((row: { id: string }) => row.id === "real-1")), KEY)).toBe(real);

  // Deleting a demo and clicking again reinstalls it once, with its seeded room.
  await page.evaluate(({ key, A, room }) => {
    localStorage.setItem(key, JSON.stringify(JSON.parse(localStorage.getItem(key)!).filter((row: { id: string }) => row.id !== A)));
    localStorage.removeItem(room);
  }, { key: KEY, A, room: ROOM_A });
  await openExample(page);
  expect((await stored(page)).filter((row) => row.id === A)).toHaveLength(1);
  expect(await page.evaluate((room) => JSON.parse(localStorage.getItem(room)!).items.length, ROOM_A)).toBe(6);

  // Reopen after reload, Report and Compare: still zero provider calls.
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "物件總覽", exact: true })).toBeVisible();
  await page.goto(`/cases/${A}/report`);
  await expect(page.getByTestId("report-executive")).toBeVisible();
  await page.goto(`/compare?cases=${A},${B}`);
  await expect(page.getByTestId("compare-difference-brief")).toBeVisible();
  expect(watcher.calls).toEqual([]);
});

test("a nearly full browser gets a truthful bounded message and nothing is evicted", async ({ page, baseURL }) => {
  const full = Array.from({ length: 9 }, (_, i) => e9Case(`real-${i}`));
  await seed(page, { rows: full });
  const watcher = await watch(page, baseURL!);
  await page.goto("/");
  const before = await page.evaluate((key) => localStorage.getItem(key), KEY);
  watcher.recording = true;
  await page.getByTestId("complete-example-start").click();
  await expect(page.getByTestId("complete-example-error")).toContainText("10 件上限");
  await expect(page.getByTestId("home-complete-example").getByRole("link", { name: "管理已儲存案件" })).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe(before);
  expect(watcher.calls).toEqual([]);
});

test("Command Palette works on Demo A without demo-only commands", async ({ page, baseURL }) => {
  await seed(page, { locale: "en" });
  const watcher = await watch(page, baseURL!);
  watcher.recording = true;
  await openExample(page, "en");
  await page.getByTestId("command-palette-trigger").click();
  const palette = page.getByTestId("command-palette");
  await expect(palette).toBeVisible();
  // Existing case commands only: no command is demo-specific.
  const ids = await palette.getByRole("option").evaluateAll((options) => options.map((option) => option.getAttribute("data-command-id") ?? ""));
  expect(ids.length).toBeGreaterThan(5);
  expect(ids.filter((id) => /demo|example/i.test(id))).toEqual([]);
  await palette.getByRole("combobox").fill("report");
  await expect(palette.getByRole("option")).toHaveCount(1);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/report$`));
  await expect(page.getByTestId("executive-room-readiness")).toHaveAttribute("data-outstanding", "5");
  expect(watcher.calls).toEqual([]);
});

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430]) {
  test(`${locale} at ${width}px: CTA is obvious, demo disclosure is localized and no page overflows`, async ({ page, baseURL }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page, { locale });
    const watcher = await watch(page, baseURL!);
    await page.goto("/");
    const cta = page.getByTestId("complete-example-start");
    await expect(cta).toBeVisible();
    const box = (await cta.boundingBox())!;
    expect(box.width).toBeGreaterThan(width * 0.8);
    expect(box.height).toBeGreaterThanOrEqual(44);
    expect(box.y).toBeLessThan(900);
    expect(await noOverflow(page)).toBe(true);
    watcher.recording = true;
    await openExample(page, locale);
    const notice = page.getByTestId("demo-case-notice");
    await expect(notice).toContainText(NOTICE[locale]);
    await expect(notice).toContainText("2026-10-01");
    await expect(notice).not.toContainText(/proptech-demo|fixture|e9/i);
    if (locale !== "zh-TW") await expect(page.getByTestId("demo-snapshot-disclosure")).not.toContainText("示範快照");
    expect(await noOverflow(page), `${locale} overview`).toBe(true);
    for (const path of [`/cases/${A}/decision-room`, `/cases/${A}/report`, `/compare?cases=${A},${B}`]) {
      await page.goto(path);
      await expect(page.getByTestId("demo-case-notice")).toBeVisible();
      expect(await noOverflow(page), `${locale} ${path}`).toBe(true);
    }
    expect(watcher.calls).toEqual([]);
  });
}
