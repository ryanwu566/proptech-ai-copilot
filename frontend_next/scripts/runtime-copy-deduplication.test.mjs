import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = new Map();
function load(name) {
  if (cache.has(name)) return cache.get(name);
  const filename = resolve(root, "lib", `${name}.ts`);
  const source = readFileSync(filename, "utf8") + (name === "experience-i18n" ? "\nexports.testKeys = Object.keys(canonicalResource);" : "");
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports = {};
  runInNewContext(output, { exports, require: (path) => load(path.replace("@/lib/", "")), Intl });
  cache.set(name, exports); return exports;
}
test("all four locale outputs, interpolated values and coverage match the starting release", () => {
  const experience = load("experience-i18n"); const runtime = load("runtime-copy");
  const values = { count: 7, total: 19, name: "fixture", source: "fixture", amount: 123 };
  const output = experience.SUPPORTED_LOCALES.map((locale) => ({ locale,
    experience: experience.testKeys.map((key) => [key, experience.translateExperience(locale, key)]),
    runtime: runtime.RUNTIME_COPY_KEYS.map((key) => [key, runtime.translateRuntimeCopy(locale, key), runtime.translateRuntimeCopy(locale, key, values)]),
  }));
  const digest = createHash("sha256").update(JSON.stringify({ output, experience: experience.getExperienceLocaleCoverage(), runtime: runtime.getRuntimeCopyCoverage() })).digest("hex");
  assert.equal(digest, "15385f48773907e8e72ed1f55b68941342ee6500cee30787604c88f9b9d38b24");
});

test("runtime resources contain no literals already supplied by locale overrides", () => {
  const filename = resolve(root, "lib/runtime-copy.ts");
  const source = ts.createSourceFile(filename, readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true);
  const overrides = load("runtime-copy-overrides"); const duplicates = [];
  function visit(node) {
    if (ts.isVariableDeclaration(node) && ["ja", "ko"].includes(node.name.getText(source)) && node.initializer && ts.isObjectLiteralExpression(node.initializer)) {
      const locale = node.name.getText(source);
      for (const property of node.initializer.properties) if (ts.isPropertyAssignment(property) && ts.isStringLiteral(property.name) && overrides.getRuntimeCopyOverride(locale, property.name.text) !== undefined) duplicates.push(`${locale}:${property.name.text}`);
    }
    ts.forEachChild(node, visit);
  }
  visit(source); assert.deepEqual(duplicates, []);
});

test("base override dictionaries contain no literals replaced by production overrides", () => {
  const duplicates = [];
  for (const name of ["runtime-copy-overrides", "experience-i18n-overrides"]) {
    const filename = resolve(root, "lib", `${name}.ts`);
    const source = ts.createSourceFile(filename, readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true);
    const dictionaries = new Map();
    function visit(node) {
      if (ts.isVariableDeclaration(node) && node.initializer && ts.isObjectLiteralExpression(node.initializer)) dictionaries.set(node.name.getText(source), node.initializer.properties.filter(ts.isPropertyAssignment).map((property) => property.name.text));
      ts.forEachChild(node, visit);
    }
    visit(source);
    for (const locale of ["ja", "ko"]) for (const key of dictionaries.get(locale) ?? []) if (dictionaries.get(`${locale}Production`)?.includes(key)) duplicates.push(`${name}:${locale}:${key}`);
  }
  assert.deepEqual(duplicates, []);
});
