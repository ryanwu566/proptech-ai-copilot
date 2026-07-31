const { spawn } = require("node:child_process");

const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3100"], {
  stdio: "inherit",
  windowsHide: true,
});

async function waitForServer() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch("http://127.0.0.1:3100/");
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Local production server did not become ready.");
}

function stopServer() {
  server.kill();
}

async function main() {
  try {
    await waitForServer();
    const result = await new Promise((resolve) => {
      const runner = spawn(process.execPath, ["node_modules/@playwright/test/cli.js", "test", ...process.argv.slice(2)], { stdio: "inherit" });
      runner.on("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
    });
    stopServer();
    process.exit(Number(result));
  } catch (error) {
    stopServer();
    process.stderr.write(`${error instanceof Error ? error.message : "E2E runner failed"}\n`);
    process.exit(1);
  }
}

main();
