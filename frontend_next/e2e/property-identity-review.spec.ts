import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { buildingHypothesisBody, parcelBuildingRelationBody, parcelHypothesisBody } from "../lib/vnext-manual-identity";
import { parseBuildingHypothesis, parseManualRelation, parseParcelHypothesis } from "../lib/vnext-identity-contract";

const WORKSPACE = "11111111-1111-4111-8111-111111111111";
const PARCEL = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const BUILDING = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

test("command bodies contain only the backend's allowed fields", () => {
  expect(WORKSPACE).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  expect(parcelHypothesisBody(WORKSPACE, { county_city: "臺北市", district_township: "中正區", section: "仁愛段", subsection: null, land_number: "123-4", confirmation_id: "forged" } as never)).toEqual({
    workspace_id: WORKSPACE,
    components: { county_city: "臺北市", district_township: "中正區", section: "仁愛段", subsection: null, land_number: "123-4" },
  });
  expect(buildingHypothesisBody(WORKSPACE, { county_city: "臺北市", district_township: "中正區", section: "仁愛段", subsection_status: "specified", subsection: "一小段", building_number: "567-8", provider_id: "forged" } as never)).toEqual({
    workspace_id: WORKSPACE, identifier_kind: "cadastral_building_number",
    components: { county_city: "臺北市", district_township: "中正區", section: "仁愛段", subsection_status: "specified", subsection: "一小段", building_number: "567-8" },
  });
  expect(parcelBuildingRelationBody(WORKSPACE, PARCEL, BUILDING)).toEqual({
    workspace_id: WORKSPACE, parcel_identity_reference_id: PARCEL, building_identity_reference_id: BUILDING,
  });
  expect(() => parcelBuildingRelationBody(WORKSPACE, "invented", BUILDING)).toThrow();
  expect(() => buildingHypothesisBody(WORKSPACE, { county_city: "臺北市", district_township: "中正區", section: "仁愛段", subsection_status: "confirmed", subsection: null, building_number: "567" } as never)).toThrow();
});

test("manual responses with forged confirmation fail closed", () => {
  const base = { hypothesis: true, property_entity_id: WORKSPACE, identity_reference_id: PARCEL, relation_id: BUILDING,
    display_value: "手動地號", reference_status: "unverified", relation_status: "proposed", source_id: "user-upload", source_type: "user",
    source_environment: "production", identity_confirmation_id: null };
  expect(() => parseParcelHypothesis({ ...base, authority: "unverified_manual_hypothesis", reference_type: "parcel", relation_type: "property_parcel", relation_status: "confirmed" })).toThrow();
  expect(() => parseBuildingHypothesis({ ...base, authority: "unverified_manual_claim", identifier_kind: "cadastral_building_number", reference_type: "building", relation_type: "property_building", identity_confirmation_id: WORKSPACE })).toThrow();
  expect(() => parseManualRelation({ ...base, authority: "unverified_manual_relation", workspace_id: WORKSPACE, parcel_identity_reference_id: PARCEL,
    building_identity_reference_id: BUILDING, direction: "bidirectional", relation_type: "parcel_building", relation_status: "confirmed" })).toThrow();
});

test("new UI files contain no embedded production credentials", () => {
  const files = ["components/property-identity-review.tsx", "components/property-identity-preview.tsx", "lib/vnext-manual-identity.ts", "app/vnext/property-identity/preview/page.tsx"];
  for (const file of files) {
    const text = readFileSync(join(process.cwd(), file), "utf8");
    expect(text).not.toMatch(/sb_secret_|service_role|eyJ[A-Za-z0-9_-]{40,}/);
  }
});

test("review starts with confirmed and disputed facts, then explicitly reveals proposals", async ({ page }) => {
  const calls: string[] = [];
  page.on("request", (request) => { if (request.url().includes("/v1/")) calls.push(request.url()); });
  await page.goto("/vnext/property-identity/preview");
  await expect(page.getByRole("heading", { name: "這筆房產的地籍身分" })).toBeVisible();
  await expect(page.getByText("示範資料，非真實地籍結果")).toBeVisible();
  await expect(page.getByTestId("identity-status-summary")).toContainText("PropertyEntity");
  await expect(page.getByTestId("identity-status-summary")).toContainText("已確認關係");
  await expect(page.getByTestId("identity-status-summary")).toContainText("有爭議");
  await expect(page.getByTestId("proposed-relation")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => JSON.parse(sessionStorage.getItem("identity-preview-graph-requests") ?? "[]") as string[])).toEqual(expect.arrayContaining(["confirmed", "disputed"]));
  expect(await page.evaluate(() => sessionStorage.getItem("identity-preview-graph-requests"))).not.toContain("proposed");
  await page.getByLabel("顯示待確認關係").check();
  await expect(page.getByTestId("proposed-relation").first()).toContainText("待確認 · proposed");
  await expect(page.getByTestId("proposed-relation").first()).toContainText("非官方地籍確認");
  await expect(page.getByTestId("proposed-relation").first()).not.toContainText("已確認關係");
  expect(await page.evaluate(() => sessionStorage.getItem("identity-preview-graph-requests"))).toContain("proposed");
  expect(calls).toEqual([]);
});

test("manual parcel, cadastral building, and existing-reference relation remain proposals", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview");
  await page.getByLabel("縣市（地號）").fill("臺北市");
  await page.getByLabel("鄉鎮市區（地號）").fill("中正區");
  await page.getByLabel("段（地號）").fill("仁愛段");
  await page.getByRole("textbox", { name: "地號", exact: true }).fill("123-4");
  await page.getByTestId("submit-parcel").click();
  await expect(page.getByTestId("parcel-result")).toContainText("手動輸入 · 未驗證 · proposed · 非官方確認結果");

  await page.getByLabel("縣市（建號）").fill("臺北市");
  await page.getByLabel("鄉鎮市區（建號）").fill("中正區");
  await page.getByLabel("段（建號）").fill("仁愛段");
  await page.getByLabel("小段狀態").selectOption("specified");
  await page.getByLabel("小段（建號）").fill("一小段");
  await page.getByRole("textbox", { name: "建號", exact: true }).fill("567-8");
  await page.getByTestId("submit-building").click();
  await expect(page.getByTestId("building-result")).toContainText("地籍建號");
  await expect(page.getByTestId("building-result")).toContainText("未驗證 · proposed");
  await expect(page.getByText("地籍建號不等於實體建物、社區、戶別或刊登物件")).toBeVisible();

  await page.getByLabel("顯示待確認關係").check();
  await expect(page.getByTestId("proposed-relation").filter({ hasText: "仁愛段 123-4 地號" })).toBeVisible();
  await expect(page.getByTestId("proposed-relation").filter({ hasText: "仁愛段 567-8 建號" })).toBeVisible();
  await expect(page.getByTestId("submit-relation")).toBeDisabled();
  await page.getByLabel("既有地號參照").selectOption({ index: 1 });
  await page.getByLabel("既有建號參照").selectOption({ index: 1 });
  await page.getByTestId("submit-relation").click();
  await expect(page.getByTestId("relation-result")).toContainText("雙向 · 未驗證手動關係 · proposed · 非官方地籍確認");
  await expect(page.getByTestId("proposed-relation").filter({ hasText: "仁愛段 123 地號 ↔ 仁愛段 567 建號" })).toBeVisible();
  await expect(page.getByTestId("evidence-count")).toHaveText("3");
});

test("empty, loading, and error states are explicit", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview?state=empty");
  await expect(page.getByText("目前沒有已確認或有爭議的地籍關係")).toBeVisible();
  await expect(page.getByText("目前沒有可顯示的證據摘要")).toBeVisible();
  await page.goto("/vnext/property-identity/preview?state=error");
  await expect(page.getByRole("alert").filter({ hasText: "載入失敗" })).toContainText("載入失敗");
  await expect(page.getByRole("button", { name: "重新載入" })).toBeVisible();
  await page.goto("/vnext/property-identity/preview?state=slow");
  await expect(page.getByRole("status").filter({ hasText: "正在載入" })).toContainText("正在載入");
  await expect(page.getByTestId("identity-status-summary")).toBeVisible();
});

test("review excludes relations belonging to another property in the same graph", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview?state=shared");
  await expect(page.getByTestId("confirmed-count")).toHaveText("1");
  await expect(page.getByTestId("identity-reference-row")).toHaveCount(2);
  await expect(page.getByText("外部房產的地籍建號")).toHaveCount(0);
});

test("changing PropertyEntity clears old references and saved hypothesis", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview?state=switch");
  await page.getByLabel("縣市（地號）").fill("臺北市");
  await page.getByLabel("鄉鎮市區（地號）").fill("中正區");
  await page.getByLabel("段（地號）").fill("仁愛段");
  await page.getByRole("textbox", { name: "地號", exact: true }).fill("123-4");
  await page.getByTestId("submit-parcel").click();
  await expect(page.getByTestId("parcel-result")).toBeVisible();
  await page.getByRole("button", { name: "切換示範房產" }).click();
  await expect(page.getByTestId("identity-status-summary")).toContainText("另一個示範房產");
  await expect(page.getByTestId("identity-reference-row")).toHaveCount(0);
  await expect(page.getByTestId("parcel-result")).toHaveCount(0);
  await expect(page.getByRole("alert").filter({ hasText: "資料格式" })).toBeVisible();
});

test("failed evidence quality is shown as failed", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview?state=quality-failed");
  await expect(page.getByText("品質：檢查未通過")).toBeVisible();
});

test("unverified partner evidence is not called user provided", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview?state=source-unverified");
  await expect(page.getByText("合作來源 · 未驗證")).toBeVisible();
  await expect(page.getByText("合作來源 · 使用者提供 · 未驗證")).toHaveCount(0);
});

test("read timeout is described as a load failure", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview?state=network-error");
  await expect(page.getByRole("alert").filter({ hasText: "載入失敗" })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "送出結果" })).toHaveCount(0);
});

test("an enabled proposal filter refreshes after a manual save", async ({ page }) => {
  await page.goto("/vnext/property-identity/preview");
  await page.getByLabel("顯示待確認關係").check();
  await page.getByLabel("縣市（地號）").fill("臺北市");
  await page.getByLabel("鄉鎮市區（地號）").fill("中正區");
  await page.getByLabel("段（地號）").fill("仁愛段");
  await page.getByRole("textbox", { name: "地號", exact: true }).fill("123-4");
  await page.getByTestId("submit-parcel").click();
  await expect(page.getByTestId("proposed-relation").filter({ hasText: "仁愛段 123-4 地號" })).toBeVisible();
});
