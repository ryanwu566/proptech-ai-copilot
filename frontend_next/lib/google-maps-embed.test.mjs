import assert from "node:assert/strict";
import test from "node:test";

import {
  GOOGLE_MAPS_EMBED_ORIGIN,
  GOOGLE_MAP_ZOOM,
  GOOGLE_STREET_VIEW_RADIUS_METRES,
  buildGoogleMapsEmbedUrls,
} from "./google-maps-embed.ts";

const BROWSER_KEY = "browser-key-for-tests";

test("builds fixed view and streetview URLs from accepted coordinates", () => {
  const urls = buildGoogleMapsEmbedUrls({
    browserKey: BROWSER_KEY,
    latitude: 25.033,
    longitude: 121.5654,
  });

  assert.ok(urls);
  const map = new URL(urls.mapUrl);
  const streetView = new URL(urls.streetViewUrl);

  assert.equal(map.origin, GOOGLE_MAPS_EMBED_ORIGIN);
  assert.equal(map.pathname, "/maps/embed/v1/view");
  assert.deepEqual(Object.fromEntries(map.searchParams), {
    key: BROWSER_KEY,
    center: "25.033,121.5654",
    zoom: String(GOOGLE_MAP_ZOOM),
    maptype: "roadmap",
  });
  assert.equal(map.searchParams.has("q"), false);

  assert.equal(streetView.origin, GOOGLE_MAPS_EMBED_ORIGIN);
  assert.equal(streetView.pathname, "/maps/embed/v1/streetview");
  assert.deepEqual(Object.fromEntries(streetView.searchParams), {
    key: BROWSER_KEY,
    location: "25.033,121.5654",
    radius: String(GOOGLE_STREET_VIEW_RADIUS_METRES),
  });
});

test("returns no Google URLs when the browser key is absent", () => {
  assert.equal(buildGoogleMapsEmbedUrls({ browserKey: "", latitude: 25.033, longitude: 121.5654 }), null);
  assert.equal(buildGoogleMapsEmbedUrls({ browserKey: "   ", latitude: 25.033, longitude: 121.5654 }), null);
});

test("rejects non-finite and out-of-range coordinates", () => {
  for (const [latitude, longitude] of [
    [Number.NaN, 121.5654],
    [Number.POSITIVE_INFINITY, 121.5654],
    [25.033, Number.NEGATIVE_INFINITY],
    [90.000001, 121.5654],
    [-90.000001, 121.5654],
    [25.033, 180.000001],
    [25.033, -180.000001],
  ]) {
    assert.equal(buildGoogleMapsEmbedUrls({ browserKey: BROWSER_KEY, latitude, longitude }), null);
  }
});

test("does not accept caller-controlled URLs, modes, addresses, or query parameters", () => {
  const attackerInput = {
    browserKey: BROWSER_KEY,
    latitude: 25.033,
    longitude: 121.5654,
    url: "https://attacker.invalid/embed",
    mode: "directions",
    address: "raw user address",
    q: "caller-controlled query",
    zoom: 1,
    radius: 999999,
  };

  const urls = buildGoogleMapsEmbedUrls(attackerInput);
  assert.ok(urls);
  assert.equal(urls.mapUrl.includes("attacker.invalid"), false);
  assert.equal(urls.mapUrl.includes("raw+user+address"), false);
  assert.equal(urls.mapUrl.includes("caller-controlled"), false);
  assert.equal(new URL(urls.mapUrl).searchParams.get("zoom"), String(GOOGLE_MAP_ZOOM));
  assert.equal(new URL(urls.streetViewUrl).searchParams.get("radius"), String(GOOGLE_STREET_VIEW_RADIUS_METRES));
});
