const { spawn } = require("node:child_process");
const { readFile } = require("node:fs/promises");
const net = require("node:net");
const path = require("node:path");

const frontendRoot = path.resolve(__dirname, "..");

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
}

async function selectOwnedPort() {
  const requested = process.env.E2E_PORT;
  const probe = net.createServer();
  try {
    await listen(probe, requested ? Number(requested) : 0);
    const address = probe.address();
    if (!address || typeof address === "string") throw new Error("Unable to select an E2E server port.");
    return address.port;
  } catch (error) {
    if (requested && error && error.code === "EADDRINUSE") {
      throw new Error(`Cannot start an owned Next.js server: port ${requested} is already in use.`);
    }
    throw error;
  } finally {
    await new Promise((resolve) => probe.close(resolve));
  }
}

async function waitForServer(server, port, buildId, serverState) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (serverState.failure) throw serverState.failure;
    if (server.exitCode !== null) throw new Error(`Owned Next.js server exited before readiness (code ${server.exitCode}).`);
    if (serverState.ready) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/_next/static/${encodeURIComponent(buildId)}/_buildManifest.js`);
        if (response.ok) return;
      } catch {}
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Owned Next.js server did not serve build ${buildId} before the readiness deadline.`);
}

async function stopServer(server) {
  if (!server || server.exitCode !== null || server.signalCode !== null) return;
  const exited = new Promise((resolve) => server.once("exit", resolve));
  server.kill();
  let forceTimer;
  const forced = new Promise((resolve) => { forceTimer = setTimeout(resolve, 5_000, "timeout"); });
  try {
    if (await Promise.race([exited, forced]) === "timeout" && server.exitCode === null && server.signalCode === null) {
      server.kill("SIGKILL");
      await exited;
    }
  } finally {
    clearTimeout(forceTimer);
  }
}

async function main() {
  const buildId = (await readFile(path.join(frontendRoot, ".next", "BUILD_ID"), "utf8")).trim();
  if (!buildId) throw new Error("E2E build identity is missing; run build:e2e first.");
  const port = await selectOwnedPort();
  const serverState = { failure: null, ready: false };
  const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", String(port)], {
    cwd: frontendRoot,
    env: { ...process.env, PROFESSIONAL_WORKSPACE: "true" },
    stdio: ["inherit", "pipe", "pipe"],
    windowsHide: true,
  });
  let serverOutputTail = "";
  server.stdout.on("data", (chunk) => {
    process.stdout.write(chunk);
    serverOutputTail = `${serverOutputTail}${chunk}`.slice(-256);
    if (serverOutputTail.includes("Ready in")) serverState.ready = true;
  });
  server.stderr.on("data", (chunk) => { process.stderr.write(chunk); });
  server.once("error", (error) => { serverState.failure = error; });
  server.once("exit", (code, signal) => {
    if (code !== 0 || signal) serverState.failure = new Error(`Owned Next.js server exited before readiness (code ${code ?? "none"}, signal ${signal ?? "none"}).`);
  });
  try {
    await waitForServer(server, port, buildId, serverState);
    const result = await new Promise((resolve) => {
      const runner = spawn(process.execPath, ["node_modules/@playwright/test/cli.js", "test", ...process.argv.slice(2)], {
        cwd: frontendRoot,
        env: { ...process.env, E2E_PORT: String(port) },
        stdio: "inherit",
        windowsHide: true,
      });
      runner.once("error", () => resolve(1));
      runner.on("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
    });
    return Number(result);
  } finally {
    await stopServer(server);
  }
}

main()
  .then((code) => { process.exitCode = code; })
  .catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : "E2E runner failed"}\n`);
    process.exitCode = 1;
  });
