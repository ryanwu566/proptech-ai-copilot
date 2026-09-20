import assert from "node:assert/strict";
import test from "node:test";

import nextConfig from "../next.config.mjs";

test("CSP permits only the required Google Embed iframe origin", async () => {
  const rules = await nextConfig.headers();
  const csp = rules[0].headers.find((header) => header.key === "Content-Security-Policy")?.value ?? "";

  assert.match(csp, /(?:^|; )frame-src https:\/\/www\.google\.com(?:;|$)/);
  assert.doesNotMatch(csp, /frame-src[^;]*(?:\*\.google|maps\.googleapis|googleusercontent)/);
});
