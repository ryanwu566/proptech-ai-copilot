import { expect, test } from "@playwright/test";
import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { accountCopy } from "../lib/account-copy";

test.skip(!process.env.WAVE1A_PYTHON, "requires an explicitly configured local Python acceptance runtime");

for (const status of ["active", "suspended"] as const) {
  test(`real backend ${status} authority survives direct calls and forged browser state`, async ({page, request}) => {
    const probe = net.createServer();
    await new Promise<void>(resolve => probe.listen(0,"127.0.0.1",resolve));
    const port = (probe.address() as net.AddressInfo).port;
    await new Promise<void>(resolve => probe.close(() => resolve()));
    const backend = spawn(process.env.WAVE1A_PYTHON!, [path.resolve("e2e/helpers/consumer-backend.py"), String(port)], {
      cwd: path.resolve(".."), windowsHide:true, stdio:"ignore",
      env:{...process.env,WAVE1A_BROWSER_ACCEPTANCE:"1",WAVE1A_FIXTURE_ACCOUNT_STATUS:status},
    });
    try {
      const origin = `http://127.0.0.1:${port}`;
      await expect.poll(async () => {
        if (backend.exitCode !== null) throw new Error("local acceptance backend exited");
        try { return (await request.get(`${origin}/__wave1a_fixture/session`)).ok(); } catch { return false; }
      }, {timeout:15_000}).toBe(true);
      const session = await (await request.get(`${origin}/__wave1a_fixture/session`)).json();
      await page.addInitScript(value => localStorage.setItem("sb-slice8-auth-auth-token",JSON.stringify(value)), session);
      await page.route("http://e2e.test/v1**", async route => {
        const url = new URL(route.request().url());
        const response = await route.fetch({url:origin + url.pathname + url.search});
        await route.fulfill({response});
      });
      const errors: string[] = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto("/account");
      await page.getByTestId("locale-switcher").selectOption("en");
      await expect(page.getByTestId("account-status")).toHaveText(accountCopy.en[status]);
      const direct = await request.get(`${origin}/v1`, {headers:{Authorization:`Bearer ${session.access_token}`}});
      expect(direct.status()).toBe(status === "active" ? 200 : 403);
      if (status === "suspended") {
        expect((await direct.json()).error.code).toBe("account_suspended");
        await page.evaluate(() => {
          localStorage.setItem("account-status","active");
          localStorage.setItem("platform_role","platform_admin");
          document.querySelector('[data-testid="account-status"]')!.textContent = "Active";
        });
        for (const endpoint of ["/v1", "/v1/workspaces/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/context"]) {
          const denied = await request.get(origin + endpoint, {headers:{Authorization:`Bearer ${session.access_token}`,"X-Role":"platform_admin"}});
          expect(denied.status()).toBe(403);
          expect((await denied.json()).error.code).toBe("account_suspended");
        }
        await page.reload();
        await expect(page.getByTestId("account-status")).toHaveText("Suspended");
      }
      expect(errors).toEqual([]);
    } finally {
      if (backend.exitCode === null) {
        const exited = new Promise<void>(resolve => backend.once("exit", () => resolve()));
        backend.kill();
        await exited;
      }
    }
  });
}
