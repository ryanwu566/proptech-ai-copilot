import { expect, test } from "@playwright/test";
import { accountCopy } from "../lib/account-copy";

test("invalid credentials have the same bounded result for existing and unknown accounts", async ({page}) => {
  const calls: string[] = [], logs: string[] = [];
  page.on("console", message => logs.push(message.text()));
  await page.route("https://slice8-auth.supabase.co/auth/v1/**", async route => {
    const request = route.request();
    expect(request.method()).toBe("POST");
    const body = request.postDataJSON();
    expect(body.password).toBe("fixture-password");
    expect(request.url()).not.toContain("fixture-password");
    calls.push(body.email);
    await route.fulfill({status:400, headers:{"X-Supabase-API-Version":"2024-01-01","Access-Control-Expose-Headers":"X-Supabase-Api-Version"},
      json:{code:"invalid_credentials",msg:body.email.startsWith("known") ? "PRIVATE incorrect password" : "PRIVATE unknown account"}});
  });
  await page.goto("/login");
  await page.getByTestId("locale-switcher").selectOption("en");
  for (const email of ["known@example.invalid", "unknown@example.invalid"]) {
    await page.getByLabel("Email address", {exact:true}).fill(email);
    await page.getByLabel("Password", {exact:true}).fill("fixture-password");
    await page.getByRole("button", {name:"Sign in",exact:true}).click();
    await expect(page.locator('main [role="alert"]')).toHaveText(accountCopy.en.provider);
    await expect(page.getByLabel("Password", {exact:true})).toHaveValue("");
    expect(await page.locator("body").textContent()).not.toMatch(/PRIVATE|incorrect password|unknown account/);
  }
  expect(calls).toEqual(["known@example.invalid", "unknown@example.invalid"]);
  expect(logs.join(" ")).not.toMatch(/fixture-password|PRIVATE/);
});
