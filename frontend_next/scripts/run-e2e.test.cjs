const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const http = require("node:http");
const path = require("node:path");
const test = require("node:test");

const frontendRoot = path.resolve(__dirname, "..");

test("the E2E runner refuses a port owned by another server", async (t) => {
  const foreignServer = http.createServer((_request, response) => {
    response.writeHead(200, { "content-type": "text/plain" });
    response.end("foreign server");
  });
  await new Promise((resolve, reject) => {
    foreignServer.once("error", reject);
    foreignServer.listen(0, "127.0.0.1", resolve);
  });
  t.after(() => new Promise((resolve) => foreignServer.close(resolve)));

  const address = foreignServer.address();
  assert(address && typeof address === "object");
  const child = spawn(process.execPath, ["e2e/run-e2e.cjs", "--list"], {
    cwd: frontendRoot,
    env: { ...process.env, E2E_PORT: String(address.port) },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  let output = "";
  child.stdout.on("data", (chunk) => { output += chunk; });
  child.stderr.on("data", (chunk) => { output += chunk; });
  // This is a test-harness deadlock guard, not a readiness or browser synchronization delay.
  const timeout = setTimeout(() => child.kill(), 20_000);
  const exitCode = await new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
  });
  clearTimeout(timeout);

  assert.notEqual(exitCode, 0, `runner trusted a server it did not own:\n${output}`);
  assert.match(output, /owned Next\.js server|exited before readiness/i);
});
