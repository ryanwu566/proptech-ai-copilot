import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { isPropertyWorkflow, setProductWorkflow } from "./product-workflow.ts";

test("only the supported property query opens the product workflow", () => {
  for (const search of ["", "?source=menu", "?workflow=", "?workflow=unknown", "?workflow=Property"]) {
    assert.equal(isPropertyWorkflow(search), false, search);
  }
  assert.equal(isPropertyWorkflow("?workflow=property"), true);
  assert.equal(isPropertyWorkflow("source=menu&workflow=property&tool=Market+Insight+Lite"), true);
});

test("setting workflow preserves the path, unrelated query values and hash", () => {
  const original = new URL("https://example.test/property/review?source=menu&tag=a%2Fb&tag=two#main-content");
  const next = setProductWorkflow(original.href, "property");
  assert.equal(next.href, "https://example.test/property/review?source=menu&tag=a%2Fb&tag=two&workflow=property#main-content");
  assert.equal(original.href, "https://example.test/property/review?source=menu&tag=a%2Fb&tag=two#main-content");
});

test("setting replaces workflow and removing it leaves other URL state intact", () => {
  assert.equal(setProductWorkflow("https://example.test/?workflow=unknown&source=menu&workflow=old#section", "property").href,
    "https://example.test/?workflow=property&source=menu#section");
  assert.equal(setProductWorkflow("https://example.test/?workflow=property&source=menu&workflow=old#section", null).href,
    "https://example.test/?source=menu#section");
  assert.equal(setProductWorkflow("https://example.test/review?workflow=property#section", null).href,
    "https://example.test/review#section");
  assert.equal(setProductWorkflow("https://example.test/review?source=menu#section", null).href,
    "https://example.test/review?source=menu#section");
});

test("workflow URL operations require no browser, storage or network access", () => {
  const names = ["window", "localStorage", "sessionStorage", "fetch", "XMLHttpRequest", "WebSocket"] as const;
  const descriptors = names.map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)] as const);
  try {
    for (const name of names) Object.defineProperty(globalThis, name, {
      configurable: true,
      get() { throw new Error(`Workflow URL operations must not access ${name}`); },
    });
    assert.equal(isPropertyWorkflow("?workflow=property&source=menu"), true);
    assert.equal(setProductWorkflow("https://example.test/?source=menu#main", "property").href,
      "https://example.test/?source=menu&workflow=property#main");
    assert.equal(setProductWorkflow("https://example.test/?workflow=property#main", null).href,
      "https://example.test/#main");
  } finally {
    for (const [name, descriptor] of descriptors) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else Reflect.deleteProperty(globalThis, name);
    }
  }
});
