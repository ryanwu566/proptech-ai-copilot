import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

const CASES = "proptech.savedCases.v1";
const A = "proptech-demo-a";
const ROOM_A = `proptech.decisionRoom.v1.${A}`;
const ROOM_B = "proptech.decisionRoom.v1.proptech-demo-b";
const FAIL = "demo-fail-room-write";

async function prepare(page: Page, baseURL: string) {
  const real = e9Case("real-storage-case");
  await page.addInitScript(({ real, cases, room, fail }) => {
    if (!sessionStorage.getItem("demo-storage-seeded")) {
      sessionStorage.setItem("demo-storage-seeded", "1");
      localStorage.setItem(cases, JSON.stringify([real]));
      localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale: "en" }));
      localStorage.setItem("proptech_onboarding_seen", "true");
      localStorage.setItem("proptech_onboarding_version", "2");
    }
    const write = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (this === localStorage && key === room && sessionStorage.getItem(fail) === "1") throw new DOMException("Storage full", "QuotaExceededError");
      return write.call(this, key, value);
    };
  }, { real, cases: CASES, room: ROOM_A, fail: FAIL });
  const calls: string[] = [];
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  return { real, calls };
}

test("a failed room write is reported and another install fills missing rooms without replacing existing rooms or real cases", async ({ page, baseURL }) => {
  const { real, calls } = await prepare(page, baseURL!);
  await page.goto("/");
  await page.evaluate((key) => sessionStorage.setItem(key, "1"), FAIL);
  await page.getByTestId("complete-example-start").click();
  await expect(page.getByTestId("complete-example-error")).toContainText("could not be fully saved");
  await expect(page).toHaveURL(/\/$/);
  await page.evaluate(({ fail, room }) => {
    sessionStorage.removeItem(fail);
    // A present sidecar, even one the reader cannot use, must never be overwritten by ensure.
    localStorage.setItem(room, "viewer-kept-room");
  }, { fail: FAIL, room: ROOM_B });
  await page.getByTestId("complete-example-start").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
  const saved = await page.evaluate(({ cases, roomA, roomB }) => ({ rows: JSON.parse(localStorage.getItem(cases)!), room: JSON.parse(localStorage.getItem(roomA)!), kept: localStorage.getItem(roomB) }), { cases: CASES, roomA: ROOM_A, roomB: ROOM_B });
  expect(saved.rows.map((row: { id: string }) => row.id).sort()).toEqual([A, "proptech-demo-b", real.id].sort());
  expect(saved.rows.find((row: { id: string }) => row.id === real.id)).toEqual(real);
  expect(saved.room.items).toHaveLength(6);
  expect(saved.kept).toBe("viewer-kept-room");
  expect(calls).toEqual([]);
});

test("restore reports a room write failure and succeeds only after its retry restores the room", async ({ page, baseURL }) => {
  const { real, calls } = await prepare(page, baseURL!);
  await page.goto("/");
  await page.getByTestId("complete-example-start").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
  await page.evaluate(({ room, fail }) => {
    const value = JSON.parse(localStorage.getItem(room)!);
    value.items[0].title = "Viewer edited action";
    localStorage.setItem(room, JSON.stringify(value));
    sessionStorage.setItem(fail, "1");
  }, { room: ROOM_A, fail: FAIL });
  await page.getByTestId("demo-restore").click();
  await expect(page.getByTestId("demo-restore-status")).toContainText("could not be restored");
  expect(await page.evaluate((room) => JSON.parse(localStorage.getItem(room)!).items[0].title, ROOM_A)).toBe("Viewer edited action");
  await page.evaluate((fail) => sessionStorage.removeItem(fail), FAIL);
  await page.getByTestId("demo-restore").click();
  await expect(page.getByTestId("demo-restore-status")).toContainText("were restored");
  expect(await page.evaluate((room) => JSON.parse(localStorage.getItem(room)!).items[0].title, ROOM_A)).not.toBe("Viewer edited action");
  expect(await page.evaluate(({ cases, id }) => JSON.parse(localStorage.getItem(cases)!).find((row: { id: string }) => row.id === id), { cases: CASES, id: real.id })).toEqual(real);
  expect(calls).toEqual([]);
});
