import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const nextRoot = path.join(frontendRoot, ".next");
const publicKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY?.trim();
const forbiddenValues = [
  process.env.GOOGLE_MAPS_API_KEY,
  process.env.GOOGLE_APPLICATION_CREDENTIALS,
  process.env.GOOGLE_SERVICE_ACCOUNT_JSON,
].filter((value) => typeof value === "string" && value.length > 0);

if (!publicKey || forbiddenValues.length !== 3) {
  process.stderr.write("GOOGLE_MAPS_BROWSER_ARTIFACTS=failed; expected one public and three forbidden credential sentinels\n");
  process.exit(1);
}

const browserArtifactRoots = [path.join(nextRoot, "static"), path.join(nextRoot, "server", "app")];
const files = browserArtifactRoots.flatMap(walkFiles);
let publicKeyOccurrences = 0;

for (const file of files) {
  const contents = fs.readFileSync(file).toString("utf8");
  if (contents.includes(publicKey)) publicKeyOccurrences += 1;
  if (forbiddenValues.some((value) => contents.includes(value))) {
    process.stderr.write(`GOOGLE_MAPS_BROWSER_ARTIFACTS=failed; forbidden server credential in ${path.relative(frontendRoot, file)}\n`);
    process.exit(1);
  }
}

if (publicKeyOccurrences === 0) {
  process.stderr.write("GOOGLE_MAPS_BROWSER_ARTIFACTS=failed; expected public browser key was not emitted\n");
  process.exit(1);
}

process.stdout.write(`GOOGLE_MAPS_BROWSER_ARTIFACTS=pass; scanned=${files.length}; public_key_files=${publicKeyOccurrences}; forbidden_credentials=absent\n`);

function walkFiles(root) {
  if (!fs.existsSync(root)) return [];
  return fs.readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(root, entry.name);
    return entry.isDirectory() ? walkFiles(target) : [target];
  });
}
