import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { homeStartCopy } from "../lib/home-start-copy";
import { overviewViewCopy } from "../lib/workspace/overview-presentation";
import { workspaceNavigationCopy } from "../lib/workspace/workspace-navigation-copy";
import { isProviderRequest } from "./helpers/provider-request";

const A = "proptech-demo-a", B = "proptech-demo-b";
const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);

for (const width of [390, 430]) for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
  test(`${locale} compressed home, Brief and tools at ${width}px with reduced motion`, async ({ page, baseURL }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    const row = e9Case();
    row.data = { inputs: row.data.inputs };
    await page.addInitScript(({ row, locale }) => {
      localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row]));
      localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
      localStorage.setItem("proptech_onboarding_seen", "true");
    }, { row, locale });
    const calls: string[] = [];
    await page.route("**/*", (route) => {
      if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
      return route.continue();
    });
    await page.goto("/");
    const hero = page.locator(".commercial-home__start");
    await expect(hero.locator(".ds-button")).toHaveCount(2);
    await expect(page.getByTestId("home-case-journey")).toHaveText(homeStartCopy[locale].journey);
    const resume = hero.getByRole("link", { name: homeStartCopy[locale].resume, exact: true });
    await expect(resume).toHaveAttribute("href", "/cases");
    await expect(resume).not.toHaveClass(/ds-button/);
    await expect(page.getByTestId("complete-example-start")).toBeInViewport();
    expect(await noOverflow(page)).toBe(true);

    await page.goto("/cases/case-a/overview");
    const brief = page.getByTestId("commercial-overview-workspace");
    await expect(brief).toContainText(overviewViewCopy[locale].eyebrow.split(" · ")[0]);
    await expect(brief.getByRole("heading", { name: overviewViewCopy[locale].unknown, exact: true })).toBeVisible();
    await expect(brief).toContainText(overviewViewCopy[locale].fresh_not_started);
    const tools = page.getByTestId("workspace-tools");
    await expect(tools).not.toHaveAttribute("open", "");
    await expect(tools.getByRole("link")).toHaveCount(0);
    const nav = page.locator(".workspace-navigation");
    await expect(nav.getByRole("link")).toHaveCount(7);
    await expect(nav.getByRole("link", { name: workspaceNavigationCopy[locale].compare, exact: true })).toHaveAttribute("href", "/compare?cases=case-a");
    await tools.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(tools.getByRole("link")).toHaveCount(4);
    await tools.getByRole("link", { name: workspaceNavigationCopy[locale].decisionRoom, exact: true }).click();
    await expect(page).toHaveURL(/case-a\/decision-room$/);
    await expect(page.getByTestId("workspace-tools")).toHaveAttribute("open", "");
    await expect(nav.locator("[aria-current='page']")).toHaveText(workspaceNavigationCopy[locale].decisionRoom);
    await expect(nav.locator("[aria-current='page']")).toHaveAttribute("data-pulse-state", /.+/);
    await expect(nav.locator("[aria-current='page']")).toBeInViewport({ ratio: 0.9 });
    await expect(page.getByTestId("room-action-summary")).toBeVisible();
    for (const [details, content] of [["room-evidence-details", "saved-evidence"], ["room-history-details", "activity-history"]]) {
      await expect(page.getByTestId(content)).toBeHidden();
      await page.getByTestId(details).locator("summary").click();
      await expect(page.getByTestId(content)).toBeVisible();
    }
    expect(await noOverflow(page)).toBe(true);
    expect(await page.locator("[data-case-route-content]").evaluate((node) => getComputedStyle(node).animationName)).toBe("none");
    expect(calls).toEqual([]);
  });
}

test("complete demo uses the Auto Brief showcase → Brief → A/B comparison → three-page Report journey", async ({ page, baseURL }) => {
  const calls: string[] = [];
  await page.addInitScript(() => localStorage.setItem("proptech_onboarding_seen", "true"));
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await page.goto("/");
  await page.getByTestId("complete-example-start").click();
  // The showcase opens on Demo A Location; its timing is owned by auto-brief-showcase.spec.ts, so skip only the presentation.
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/location$`));
  const stage = page.getByTestId("auto-brief-stage");
  await expect(stage).toHaveAttribute("data-showcase", "on");
  await page.getByTestId("auto-brief-skip").click();
  await expect(stage).toHaveAttribute("data-scene", "complete");
  await page.getByTestId("auto-brief-view-brief").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
  await expect(page.getByTestId("commercial-overview-workspace")).toContainText("看屋前簡報");
  await expect(page.getByTestId("demo-compare")).toHaveCount(1);
  await page.getByTestId("demo-compare").click();
  await expect(page).toHaveURL(new RegExp(`/compare\\?cases=${A},${B}$`));
  await expect(page.getByTestId("compare-report-handoff").getByRole("link")).toHaveCount(2);
  await page.getByTestId("compare-report-handoff").getByRole("link").first().click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/report$`));
  for (const id of ["report-executive", "report-core-page-2", "report-core-page-3"]) await expect(page.getByTestId(id)).toBeVisible();
  expect(calls).toEqual([]);
});

test("saved-evidence deep link reveals the existing Decision Room disclosure", async ({ page }) => {
  await page.addInitScript((row) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), e9Case());
  await page.goto("/cases/case-a/decision-room#saved-evidence");
  await expect(page.getByTestId("room-evidence-details")).toHaveAttribute("open", "");
  await expect(page.getByTestId("saved-evidence")).toBeVisible();
  await expect(page.getByTestId("saved-evidence")).toBeInViewport();
  await expect(page.getByTestId("room-history-details")).not.toHaveAttribute("open", "");
});

test("saved evidence footer follows Market → Location → Risk → Money → Brief → Compare", async ({ page, baseURL }) => {
  await page.addInitScript((row) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), e9Case());
  const calls: string[] = [];
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await page.goto("/cases/case-a/market");
  for (const section of ["location", "risk", "finance", "overview"]) {
    const primary = page.getByTestId("case-workflow-handoff").getByRole("link").first();
    await expect(primary).toHaveAttribute("href", `/cases/case-a/${section}`);
    await primary.click();
    await expect(page).toHaveURL(new RegExp(`/cases/case-a/${section}$`));
  }
  await page.getByTestId("case-workflow-handoff").getByRole("link").first().click();
  await expect(page).toHaveURL(/\/compare\?cases=case-a$/);
  expect(calls).toEqual([]);
});
