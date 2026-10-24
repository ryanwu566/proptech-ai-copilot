import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const COMPONENT = "components/app-entrance-motion/app-entrance-motion.tsx";
const STYLES = "components/app-entrance-motion/app-entrance-motion.module.css";

const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8");
const dataModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const ms = (value) => (value.endsWith("ms") ? Number.parseFloat(value) : Number.parseFloat(value) * 1000);

async function loadComponent() {
  const { outputText } = ts.transpileModule(read(COMPONENT), {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  // CSS module class names resolve to their own keys, as a stand-in for the bundler's hashed names.
  const stylesUrl = dataModule("export default new Proxy({}, { get: (_, key) => String(key) });");
  const source = outputText
    .replaceAll('"react/jsx-runtime"', JSON.stringify(import.meta.resolve("react/jsx-runtime")))
    .replaceAll('"react"', JSON.stringify(import.meta.resolve("react")))
    .replaceAll('"./app-entrance-motion.module.css"', JSON.stringify(stylesUrl));
  return import(dataModule(source));
}

/** Top-level rules only (outside @media), keyed by selector. */
function rules(css) {
  const out = new Map();
  for (const match of css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/(^|\n)([.][^{@\n]+)\{([^}]*)\}/g)) {
    out.set(match[2].trim(), match[3]);
  }
  return out;
}

function mediaBlock(css, query) {
  const start = css.indexOf(`@media (${query})`);
  assert.notEqual(start, -1, `missing @media (${query})`);
  const open = css.indexOf("{", start);
  let depth = 0;
  for (let index = open; index < css.length; index += 1) {
    if (css[index] === "{") depth += 1;
    if (css[index] === "}" && --depth === 0) return css.slice(open + 1, index);
  }
  throw new Error("unterminated media block");
}

/** End time in ms of every `animation:` shorthand (duration + delay). */
function animationEnds(declarations) {
  return [...declarations.matchAll(/animation:\s*([^;]+);/g)]
    .filter((match) => match[1].trim() !== "none")
    .map((match) => {
      const times = match[1].match(/\d+(?:\.\d+)?m?s\b/g) ?? [];
      return times.map(ms).reduce((sum, value) => sum + value, 0);
    });
}

test("the entrance is server-rendered as one hidden, non-interactive decorative layer", async () => {
  const { AppEntranceMotion } = await loadComponent();
  const markup = renderToStaticMarkup(React.createElement(AppEntranceMotion));
  assert.match(markup, /^<div class="layer" data-app-entrance="" aria-hidden="true">/);
  assert.doesNotMatch(markup, /tabindex|role=|<button|<a |<input|href=/);
  assert.equal((markup.match(/data-app-entrance/g) ?? []).length, 1);
});

test("the entrance reads no data and loads nothing", () => {
  const source = read(COMPONENT);
  const imports = [...source.matchAll(/from\s+"([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(imports.sort(), ["./app-entrance-motion.module.css", "react"]);
  assert.doesNotMatch(source, /fetch\(|XMLHttpRequest|localStorage|sessionStorage|router|usePathname|import\(/);
  assert.doesNotMatch(read(STYLES), /url\(|@import/);
});

test("the sequence is 800–1200ms, compositor-only, finite and ends hidden without JavaScript", () => {
  const css = read(STYLES);
  const top = rules(css);
  const layer = top.get(".layer");
  assert.match(layer, /position:\s*fixed/);
  assert.match(layer, /pointer-events:\s*none/);
  const ends = [...top.values()].flatMap(animationEnds);
  const total = Math.max(...ends);
  assert.ok(total >= 800 && total <= 1200, `sequence lasts ${total}ms`);
  assert.equal(Math.max(...animationEnds(layer)), total, "the layer exit is the last thing to finish");
  assert.match(css, /@keyframes layer-exit\s*\{\s*to\s*\{[^}]*opacity:\s*0;[^}]*visibility:\s*hidden/);
  assert.doesNotMatch(css, /infinite|alternate/);
  for (const [, body] of css.matchAll(/@keyframes [\w-]+\s*\{([\s\S]*?\})\s*\}/g)) {
    const properties = [...body.matchAll(/([a-z-]+):/g)].map((match) => match[1]);
    for (const property of properties) assert.ok(["opacity", "transform", "visibility"].includes(property), `animates ${property}`);
  }
});

test("reduced motion removes all movement and lifts the layer within 200ms", () => {
  const reduced = mediaBlock(read(STYLES), "prefers-reduced-motion: reduce");
  assert.match(reduced, /\.stage, \.mark, \.wordmark, \.rule, \.point\s*\{\s*animation:\s*none;/);
  const layer = reduced.match(/\.layer\s*\{([^}]*)\}/)[1];
  assert.ok(Math.max(...animationEnds(layer)) <= 200);
  assert.doesNotMatch(layer, /\d+ms\s+\d+ms/, "no delay before the layer lifts");
});

test("the root layout mounts the entrance once, outside every route segment", () => {
  const layout = read("app/layout.tsx");
  assert.equal((layout.match(/<AppEntranceMotion \/>/g) ?? []).length, 1);
  assert.match(layout, /<body><AppEntranceMotion \/>/);
  const users = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(path.join(root, dir), { withFileTypes: true })) {
      const relative = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(relative);
      else if (/\.tsx?$/.test(entry.name) && read(relative).includes("AppEntranceMotion")) users.push(relative.replaceAll("\\", "/"));
    }
  };
  walk("app");
  walk("components");
  assert.deepEqual(users.sort(), ["app/layout.tsx", COMPONENT]);
});
