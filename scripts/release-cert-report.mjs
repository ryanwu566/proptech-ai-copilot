#!/usr/bin/env node
/**
 * Release Certification Report Generator
 * ───────────────────────────────────────
 * Runs the release smoke suite and produces a structured report.
 *
 * Usage:
 *   node scripts/release-cert-report.mjs [--production]
 *
 * Options:
 *   --production  Target production URL instead of localhost
 */

import { execSync } from "child_process";
import { existsSync, readFileSync, writeFileSync } from "fs";

const isProduction = process.argv.includes("--production");
const baseUrl = isProduction ? "https://proptech-ai-copilot.vercel.app" : "http://127.0.0.1:3100";
const testFile = isProduction ? "e2e/production-smoke.spec.ts" : "e2e/release-smoke.spec.ts";

console.log(`\n🏗️  Release Certification Report`);
console.log(`   Target: ${baseUrl}`);
console.log(`   Suite: ${testFile}\n`);

const start = Date.now();

let exitCode = 0;
let jsonOutput = "";

try {
  const env = { ...process.env, E2E_BASE_URL: baseUrl };
  const cwd = new URL("../frontend_next", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
  const cmd = `npx playwright test ${testFile} --project=chromium --workers=1 --reporter=json`;
  jsonOutput = execSync(cmd, { cwd, env, encoding: "utf-8", timeout: 600000 });
} catch (err) {
  exitCode = err.status || 1;
  jsonOutput = err.stdout || "";
}

const duration = Math.round((Date.now() - start) / 1000);

// Parse results
let results = { suites: [] };
try { results = JSON.parse(jsonOutput); } catch { /* partial output */ }

function countTests(suites) {
  let pass = 0, fail = 0;
  for (const suite of suites) {
    for (const spec of suite.specs || []) {
      for (const test of spec.tests || []) {
        for (const result of test.results || []) {
          if (result.status === "passed") pass++;
          else fail++;
        }
      }
    }
    const sub = countTests(suite.suites || []);
    pass += sub.pass;
    fail += sub.fail;
  }
  return { pass, fail };
}

const { pass, fail } = countTests(results.suites || []);

const report = {
  timestamp: new Date().toISOString(),
  target: baseUrl,
  suite: testFile,
  duration_seconds: duration,
  pass_count: pass,
  fail_count: fail,
  verdict: fail === 0 ? "PASS" : "FAIL",
  p0_blockers: fail > 0 ? fail : 0,
};

console.log(`\n═══════════════════════════════════════`);
console.log(`  RELEASE CERTIFICATION REPORT`);
console.log(`═══════════════════════════════════════`);
console.log(`  Target:    ${report.target}`);
console.log(`  Duration:  ${report.duration_seconds}s`);
console.log(`  Passed:    ${report.pass_count}`);
console.log(`  Failed:    ${report.fail_count}`);
console.log(`  Verdict:   ${report.verdict}`);
console.log(`═══════════════════════════════════════\n`);

if (report.verdict === "FAIL") {
  console.log("❌ RELEASE BLOCKED — P0 failures detected.\n");
  process.exit(1);
} else {
  console.log("✅ RELEASE CANDIDATE APPROVED.\n");
  process.exit(0);
}
