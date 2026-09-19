import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const firstPort = Number(process.env.WORKSPACE_FLAG_TEST_PORT ?? "3197");
const caseId = "11111111-1111-4111-8111-111111111111";

async function waitForServer(port) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/`);
      if (response.ok) return;
    } catch { /* Keep waiting for the bounded local server. */ }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error("Feature-off test server did not become ready.");
}

async function assertFlagOff(label, value, port) {
  const environment = { ...process.env };
  if (value === undefined) delete environment.PROFESSIONAL_WORKSPACE;
  else environment.PROFESSIONAL_WORKSPACE = value;
  const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", String(port)], {
    cwd: frontendRoot,
    env: environment,
    stdio: "inherit",
    windowsHide: true,
  });
  try {
    await waitForServer(port);
    const response = await fetch(`http://127.0.0.1:${port}/workspace/${caseId}`, { redirect: "manual" });
    if (response.status !== 404) throw new Error(`Expected ${label} route to return 404, received ${response.status}.`);
  } finally {
    server.kill();
  }
}

await assertFlagOff("unset feature flag", undefined, firstPort);
await assertFlagOff("false feature flag", "false", firstPort + 1);
await assertFlagOff("unknown feature flag", "unexpected", firstPort + 2);
process.stdout.write("PROFESSIONAL_WORKSPACE_FLAG_OFF=pass\n");
