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
  const at = query.startsWith("screen") ? `@media ${query}` : `@media (${query})`;
  const start = css.indexOf(at);
  assert.notEqual(start, -1, `missing ${at}`);
  const open = css.indexOf("{", start);
  let depth = 0;
  for (let index = open; index < css.length; index += 1) {
    if (css[index] === "{") depth += 1;
    if (css[index] === "}" && --depth === 0) return css.slice(open + 1, index);
  }
  throw new Error("unterminated media block");
}

/** Splits an `animation:` value into its comma-separated layers, ignoring commas inside cubic-bezier() and var(). */
function layers(value) {
  const out = [];
  let depth = 0;
  let start = 0;
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === "(") depth += 1;
    if (value[index] === ")") depth -= 1;
    if (value[index] === "," && depth === 0) { out.push(value.slice(start, index)); start = index + 1; }
  }
  return [...out, value.slice(start)].map((layer) => layer.trim());
}

/** Each layer of every `animation:` shorthand as { name, start, end } in ms. */
function animationLayers(declarations) {
  return [...declarations.matchAll(/animation:\s*([^;]+);/g)]
    .filter((match) => match[1].trim() !== "none")
    .flatMap((match) => layers(match[1]).map((layer) => {
      const [duration = 0, delay = 0] = (layer.match(/\d+(?:\.\d+)?m?s\b/g) ?? []).map(ms);
      return { name: layer.split(/\s+/)[0], start: delay, end: duration + delay };
    }));
}

/** End time in ms of every animation layer (duration + delay). */
function animationEnds(declarations) {
  return animationLayers(declarations).map((layer) => layer.end);
}

/** The translateZ, in px, of each frame of a keyframes rule. */
function keyframeZ(css, name) {
  const body = css.match(new RegExp(`@keyframes ${name}\\s*\\{([\\s\\S]*?\\})\\s*\\}`))[1];
  return [...body.matchAll(/translate3d\(0, 0, (-?\d+)px\)/g)].map((match) => Number(match[1]));
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

test("the sequence is 2200–2800ms, compositor-only, finite and ends hidden without JavaScript", () => {
  const css = read(STYLES);
  const top = rules(css);
  const layer = top.get(".layer");
  assert.match(layer, /position:\s*fixed/);
  assert.match(layer, /pointer-events:\s*none/);
  const ends = [...top.values()].flatMap(animationEnds);
  const total = Math.max(...ends);
  assert.ok(total >= 2200 && total <= 2800, `sequence lasts ${total}ms`);
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
  assert.match(reduced, /\.plane, \.door, \.light, \.frame, \.mark, \.wordmark, \.rule, \.point\s*\{\s*animation:\s*none;/);
  assert.match(reduced, /\.space, \.wash\s*\{\s*display:\s*none;/, "no scene, no perspective, no depth");
  const layer = reduced.match(/\.layer\s*\{([^}]*)\}/)[1];
  assert.match(layer, /background:\s*var\(--canvas\)/, "a plain canvas, not the dark stage");
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

test("the evidence trace keeps one point hollow: the opening never shows every item as confirmed", async () => {
  const { AppEntranceMotion } = await loadComponent();
  const markup = renderToStaticMarkup(React.createElement(AppEntranceMotion));
  assert.equal((markup.match(/class="point"/g) ?? []).length, 4);
  const hollow = rules(read(STYLES)).get(".point:nth-child(4)");
  assert.match(hollow, /background:\s*var\(--stage\)/);
  assert.match(hollow, /box-shadow:\s*inset/);
});

test("a pointer, wheel or key press fast-forwards the entrance instead of waiting it out", () => {
  const source = read(COMPONENT);
  assert.match(source, /INTENT_EVENTS = \["pointerdown", "keydown", "wheel", "touchstart"\]/);
  assert.match(source, /passive: true/);
  assert.match(source, /animation\.finish\(\)/);
  assert.match(source, /removeEventListener\(type, skip/);
});

test("Home's opening layering is gated on the entrance layer, opt-in, compositor-only and done when the layer ends", () => {
  const home = read("app/home.css").replace(/\/\*[\s\S]*?\*\//g, "");
  const total = Math.max(...[...rules(read(STYLES)).values()].flatMap(animationEnds));
  const block = mediaBlock(home, "screen and (prefers-reduced-motion: no-preference)");
  const uses = [...home.matchAll(/^.*home-arrive \d.*$/gm)].map((match) => match[0]);
  assert.equal(uses.length, 3);
  for (const use of uses) {
    assert.ok(block.includes(use.trim()), `home-arrive used outside the opt-in block: ${use}`);
    assert.match(use, /^\s*body:has\(> \[data-app-entrance\]\) /, "layering only plays while the entrance layer is mounted");
    assert.ok(Math.max(...animationEnds(use)) <= total, `${use} ends after the layer`);
  }
  const frames = home.match(/@keyframes home-arrive\s*\{([\s\S]*?\})\s*\}/)[1];
  for (const [, property] of frames.matchAll(/([a-z-]+):/g)) assert.ok(["opacity", "transform"].includes(property), `home-arrive animates ${property}`);
});

test("the camera moves through a corridor in real perspective, painted far to near", async () => {
  const css = read(STYLES);
  const top = rules(css);
  assert.match(top.get(".space"), /perspective:\s*\d+px/);
  const { AppEntranceMotion } = await loadComponent();
  const markup = renderToStaticMarkup(React.createElement(AppEntranceMotion));
  const planes = [...markup.matchAll(/class="plane (\w+)"/g)].map((match) => match[1]);
  assert.deepEqual(planes, ["doorPlane", "frame4", "frame3", "frame2", "frame1", "brandPlane"]);
  const depth = (plane) => keyframeZ(css, animationLayers(top.get(`.${plane}`))[0].name);
  const starts = planes.slice(0, 5).map((plane) => depth(plane)[0]);
  assert.deepEqual([...starts].sort((a, b) => a - b), starts, "the frames paint in depth order");
  for (const plane of planes) {
    const [from, to] = depth(plane);
    assert.ok(to > from, `${plane} comes toward the camera`);
    assert.ok(to < 1000, `${plane} never reaches the camera plane`);
  }
});

test("every plane that nears the camera fades first, and the doorway hands over to the canvas before the stage lifts", () => {
  const css = read(STYLES);
  const top = rules(css);
  const exit = animationLayers(top.get(".layer")).find((layer) => layer.name === "layer-exit");
  for (const plane of ["frame1", "frame2", "frame3", "frame4", "brandPlane"]) {
    const [dolly, pass] = animationLayers(top.get(`.${plane}`));
    assert.equal(pass.name, "pass", `${plane} fades as it passes`);
    assert.equal(pass.end, dolly.end, `${plane} is gone when it stops moving`);
    assert.ok(dolly.end <= exit.start, `${plane} finishes before the stage lifts`);
  }
  const door = animationLayers(top.get(".doorPlane"))[0];
  const wash = animationLayers(top.get(".wash"))[0];
  assert.ok(wash.end <= door.end && door.end <= exit.start, "the canvas covers the view before the stage lifts");
  assert.match(css, /@keyframes pass\s*\{\s*to\s*\{\s*opacity:\s*0;/);
  assert.doesNotMatch(css, /filter:|blur\(/, "no blur");
});
