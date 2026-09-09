import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:net";

const hostname = "127.0.0.1";
const port = Number(process.env.COMPARE_PREVIEW_PORT || 3104);

await new Promise((resolve, reject) => {
  const probe = createServer();
  probe.once("error", () => reject(new Error(`port ${port} is already in use; refusing to reuse another track's server`)));
  probe.listen(port, hostname, () => probe.close(resolve));
});

const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--hostname", hostname, "--port", String(port)], {
  cwd: process.cwd(),
  env: { ...process.env, NODE_ENV: "production" },
  stdio: ["ignore", "pipe", "pipe"],
  windowsHide: true,
});
let serverOutput = "";
server.stdout.on("data", (chunk) => { serverOutput += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverOutput += chunk.toString(); });

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

const deadline = Date.now() + 60_000;
let response;
try {
  while (Date.now() < deadline) {
    if (server.exitCode !== null) throw new Error(`production server exited with ${server.exitCode}\n${serverOutput}`);
    try {
      response = await fetch(`http://${hostname}:${port}/dev/property-compare-preview`, { redirect: "manual" });
      break;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 350));
    }
  }
  if (!response) throw new Error(`production server did not become ready\n${serverOutput}`);
  const body = await response.text();
  const fixtureContent = body.includes("property-compare-synthetic-preview") || body.includes("比較呈現實驗室") || body.includes("全頁皆為合成資料");
  const excluded = response.status === 404 && !fixtureContent;
  if (!excluded) throw new Error(`preview exclusion failed: status=${response.status}; fixtureContent=${fixtureContent}`);
  process.stdout.write(`PRODUCTION_PREVIEW_EXCLUSION=pass; status=${response.status}; fixture_content=false\n`);
} finally {
  await stopServer();
}
