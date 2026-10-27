import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { formatLocationDistance, formatLocationDuration, locationViewCopy } from "./location-view-copy.ts";
// @ts-expect-error Native TS runner extension.
import { commuteRouteCopy } from "../commute-route-copy.ts";
// @ts-expect-error Native TS runner extension.
import { locationConfirmationCopy } from "./location-confirmation-copy.ts";
// @ts-expect-error Native TS runner extension.
import { formatDistance, formatDuration } from "../commercial/formatters.ts";

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const HAN = /[㐀-鿿]/;
const KANA = /[぀-ヿ]/;
const HANGUL = /[가-힯]/;
const RAW = /\b(google_routes|google_places|risk_facilities_\w+|property_identity_mismatch|successful_query|reason_code|village_code)\b/;

for (const [name, catalogue] of [["Location view", locationViewCopy], ["Destination route", commuteRouteCopy]] as const) {
  test(`${name} copy is complete in four locales with no mixed scripts or raw keys`, () => {
    const keys = Object.keys(catalogue["zh-TW"]).sort();
    for (const locale of LOCALES) {
      const entries = Object.entries(catalogue[locale] as Record<string, string>);
      assert.deepEqual(entries.map(([key]) => key).sort(), keys, `${locale} keys`);
      for (const [key, value] of entries) {
        assert.ok(value.trim(), `${locale}.${key} is empty`);
        assert.doesNotMatch(value, RAW, `${locale}.${key} exposes a raw key`);
        if (locale === "en") assert.ok(!HAN.test(value) && !KANA.test(value) && !HANGUL.test(value), `en.${key}: ${value}`);
        if (locale === "ko") assert.ok(!HAN.test(value) && !KANA.test(value), `ko.${key}: ${value}`);
        if (locale === "ja") assert.ok(!HANGUL.test(value), `ja.${key}: ${value}`);
        if (locale === "zh-TW") assert.ok(!KANA.test(value) && !HANGUL.test(value), `zh-TW.${key}: ${value}`);
      }
    }
  });
}

test("zh-TW confirmation copy uses Taiwan punctuation; Japanese keeps its own middle dot", () => {
  for (const [key, value] of Object.entries(locationConfirmationCopy["zh-TW"] as Record<string, string>)) assert.ok(!value.includes("・"), `zh-TW.${key}: ${value}`);
  assert.equal(locationConfirmationCopy["zh-TW"].badge_administrative_mismatch, "行政區不一致 · 不可確認");
  assert.equal(locationConfirmationCopy.ja.badge_administrative_mismatch, "行政区の不一致・確定不可");
});

test("route distance and duration localize; zh-TW output matches the shared formatter", () => {
  for (const metres of [0, 640, 999, 1_000, 8_100, 12_400]) assert.equal(formatLocationDistance(metres, "zh-TW"), formatDistance(metres));
  for (const minutes of [0, 23, 59, 60, 95, 120]) assert.equal(formatLocationDuration(minutes, "zh-TW"), formatDuration(minutes));
  assert.equal(formatLocationDistance(8_100, "en"), "8.1 km");
  assert.equal(formatLocationDistance(640, "ko"), "640 m");
  assert.equal(formatLocationDuration(23, "en"), "About 23 min");
  assert.equal(formatLocationDuration(95, "ja"), "1 時間 35 分");
  assert.equal(formatLocationDuration(120, "ko"), "2시간");
  // Unknown stays unknown, never zero.
  assert.equal(formatLocationDistance(null, "en"), "Not provided");
  assert.equal(formatLocationDuration(undefined, "ja"), "未提供");
});

test("legacy and caveat copy keeps its meaning in every locale", () => {
  assert.match(locationViewCopy.en.mapAttribution, /not a cadastral boundary/);
  assert.match(locationViewCopy.en.riskNoMatch, /does not mean it is safe/);
  assert.match(locationViewCopy.en.riskLimitation, /does not mean zero facilities or safety/);
  assert.match(locationViewCopy.en.legacyDescription, /do not make a property better/);
  for (const locale of LOCALES) assert.match(locationViewCopy[locale].savedWarnings, /\{\{count\}\}/);
});
