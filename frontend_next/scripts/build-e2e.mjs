import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const hasExplicitApiOrigin = Object.prototype.hasOwnProperty.call(process.env, "NEXT_PUBLIC_API_BASE_URL");
const environment = {
  ...process.env,
  NEXT_PUBLIC_API_BASE_URL: hasExplicitApiOrigin ? process.env.NEXT_PUBLIC_API_BASE_URL : "http://e2e.test",
  NEXT_PUBLIC_APP_ENV: "test",
};

if (environment.NEXT_PUBLIC_APP_ENV !== "test" || environment.NEXT_PUBLIC_API_BASE_URL !== "http://e2e.test") {
  process.stderr.write("E2E_BUILD_PREFLIGHT=failed; expected test environment and e2e.test API origin\n");
  process.exit(1);
}

process.stdout.write("E2E_BUILD_PREFLIGHT=pass\n");
const nextCli = path.join(frontendRoot, "node_modules", "next", "dist", "bin", "next");
const result = spawnSync(process.execPath, [nextCli, "build"], {
  cwd: frontendRoot,
  env: environment,
  stdio: "inherit",
  windowsHide: true,
});

if (result.error) {
  process.stderr.write("E2E_BUILD_PREFLIGHT=failed; Next.js build process unavailable\n");
  process.exit(1);
}
process.exit(result.status ?? 1);
