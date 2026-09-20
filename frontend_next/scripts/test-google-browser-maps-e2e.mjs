import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicKey = "e2e-public-google-maps-browser-key";
const backendKey = "e2e-forbidden-backend-google-maps-key";
const serviceAccountPath = "e2e-forbidden-service-account-credential-path";
const serviceAccountJson = "e2e-forbidden-service-account-private-key";

const withoutBrowserKey = { ...process.env };
withoutBrowserKey.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY = "";
run(["scripts/build-e2e.mjs"], withoutBrowserKey);
run(["e2e/run-e2e.cjs", "e2e/google-browser-maps.spec.ts", "--grep", "@browser-key-missing", "--retries=0", "--project=chromium", "--workers=1"], withoutBrowserKey);
run(["e2e/run-e2e.cjs", "e2e/market-insight-east-west-identity.spec.ts", "--grep", "East/West road identity: Location Insight", "--retries=0", "--project=chromium", "--workers=1"], withoutBrowserKey);

const withBrowserKey = {
  ...process.env,
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY: publicKey,
  GOOGLE_MAPS_API_KEY: backendKey,
  GOOGLE_APPLICATION_CREDENTIALS: serviceAccountPath,
  GOOGLE_SERVICE_ACCOUNT_JSON: serviceAccountJson,
};
run(["scripts/build-e2e.mjs"], withBrowserKey);
run(["scripts/assert-google-maps-browser-artifacts.mjs"], withBrowserKey);
run(["e2e/run-e2e.cjs", "e2e/google-browser-maps.spec.ts", "--grep-invert", "@browser-key-missing", "--retries=0", "--project=chromium", "--workers=1"], withBrowserKey);

function run(args, env) {
  const result = spawnSync(process.execPath, args, { cwd: frontendRoot, env, stdio: "inherit", windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
