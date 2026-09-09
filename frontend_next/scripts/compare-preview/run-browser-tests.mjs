import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:net";

const hostname = "127.0.0.1";
const port = Number(process.env.COMPARE_PREVIEW_PORT || 3104);
const environment = { ...process.env, NEXT_TELEMETRY_DISABLED: "1" };

await new Promise((resolve, reject) => {
  const probe = createServer();
  probe.once("error", () => reject(new Error(`port ${port} is already in use; refusing to reuse another track's server`)));
  probe.listen(port, hostname, () => probe.close(resolve));
});

const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "dev", "--hostname", hostname, "--port", String(port)], {
  cwd: process.cwd(),
  env: environment,
  stdio: "inherit",
  windowsHide: true,
});

function windowsListenerPid() {
  const netstat = spawnSync("netstat", ["-ano", "-p", "tcp"], { encoding: "utf8", windowsHide: true });
  const listener = netstat.stdout?.split(/\r?\n/).find((line) => line.includes(`${hostname}:${port}`) && line.includes("LISTENING"));
  return listener?.trim().split(/\s+/).at(-1);
}

async function stopServer() {
  if (process.platform === "win32") {
    try { server.kill("SIGKILL"); } catch {}
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const listenerPid = windowsListenerPid();
      if (listenerPid) {
        try { process.kill(Number(listenerPid), "SIGKILL"); } catch {
          spawnSync("taskkill", ["/PID", listenerPid, "/T", "/F"], { stdio: "ignore", windowsHide: true });
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
      if (!windowsListenerPid()) return;
    }
    throw new Error(`failed to release comparison preview port ${port}`);
  } else {
    server.kill("SIGTERM");
  }
}

async function waitForServer() {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) throw new Error(`comparison preview server exited with ${server.exitCode}`);
    try {
      const response = await fetch(`http://${hostname}:${port}/dev/property-compare-preview`);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  throw new Error("comparison preview server did not become ready");
}

function runPlaywright() {
  return new Promise((resolve) => {
    const runner = spawn(process.execPath, ["node_modules/@playwright/test/cli.js", "test", "--config=playwright.compare-preview.config.ts"], {
      cwd: process.cwd(),
      env: environment,
      stdio: "inherit",
      windowsHide: true,
    });
    runner.once("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
  });
}

try {
  await waitForServer();
  const exitCode = await runPlaywright();
  await stopServer();
  process.exit(Number(exitCode));
} catch (error) {
  await stopServer();
  process.stderr.write(`${error instanceof Error ? error.message : "comparison browser test failed"}\n`);
  process.exit(1);
}
