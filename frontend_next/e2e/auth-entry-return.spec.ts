import { expect, test, type Page } from "@playwright/test";
import { accountCopy } from "../lib/account-copy";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

const AUTH = "https://slice8-auth.supabase.co";
const USER = "11111111-1111-4111-8111-111111111111";
const KEY = "proptech.savedCases.v1";
function session(exp = 4102444800) {
  const p = (v: object) => Buffer.from(JSON.stringify(v)).toString("base64url");
  return { access_token: `${p({alg:"ES256",kid:"fixture"})}.${p({sub:USER,aud:"authenticated",role:"authenticated",iss:`${AUTH}/auth/v1`,exp})}.synthetic`, refresh_token:"synthetic-refresh", token_type:"bearer", expires_in:3600, expires_at:exp,
    user:{id:USER,email:"person@example.invalid",aud:"authenticated",role:"authenticated",app_metadata:{},user_metadata:{},created_at:"2026-10-13T00:00:00Z"} };
}
async function setup(page: Page, outcome = "authenticated") {
  const calls: string[] = [];
  await page.addInitScript(({key, saved}) => { if (!localStorage.getItem("proptech.locale.v1")) localStorage.setItem("proptech.locale.v1", JSON.stringify({version:1,locale:"en"})); if (!localStorage.getItem(key)) localStorage.setItem(key, saved); }, {key:KEY,saved:JSON.stringify([e9Case()])});
  await page.route(`${AUTH}/auth/v1/**`, route => {
    const path = new URL(route.request().url()).pathname;
    calls.push(path);
    if (path.endsWith("/signup") && outcome === "request_accepted") return route.fulfill({status:422,headers:{"X-Supabase-API-Version":"2024-01-01","Access-Control-Expose-Headers":"X-Supabase-API-Version"},json:{code:"user_already_exists",msg:"private"}});
    return route.fulfill({json: path.endsWith("/signup") && outcome === "confirmation_required" ? {id:USER,email:"person@example.invalid",identities:[]} : path.endsWith("/user") ? session().user : session()});
  });
  await page.route("http://e2e.test/v1/**", route => {
    calls.push(new URL(route.request().url()).pathname);
    return route.fulfill({json:{user_id:USER,status:"active",platform_role:"consumer",created_at:"2026-10-13T00:00:00Z",updated_at:"2026-10-13T00:00:00Z"}});
  });
  return calls;
}
async function english(page: Page) {
  // Home retains its existing locale controls; other pages expose the header switcher.
  await page.getByTestId("locale-switcher").first().selectOption("en");
}
async function submit(page: Page, mode: "login" | "signup") {
  await page.getByLabel("Email address",{exact:true}).fill("person@example.invalid");
  await page.getByLabel("Password",{exact:true}).fill("valid-password");
  await page.getByRole("button",{name:mode === "login" ? "Sign in" : "Create account",exact:true}).click();
}

test("anonymous cold routes do not download the provider SDK; login still loads it", async ({page}) => {
  await setup(page);
  // Match the route-budget definition: measure the current route, excluding
  // Next's speculative RSC prefetch of other routes (such as /cases Cloud UI).
  await page.route("**/*", route => {
    const headers = route.request().headers();
    return headers["next-router-prefetch"] || headers.purpose === "prefetch" || headers["sec-purpose"]?.includes("prefetch")
      ? route.abort() : route.fallback();
  });
  const scripts: Promise<boolean>[] = [];
  page.on("response", response => {
    if (response.url().includes("/_next/static/") && new URL(response.url()).pathname.endsWith(".js")) {
      scripts.push(response.text().then(source => source.includes("AuthRetryableFetchError")));
    }
  });
  for (const path of ["/", "/cases/case-a/finance", "/compare", "/places", "/preferences"]) {
    await page.goto(path);
    await expect(page.getByTestId("auth-entry-actions").getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
    await expect(page.getByTestId("auth-entry-actions").getByRole("link",{name:"Create account",exact:true})).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect((await Promise.all(scripts)).some(Boolean), path).toBe(false);
  }
  // A positive control prevents a renamed/minified SDK marker from hiding a regression.
  await page.goto("/login");
  await expect(page.getByLabel("Email address",{exact:true})).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect((await Promise.all(scripts)).some(Boolean)).toBe(true);
});

test("sign in and sign out in another tab update an SDK-free anonymous header", async ({page,context}) => {
  await setup(page); await page.goto("/cases");
  const group = page.getByTestId("auth-entry-actions");
  await expect(group.getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
  const account = await context.newPage(); await setup(account);
  await account.goto("/login"); await submit(account,"login");
  await expect(account).toHaveURL(/\/account$/);
  await expect(group.getByRole("link",{name:"Account",exact:true})).toBeVisible();
  await account.getByRole("button",{name:"Sign out of this device",exact:true}).click();
  await expect(group.getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
  await expect(account.getByTestId("auth-entry-actions").getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
});

for (const locale of ["zh-TW","en","ja","ko"] as const) for (const width of [390,430]) {
  test(`${locale} ${width}: Home and header expose keyboard accessible localized auth`, async ({page}, info) => {
    const calls = await setup(page);
    await page.setViewportSize({width,height:900});
    for (const path of ["/", "/cases"]) {
      await page.goto(path);
      const group = page.getByTestId("auth-entry-actions");
      // Wait for session/locale restoration before changing the server-rendered select.
      await expect(group.getByRole("link",{name:accountCopy[path === "/" ? "en" : locale].login,exact:true})).toBeVisible();
      await page.getByTestId("locale-switcher").first().selectOption(locale);
      const login = group.getByRole("link",{name:accountCopy[locale].login,exact:true});
      const signup = group.getByRole("link",{name:accountCopy[locale].signup,exact:true});
      await expect(login).toBeVisible(); await expect(signup).toBeVisible();
      await expect(signup).toHaveAttribute("href", `/signup?next=${encodeURIComponent(path)}`);
      await login.focus(); await expect(login).toBeFocused();
      await page.keyboard.press("Tab"); await expect(signup).toBeFocused();
      expect(await signup.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe("none");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const header = page.locator(".commercial-global-header");
      await expect(header).toHaveCount(1);
      await expect(header.getByTestId("auth-entry-actions")).toHaveCount(1);
      await expect(page.getByTestId("locale-switcher")).toHaveCount(1);
      await page.screenshot({path:info.outputPath(`${path === "/" ? "home" : "header"}-${locale}-${width}.png`)});
      await login.click();
      await expect(page.locator("main").getByRole("link",{name:accountCopy[locale].backToJourney})).toHaveAttribute("href",path);
    }
    expect(calls).toEqual([]);
  });
}
test("restored session shows Account without account profile requests", async ({page}) => {
  const calls = await setup(page);
  await page.addInitScript(value => localStorage.setItem("sb-slice8-auth-auth-token",JSON.stringify(value)),session());
  for (const path of ["/", "/compare"]) {
    await page.goto(path); await english(page);
    const group = page.getByTestId("auth-entry-actions");
    await expect(group.getByRole("link",{name:"Account",exact:true})).toBeVisible();
    await expect(group.getByRole("link",{name:"Create account",exact:true})).toHaveCount(0);
  }
  expect(calls).toEqual([]);
});
test("pending session restoration stays neutral until refresh settles", async ({page}) => {
  await setup(page);
  await page.addInitScript(value => localStorage.setItem("sb-slice8-auth-auth-token",JSON.stringify(value)),session(Math.floor(Date.now()/1000) - 60));
  let release!: () => void;
  let started!: () => void;
  const ready = new Promise<void>(resolve => { started = resolve; });
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route(`${AUTH}/auth/v1/token**`, async route => { started(); await gate; await route.fulfill({json:session()}); });
  await page.goto("/cases");
  await ready;
  try {
    const group = page.getByTestId("auth-entry-actions");
    await expect(group).toContainText(accountCopy.en.working);
    await expect(group.getByRole("link",{name:"Sign in",exact:true})).toHaveCount(0);
    await expect(group.getByRole("link",{name:"Create account",exact:true})).toHaveCount(0);
  } finally { release(); }
  await expect(page.getByTestId("auth-entry-actions").getByRole("link",{name:"Account",exact:true})).toBeVisible();
});
test("expired session login retains the Finance case", async ({page}) => {
  await setup(page);
  await page.addInitScript(value => { if (!localStorage.getItem("expired-fixture-seeded")) { localStorage.setItem("sb-slice8-auth-auth-token",JSON.stringify(value)); localStorage.setItem("expired-fixture-seeded","yes"); } },session(Math.floor(Date.now()/1000) - 60));
  await page.route(`${AUTH}/auth/v1/token**`, route => new URL(route.request().url()).searchParams.get("grant_type") === "refresh_token"
    ? route.fulfill({status:400,json:{code:"refresh_token_not_found",msg:"expired"}}) : route.fulfill({json:session()}));
  await page.goto("/cases/case-a/finance"); await english(page);
  await page.getByTestId("auth-entry-actions").getByRole("link",{name:"Sign in",exact:true}).click();
  await submit(page,"login"); await expect(page).toHaveURL(/\/cases\/case-a\/finance$/);
});
for (const section of ["risk", "evidence"]) test(`login from ${section} returns to the same local case without upload`, async ({page}) => {
  const calls = await setup(page);
  const destination = `/cases/case-a/${section}`;
  await page.goto(destination); await english(page);
  // Risk's opt-in map entry proves case restoration without requesting map assets.
  if (section === "risk") await expect(page.getByTestId("show-risk-map")).toBeVisible();
  const saved = await page.evaluate(key => localStorage.getItem(key), KEY);
  await page.getByTestId("auth-entry-actions").getByRole("link",{name:"Sign in",exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`/login\\?next=${encodeURIComponent(destination)}$`));
  await expect(page.locator("main").getByRole("link",{name:"Back to where you left off"})).toHaveAttribute("href",destination);
  await submit(page,"login"); await expect(page).toHaveURL(new RegExp(`${destination}$`));
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(saved);
  expect(calls.every(path => ["/auth/v1/token","/auth/v1/user","/v1/account"].includes(path))).toBe(true);
});
for (const outcome of ["authenticated","confirmation_required","request_accepted"]) {
  test(`signup from Compare: ${outcome}`, async ({page}) => {
    const calls = await setup(page,outcome);
    const destination = "/compare?cases=case-a&fields=all";
    await page.goto(destination); await english(page);
    const saved = await page.evaluate(key => localStorage.getItem(key), KEY);
    await page.getByTestId("auth-entry-actions").getByRole("link",{name:"Create account",exact:true}).click();
    await submit(page,"signup");
    if (outcome === "authenticated") await expect(page).toHaveURL(new RegExp(`${destination.replace("?", "\\?")}$`));
    else {
      await expect(page.locator("#account-message")).toHaveText(accountCopy.en.accepted);
      await expect(page).toHaveURL(new RegExp(`/signup\\?next=${encodeURIComponent(destination)}$`));
      await page.locator("main").getByRole("link",{name:"Continue exploring",exact:true}).click();
      await expect(page).toHaveURL(new RegExp(`${destination.replace("?", "\\?")}$`));
    }
    expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(saved);
    expect(calls.every(path => ["/auth/v1/signup","/auth/v1/user","/v1/account"].includes(path))).toBe(true);
  });
}
for (const mode of ["login","signup"] as const) for (const next of ["", "?next=https://evil.test", "?next=//evil.test", "?next=%252F%252Fevil.test"]) {
  test(`${mode} safely falls back for ${next || "direct entry"}`, async ({page}) => {
    await setup(page); await page.goto(`/${mode}${next}`); await english(page);
    await expect(page.locator("main").getByRole("link",{name:"Continue exploring"})).toHaveAttribute("href","/");
    await submit(page,mode); await expect(page).toHaveURL(/\/account$/);
  });
}
test("missing account offers both actions and auth cross links retain intent", async ({page}) => {
  await setup(page); await page.goto("/account"); await english(page);
  await expect(page.locator("main").getByRole("link",{name:"Sign in",exact:true})).toBeVisible();
  await page.locator("main").getByRole("link",{name:"Create account",exact:true}).click();
  await page.goto("/login?next=%2Fcases%2Fcase-a%2Ffinance");
  await page.locator("main").getByRole("link",{name:"Create account",exact:true}).click();
  await expect(page).toHaveURL(/\/signup\?next=%2Fcases%2Fcase-a%2Ffinance$/);
  await page.locator("main").getByRole("link",{name:"Back to where you left off"}).click();
  await expect(page).toHaveURL(/\/cases\/case-a\/finance$/);
});
