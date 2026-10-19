import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
// @ts-expect-error Node's native test runner uses source extensions.
import { TOUR_STEPS, TOUR_VERSION, readTourStatus } from "./guided-tour.ts";
// @ts-expect-error Node's native test runner uses source extensions.
import { GUIDED_TOUR_COPY, GUIDED_TOUR_COPY_KEYS } from "./guided-tour-copy.ts";
// @ts-expect-error Node's native test runner uses source extensions.
import { DEMO_COPY } from "./guided-case-simulation-copy.ts";
// @ts-expect-error Node's native test runner uses source extensions.
import { DEMO_CASE } from "./guided-case-simulation.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

test("the tour is the five-step modern case story", () => {
  assert.deepEqual(TOUR_STEPS.map((step) => step.id), ["createCase", "confirmLocation", "knownUnknown", "marketRisk", "questionsReport"]);
  assert.deepEqual(TOUR_STEPS.map((step) => GUIDED_TOUR_COPY["zh-TW"][step.label]), ["建立案件", "確認位置", "已知與未知", "市場與風險", "問題、比較與報告"]);
  assert.equal(TOUR_VERSION, "4");
  // Records from the seven-step tour no longer count as a current completion.
  assert.equal(readTourStatus({ getItem: () => JSON.stringify({ version: "3", status: "completed" }), setItem: () => {} }), null);
});

test("tour and fixture copy is complete in all four locales and keeps the trust boundary", () => {
  for (const locale of LOCALES) {
    for (const key of GUIDED_TOUR_COPY_KEYS) assert.ok(GUIDED_TOUR_COPY[locale][key]?.trim(), `${locale}:${key}`);
    assert.deepEqual(Object.keys(DEMO_COPY[locale]).sort(), Object.keys(DEMO_COPY.en).sort(), locale);
    for (const value of Object.values(DEMO_COPY[locale]) as string[]) assert.ok(value.trim(), locale);
    assert.match(DEMO_COPY[locale].unknownSafe, /≠/, locale);
  }
  for (const [locale, safe] of [["zh-TW", "未知不等於安全"], ["en", "Unknown does not mean safe"], ["ja", "不明は安全を意味しません"], ["ko", "알 수 없음은 안전을 뜻하지 않습니다"]] as const) {
    assert.ok(GUIDED_TOUR_COPY[locale]["guide.unknown.description"].includes(safe), locale);
  }
  for (const locale of LOCALES) for (const value of Object.values(GUIDED_TOUR_COPY[locale]) as string[]) {
    assert.doesNotMatch(value, /\bAI\b|guarantee|保證|credit scor|信用評分/i, `${locale}: ${value}`);
  }
});

test("the shared fixture is synthetic and presentation-only", () => {
  assert.equal(DEMO_CASE.synthetic, true);
  assert.match(DEMO_CASE.demoId, /^demo:/);
  assert.ok(Object.isFrozen(DEMO_CASE));
  assert.ok(!("caseId" in DEMO_CASE) && !("id" in DEMO_CASE), "fixture must not look like a SavedCase");
});

// Static proof: no module reachable from the tour/demo entry points can issue a provider call.
function closure(entries: string[]): Set<string> {
  const seen = new Set<string>();
  const visit = (file: string) => {
    if (seen.has(file)) return;
    seen.add(file);
    const source = readFileSync(file, "utf8");
    for (const match of source.matchAll(/(?:import|export)\s[^;]*?from\s+["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)|^import\s+["']([^"']+)["']/gm)) {
      const specifier = match[1] ?? match[2] ?? match[3];
      if (!specifier.startsWith("@/") && !specifier.startsWith(".")) continue;
      const base = specifier.startsWith("@/") ? path.join(root, specifier.slice(2)) : path.resolve(path.dirname(file), specifier);
      const resolved = [base, `${base}.ts`, `${base}.tsx`, path.join(base, "index.ts")].find((candidate) => /\.tsx?$/.test(candidate) && existsSync(candidate));
      if (resolved) visit(resolved);
    }
  };
  for (const entry of entries) visit(path.join(root, entry));
  return seen;
}

test("tour, Start-tour entry and fixture demo have no provider-triggering code path", () => {
  const files = closure(["components/guided-tour-entry.tsx", "components/onboarding-tour.tsx", "components/guided-case-simulation.tsx"]);
  const relative = [...files].map((file) => path.relative(root, file).replaceAll("\\", "/"));
  assert.ok(relative.includes("lib/guided-case-simulation.ts"));
  for (const forbidden of ["lib/api.ts", "lib/demo-runner.ts", "components/guided-demo-runner.tsx", "lib/case-storage.ts", "lib/workspace/case-repository.ts", "lib/cloud-case-client.ts", "lib/account-client.ts"]) {
    assert.ok(!relative.includes(forbidden), `${forbidden} is reachable from the tour`);
  }
  for (const file of files) {
    const source = readFileSync(file, "utf8");
    assert.doesNotMatch(source, /\bfetch\s*\(|XMLHttpRequest|navigator\.sendBeacon|new\s+WebSocket|EventSource\(/, path.relative(root, file));
  }
});
