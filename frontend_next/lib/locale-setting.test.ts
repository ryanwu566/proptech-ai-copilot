import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native Node runner requires source extension.
import { readLocaleSetting, saveLocaleSetting } from "./locale-setting.ts";
test("all four locales persist and invalid settings use the default", () => {
  let value: string | null = null;
  const storage = { getItem: () => value, setItem: (_key: string, data: string) => { value = data; } };
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) { saveLocaleSetting(storage, locale); assert.equal(readLocaleSetting(storage), locale); }
  for (const invalid of ["{", '{"version":2,"locale":"en"}', '{"version":1,"locale":"xx"}']) { value = invalid; assert.equal(readLocaleSetting(storage), null); }
  assert.equal(readLocaleSetting({ getItem: () => { throw Error("denied"); } }), null);
  assert.doesNotThrow(() => saveLocaleSetting({ setItem: () => { throw Error("denied"); } }, "ja"));
});
