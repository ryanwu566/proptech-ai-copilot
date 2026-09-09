const { spawn, spawnSync } = require("node:child_process");
const path = require("node:path");

const frontendRoot = path.resolve(__dirname, "..");
const productionTarget = process.env.SPATIAL_PREVIEW_E2E_TARGET === "production";
const port = productionTarget ? 3103 : 3102;
const mode = productionTarget ? "start" : "dev";
const nextCli = path.join(frontendRoot, "node_modules", "next", "dist", "bin", "next");
const playwrightCli = path.join(frontendRoot, "node_modules", "@playwright", "test", "cli.js");
const serverEnvironment = { ...process.env };

const server = spawn(process.execPath, [nextCli, mode, "--hostname", "127.0.0.1", "--port", String(port)], {
  cwd: frontendRoot,
  env: serverEnvironment,
  stdio: "inherit",
  windowsHide: true,
  detached: process.platform !== "win32",
});

let stopped = false;

function stopOwnedServer() {
  if (stopped || !server.pid) return;
  stopped = true;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/pid", String(server.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
  } else {
    try { process.kill(-server.pid, "SIGTERM"); } catch {}
  }
}

async function waitForServer() {
  const pathToCheck = productionTarget ? "/" : "/dev/spatial-map-preview";
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}${pathToCheck}`);
      if (response.status < 500) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Preview server on port ${port} did not become ready.`);
}

async function run() {
  try {
    await waitForServer();
    const result = await new Promise((resolve, reject) => {
      const tests = spawn(process.execPath, [playwrightCli, "test", "--config=playwright.spatial-map-preview.config.ts"], {
        cwd: frontendRoot,
        env: { ...process.env, SPATIAL_PREVIEW_EXTERNAL_SERVER: "1" },
        stdio: "inherit",
        windowsHide: true,
      });
      tests.on("error", reject);
      tests.on("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
    });
    stopOwnedServer();
    process.exit(Number(result));
  } catch (error) {
    stopOwnedServer();
    process.stderr.write(`${error instanceof Error ? error.message : "Spatial preview E2E runner failed."}\n`);
    process.exit(1);
  }
}

server.on("error", (error) => {
  process.stderr.write(`Unable to start owned preview server: ${error.message}\n`);
  stopOwnedServer();
  process.exit(1);
});
process.once("SIGINT", () => { stopOwnedServer(); process.exit(130); });
process.once("SIGTERM", () => { stopOwnedServer(); process.exit(143); });

run();
