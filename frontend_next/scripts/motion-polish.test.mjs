import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");

const OPT_IN = "@media screen and (prefers-reduced-motion: no-preference)";
// Staged reveals added on top of the case-route column enter; each file owns its keyframes.
const STAGED = {
  "components/workspace/workspace-shell.module.css": ["case-fade", "case-settle"],
  "components/workspace/overview/overview-view.module.css": ["brief-group"],
  "components/evidence/evidence.module.css": ["compare-settle", "compare-fade", "report-sheet"],
  "components/page-help/page-help.module.css": ["help-sheet", "help-sheet-rise", "help-fade", "help-settle", "help-land", "help-land-diamond"],
};

/** Every top-level `@media <query>` block body with that exact query. */
function mediaBlocks(css, query) {
  const blocks = [];
  for (let start = css.indexOf(query); start !== -1; start = css.indexOf(query, start + 1)) {
    const open = css.indexOf("{", start);
    let depth = 0;
    for (let index = open; index < css.length; index += 1) {
      if (css[index] === "{") depth += 1;
      if (css[index] === "}" && --depth === 0) { blocks.push(css.slice(open + 1, index)); break; }
    }
  }
  return blocks;
}

function keyframes(css, name) {
  const match = css.match(new RegExp(`@keyframes ${name}\\s*\\{([\\s\\S]*?\\})\\s*\\}`));
  assert.ok(match, `missing @keyframes ${name}`);
  return match[1];
}

test("motion tokens define one settle duration, one stagger step and one rise distance", () => {
  const tokens = read("app/design-tokens.css");
  assert.match(tokens, /--duration-settle:\s*360ms;/);
  assert.match(tokens, /--motion-stagger:\s*40ms;/);
  assert.match(tokens, /--motion-rise:\s*8px;/);
});

for (const [file, names] of Object.entries(STAGED)) {
  test(`${file}: staged reveals are screen-only, opt-in, compositor-only and finite`, () => {
    const css = read(file);
    const optIn = mediaBlocks(css, OPT_IN).join("\n");
    for (const name of names) {
      for (const [, property] of keyframes(css, name).matchAll(/([a-z-]+)\s*:/g)) {
        assert.ok(["opacity", "transform"].includes(property), `${name} animates ${property}`);
      }
      // Used only inside the opt-in block, so reduced motion and print render still.
      const uses = [...css.matchAll(new RegExp(`animation(?:-name)?:[^;]*\\b${name}\\b`, "g"))].length;
      const optInUses = [...optIn.matchAll(new RegExp(`animation(?:-name)?:[^;]*\\b${name}\\b`, "g"))].length;
      assert.ok(uses > 0, `${name} is unused`);
      assert.equal(optInUses, uses, `${name} is used outside ${OPT_IN}`);
    }
    assert.doesNotMatch(optIn, /infinite|alternate/);
    // Delays stay inside a short sequence: at most five stagger steps.
    for (const [, steps] of optIn.matchAll(/calc\((\d+) \* var\(--motion-stagger\)\)/g)) assert.ok(Number(steps) <= 5, `${steps} stagger steps`);
  });
}

test("Compare columns share one entrance so no case is shown first", () => {
  const optIn = mediaBlocks(read("components/evidence/evidence.module.css"), OPT_IN).join("\n");
  assert.match(optIn, /\.table thead th, \.mobileHeader \{ animation: compare-settle [^;]*; \}/);
  assert.doesNotMatch(optIn, /thead th:nth-|mobileHeader:nth-|th:first-child[^{]*\{[^}]*animation/);
});

test("only the primary action lifts on hover, never under reduced motion or while pressed", () => {
  const tokens = read("app/design-tokens.css");
  const lift = mediaBlocks(tokens, "@media (hover: hover) and (prefers-reduced-motion: no-preference)").join("\n");
  assert.match(lift, /\.ds-button--primary:not\(:disabled\):not\(\[aria-disabled="true"\]\):not\(:active\):hover \{ transform: translateY\(-1px\);/);
  assert.doesNotMatch(lift, /ds-button--(secondary|tertiary|destructive)/);
});
