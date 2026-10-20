import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

// Decision Room → Report closure: buyer actions flow from the saved room into the report
// with no provider call, no duplicate evidence-linked action and no change to the 3-page core.
test.beforeEach(({}, testInfo) => { test.setTimeout(Math.max(90_000, testInfo.project.timeout)); });

const CASES = "proptech.savedCases.v1";
const ROOM = "proptech.decisionRoom.v1.case-a";
const AT = "2026-10-19T08:00:00.000Z";
type Row = Record<string, string>;
const row = (id: string, kind: string, title: string, status: string, extra: Row = {}): Row => ({ id, kind, title, owner: "買方", dueDate: "", status, resolution: status === "done" ? "已取得書面確認" : "", origin: "manual", sourceKey: "", note: "", createdAt: AT, updatedAt: AT, ...extra });
function room(items: Row[]) {
  return { version: 1, caseId: "case-a", revision: 3, updatedAt: AT, notes: [], items, verifications: [], askingPrice: { priceWan: null, sourceUrl: "", sourceNote: "", checkedDate: "" }, history: [{ id: "h1", at: AT, kind: "verification_added", subject: "淹水潛勢" }] };
}
const BASIC = [
  row("v-flood", "verification", "淹水潛勢", "open", { origin: "risk", sourceKey: "risk-flood", note: "向管委會確認地下室歷史淹水紀錄", owner: "管委會", dueDate: "2026-11-01" }),
  row("t-blocked", "task", "取得最新謄本", "blocked", { owner: "代書" }),
  row("q-fee", "question", "管理費是否含車位？", "open", { owner: "仲介" }),
  row("t-other", "task", "安排第二次看屋", "in_progress"),
  row("v-done", "verification", "確認產權面積", "done", { origin: "identity", sourceKey: "property-area" }),
];
const long = (n: number) => `向管委會、仲介與代書逐項確認第 ${n} 項文件、公共設施與歷史修繕紀錄並保留書面資料`;
const HEAVY = [...BASIC, ...Array.from({ length: 6 }, (_, i) => row(`m${i}`, i % 2 ? "question" : "task", long(i), i === 0 ? "blocked" : "open", { owner: "Management committee representative", dueDate: "2026-11-15", note: long(i) })), row("d2", "task", "比對實價登錄", "done"), row("d3", "question", "車位是否獨立權狀", "done"), row("d4", "task", "確認貸款成數", "done")];

async function seed(page: Page, { locale = "en", items }: { locale?: string; items?: Row[] } = {}) {
  await page.addInitScript(({ cases, key, roomKey, roomValue, locale }) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(cases));
    if (roomValue && !localStorage.getItem(roomKey)) localStorage.setItem(roomKey, JSON.stringify(roomValue));
    if (!localStorage.getItem("proptech.locale.v1")) localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, { cases: [e9Case(), e9Case("case-b")], key: CASES, roomKey: ROOM, roomValue: items ? room(items) : null, locale });
}
async function watch(page: Page, baseURL: string) {
  const calls: string[] = []; const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  return { calls, errors };
}
const storedItems = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "{\"items\":[]}").items as Row[], ROOM);
const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);

test("manual verification → owner → status → evidence action → reopen → report projection, with zero provider calls", async ({ page, baseURL }) => {
  await seed(page); const { calls, errors } = await watch(page, baseURL!);
  await page.goto("/cases/case-a/decision-room");
  await expect(page.getByTestId("room-readiness")).toHaveText(/No Decision Room actions recorded yet/);
  const verification = page.getByTestId("verification-items");
  await verification.getByRole("button", { name: "Add", exact: true }).click();
  const form = page.getByTestId("new-verification-form");
  await form.getByLabel("Item details").fill("Confirm basement flood history with management");
  await form.getByLabel("Owner", { exact: true }).fill("Buyer");
  await form.getByLabel("Due date", { exact: true }).fill("2026-11-01");
  await form.getByRole("button", { name: "Save", exact: true }).click();
  const manual = verification.getByTestId("room-action").filter({ hasText: "Confirm basement flood history" });
  await expect(manual).toHaveAttribute("data-origin", "manual");
  await expect(manual).toContainText("From: Manual");
  await expect(manual).toContainText("Owner: Buyer");
  await expect(page.getByTestId("room-readiness")).toHaveText("1 action(s) still open before an offer, 1 of them verification.");

  await manual.getByRole("button", { name: "Edit", exact: true }).click();
  const edit = verification.getByTestId("item-edit-form");
  await edit.getByLabel("Status", { exact: true }).selectOption("blocked");
  await edit.getByLabel("Owner", { exact: true }).fill("Partner");
  await edit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(manual).toHaveAttribute("data-status", "blocked");
  await expect(manual).toContainText("Owner: Partner");
  await expect(page.getByTestId("room-count-open")).toContainText("of which blocked 1");
  await expect(page.getByTestId("room-readiness")).toHaveText("1 action(s) still open before an offer, 1 of them verification.");

  // Saved-evidence check → verification action, keyed by its evidence ID; the button disappears once added.
  const first = page.getByTestId("evidence-actions").locator('li[data-testid^="evidence-action-risk-"]').filter({ has: page.getByRole("button") }).first();
  const key = (await first.getAttribute("data-testid"))!.replace("evidence-action-", "");
  const candidate = page.getByTestId(`evidence-action-${key}`);
  await candidate.getByRole("button", { name: "Add to Decision Room" }).click();
  await expect(candidate.getByTestId("evidence-action-in-room")).toHaveText("In Decision Room · Open");
  await expect(candidate.getByRole("button")).toHaveCount(0);
  const linked = verification.locator(`[data-source-key="${key}"]`);
  await expect(linked).toHaveAttribute("data-origin", "risk");
  await expect(linked).toContainText("From: Risk · Linked to saved evidence");
  expect((await storedItems(page)).filter((item) => item.sourceKey === key)).toHaveLength(1);

  // Persistence: refresh, route change, Home → reopen.
  await page.reload();
  await expect(verification.getByTestId("room-action")).toHaveCount(2);
  await page.goto("/");
  await page.goto("/cases/case-a/decision-room");
  await expect(verification.locator(`[data-source-key="${key}"]`)).toBeVisible();
  await expect(verification.getByTestId("room-action").filter({ hasText: "Confirm basement" })).toHaveAttribute("data-status", "blocked");

  // Report projection.
  await page.locator('.workspace-navigation a[href="/cases/case-a/report"]').click();
  await expect(page).toHaveURL(/\/report$/);
  const readiness = page.getByTestId("executive-room-readiness");
  await expect(readiness).toHaveAttribute("data-outstanding", "2");
  await expect(readiness).toContainText("2 action(s) still open before an offer, 2 of them verification.");
  await expect(readiness).toContainText("Open 1 · In progress 0 · Blocked 1 · Completed 0");
  const rows = page.getByTestId("core-room-action");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toHaveAttribute("data-origin", "risk");
  await expect(rows.nth(1)).toContainText("Confirm basement flood history");
  await expect(rows.nth(1)).toContainText("Owner: Partner · Status: Blocked");
  await expect(rows.nth(1)).toContainText("From: Manual");
  await expect(page.getByTestId("report-core-page-2").locator(`[data-testid="core-room-ref"][data-source-key="${key}"]`)).toHaveCount(1);
  await expect(page.getByTestId("report-room-appendix").getByTestId("appendix-room-action")).toHaveCount(2);

  // Report → back to Decision Room; completing the linked action stops it counting.
  await page.getByTestId("report-open-room").click();
  await expect(page).toHaveURL(/\/decision-room$/);
  await linked.getByRole("button", { name: "Edit", exact: true }).click();
  const done = verification.getByTestId("item-edit-form");
  await done.getByLabel("Status", { exact: true }).selectOption("done");
  await done.getByLabel("Resolution", { exact: true }).fill("Official map checked with the agent");
  await done.getByRole("button", { name: "Save", exact: true }).click();
  await expect(linked).toHaveAttribute("data-status", "done");
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("executive-room-readiness")).toHaveAttribute("data-outstanding", "1");
  await expect(page.getByTestId("core-room-action")).toHaveCount(1);
  await expect(page.getByTestId("core-room-completed")).toContainText("Completed (1)");
  expect(calls).toEqual([]);
  expect(errors).toEqual([]);
});

test("Overview CTA adds a saved-evidence action once; repeat clicks and reopen never duplicate", async ({ page, baseURL }) => {
  await seed(page); const { calls } = await watch(page, baseURL!);
  await page.goto("/cases/case-a/overview");
  const cta = page.getByTestId("add-to-room").first();
  const key = (await cta.getAttribute("data-source-key"))!;
  await cta.getByRole("button", { name: "Add to Decision Room" }).click();
  const existing = page.locator(`[data-testid="add-to-room-existing"][data-source-key="${key}"]`);
  await expect(existing).toHaveText("In Decision Room · Open");
  await page.reload();
  await expect(existing).toBeVisible();
  await expect(page.locator(`[data-testid="add-to-room"][data-source-key="${key}"]`)).toHaveCount(0);
  expect((await storedItems(page)).filter((item) => item.sourceKey === key)).toHaveLength(1);
  await existing.click();
  await expect(page).toHaveURL(/\/decision-room#verification-items$/);
  await expect(page.getByTestId(`evidence-action-${key}`).getByTestId("evidence-action-in-room")).toBeVisible();
  // Opening pages creates nothing by itself.
  for (const path of ["report", "decision-room", "overview"]) await page.goto(`/cases/case-a/${path}`);
  expect(await storedItems(page)).toHaveLength(1);
  expect(calls).toEqual([]);
});

const LOCALE_TEXT: Record<string, { readiness: string; page3: string; room: string; status: string; manual: string }> = {
  "zh-TW": { readiness: "出價前仍有 4 項待處理事項，其中 1 項待查證。", page3: "出價前待辦", room: "前往決策室", status: "受阻", manual: "手動新增" },
  en: { readiness: "4 action(s) still open before an offer, 1 of them verification.", page3: "Before an offer", room: "Open Decision Room", status: "Blocked", manual: "Manual" },
  ja: { readiness: "申込前に未完了のアクションが 4 件あり、うち確認事項は 1 件です。", page3: "申込前の対応事項", room: "意思決定ルームを開く", status: "ブロック中", manual: "手動追加" },
  ko: { readiness: "제안 전 미완료 작업이 4건 남아 있으며, 그중 확인 작업은 1건입니다.", page3: "제안 전 할 일", room: "의사결정 룸 열기", status: "막힘", manual: "수동 추가" },
};
for (const [locale, text] of Object.entries(LOCALE_TEXT)) {
  test(`report and room reproduce saved action state in ${locale}`, async ({ page, baseURL }) => {
    await seed(page, { locale, items: BASIC }); const { calls } = await watch(page, baseURL!);
    await page.goto("/cases/case-a/report");
    await expect(page.getByTestId("executive-room-readiness")).toContainText(text.readiness);
    const close = page.getByTestId("core-room-actions");
    await expect(close.getByRole("heading", { level: 3 })).toHaveText(text.page3);
    await expect(page.getByTestId("report-open-room")).toHaveText(text.room);
    await expect(page.getByTestId("core-room-action")).toHaveText([/淹水潛勢/, /取得最新謄本/, /管理費是否含車位/, /安排第二次看屋/]);
    await expect(page.getByTestId("core-room-action").nth(1)).toContainText(text.status);
    await expect(page.getByTestId("core-room-action").nth(2)).toContainText(text.manual);
    await expect(page.getByTestId("core-room-completed")).toContainText("確認產權面積");
    // Unresolved flood evidence points at its action on page two; manual work never links to evidence.
    const ref = page.getByTestId("report-core-page-2").locator('[data-testid="core-room-ref"][data-source-key="risk-flood"]');
    await expect(ref).toContainText("淹水潛勢");
    await expect(ref).toContainText("管委會");
    if (locale !== "zh-TW") for (const zh of ["出價前待辦", "決策室行動狀態", "負責人", "待處理", "受阻", "手動新增", "下一步"]) await expect(close).not.toContainText(zh);
    await page.goto("/cases/case-a/decision-room");
    await expect(page.getByTestId("room-action-summary")).toHaveAttribute("data-readiness", "outstanding");
    await expect(page.getByTestId("room-readiness")).toHaveText(text.readiness);
    expect(calls).toEqual([]);
  });
}

for (const [width, height] of [[390, 844], [430, 932]]) {
  test(`${width}px Decision Room and report stay readable without horizontal overflow`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    for (const locale of ["zh-TW", "en", "ja", "ko"]) {
      await page.addInitScript((locale) => localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale })), locale);
      await seed(page, { locale, items: HEAVY });
      await page.goto("/cases/case-a/decision-room");
      await expect(page.getByTestId("room-action-summary")).toBeVisible();
      const action = page.getByTestId("room-action").first();
      await expect(action).toBeVisible();
      expect((await action.boundingBox())!.width, `${locale} action row is not microscopic`).toBeGreaterThan(width * 0.7);
      expect(await noOverflow(page), `${locale} room`).toBe(true);
      await page.goto("/cases/case-a/report");
      await expect(page.getByTestId("core-room-actions")).toBeVisible();
      expect(await noOverflow(page), `${locale} report`).toBe(true);
    }
  });
}

/** Chromium writes one uncompressed `/Type /Page` dictionary per physical sheet. */
const sheets = (pdf: Buffer) => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;
async function only(page: Page, hidden: string[]) {
  await page.evaluate((selectors) => {
    document.getElementById("core-measure")?.remove();
    const style = document.createElement("style"); style.id = "core-measure";
    style.textContent = selectors.map((selector) => `${selector} { display: none !important; }`).join("\n");
    document.head.append(style);
  }, hidden);
}
for (const locale of ["zh-TW", "en", "ja", "ko"]) {
  test(`A4 core stays three pages with a full Decision Room and prints action rows (${locale})`, async ({ page, baseURL }) => {
    await seed(page, { locale, items: HEAVY }); const { calls } = await watch(page, baseURL!);
    await page.goto("/cases/case-a/report");
    await expect(page.getByTestId("core-room-actions")).toBeVisible();
    await expect(page.getByTestId("core-room-action")).toHaveCount(4);
    await expect(page.getByTestId("core-room-more")).toBeVisible();
    await page.emulateMedia({ media: "print" });
    // Browser-only controls never print; owner, status and action text do.
    await expect(page.getByTestId("core-room-actions").getByRole("link")).toBeHidden();
    await expect(page.getByTestId("report-controls")).toBeHidden();
    for (const testId of ["executive-room-readiness", "core-room-actions", "report-room-appendix"]) await expect(page.getByTestId(testId)).toBeVisible();
    const printed = await page.getByTestId("core-room-actions").innerText();
    expect(printed).toContain("Management committee representative");
    expect(printed).toContain("淹水潛勢");
    for (const box of await page.getByTestId("core-room-action").evaluateAll((nodes) => nodes.map((node) => ({ scroll: node.scrollWidth, client: node.clientWidth })))) expect(box.scroll, "row is not clipped").toBeLessThanOrEqual(box.client + 1);
    const PAGE2 = '[data-testid="report-core-page-2"]', PAGE3 = '[data-testid="report-core-page-3"]', APPENDIX = '[data-testid="report-appendix"]', REFS = '[data-testid="report-citation-references"]';
    const pdf = () => page.pdf({ preferCSSPageSize: true, printBackground: true });
    const total = sheets(await pdf());
    await only(page, [PAGE2, PAGE3, APPENDIX, REFS]); const one = sheets(await pdf());
    await only(page, [PAGE3, APPENDIX, REFS]); const two = sheets(await pdf());
    await only(page, [APPENDIX, REFS]); const three = sheets(await pdf());
    expect([one, two, three], "cumulative core pages: no core page spills").toEqual([1, 2, 3]);
    expect(total).toBeGreaterThan(3);
    expect(calls).toEqual([]);
  });
}
