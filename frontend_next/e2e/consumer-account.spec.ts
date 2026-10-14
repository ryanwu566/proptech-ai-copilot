import { expect, test, type Page } from "@playwright/test";
import { accountCopy } from "../lib/account-copy";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

const AUTH = "https://slice8-auth.supabase.co";
const API = "http://e2e.test";
const USER = "11111111-1111-4111-8111-111111111111";
const KEY = "proptech.savedCases.v1";
function token(payload: Record<string, unknown> = {}) {
  const p = (v: object) => Buffer.from(JSON.stringify(v)).toString("base64url");
  return `${p({alg:"ES256",kid:"fixture"})}.${p({sub:USER,aud:"authenticated",role:"authenticated",iss:`${AUTH}/auth/v1`,exp:4102444800,...payload})}.synthetic`;
}
function session(access_token = token()) {
  return {access_token,refresh_token:"synthetic-refresh",token_type:"bearer",expires_in:3600,expires_at:4102444800,
    user:{id:USER,email:"person@example.invalid",aud:"authenticated",role:"authenticated",app_metadata:{},user_metadata:{},created_at:"2026-10-13T00:00:00Z"}};
}
async function seed(page: Page, accessToken = token()) {
  await page.addInitScript(value => localStorage.setItem("sb-slice8-auth-auth-token",JSON.stringify(value)), session(accessToken));
}
async function provider(page: Page, options: {signup?: "authenticated" | "confirmation" | "duplicate"; status?: "active" | "suspended"; backendStatus?: number} = {}) {
  const calls: string[] = [];
  await page.route(`${AUTH}/auth/v1/**`, route => {
    const r=route.request(); calls.push(new URL(r.url()).pathname);
    if (r.url().includes("/signup")) {
      if (options.signup === "duplicate") return route.fulfill({status:422,headers:{"X-Supabase-API-Version":"2024-01-01", "Access-Control-Expose-Headers":"X-Supabase-Api-Version"},json:{code:"user_already_exists",msg:"RAW PROVIDER SECRET"}});
      return route.fulfill({json:options.signup === "authenticated" ? session() : {id:USER,email:"person@example.invalid",identities:[]}});
    }
    if (r.url().includes("/token")) return route.fulfill({json:session()});
    if (r.url().includes("/user")) return route.fulfill({json:session().user});
    return route.fulfill({status:200,json:{}});
  });
  await page.route(`${API}/v1/**`, route => {
    calls.push(new URL(route.request().url()).pathname);
    expect(route.request().headers().authorization).toBe(`Bearer ${token()}`);
    if (options.backendStatus) return route.fulfill({status:options.backendStatus,json:{error:{code:"authentication_required",message:"RAW BACKEND SECRET"}}});
    return route.fulfill({json:{user_id:USER,status:options.status??"active",platform_role:"consumer",created_at:"2026-10-13T00:00:00Z",updated_at:"2026-10-13T00:00:00Z"}});
  });
  return calls;
}

for (const locale of ["zh-TW","en","ja","ko"] as const) for (const width of [390,430,1024,1440]) {
  test(`${locale} ${width}: three consumer routes are localized, accessible and bounded`, async ({page},info) => {
    const calls = await provider(page); await page.setViewportSize({width,height:900});
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    for (const route of ["login","signup","account"] as const) {
      if (route === "account") await page.evaluate(value => localStorage.setItem("sb-slice8-auth-auth-token", JSON.stringify(value)), session());
      await page.goto(`/${route}`); await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.getByRole("heading",{level:1,name:accountCopy[locale][route]})).toBeVisible();
      await expect(page.getByText(accountCopy[locale].localNote)).toBeVisible();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
      if (route !== "account") {
        const email=page.getByLabel(accountCopy[locale].email,{exact:true}); await email.focus();
        await expect(email).toBeFocused(); expect(await email.evaluate(el=>getComputedStyle(el).outlineStyle)).not.toBe("none");
        await expect(page.getByLabel(accountCopy[locale].password,{exact:true})).toHaveAttribute("type","password");
        await page.keyboard.press("Tab");
        await expect(page.getByLabel(accountCopy[locale].password,{exact:true})).toBeFocused();
      } else {
        await expect(page.getByTestId("account-status")).toHaveText(accountCopy[locale].active);
        await expect(page.getByText("person@example.invalid", {exact:true})).toBeVisible();
      }
      await page.screenshot({path:info.outputPath(`${route}-${locale}-${width}.png`),fullPage:true});
    }
    expect(calls.every(path => path === "/v1/account")).toBe(true);
    expect(errors).toEqual([]);
  });
}
test("login, restore and logout preserve browser Saved Cases and expose no credentials",async({page})=>{
  const saved=JSON.stringify([e9Case()]);
  const stores = Object.fromEntries([KEY, "proptech.preferenceProfile.v1", "proptech.scenarios.v1", "proptech.decisionRoom.v1.case-a", "proptech.my-places.v1", "proptech.case-commute.v1"]
    .map(key => [key, key === KEY ? saved : `opaque-browser-owned-${key}`]));
  await page.addInitScript(stores => { for (const [key, value] of Object.entries(stores)) if (localStorage.getItem(key) === null) localStorage.setItem(key, value); }, stores);
  const logs:string[]=[]; page.on("console",message=>logs.push(message.text()));
  const calls=await provider(page); await page.goto("/login?next=https://attacker.invalid");
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByLabel("Email address",{exact:true}).fill("person@example.invalid");
  await page.getByLabel("Password",{exact:true}).fill("valid-password");
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page).toHaveURL(/\/account$/); await expect(page.getByTestId("account-status")).toHaveText("Active");
  await page.reload(); await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("account-status")).toHaveText("Active");
  expect(await page.evaluate(key=>localStorage.getItem(key),KEY)).toBe(saved);
  expect(await page.evaluate(keys => Object.fromEntries(keys.map(key => [key,localStorage.getItem(key)])), Object.keys(stores))).toEqual(stores);
  expect(calls.every(p=>["/auth/v1/token","/auth/v1/user","/v1/account"].includes(p))).toBe(true);
  await page.getByRole("button",{name:"Sign out of this device"}).click();
  await expect(page.getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem("sb-slice8-auth-auth-token"))).toBeNull();
  expect(await page.evaluate(key=>localStorage.getItem(key),KEY)).toBe(saved);
  expect(await page.evaluate(keys => Object.fromEntries(keys.map(key => [key,localStorage.getItem(key)])), Object.keys(stores))).toEqual(stores);
  expect(logs.join(" ")).not.toMatch(/valid-password|synthetic-refresh|RAW|synthetic/);
  expect(await page.locator("body").textContent()).not.toContain(token());
});
for (const state of ["confirmation","duplicate","authenticated"] as const) {
  test(`signup ${state} has honest public outcomes`,async({page})=>{
    await provider(page,{signup:state}); await page.goto("/signup"); await page.getByTestId("locale-switcher").selectOption("en");
    await page.getByLabel("Email address",{exact:true}).fill("person@example.invalid");
    await page.getByLabel("Password",{exact:true}).fill("valid-password");
    await page.getByRole("button",{name:"Create account",exact:true}).click();
    if(state==="authenticated") { await expect(page).toHaveURL(/\/account$/); await expect(page.getByTestId("account-status")).toHaveText("Active"); }
    else await expect(page.getByRole("status")).toContainText(accountCopy.en.accepted);
    expect(await page.locator("body").textContent()).not.toContain("RAW PROVIDER SECRET");
    expect(page.url()).not.toContain("valid-password");
  });
}
test("invalid signup and reset requests validate before contacting provider",async({page})=>{
  const calls=await provider(page); await page.goto("/signup"); await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByRole("button",{name:"Create account",exact:true}).click();
  await expect(page.locator('main [role="alert"]')).toHaveText(accountCopy.en.validation); expect(calls).toHaveLength(0);
  await page.goto("/login"); await page.getByTestId("locale-switcher").selectOption("en");
  await page.getByRole("button",{name:"Request password reset"}).click();
  await expect(page.locator('main [role="alert"]')).toHaveText(accountCopy.en.resetValidation);
  await page.getByLabel("Email address",{exact:true}).fill("person@example.invalid");
  await page.getByRole("button",{name:"Request password reset"}).click();
  await expect(page.getByRole("status")).toContainText(accountCopy.en.resetAccepted);
});
test("suspension is shown with bounded account status",async({page})=>{
  await seed(page); await provider(page,{status:"suspended"}); await page.goto("/account");
  await page.getByTestId("locale-switcher").selectOption("en"); await expect(page.getByTestId("account-status")).toHaveText("Suspended");
  await expect(page.getByText(accountCopy.en.suspensionNote)).toBeVisible();
});
test("backend 401 expires session once without exposing raw errors",async({page})=>{
  await seed(page); const calls=await provider(page,{backendStatus:401}); await page.goto("/account");
  await page.getByTestId("locale-switcher").selectOption("en"); await expect(page.getByText(accountCopy.en.expired)).toBeVisible();
  expect(calls.filter(p=>p==="/v1/account")).toHaveLength(1);
  expect(await page.locator("body").textContent()).not.toContain("RAW BACKEND SECRET");
});
test("malformed stored token never reaches protected API",async({page})=>{
  await seed(page,"malformed.token.value"); const calls=await provider(page); await page.goto("/account");
  await page.getByTestId("locale-switcher").selectOption("en"); await expect(page.getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
  expect(calls).not.toContain("/v1/account");
});
for (const action of ["signup", "login", "reset"] as const) {
  test(`stalled ${action} returns to a usable bounded error state`, async ({page}) => {
    await provider(page);
    await page.route(`${AUTH}/auth/v1/**`, () => { /* Intentionally never completes; transport must abort. */ });
    await page.goto(action === "signup" ? "/signup" : "/login");
    await page.getByTestId("locale-switcher").selectOption("en");
    await page.getByLabel("Email address", {exact:true}).fill("person@example.invalid");
    if (action !== "reset") await page.getByLabel("Password", {exact:true}).fill("valid-password");
    const name = action === "signup" ? "Create account" : action === "login" ? "Sign in" : "Request password reset";
    await page.getByRole("button", {name, exact:true}).click();
    await expect(page.locator('main [role="alert"]')).toHaveText(accountCopy.en.provider, {timeout:20_000});
    await expect(page.getByRole("button", {name, exact:true})).toBeEnabled();
  });
}
