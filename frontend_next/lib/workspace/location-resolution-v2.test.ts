import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { interpretLocationResolution } from "./location-confirmation.ts";
// @ts-expect-error Native TS runner extension.
import { locationConfirmationCopy } from "./location-confirmation-copy.ts";

/** Gate L1-1: Google-first candidates, administrative fail-closed, bounded choice. */
const HAN = /[㐀-鿿]/;

test("resolver: wrong-district candidate is shown as blocked and never confirmable", () => {
  const result = interpretLocationResolution({ status: "unresolved", source: "none", confidence: "unknown", latitude: null, longitude: null, resolution_reason: "administrative_mismatch",
    candidates: [{ source: "google", formatted_address: "238台灣新北市樹林區中正路191號", latitude: 24.99, longitude: 121.42, county: "新北市", district: "樹林區", postal_code: "238", place_id: "x", admin_check: "district_mismatch", confirmable: false, block_reason: "administrative_mismatch" }] }, "新北市新莊區中正路191號");
  assert.equal(result.kind, "blocked");
  assert.equal(result.reason, "administrative_mismatch");
  assert.equal(result.rejected?.[0].district, "樹林區");
  assert.equal("candidate" in result, false);
});

test("resolver: multiple plausible Google candidates require an explicit choice", () => {
  const base = { source: "google", admin_check: "county_unverified", confirmable: true, block_reason: null, place_id: null };
  const result = interpretLocationResolution({ status: "ambiguous", source: "google", confidence: "unknown", latitude: null, longitude: null, resolution_reason: "multiple_candidates", candidates: [
    { ...base, formatted_address: "110台灣臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, county: "臺北市", district: "信義區", postal_code: "110" },
    { ...base, formatted_address: "201台灣基隆市信義區市府路1號", latitude: 25.13, longitude: 121.75, county: "基隆市", district: "信義區", postal_code: "201" },
    { ...base, formatted_address: "台灣臺北市大安區市府路1號", latitude: 25.03, longitude: 121.54, county: "臺北市", district: "大安區", postal_code: null },
  ] }, "信義區市府路1號");
  assert.equal(result.kind, "choice");
  assert.deepEqual(result.candidates.map((c: { county: string | null }) => c.county), ["臺北市", "基隆市"], "a candidate contradicting the typed district is dropped");
  assert.ok(result.candidates.every((c: { countyUnverified?: boolean }) => c.countyUnverified === true));
});

test("resolver: accepted candidate carries postal code but never parcel identity", () => {
  const result = interpretLocationResolution({ status: "resolved", source: "google", confidence: "high", latitude: 25.0375, longitude: 121.5637, county: "臺北市", district: "信義區", postal_code: "110", formatted_address: "110台灣臺北市信義區市府路1號" }, "臺北市信義區市府路1號");
  assert.equal(result.kind, "candidate");
  assert.equal(result.candidate.postalCode, "110");
  assert.equal(result.candidate.countyUnverified, undefined);
});

for (const locale of ["zh-TW", "en", "ja", "ko"]) test(`locationConfirmationCopy: ${locale} covers every key with real copy`, () => {
  const catalogue = locationConfirmationCopy as Record<string, Record<string, string>>;
  assert.deepEqual(Object.keys(catalogue[locale]).sort(), Object.keys(catalogue["zh-TW"]).sort());
  for (const [key, text] of Object.entries(catalogue[locale])) {
    assert.ok(text.trim().length > 0, `${locale}.${key}`);
    assert.doesNotMatch(text, /(?:administrative_mismatch|district_mismatch|address_mismatch|low_precision)/, `${locale}.${key} leaks a raw key`);
    if (locale === "en" || locale === "ko") assert.doesNotMatch(text, HAN, `${locale}.${key} contains Chinese`);
  }
});
