import { expect, test } from "@playwright/test";
import { spawn } from "node:child_process";
import { writeFile } from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { accountCopy } from "../lib/account-copy";
import { connectionErrorCategory, safeBackendCall } from "./helpers/backend-diagnostics";

test.skip(!process.env.WAVE1A_PYTHON, "requires an explicitly configured local Python acceptance runtime");

for (const status of ["active", "suspended"] as const) {
  test(`real backend ${status} authority survives direct calls and forged browser state`, async ({page, request}, testInfo) => {
    const probe = net.createServer();
    await new Promise<void>(resolve => probe.listen(0,"127.0.0.1",resolve));
    const port = (probe.address() as net.AddressInfo).port;
    await new Promise<void>(resolve => probe.close(() => resolve()));
    // Establish artifact paths before owning a child process, so an output
    // directory failure cannot strand a backend outside cleanup protection.
    const tracePath = testInfo.outputPath("backend-startup.trace.zip");
    const diagnosticsPath = testInfo.outputPath("backend-startup-diagnostics.json");
    const started = performance.now();
    const elapsed = () => Math.round(performance.now() - started);
    const diagnostics = {
      accountStatus: status, readinessDeadlineMs: 15_000, spawnSucceeded: false,
      pid: null as number | null, spawnErrorCategory: null as string | null,
      exitCode: null as number | null, exitSignal: null as string | null,
      prematureExit: false, exitElapsedMs: null as number | null,
      readinessElapsedMs: null as number | null, pollAttempts: 0,
      connectionErrors: { refused: 0, reset: 0, timeout: 0, other: 0 },
      httpStatuses: {} as Record<string, number>, lastSuccessfulMilestone: null as string | null,
      milestones: [] as { name: string; elapsedMs: number; helperElapsedMs: number }[],
      stderrCategories: [] as string[], fixtureSessionEndpointReached: false,
      readinessSucceeded: false, browserNavigationBegan: false, browserNavigationCompleted: false,
      accountStatusAssertionPassed: false, directAuthorizationAssertionPassed: false,
      suspensionForgeryAssertionsPassed: false, allAssertionsCompleted: false,
      cleanupStarted: false, cleanupCompleted: false, observationElapsedMs: 0,
    };
    const backend = spawn(process.env.WAVE1A_PYTHON!, [path.resolve("e2e/helpers/consumer-backend.py"), String(port)], {
      cwd: path.resolve(".."), windowsHide:true, stdio:["ignore", "ignore", "pipe"],
      env:{...process.env,WAVE1A_BROWSER_ACCEPTANCE:"1",WAVE1A_FIXTURE_ACCOUNT_STATUS:status,
        WAVE1A_STARTUP_DIAGNOSTICS:"1"},
    });
    backend.once("spawn", () => { diagnostics.spawnSucceeded = true; diagnostics.pid = backend.pid ?? null; });
    backend.once("error", error => {
      const code = (error as NodeJS.ErrnoException).code;
      diagnostics.spawnErrorCategory = code === "ENOENT" || code === "EACCES" ? code : "spawn_error";
    });
    backend.once("exit", (code, signal) => {
      diagnostics.exitCode = code; diagnostics.exitSignal = signal;
      diagnostics.exitElapsedMs = elapsed(); diagnostics.prematureExit = !diagnostics.cleanupStarted;
    });
    const allowedMilestones = new Set(["helper_started", "environment_sanitized", "jwt_imported", "crypto_imported",
      "uvicorn_imported", "app_imported", "dependencies_imported",
      "signing_key_created", "server_starting", "fixture_session_reached"]);
    let pendingStderr = "";
    backend.stderr?.on("data", (chunk: Buffer) => {
      pendingStderr = (pendingStderr + chunk.toString("utf8")).slice(-4096);
      const lines = pendingStderr.split("\n");
      pendingStderr = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("WAVE1A_STARTUP ")) {
          try {
            const value = JSON.parse(line.slice("WAVE1A_STARTUP ".length));
            if (allowedMilestones.has(value.milestone) && Number.isSafeInteger(value.elapsed_ms)
                && value.elapsed_ms >= 0 && !diagnostics.milestones.some(item => item.name === value.milestone)) {
              diagnostics.lastSuccessfulMilestone = value.milestone;
              diagnostics.milestones.push({name:value.milestone,elapsedMs:elapsed(),helperElapsedMs:value.elapsed_ms});
              if (value.milestone === "fixture_session_reached") diagnostics.fixtureSessionEndpointReached = true;
            }
          } catch { /* Discard malformed diagnostics and all unapproved text. */ }
        } else {
          for (const category of ["ModuleNotFoundError", "ImportError", "RuntimeError", "AssertionError", "OSError"]) {
            if (line.includes(category) && !diagnostics.stderrCategories.includes(category)) diagnostics.stderrCategories.push(category);
          }
          for (const [pattern,category] of [[/10048|address already in use/i,"address_in_use"],
            [/PermissionError|permission denied/i,"permission_denied"]] as const) {
            if (pattern.test(line) && !diagnostics.stderrCategories.includes(category)) diagnostics.stderrCategories.push(category);
          }
        }
      }
    });
    // Trace only the empty browser context during startup. Stop before any
    // session, localStorage or Authorization value enters browser operations.
    let startupTraceOpen = false;
    try {
      await page.context().tracing.start({screenshots:true,snapshots:false,sources:false});
      startupTraceOpen = true;
      await page.context().tracing.group("fixture backend readiness (15 seconds)");
      const origin = `http://127.0.0.1:${port}`;
      await expect.poll(async () => {
        diagnostics.pollAttempts += 1;
        if (diagnostics.spawnErrorCategory) throw new Error("local acceptance backend spawn failed");
        if (backend.exitCode !== null || backend.signalCode !== null) throw new Error("local acceptance backend exited");
        try {
          const response = await request.get(`${origin}/__wave1a_fixture/session`);
          const code = String(response.status());
          diagnostics.httpStatuses[code] = (diagnostics.httpStatuses[code] ?? 0) + 1;
          if (response.ok()) diagnostics.fixtureSessionEndpointReached = true;
          return response.ok();
        } catch (error) {
          const category = connectionErrorCategory(error);
          diagnostics.connectionErrors[category] += 1;
          return false;
        }
      }, {timeout:15_000}).toBe(true);
      diagnostics.readinessSucceeded = true;
      diagnostics.readinessElapsedMs = elapsed();
      await page.context().tracing.groupEnd();
      await page.context().tracing.stop({path:tracePath});
      startupTraceOpen = false;
      const session = await safeBackendCall("fixture-session", async () =>
        (await request.get(`${origin}/__wave1a_fixture/session`)).json());
      await safeBackendCall("browser-session", () =>
        page.addInitScript(value => localStorage.setItem("sb-slice8-auth-auth-token",JSON.stringify(value)), session));
      await page.route("http://e2e.test/v1**", async route => {
        const url = new URL(route.request().url());
        const response = await safeBackendCall("forwarded-api", () => route.fetch({url:origin + url.pathname + url.search}));
        await route.fulfill({response});
      });
      const errors: string[] = [];
      page.on("pageerror", error => errors.push(error.message));
      diagnostics.browserNavigationBegan = true;
      await safeBackendCall("account-navigation", () => page.goto("/account"));
      diagnostics.browserNavigationCompleted = true;
      await page.getByTestId("locale-switcher").selectOption("en");
      await expect(page.getByTestId("account-status")).toHaveText(accountCopy.en[status]);
      diagnostics.accountStatusAssertionPassed = true;
      const direct = await safeBackendCall("direct-api", () =>
        request.get(`${origin}/v1`, {headers:{Authorization:`Bearer ${session.access_token}`}}));
      expect(direct.status()).toBe(status === "active" ? 200 : 403);
      diagnostics.directAuthorizationAssertionPassed = true;
      if (status === "suspended") {
        expect((await direct.json()).error.code).toBe("account_suspended");
        await page.evaluate(() => {
          localStorage.setItem("account-status","active");
          localStorage.setItem("platform_role","platform_admin");
          document.querySelector('[data-testid="account-status"]')!.textContent = "Active";
        });
        for (const endpoint of ["/v1", "/v1/workspaces/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/context"]) {
          const denied = await safeBackendCall("denied-api", () =>
            request.get(origin + endpoint, {headers:{Authorization:`Bearer ${session.access_token}`,"X-Role":"platform_admin"}}));
          expect(denied.status()).toBe(403);
          expect((await denied.json()).error.code).toBe("account_suspended");
        }
        await safeBackendCall("account-reload", () => page.reload());
        await expect(page.getByTestId("account-status")).toHaveText("Suspended");
        diagnostics.suspensionForgeryAssertionsPassed = true;
      }
      expect(errors).toEqual([]);
      diagnostics.allAssertionsCompleted = true;
    } finally {
      diagnostics.observationElapsedMs = elapsed();
      try {
        await writeFile(diagnosticsPath, JSON.stringify(diagnostics,null,2));
        if (startupTraceOpen) {
          await page.context().tracing.groupEnd();
          await page.context().tracing.stop({path:tracePath});
        }
        await testInfo.attach("credential-free startup trace", {path:tracePath,contentType:"application/zip"});
      } finally {
        diagnostics.cleanupStarted = true;
        if (backend.pid && backend.exitCode === null && backend.signalCode === null) {
          const exited = new Promise<void>(resolve => backend.once("exit", () => resolve()));
          if (process.platform === "win32") {
            // A venv launcher may own another Python process. Stop only this
            // fixture's process tree, including that owned child.
            await new Promise<void>((resolve, reject) => {
              const stop = spawn("taskkill", ["/PID",String(backend.pid),"/T","/F"], {windowsHide:true,stdio:"ignore"});
              stop.once("error", reject);
              stop.once("exit", code => code === 0 || backend.exitCode !== null || backend.signalCode !== null
                ? resolve() : reject(new Error("local acceptance backend cleanup failed")));
            });
          } else backend.kill();
          await exited;
        }
        diagnostics.cleanupCompleted = true;
        diagnostics.observationElapsedMs = elapsed();
        await writeFile(diagnosticsPath, JSON.stringify(diagnostics,null,2));
        await testInfo.attach("backend startup diagnostics", {path:diagnosticsPath,contentType:"application/json"});
      }
    }
  });
}
