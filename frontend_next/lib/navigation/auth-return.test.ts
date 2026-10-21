import assert from "node:assert/strict";
import { test } from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { authEntryHref, safeAuthReturn } from "./auth-return.ts";

for (const path of ["/", "/cases", "/compare", "/account", "/places", "/preferences", "/cases/case-a/risk", "/cases/case-a/finance", "/cases/case-a/decision-room", "/cases/case-a/evidence"]) {
  test(`accepts app destination ${path}`, () => assert.equal(safeAuthReturn(path), path));
}
for (const value of [null, "", "https://evil.test", "//evil.test", "javascript:alert(1)", "%2F%2Fevil.test", "%252F%252Fevil.test", "/%2fevil.test", "/\\evil.test", "\\\\evil.test", "/cases/%5cevil/risk", "/cases/%2f%2fevil/risk", "/cases/../risk", "/cases/%2e%2e/risk", "/cases/case-a/unknown", "/login", "/signup", "/api/redirect", " /compare", "/compare\n", "/compare?next=https://evil.test", "/compare#//evil.test", "https:/\\evil.test"]) {
  test(`rejects unsafe or non-workflow destination ${JSON.stringify(value)}`, () => assert.equal(safeAuthReturn(value), null));
}
test("builds auth links only with safe return intent", () => {
  assert.equal(authEntryHref("login", "/cases/case-a/risk"), "/login?next=%2Fcases%2Fcase-a%2Frisk");
  assert.equal(authEntryHref("signup", "//evil.test"), "/signup");
  assert.equal(authEntryHref("signup", null), "/signup");
});
test("rejects control characters even after a valid case path", () => {
  assert.equal(safeAuthReturn("/cases/case-a/risk\n"), null);
});
test("preserves Compare selection and supported field view only", () => {
  assert.equal(safeAuthReturn("/compare?cases=case-a,case-b&fields=all"), "/compare?cases=case-a,case-b&fields=all");
  assert.equal(safeAuthReturn("/compare?cases=case-a%2Ccase-b"), "/compare?cases=case-a,case-b");
  for (const value of ["/compare?cases=https://evil.test", "/compare?cases=%252f%252fevil.test", "/compare?fields=//evil.test", "/compare?cases=a&cases=b", "/compare?next=/cases", "/compare?cases=a,b,c,d,e", "/compare?cases=a,a"]) assert.equal(safeAuthReturn(value), null);
});
