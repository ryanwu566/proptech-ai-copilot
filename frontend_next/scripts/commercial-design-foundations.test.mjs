import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function customProperties(css) {
  return new Map(
    [...css.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)].map((match) => [match[1], match[2].trim()]),
  );
}

function contrastRatio(first, second) {
  const luminance = (hex) => {
    const channels = hex.slice(1).match(/.{2}/g).map((value) => Number.parseInt(value, 16) / 255);
    const linear = channels.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  };
  const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

function dataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
}

function transpile(relativePath) {
  const sourcePath = path.join(root, relativePath);
  const result = ts.transpileModule(fs.readFileSync(sourcePath, "utf8"), {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: sourcePath,
    reportDiagnostics: true,
  });
  const errors = (result.diagnostics ?? []).filter((item) => item.category === ts.DiagnosticCategory.Error);
  assert.equal(errors.length, 0, ts.formatDiagnostics(errors, {
    getCanonicalFileName: (name) => name,
    getCurrentDirectory: () => root,
    getNewLine: () => "\n",
  }));
  return result.outputText;
}

const jsxRuntimeUrl = import.meta.resolve("react/jsx-runtime");
const reactUrl = import.meta.resolve("react");
const typesUrl = dataModule(transpile("components/design-system/types.ts"));
const asyncStateRoleUrl = dataModule(transpile("lib/commercial/async-state-role.ts"));
const commercialStateUrl = dataModule(transpile("lib/commercial/state.ts").replaceAll('"./async-state-role.ts"', JSON.stringify(asyncStateRoleUrl)));

async function componentModule(relativePath) {
  const source = transpile(relativePath)
    .replaceAll('"react/jsx-runtime"', JSON.stringify(jsxRuntimeUrl))
    .replaceAll('"react"', JSON.stringify(reactUrl))
    .replaceAll('"./types"', JSON.stringify(typesUrl))
    .replaceAll('"@/lib/commercial/state"', JSON.stringify(commercialStateUrl))
    .replaceAll('"@/lib/commercial/async-state-role"', JSON.stringify(asyncStateRoleUrl));
  return import(dataModule(source));
}

test("commercial tokens expose the approved spacing, radius, motion, and layout scales", () => {
  const tokens = customProperties(read("app/design-tokens.css"));
  const expected = {
    "--space-1": "0.25rem",
    "--space-4": "1rem",
    "--radius-control": "0.375rem",
    "--radius-panel": "0.5rem",
    "--radius-dialog": "0.75rem",
    "--duration-feedback": "120ms",
    "--duration-standard": "180ms",
    "--duration-panel": "240ms",
    "--width-content": "90rem",
    "--width-reading": "60rem",
    "--width-gis": "105rem",
    "--control-standard": "2.5rem",
    "--control-touch": "2.75rem",
  };
  for (const [name, value] of Object.entries(expected)) assert.equal(tokens.get(name), value, name);
});

test("commercial tokens provide every generic visual role without domain-specific safety semantics", () => {
  const css = read("app/design-tokens.css");
  const tokens = customProperties(css);
  for (const role of ["neutral", "information", "warning", "error", "success", "disabled"]) {
    assert.ok(tokens.has(`--status-${role}`), `missing ${role} foreground`);
    assert.ok(tokens.has(`--status-${role}-surface`), `missing ${role} surface`);
    assert.ok(tokens.has(`--status-${role}-border`), `missing ${role} border`);
  }
  assert.doesNotMatch(css, /safe-property|recommended-investment|low-hazard/i);
});

test("action, focus, control boundary, and status text tokens meet WCAG contrast minima", () => {
  const tokens = customProperties(read("app/design-tokens.css"));
  assert.ok(contrastRatio(tokens.get("--action"), tokens.get("--surface-primary")) >= 4.5, "primary action text/background");
  assert.ok(contrastRatio(tokens.get("--focus"), tokens.get("--surface-primary")) >= 3, "focus on primary surface");
  assert.ok(contrastRatio(tokens.get("--focus"), tokens.get("--canvas")) >= 3, "focus on canvas");
  assert.ok(contrastRatio(tokens.get("--border-strong"), tokens.get("--surface-primary")) >= 3, "control boundary");
  for (const role of ["neutral", "information", "warning", "error", "success"]) {
    assert.ok(contrastRatio(tokens.get(`--status-${role}`), tokens.get(`--status-${role}-surface`)) >= 4.5, `${role} text`);
  }
});

test("foundation entry points exist for controls, states, structures, and analytical frames", () => {
  const files = [
    "components/design-system/button.tsx",
    "components/design-system/field.tsx",
    "components/design-system/status-label.tsx",
    "components/design-system/message.tsx",
    "components/design-system/async-state.tsx",
    "components/design-system/section.tsx",
    "components/design-system/summary-strip.tsx",
    "components/design-system/disclosure.tsx",
    "components/design-system/data-table.tsx",
    "components/design-system/chart-frame.tsx",
    "components/design-system/map-frame.tsx",
    "components/design-system/navigation.tsx",
  ];
  for (const file of files) assert.ok(fs.statSync(path.join(root, file)).isFile(), file);
  const implementation = files.map(read).join("\n");
  assert.doesNotMatch(implementation, /(emerald|amber|rose|violet|cyan|#[0-9a-f]{3,8})/i);
});

test("global styles import tokens and provide visible focus, numeric grouping, and reduced motion", () => {
  const css = read("app/globals.css");
  assert.match(css, /@import\s+["']\.\/design-tokens\.css["'];/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /font-variant-numeric:\s*tabular-nums lining-nums/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test("icon-only buttons reject an inaccessible missing name", async () => {
  const { CommercialButton } = await componentModule("components/design-system/button.tsx");
  assert.throws(
    () => renderToStaticMarkup(React.createElement(CommercialButton, { iconOnly: true }, "×")),
    /accessible name/i,
  );
  const markup = renderToStaticMarkup(React.createElement(CommercialButton, { iconOnly: true, "aria-label": "Close" }, "×"));
  assert.match(markup, /aria-label="Close"/);
});

test("scrollable data tables expose a named keyboard-focusable region", async () => {
  const { DataTable } = await componentModule("components/design-system/data-table.tsx");
  const markup = renderToStaticMarkup(React.createElement(DataTable, { caption: "Comparable sales" }, React.createElement("tbody")));
  assert.match(markup, /role="region"/);
  assert.match(markup, /aria-label="Comparable sales"/);
  assert.match(markup, /tabindex="0"/i);
  assert.match(markup, /<caption>Comparable sales<\/caption>/);
  assert.throws(
    () => renderToStaticMarkup(React.createElement(DataTable, { caption: "Comparable sales", responsiveStrategy: "stack" }, React.createElement("tbody"))),
    /only supports the scroll strategy/i,
  );
});

test("field errors remain associated with the labeled control", async () => {
  const { Field, Input } = await componentModule("components/design-system/field.tsx");
  const markup = renderToStaticMarkup(React.createElement(Field, {
    label: "Asking price",
    helperText: "Enter ten-thousands of NTD",
    errorText: "A price is required",
    required: true,
  }, React.createElement(Input, { name: "price" })));
  const inputId = markup.match(/<input[^>]*\sid="([^"]+)"/)?.[1];
  assert.ok(inputId);
  assert.match(markup, new RegExp(`<label[^>]*for="${inputId}"`));
  assert.match(markup, /aria-invalid="true"/);
  assert.match(markup, /aria-required="true"/);
  assert.match(markup, /<input[^>]*required=""/);
  assert.match(markup, /aria-describedby="[^"]+helper [^"]+error"/);
  assert.match(markup, /role="alert"/);
});

test("unit input exposes its visible unit to assistive technology", async () => {
  const { UnitInput } = await componentModule("components/design-system/field.tsx");
  const markup = renderToStaticMarkup(React.createElement(UnitInput, { suffix: "萬元", unitLabel: "金額單位：萬元", name: "price" }));
  const descriptionId = markup.match(/aria-describedby="([^"]+)"/)?.[1];
  assert.ok(descriptionId);
  assert.match(markup, new RegExp(`<span[^>]*id="${descriptionId}"[^>]*>金額單位：萬元<\\/span>`));
});

test("status roles include visible wording and a redundant icon", async () => {
  const { StatusLabel } = await componentModule("components/design-system/status-label.tsx");
  const markup = renderToStaticMarkup(React.createElement(StatusLabel, { semanticRole: "success" }, "Verification completed"));
  assert.match(markup, /data-visual-role="success"/);
  assert.match(markup, /aria-hidden="true">✓/);
  assert.match(markup, />Verification completed</);
});

test("async states render the canonical commercial semantic role", async () => {
  const { AsyncState } = await componentModule("components/design-system/async-state.tsx");
  const expectedRoles = {
    not_started: "neutral",
    input_required: "warning",
    no_match: "neutral",
    no_coverage: "warning",
    unavailable: "warning",
    unsupported: "disabled",
    error: "error",
    loading: "information",
  };

  for (const [kind, role] of Object.entries(expectedRoles)) {
    const markup = renderToStaticMarkup(React.createElement(AsyncState, { kind, title: kind }));
    assert.match(markup, new RegExp(`ds-role-${role}(?:\\s|\")`), `${kind} should render ${role}`);
  }
});

test("navigation links preserve identification and accessibility attributes", async () => {
  const { NavigationItem } = await componentModule("components/design-system/navigation.tsx");
  const markup = renderToStaticMarkup(React.createElement(NavigationItem, {
    href: "/cases",
    id: "saved-cases",
    "aria-label": "Saved cases",
    "aria-describedby": "case-help",
    current: true,
  }, "Cases"));
  assert.match(markup, /href="\/cases"/);
  assert.match(markup, /id="saved-cases"/);
  assert.match(markup, /aria-label="Saved cases"/);
  assert.match(markup, /aria-describedby="case-help"/);
  assert.match(markup, /aria-current="page"/);
});
